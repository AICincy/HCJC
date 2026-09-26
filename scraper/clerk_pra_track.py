"""Write the tracked PRA packet files committed on main."""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from scraper.clerk_pra import (
    LEGAL_BASIS,
    LEGAL_BASIS_EFFECTIVE,
    LEGAL_BASIS_LEGISLATION,
    LEGAL_BASIS_VERIFIED_UTC,
    STATUS_DRAFT,
    full_name,
    known_case_numbers,
    load_roster,
    normalize_folder_date,
    render_letter,
    render_readme,
    sanitize_filename_part,
)
from scraper.clerk_pra_docx import write_letter_docx

log = logging.getLogger(__name__)


def write_history(out_root: Path, folder_date: str) -> None:
    hist_path = Path("data/history.json")
    rows = json.loads(hist_path.read_text(encoding="utf-8")) if hist_path.exists() else []
    lines = [
        "# PRA roster historicals",
        "",
        "Daily HCSO roster counts from `data/history.json`.",
        "Letters regenerate from `data/current.json`.",
        "",
        "| Date | In custody | Booked 24h | Released 24h | Packet |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        day = row.get("date") or ""
        marker = f"[PACKET](./{day}/PACKET.md)" if day == folder_date else "\u2014"
        lines.append(
            f"| {day} | {row.get('count', '')} | {row.get('booked_24h', '')} | "
            f"{row.get('released_24h', '')} | {marker} |"
        )
    (out_root / "HISTORY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_tracked_packet(inmates, snapshot_date, folder_date, out_root: Path) -> Path:
    generated_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    folder = out_root / folder_date
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {}
    parts = [
        f"# Clerk PRA packet \u2014 {folder_date}",
        "",
        "Drafts only. Human send gate. JCStream never sends.",
        "",
    ]
    written = 0
    for inmate in inmates:
        inmate_number = str(inmate.get("inmate_number") or "").strip()
        name = full_name(inmate)
        if not inmate_number or not name:
            continue
        stem = (
            f"{sanitize_filename_part(inmate_number)}_"
            f"{sanitize_filename_part(inmate.get('last_name') or '')}_"
            f"{sanitize_filename_part(inmate.get('first_name') or '')}"
        )
        letter = render_letter(inmate, snapshot_date, generated_utc)
        parts.extend(["---", "", letter, ""])
        manifest[inmate_number] = {
            "full_name": name,
            "date_of_birth": (inmate.get("date_of_birth") or "").strip(),
            "booking_date": (inmate.get("booking_date") or "").strip(),
            "known_case_numbers": known_case_numbers(inmate),
            "letter_file": "PACKET.docx",
            "letter_anchor": stem,
            "generated_utc": generated_utc,
            "status": STATUS_DRAFT,
            "clerk_response": None,
        }
        written += 1
    packet_md = "\n".join(parts)
    (folder / "PACKET.md").write_text(packet_md, encoding="utf-8")
    write_letter_docx(folder / "PACKET.docx", packet_md)
    (folder / "README.md").write_text(render_readme(folder_date, written, generated_utc), encoding="utf-8")
    (folder / "manifest.json").write_text(
        json.dumps(
            {
                "packet": {
                    "folder_date": folder_date,
                    "generated_utc": generated_utc,
                    "generator": "scraper/clerk_pra_track.py",
                    "source_snapshot": f"data/current.json ({snapshot_date})",
                    "letter_count": written,
                    "legal_basis": LEGAL_BASIS,
                    "legal_basis_effective": LEGAL_BASIS_EFFECTIVE,
                    "legal_basis_legislation": LEGAL_BASIS_LEGISLATION,
                    "legal_basis_verified_utc": LEGAL_BASIS_VERIFIED_UTC,
                    "tracked_files": ["README.md", "manifest.json", "PACKET.md", "PACKET.docx"],
                    "status": STATUS_DRAFT,
                    "note": "Draft letters only. The human sender sends. JCStream never sends.",
                },
                "requests": manifest,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_history(out_root, folder_date)
    (out_root / "README.md").write_text(
        f"""# Clerk PRA packets

Draft ORC 149.43 request letters for Hamilton County Clerk of Courts.

- Human send gate. JCStream never sends.
- Dated folders stay on `main` as historicals.
- Tracked files per day: `README.md`, `manifest.json`, `PACKET.md`, `PACKET.docx`.

Latest packet: [`{folder_date}/PACKET.docx`](./{folder_date}/PACKET.docx)
Roster historicals: [`HISTORY.md`](./HISTORY.md)
""",
        encoding="utf-8",
    )
    log.info("wrote tracked packet (%d letters) to %s", written, folder)
    return folder


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Write tracked PRA packet files")
    parser.add_argument("--date", default=None)
    parser.add_argument("--out", type=Path, default=Path("pra_requests"))
    parser.add_argument("--roster", type=Path, default=Path("data/current.json"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not args.roster.exists():
        log.error("roster not found: %s", args.roster)
        return 2
    inmates, snapshot_date = load_roster(args.roster)
    try:
        folder_date = normalize_folder_date(args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    except ValueError as e:
        log.error("%s", e)
        return 2
    write_tracked_packet(inmates, snapshot_date or folder_date, folder_date, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
