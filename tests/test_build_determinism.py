"""Guards that committed ``docs/`` artifacts were produced by the deterministic build.

PR #503 (issue #502, merged as 5d90340) anchored the build clock to the roster
vintage so repeated builds of one snapshot are byte-identical. The fix was
correct but the ``docs/`` tree committed at that merge had been generated
*before* it landed -- at 01:07:24Z by 5790d1a16d -- so the branch-serve deploy
kept publishing pre-fix artifacts while every gate stayed green:

    docs/data/transparency_metrics.json
        computed_utc      2026-09-24T01:07:24Z   <- wall-clock at build time
        freshness_hours   1.5                    <- age of the docs build, not the roster
    data/current.json
        generated_utc     2026-09-23T23:35:42Z   <- the anchor the fix requires

Those disagree by construction under the anchored build, which makes the pair a
cheap stand-in for a full rebuild comparison. The HTML freshness probe could not
catch this: it reads the ``jcstream:generated-utc`` meta stamp, which was
correct, so 654 stale files published without tripping a single check.

Existing timeline tests monkeypatch ``_now_naive_est`` (see tests/test_shape.py),
which pins the clock rather than proving ``build()`` pins it -- so the wiring in
web/build.py is guarded here too.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import pytest

from web.shape import common as shape_common

REPO_ROOT = Path(__file__).resolve().parent.parent
CURRENT_JSON = REPO_ROOT / "data" / "current.json"
PUBLISHED_METRICS = REPO_ROOT / "docs" / "data" / "transparency_metrics.json"
PUBLISHED_SUMS = REPO_ROOT / "docs" / "data" / "SHA256SUMS"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _restore_build_clock():
    """Never leak an anchor into other tests; ``build()`` clears its own."""
    yield
    shape_common.set_build_now_from_utc(None)


def test_published_transparency_metrics_are_anchored_to_roster_vintage() -> None:
    """``computed_utc`` must equal the roster vintage, not a wall-clock build time.

    Under the Option B anchor these are identical by construction. A mismatch
    means ``docs/`` was built by pre-fix code and the published transparency
    page is reporting the age of the *build* as the age of the *roster*.
    """
    for path in (CURRENT_JSON, PUBLISHED_METRICS):
        assert path.is_file(), f"missing {path.relative_to(REPO_ROOT)}"

    vintage = _read_json(CURRENT_JSON)["generated_utc"]
    metrics = _read_json(PUBLISHED_METRICS)

    assert metrics["computed_utc"] == vintage, (
        f"docs/data/transparency_metrics.json was not built by the deterministic "
        f"build: computed_utc={metrics['computed_utc']} but the roster vintage is "
        f"{vintage}. Rebuild with `JCSTREAM_SITE_BASE_URL='' "
        f"JCSTREAM_CNAME=www.aretheyinjail.com python -m web.build` and commit docs/."
    )

    # Anchored to the vintage, both ages collapse to zero; a nonzero value is
    # the same stale-artifact signature expressed in hours.
    assert metrics["roster_age_hours"] == 0.0, (
        f"roster_age_hours={metrics['roster_age_hours']} implies a wall-clock build"
    )
    assert metrics["roster_generated_utc"] == vintage


def test_build_anchors_clock_to_snapshot_vintage() -> None:
    """``build()`` must anchor the clock before rendering and clear it after.

    Guards the wiring the timeline tests bypass by monkeypatching. Dropping the
    anchor call silently returns ``now_x`` / days-in-custody to wall-clock, so
    inmate pages drift ~0.1% per rebuild and never settle byte-identical.
    """
    source = (REPO_ROOT / "web" / "build.py").read_text(encoding="utf-8")

    assert re.search(
        r"set_build_now_from_utc\(\s*snapshot\.generated_utc", source
    ), "web/build.py must anchor the build clock to snapshot.generated_utc"

    # The anchor has to be set before the render call, not after it. Compare
    # against the invocation (indented, argument list) rather than the bare
    # symbol, whose first occurrence is the `def _render_build(` header above.
    anchor_at = source.index("set_build_now_from_utc(snapshot.generated_utc")
    render_at = source.index("        _render_build(env,")
    assert anchor_at < render_at, "clock anchor must be set before _render_build()"

    # And cleared on exit, or the anchor leaks into later builds/tests.
    clear_at = source.index("_clear_anchor(None)")
    assert clear_at > render_at, "clock anchor must be cleared after the render"


def test_anchored_clock_is_data_vintage_not_wall_clock() -> None:
    """The anchor must actually take effect and survive a wall-clock advance."""
    shape_common.set_build_now_from_utc("2026-09-23T23:35:42Z")
    first = shape_common._now_naive_est()

    # 23:35:42Z on 2026-09-23 is EDT (UTC-4), so naive Eastern 19:35:42.
    assert first == datetime(2026, 9, 23, 19, 35, 42)

    # Repeat calls are stable: no wall-clock component remains.
    assert shape_common._now_naive_est() == first

    # Clearing must resume wall-clock, which the empty-bootstrap path (no
    # vintage yet) relies on. Asserted by anchoring far in the past, clearing,
    # and requiring the clock to have moved off it -- timezone-independent.
    shape_common.set_build_now_from_utc("2000-06-01T12:00:00Z")
    stale = shape_common._now_naive_est()
    assert stale.year == 2000 and stale.month == 6, f"anchor ignored: {stale}"

    shape_common.set_build_now_from_utc(None)
    resumed = shape_common._now_naive_est()
    assert resumed.tzinfo is None, "consumers compare against naive local midnights"
    assert resumed.year > 2000, "clearing the anchor did not resume wall-clock"


def test_published_checksums_match_published_data() -> None:
    """``docs/data/SHA256SUMS`` must describe the ``docs/data/*.json`` actually committed.

    Note this would NOT have caught the 5d90340 stale-artifact publish: that
    tree was internally consistent, its manifest hashing the same pre-fix bytes
    it shipped (verified: both ``89f5e378...``). It guards the *adjacent* mode --
    a partial rebuild where ``data/`` advances but ``docs/`` is committed
    piecemeal, leaving the published set disagreeing with its own manifest.
    """
    assert PUBLISHED_SUMS.is_file(), "docs/data/SHA256SUMS missing"

    expected: dict[str, str] = {}
    for line in PUBLISHED_SUMS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, name = line.partition("  ")
        expected[name.strip()] = digest.strip()

    assert expected, "docs/data/SHA256SUMS is empty"

    data_dir = PUBLISHED_SUMS.parent
    actual = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(data_dir.glob("*.json"))
    }

    assert set(expected) == set(actual), (
        f"SHA256SUMS lists {sorted(set(expected) ^ set(actual))} inconsistently with "
        f"docs/data/*.json"
    )
    mismatched = sorted(n for n in expected if expected[n] != actual[n])
    assert not mismatched, (
        f"published data does not match its manifest: {mismatched}. "
        f"docs/ is a partial or stale rebuild; regenerate and commit it whole."
    )
