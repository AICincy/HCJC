"""Probe live HTML pages and fail when the deployed site is stale.

Every rendered page carries a machine-readable roster vintage stamp::

    <meta name="jcstream:generated-utc" content="2026-09-23T19:35:00Z">

The stamp is the ``generated_utc`` value in the candidate's
``data/current.json``.  The gate checks all of the following before it compares
ages:

* the tip snapshot and candidate HTML have the same, strict UTC vintage;
* the live response is a successful HTML response (not a redirect, JSON error,
  or an HTML page from before the marker rollout);
* the live vintage is no more than ``--max-lag-hours`` behind the tip; and
* the candidate is not older than live when ``--fail-on-live-newer`` is used.

The last check is deliberately opt-in for library/diagnostic use because a
checkout can legitimately lag a successful production deploy. The production
``live-parity.yml`` gate enables it: deploying a candidate made from an older
tip would regress the published data, so the deployment safety check fails
closed. A future-dated live stamp is reported as a warning rather than treated
as proof of freshness.

There is no recovery mode and no retry loop. This workflow only observes the
live site; a red run is the alert and no deploy is attempted.
"""

from __future__ import annotations

import argparse
import json
import re
import socket
import ssl
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

# A fractional part is valid ISO-8601 and is retained for precise boundary
# decisions.  The build normally emits whole seconds, but the probe must not
# silently truncate a microsecond-precision source timestamp.
_UTC_STAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
# Kept as a public compatibility name for callers that imported the old regex.
MARKER_RE = re.compile(
    r"<meta[^>]*name=[\"']jcstream:generated-utc[\"'][^>]*content=[\"']([^\"']*)[\"']",
    re.IGNORECASE,
)

# A timestamp this far in the future is more plausibly a tampered stamp or a
# bad clock than a real deploy.  It should be visible, but it must not be
# converted into a false "candidate regression" failure.
_FUTURE_TOLERANCE = timedelta(hours=24)
_SUSPICIOUSLY_OLD = datetime(2000, 1, 1, tzinfo=timezone.utc)


class _NoRedirect(HTTPRedirectHandler):
    """Make a redirect an observable HTTP failure instead of following it."""

    def redirect_request(self, req, fp, code, msg, headers, new):  # type: ignore[no-untyped-def]
        return None


# Module-level seam retained for tests and operator diagnostics that used to
# monkeypatch urllib's ``urlopen`` directly. It is backed by a no-redirect
# opener so a 3xx remains a failure.
urlopen = build_opener(_NoRedirect).open


class _StampParser(HTMLParser):
    """Extract marker values without depending on HTML attribute order."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.values: list[str | None] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return
        attributes = {key.lower(): value for key, value in attrs}
        if str(attributes.get("name") or "").lower() == "jcstream:generated-utc":
            self.values.append(attributes.get("content"))


def fetch(url: str, timeout: float) -> tuple[int, str, bytes]:
    """Fetch one page without following redirects.

    Keeping the return shape compatible with the original probe makes it easy
    for tests and on-call diagnostics to monkeypatch this boundary.
    """
    request = Request(url, headers={"User-Agent": "HCJC-live-parity/1.0", "Accept": "text/html"})
    with urlopen(request, timeout=timeout) as response:
        return response.status, response.headers.get("content-type", ""), response.read()


def _marker_values(html: str) -> list[str | None]:
    parser = _StampParser()
    try:
        parser.feed(html)
        parser.close()
    except (ValueError, TypeError):
        # Broken markup does not make the probe crash.  If the marker cannot
        # be recovered, the caller reports a missing stamp and fails closed.
        return []
    return parser.values


def extract_vintage(html: str) -> str | None:
    """Return the first non-empty freshness stamp, or ``None`` when absent.

    An empty ``content`` attribute counts as absent: a bootstrap build has no
    meaningful vintage to stamp.  Attribute order and case are irrelevant,
    which lets the probe inspect valid HTML emitted by an intermediary.
    """
    for value in _marker_values(html):
        if value:
            return value
    return None


def parse_stamp(stamp: str) -> datetime:
    """Parse the strict UTC stamp shape used by the live-parity contract.

    A bare timestamp, a space separator, and an offset-bearing timestamp are
    rejected.  The explicit ``Z`` suffix is the contract's timezone boundary;
    ``datetime.fromisoformat`` is used only after the regex has enforced it.
    """
    if not isinstance(stamp, str) or not _UTC_STAMP_RE.fullmatch(stamp):
        raise ValueError(f"not a strict ISO-8601 UTC stamp with Z suffix: {stamp!r}")
    try:
        return datetime.fromisoformat(stamp[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"invalid ISO-8601 UTC stamp {stamp!r}: {exc}") from exc


def load_tip_vintage(data_path: Path) -> str:
    """Read and validate the tip's roster vintage from ``data/current.json``."""
    snapshot = json.loads(data_path.read_text(encoding="utf-8"))
    stamp = snapshot["generated_utc"]
    if not isinstance(stamp, str) or not stamp:
        raise ValueError(f"generated_utc must be a non-empty string, got {stamp!r}")
    parse_stamp(stamp)
    return stamp


