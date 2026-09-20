"""Offline operator-run ingestion for court reference datasets.

Reads crawl exports from outside the repo, validates, and atomically writes
canonical datasets:
  data/court_bond_schedule.json

Any validation FAIL aborts with nothing written (fail-closed).
Raw crawl output is never committed.

Usage:
  python -m scraper.ingest_court_content --bond-source ~/workspace/firecrawl-zips/structured/bond_schedule.json
"""
from __future__ import annotations

import argparse
import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

TIER_VOCAB = re.compile(r'^(\$[\d,]+ (@ 10%|\+ REVIEW)|O\.R\.|NO BOND)$')

# 12 codes with conflicting typical_bond values - pending re-extraction
CONFLICTING_CODES = {
    "2903.06", "4510.11", "2907.09", "2903.13", "2903.21",
    "2919.25", "2919.27", "2923.12", "2919.22", "2921.331",
    "2917.31", "2903.211",
}


def _normalize_tier(val: str) -> str:
    # Normalize "$5000 @ 10%" -> "$5,000 @ 10%" for consistent vocab check
    val = val.strip()
    # Fix missing comma in thousands: $5000 -> $5,000
    def _fix(m):
        num = m.group(1).replace(",", "")
        try:
            n = int(num)
            return f"${n:,}"
        except ValueError:
            return m.group(0)
    val = re.sub(r'\$(\d[\d,]*)', _fix, val)
    return val


def ingest_bond_schedule(source_path: Path, operator: str = "operator") -> dict:
    with open(source_path, encoding="utf-8") as f:
        raw = json.load(f)

    rows = raw.get("rows", [])
    special = raw.get("special", [])

    if len(rows) != 19:
        raise ValueError(f"B-1 count band FAIL: expected 19 rows, got {len(rows)}")

    # Validate tier vocabulary
    for r in rows:
        for key in ("in_county", "out_of_county", "out_of_state_no_address"):
            v = _normalize_tier(r.get(key, ""))
            if not TIER_VOCAB.match(v):
                raise ValueError(f"B-4 tier vocab FAIL: {r.get('offense')} {key}={r.get(key)!r} normalized={v!r}")
            # Write back normalized
            r[key] = v

    # Split special into components
    no_standard = []
    felony_notes = []
    general_notes = []

    for entry in special:
        section = entry.get("section", "")
        offense = entry.get("offense", "").strip()
        note = entry.get("note", "").strip()
        orc = entry.get("orc", "").strip()

        if section == "felony_note":
            if not offense:
                raise ValueError(f"B-2 felony_note missing offense: {entry}")
            felony_notes.append({"offense": offense, "orc": orc})
        elif section == "no_standard_bond":
            if offense == "MISDEMEANOR CHARGES WITHOUT STANDARD BONDS":
                # Section header artifact - drop from list, not a real offense
                continue
            if not offense and note:
                # Empty-offense rows are general notes, not offenses
                general_notes.append({"note": note})
                continue
            if offense and not orc and not note:
                # Header-like artifact already handled; anything else without orc/note is suspect
                # The EMU and interpretation notes have note field, handled above
                continue
            if offense:
                # True no-standard-bond offense - must have ORC except header which we dropped
                if not orc:
                    raise ValueError(f"B-2 no_standard_bond offense missing ORC: {offense}")
                no_standard.append({"offense": offense, "orc": orc})
            elif note:
                general_notes.append({"note": note})
        else:
            raise ValueError(f"B-2 unknown section: {section}")

    # Expected: 14 offenses + 2 felony notes + 3 general notes (EMU + 2 interpretation)
    if len(no_standard) != 14:
        raise ValueError(f"B-2 count FAIL: expected 14 no-standard offenses, got {len(no_standard)}")
    if len(felony_notes) != 2:
        raise ValueError(f"B-2 count FAIL: expected 2 felony notes, got {len(felony_notes)}")
    # general_notes should be 3: EMU + 2 interpretation notes
    if len(general_notes) != 3:
        raise ValueError(f"B-2 count FAIL: expected 3 general notes, got {len(general_notes)}: {general_notes}")

    # Check for SEXAUL typo preservation (stored verbatim, corrected at render)
    sexaul_rows = [r for r in rows if "SEXAUL" in r.get("offense", "")]
    if len(sexaul_rows) != 1:
        raise ValueError(f"B-2 SEXAUL quarantine FAIL: expected 1 row with typo, got {len(sexaul_rows)}")

    provenance = {
        "schema_version": "1.0",
        "source": raw.get("source", "bond_sched_latest.pdf (Standard Bond Schedule rev. 3/5/2026, hamiltoncountycourts.org)"),
        "crawl_date": "2026-09-20",
        "ingested_utc": datetime.now(timezone.utc).isoformat(),
        "ingested_by": operator,
        "counts": {
            "schedule_rows": len(rows),
            "no_standard_bond": len(no_standard),
            "felony_notes": len(felony_notes),
            "general_notes": len(general_notes),
        },
        "schedule_revision": "3/5/2026",
        "max_age_days": 365,
        "conflicting_typical_bond_codes": sorted(CONFLICTING_CODES),
        "conflicting_codes_status": "not_established_pending_reextraction",
    }

    dataset = {
        "_provenance": provenance,
        "rows": rows,
        "no_standard_bond": no_standard,
        "felony_notes": felony_notes,
        "general_notes": general_notes,
    }
    return dataset


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=str(path.parent), delete=False, suffix=".tmp") as tf:
        json.dump(data, tf, indent=2, ensure_ascii=False)
        tf.write("\n")
        tmp_name = tf.name
    Path(tmp_name).replace(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bond-source", required=True, help="Path to structured bond_schedule.json")
    ap.add_argument("--operator", default="operator", help="Operator name for provenance")
    ap.add_argument("--acknowledge-warnings", action="store_true", help="Acknowledge warnings and proceed")
    args = ap.parse_args()

    dataset = ingest_bond_schedule(Path(args.bond_source), operator=args.operator)
    out = DATA_DIR / "court_bond_schedule.json"
    _atomic_write(out, dataset)
    print(f"Wrote {out} with {dataset['_provenance']['counts']}")


if __name__ == "__main__":
    main()
