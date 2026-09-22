"""Non-HTML output functions for the JCStream static site.

Handles static file copying, JSON manifests, well-known files, and checksums.
Extracted from web/build.py for modularity.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scraper.models import Snapshot
from web.classify import (
    _primary_tier,
)
from web.shape import (
    _cached_offenses,
    _card_data_attrs,
    _primary_chapter,
    _primary_charge,
)

log = logging.getLogger("jcstream.site")

STATIC_DIR = Path(__file__).parent / "static"
PHOTOS_DIR = Path(__file__).resolve().parent.parent / "data" / "photos"


def _copy_static(out_dir: Path) -> None:
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, out_dir / "static", dirs_exist_ok=True)
    # Browsers always request /favicon.ico; GitHub Pages 404s without a root file.
    # The seal is a PNG; modern browsers accept it at this path, and <link rel=icon>
    # also points at the PNG under /static/img/.
    fav = STATIC_DIR / "img" / "hcjc-seal.png"
    if fav.exists():
        shutil.copy2(fav, out_dir / "favicon.ico")
        shutil.copy2(fav, out_dir / "apple-touch-icon.png")


def _copy_photos(out_dir: Path) -> None:
    # V8-F1/V9-L01: never silently skip. A missing/empty photo source means
    # every /photos/<n>.jpg reference 404s, so say so loudly at build time.
    if not PHOTOS_DIR.exists():
        log.warning(
            "photo source %s missing: booking-photo <img> references will 404; "
            "templates degrade via the main.js photo fallback",
            PHOTOS_DIR,
        )
        return
    if not any(PHOTOS_DIR.iterdir()):
        log.warning(
            "photo source %s is empty: booking-photo <img> references will 404",
            PHOTOS_DIR,
        )
        return
    shutil.copytree(PHOTOS_DIR, out_dir / "photos", dirs_exist_ok=True)


def _write_manifest(out_dir: Path, base_url: str) -> None:
    """Minimal web app manifest -- gives the bookmark a name/icon/theme.
    Deliberately `display: browser` (not a PWA): a stale cached jail roster
    would be misleading, so no service worker."""
    manifest = {
        "name": "JCStream -- Hamilton County, OH jail roster mirror",
        "short_name": "JCStream",
        "description": "Public-records mirror of the Hamilton County (Ohio) Justice Center inmate roster.",
        "start_url": (base_url or "") + "/",
        "scope": (base_url or "") + "/",
        "display": "browser",
        "background_color": "#14181f",
        "theme_color": "#14181f",
        "icons": [
            {
                "src": (base_url or "") + "/static/img/hcjc-seal-2x.png",
                "sizes": "72x72",
                "type": "image/png",
                "purpose": "any",
            }
        ],
    }
    (out_dir / "manifest.webmanifest").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _write_search_json(out_dir: Path, snapshot: Snapshot, offenses: dict | None = None) -> None:
    """Compact searchable index of the current roster -- useful for API
    consumers and as a base for a future client-side search UI.
    One row per inmate: n=name, c=primary offense category, t=tier, id,
    s=full card search text (all charge descriptions and ORC codes).

    The tier is user-facing data, so it resolves through the offenses dict
    like every other displayed tier (F-10-02).
    """
    if offenses is None:
        offenses = _cached_offenses()
    rows = []
    for inm in snapshot.inmates:
        tier = _primary_tier(inm, offenses)
        chap = _primary_chapter(inm)
        rows.append(
            {
                "n": inm.full_name,
                "s": _card_data_attrs(inm)["search"],
                "c": (chap["label"] if chap else _primary_charge(inm)) or "",
                "t": tier["kind"] if tier else "",
                "b": inm.booking_date or "",
                "id": inm.inmate_number,
            }
        )
    payload = {
        "generated_utc": snapshot.generated_utc,
        "count": len(rows),
        "rows": rows,
    }
    (out_dir / "search.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def _write_dispatches(out_dir: Path, points: list[dict], generated_utc: str = "") -> None:
    # C-3: pin generated_utc to the roster's vintage (passed by the caller)
    # instead of wall-clock now(). During a sustained HCSO outage the roster
    # is frozen, so a pure timestamp rewrite is pure commit churn -- a sweep
    # commit every cycle with no data change, and SHA256SUMS rewriting itself.
    # Falls back to now() when the caller passes nothing.
    payload = {
        "generated_utc": generated_utc
        or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(points),
        "points": points,
    }
    (out_dir / "dispatches.json").write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def _write_cname(out_dir: Path) -> None:
    """GitHub Pages custom-domain file. Written from JCSTREAM_CNAME so it
    survives the docs/ rebuild; skipped if the env var is empty."""
    domain = (os.environ.get("JCSTREAM_CNAME", "") or "").strip()
    if domain:
        (out_dir / "CNAME").write_text(domain + "\n", encoding="utf-8")


def _write_well_known(out_dir: Path, site_url: str, generated_utc: str) -> None:
    """robots.txt + .well-known/security.txt + humans.txt -- make the
    don't-amplify posture explicit at the protocol level and give crawlers /
    researchers a clear, no-fee contact point. RSS readers ignore robots.txt,
    so the feeds stay usable for people."""
    repo = os.environ.get("GITHUB_REPOSITORY", "AICincy/HCJC")
    issues = f"https://github.com/{repo}/issues"
    (out_dir / "robots.txt").write_text(
        "# JCStream mirrors public records and asks search engines not to index it\n"
        '# (every page also carries <meta name="robots" content="noindex">).\n'
        "# Feeds and raw data are linked from /data/ -- RSS readers don't honour\n"
        "# robots.txt, so subscriptions still work.\n"
        "User-agent: *\n"
        "Disallow: /\n",
        encoding="utf-8",
    )
    # C-3: base Expires on the passed-in generated_utc (roster vintage), not
    # wall-clock now(). security.txt is informational here, not a security
    # boundary; pinning it means a frozen roster produces a byte-stable file
    # instead of timestamp churn on every build.
    try:
        base = datetime.strptime(generated_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        base = datetime.now(timezone.utc)
    expires = (base + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
    wk = out_dir / ".well-known"
    wk.mkdir(parents=True, exist_ok=True)
    (wk / "security.txt").write_text(
        f"# JCStream is a static mirror of public records (ORC \u00a7149.43). For data\n"
        f"# corrections, sealing/expungement removal, or any security or privacy\n"
        f"# concern, open an issue -- there is never a fee.\n"
        f"Contact: {issues}\n"
        f"Expires: {expires}\n"
        f"Preferred-Languages: en\n" + (f"Canonical: {site_url}/.well-known/security.txt\n" if site_url else ""),
        encoding="utf-8",
    )
    (out_dir / "humans.txt").write_text(
        "/* PROJECT */\n"
        "  JCStream -- mirror of the Hamilton County, OH Justice Center inmate roster\n"
        f"  Site: {site_url or 'https://www.aretheyinjail.com'}\n"
        "  Source: https://github.com/AICincy/HCJC (MIT)\n"
        f"  Corrections / sealing / removal: {issues} -- no fee, ever\n"
        "\n/* DATA */\n"
        "  HCSO public inmate roster (ORC \u00a7149.43) + Cincinnati Open Data feeds\n"
        "  No historical archive -- records drop off when HCSO removes them\n"
        f"  Rebuilt on a best-effort schedule via GitHub Actions -- last build {generated_utc or chr(8212)}\n"
        "\n/* BUILT WITH */\n"
        "  Python -- Jinja2 -- httpx -- selectolax -- Pillow -- GitHub Pages\n",
        encoding="utf-8",
    )


def _write_checksums(out_dir: Path) -> None:
    """SHA-256 manifest of the published data files -- cheap tamper-evidence
    on top of the (already authenticated) git history. Not 'Web3'; just hygiene."""
    data_out = out_dir / "data"
    if not data_out.exists():
        return
    lines = []
    for f in sorted(data_out.glob("*.json")):
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        lines.append(f"{h}  {f.name}")
    if lines:
        (data_out / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