def _lag_hours(tip: datetime, live: datetime) -> float:
    """Return positive hours when live is older than tip."""
    return (tip - live).total_seconds() / 3600.0


def _is_suspicious_future(stamp: datetime, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    return stamp > now + _FUTURE_TOLERANCE


def _live_http_error(label: str, url: str, code: int) -> str:
    if code == 404:
        return f"{label}: live tree returned 404 from {url}; check domain/path or DNS"
    if code >= 500:
        return f"{label}: live tree returned {code} from {url}; check server health"
    if 300 <= code < 400:
        return f"{label}: live tree returned redirect HTTP {code} from {url}; expected the final HTML path"
    return f"{label}: live tree returned HTTP {code} from {url}"


def _live_network_error(label: str, exc: BaseException) -> str:
    reason = getattr(exc, "reason", exc)
    if isinstance(reason, (socket.timeout, TimeoutError)) or "timed out" in str(reason).lower():
        return f"{label}: live server unresponsive (timeout); probe timeout is enforced at the request boundary"
    if isinstance(reason, ssl.SSLError) or isinstance(exc, ssl.SSLError) or "ssl" in str(reason).lower():
        return f"{label}: TLS verification failed; check certificate or domain ({reason})"
    return f"{label}: live probe failed: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check that live HTML reflects a fresh deploy.")
    parser.add_argument("--site", default="https://www.aretheyinjail.com")
    parser.add_argument("--local", type=Path, default=Path("docs"))
    parser.add_argument("--data", type=Path, default=Path("data/current.json"))
    parser.add_argument(
        "--page",
        action="append",
        help="HTML path below the site root to probe (repeatable; default index.html)",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument(
        "--max-lag-hours",
        type=float,
        default=26.0,
        help="Fail when the live vintage lags the tip vintage by more than this many hours",
    )
    parser.add_argument(
        "--fail-on-live-newer",
        action="store_true",
        help="Fail when live is newer than the candidate/tip (production regression policy)",
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    if args.max_lag_hours < 0:
        parser.error("--max-lag-hours cannot be negative")

    pages = args.page or ["index.html"]
    errors: list[str] = []
    warnings: list[str] = []

    try:
        repo_stamp = load_tip_vintage(args.data)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"::error title=Live HTML freshness::cannot read tip vintage from {args.data}: {exc}")
        print(f"ERROR: cannot read tip vintage from {args.data}: {exc}")
        return 1
    repo_dt = parse_stamp(repo_stamp)

    for page in pages:
        label = f"/{page}"
        candidate_path = args.local / page
        try:
            candidate_html = candidate_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{label}: candidate build unreadable ({candidate_path}): {exc}")
            continue
        candidate_stamp = extract_vintage(candidate_html)
        if candidate_stamp is None:
            errors.append(
                f"{label}: candidate {candidate_path} carries no jcstream:generated-utc stamp; "
                "the build/template no longer stamps pages"
            )
            continue
        try:
            parse_stamp(candidate_stamp)
        except ValueError as exc:
            errors.append(f"{label}: candidate vintage malformed: {exc}")
            continue
        if candidate_stamp != repo_stamp:
            errors.append(
                f"{label}: candidate vintage {candidate_stamp} != tip vintage {repo_stamp} "
                "(build ran on stale or foreign data)"
            )
            continue

        url = args.site.rstrip("/") + "/" + page
        try:
            status, content_type, body = fetch(url, args.timeout)
        except HTTPError as exc:
            errors.append(_live_http_error(label, url, exc.code))
            continue
        except (socket.timeout, TimeoutError, ssl.SSLError) as exc:
            errors.append(_live_network_error(label, exc))
            continue
        except URLError as exc:
            errors.append(_live_network_error(label, exc))
            continue
        if status < 200 or status >= 300:
            errors.append(_live_http_error(label, url, status))
            continue
        if "html" not in content_type.lower():
            errors.append(f"{label}: Expected HTML; got Content-Type: {content_type or '(missing)'}")
            continue
        live_html = body.decode("utf-8", errors="replace")
        live_stamp = extract_vintage(live_html)
        if live_stamp is None:
            errors.append(
                f"{label}: live tree lacks freshness stamp; live HTML carries no "
                "jcstream:generated-utc marker (likely predates deployment of this feature)"
            )
            continue
        try:
            live_dt = parse_stamp(live_stamp)
        except ValueError as exc:
            errors.append(f"{label}: live vintage malformed: {exc}")
            continue

        lag_hours = _lag_hours(repo_dt, live_dt)
        future = _is_suspicious_future(live_dt)
        if future:
            warnings.append(
                f"{label}: live vintage {live_stamp} is suspiciously in the future "
                f"(lag {lag_hours:.2f} h); check stamp generation or clock skew"
            )
            # Do not let an obviously tampered/future stamp turn into a second
            # regression error. The future warning is the actionable result.
            continue
        if lag_hours > args.max_lag_hours:
            detail = (
                f"{label}: live HTML is stale: vintage {live_stamp} lags tip vintage {repo_stamp} "
                f"by {lag_hours:.5f} h (max {args.max_lag_hours:g} h); the Pages deploy looks broken"
            )
            if live_dt < _SUSPICIOUSLY_OLD:
                detail = (
                    f"{label}: Detected suspiciously old timestamp {live_stamp}; possible tampering "
                    f"or clock skew. Live HTML lags tip by {lag_hours:.5f} h."
                )
            errors.append(detail)
        elif lag_hours < 0:
            message = (
                f"{label}: live vintage {live_stamp} is newer than candidate/tip vintage {repo_stamp} "
                f"(lag {lag_hours:.2f} h; negative means live is newer)"
            )
            if args.fail_on_live_newer:
                errors.append(
                    f"Candidate data vintage ({candidate_stamp}) is older than live data ({live_stamp}); "
                    "this rebuild would regress content freshness. "
                    + message
                )
            else:
                warnings.append(message + "; checkout lagged the last deploy")
        else:
            print(f"  {label}: fresh (live {live_stamp}, tip {repo_stamp}, lag {lag_hours:.2f} h)")

    for warning in warnings:
        print(f"::warning title=Live HTML freshness::{warning}")
    if errors:
        for error in errors:
            print(f"::error title=Live HTML freshness::{error}")
        print(f"live HTML freshness failed: {len(errors)} error(s) across {len(pages)} page(s)")
        return 1
    print(
        f"live HTML freshness OK: {len(pages)} page(s) within {args.max_lag_hours:g} h "
        f"of the tip vintage {repo_stamp}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
