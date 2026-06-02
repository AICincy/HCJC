"""Non-HTML output functions for the JCStream static site.

Handles static file copying, JSON manifests, well-known files, and checksums.
Extracted from web/build.py for modularity.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scraper.models import Snapshot
from web.classify import (
    _primary_tier,
)
from web.shape import (
    _primary_chapter,
    _primary_charge,
)

STATIC_DIR = Path(__file__).parent / "static"
PHOTOS_DIR = Path("data/photos")


def _copy_static(out_dir: Path) -> None:
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, out_dir / "static", dirs_exist_ok=True)


def _copy_photos(out_dir: Path) -> None:
    if PHOTOS_DIR.exists() and any(PHOTOS_DIR.iterdir()):
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
        "icons": [],
    }
    (out_dir / "manifest.webmanifest").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _write_search_json(out_dir: Path, snapshot: Snapshot) -> None:
    """Compact searchable index of the current roster -- useful for API
    consumers and as a base for a future client-side search UI.
    One row per inmate: n=name, c=primary offense category, t=tier, id."""
    rows = []
    for inm in snapshot.inmates:
        tier = _primary_tier(inm)
        chap = _primary_chapter(inm)
        rows.append(
            {
                "n": inm.full_name,
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


def _write_dispatches(out_dir: Path, points: list[dict]) -> None:
    payload = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
    issues = "https://github.com/AICincy/JCStream/issues"
    (out_dir / "robots.txt").write_text(
        "# JCStream mirrors public records and asks search engines not to index it\n"
        '# (every page also carries <meta name="robots" content="noindex">).\n'
        "# Feeds and raw data are linked from /data/ -- RSS readers don't honour\n"
        "# robots.txt, so subscriptions still work.\n"
        "User-agent: *\n"
        "Disallow: /\n",
        encoding="utf-8",
    )
    expires = (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
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
        "  Source: https://github.com/AICincy/JCStream (MIT)\n"
        f"  Corrections / sealing / removal: {issues} -- no fee, ever\n"
        "\n/* DATA */\n"
        "  HCSO public inmate roster (ORC \u00a7149.43) + Cincinnati Open Data feeds\n"
        "  No historical archive -- records drop off when HCSO removes them\n"
        f"  Rebuilt every ~20-45 minutes via GitHub Actions -- last build {generated_utc or chr(8212)}\n"
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
