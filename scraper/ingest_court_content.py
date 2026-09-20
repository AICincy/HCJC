"""Offline operator-run ingestion for court reference datasets.

Reads crawl exports from outside the repo, validates, and atomically writes
canonical datasets:
  data/court_bond_schedule.json
  data/court_judges.json

Any validation FAIL aborts with nothing written (fail-closed).
Raw crawl output is never committed.

Usage:
  python -m scraper.ingest_court_content --bond-source ~/workspace/firecrawl-zips/structured/bond_schedule.json
  python -m scraper.ingest_court_content --judges-source ~/workspace/firecrawl-zips/structured/judges.json
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


# ---------------------------------------------------------------------------
# Judges ingestion: judges.json -> data/court_judges.json
# ---------------------------------------------------------------------------

JUDGE_COURT_VOCAB = {"Common Pleas", "Municipal"}
EXPECTED_JUDGE_COUNT = 30

# The 5 auxiliary records Firecrawl bundles with the judge profiles:
# 1 "Municipal Judge Assignments" index page, 3 Janaya Trotter Bratton
# sub-pages (civil cases, criminal cases, civil case forms), 1 Samantha
# Silverstein civil-case-forms sub-page. True judge profiles are titled
# "Common Pleas Court Judge <name>" / "Municipal Court Judge <name>".
_AUX_TITLE_PAT = re.compile(
    r"judge assignments|civil case forms|(?:civil|criminal) cases",
    re.IGNORECASE,
)

_NAME_PREFIX_PAT = re.compile(
    r"^(common pleas (court )?judge|municipal (court )?judge)\s+", re.IGNORECASE
)

_PHONE_PAT = re.compile(r"^(\(\d{3}\) \d{3}-\d{4}|\d{3}-\d{3}-\d{4})$")
_FAX_DIGITS_PAT = re.compile(r"^\d{3}-\d{3}-\d{4}$")
_EMAIL_PAT = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")

# Markdown syntax stripped from bios before quarantine classification.
_MD_IMAGE_PAT = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK_PAT = re.compile(r"\[([^\]]*)\]\([^)]*\)")
# Plea-form download lists are procedure documents, not biographies.
_FORM_LIST_PAT = re.compile(
    r"\b(guilty plea|no[- ]contest plea|jury waiver|reagan tokes|alford)\b",
    re.IGNORECASE,
)
# A Common Pleas record whose bio describes Municipal Court service
# (career-progression bio text that was never updated).
_CP_ELECTED_MUNI_PAT = re.compile(
    r"elected to the Hamilton County Municipal Court", re.IGNORECASE
)
_TERMINAL_PUNCT = (".", "!", "?", '"', "'", ")", "]")

# Firecrawl caps the bio field at 600 chars (observed on the two genuinely
# truncated bios, Silverstein and McDowell, both cut mid-word at the cap).
_TRUNCATION_CAP = 600


def _is_auxiliary_record(rec: dict) -> bool:
    title = rec.get("page_title", "") or ""
    url = rec.get("url", "") or ""
    return bool(_AUX_TITLE_PAT.search(title) or _AUX_TITLE_PAT.search(url))


def _clean_judge_name(raw: object) -> str:
    name = _NAME_PREFIX_PAT.sub("", str(raw or "").strip()).strip()
    if not name:
        raise ValueError("J-3 empty judge name after prefix strip")
    if name.isupper():
        # The 4 ALL-CAPS records (Stefanou, Colliver, R. Bernard Mundy,
        # Rodney J. Harris): title-case to match HAMCO display names.
        name = name.title()
    return name


def _normalize_fax(raw: object) -> str:
    fax = str(raw or "").strip()
    if not fax:
        return ""
    # "(513) 946-5864" -> "513-946-5864": collapse the parenthesized
    # area code into dash form before stripping separators.
    fax = re.sub(r"^\((\d{3})\)\s*", r"\1-", fax)
    fax = re.sub(r"[()\s]", "", fax)
    if not _FAX_DIGITS_PAT.match(fax):
        raise ValueError(f"J-4 fax format FAIL: {raw!r}")
    return fax


def _clean_bio(raw: object) -> str:
    bio = str(raw or "")
    bio = _MD_IMAGE_PAT.sub("", bio)  # drop images entirely
    bio = _MD_LINK_PAT.sub(r"\1", bio)  # keep link text, drop URLs
    bio = bio.replace("\\*", "*")  # extraction-escaped emphasis
    bio = re.sub(r"[ \t]+", " ", bio)
    bio = re.sub(r"\n{3,}", "\n\n", bio)
    return bio.strip().rstrip("*").strip()


def _classify_bio(rec: dict) -> tuple[str, str]:
    """Return (cleaned_bio, bio_status) with bio_status in clean|needs_review|omitted."""
    raw = rec.get("bio") or ""
    bio = _clean_bio(raw)
    if not bio:
        return "", "omitted"
    if _FORM_LIST_PAT.search(bio):
        return bio, "needs_review"  # plea-form download list, not a bio
    if "zoom.us" in str(raw).lower():
        return bio, "needs_review"  # meeting link; needs human review
    if rec.get("court") == "Common Pleas" and _CP_ELECTED_MUNI_PAT.search(bio):
        return bio, "needs_review"  # bio describes Municipal service on a CP record
    # Truncation: field cap with no terminal punctuation (Silverstein,
    # McDowell both cut mid-word at the 600-char cap), or a single-char
    # final token.
    tokens = bio.split()
    truncated = (len(str(raw)) >= _TRUNCATION_CAP and not bio.endswith(_TERMINAL_PUNCT)) or (
        bool(tokens) and len(tokens[-1]) == 1 and tokens[-1].isalnum()
    )
    if truncated:
        return bio, "omitted"
    return bio, "clean"


def _ingest_judge_record(rec: dict) -> dict:
    court = str(rec.get("court") or "").strip()
    if court not in JUDGE_COURT_VOCAB:
        raise ValueError(f"J-3 court vocab FAIL: {rec.get('name')!r} court={court!r}")
    name = _clean_judge_name(rec.get("name", ""))

    phones = rec.get("phones") or []
    if not isinstance(phones, list) or not phones:
        raise ValueError(f"J-4 phones FAIL: {name} has no phones")
    for p in phones:
        if not _PHONE_PAT.match(str(p or "").strip()):
            raise ValueError(f"J-4 phone format FAIL: {name} phone={p!r}")
    phones = [str(p).strip() for p in phones]

    fax = _normalize_fax(rec.get("fax", ""))
    email = str(rec.get("email") or "").strip()
    if email and not _EMAIL_PAT.match(email):
        raise ValueError(f"J-4 email format FAIL: {name} email={email!r}")

    bio, bio_status = _classify_bio(rec)

    return {
        "name": name,
        "title": "Municipal Court Judge" if court == "Municipal" else "Common Pleas Court Judge",
        "court": court,
        "courtroom": str(rec.get("courtroom") or "").strip(),
        "bailiff": str(rec.get("bailiff") or "").strip(),
        "law_clerk": str(rec.get("law_clerk") or "").strip(),
        "phone": phones[0],
        "phones": phones,
        "fax": fax,
        "email": email,
        "bio": bio,
        "bio_status": bio_status,
        "source_url": str(rec.get("url") or "").strip(),
    }


def ingest_judges(source_path: Path, operator: str = "operator") -> dict:
    with open(source_path, encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        raise ValueError(f"J-1 judges source FAIL: expected a list, got {type(raw).__name__}")

    judges: list[dict] = []
    aux_count = 0
    for rec in raw:
        if not isinstance(rec, dict):
            raise ValueError("J-1 judge record FAIL: not an object")
        if _is_auxiliary_record(rec):
            aux_count += 1
            continue
        judges.append(_ingest_judge_record(rec))

    if len(judges) != EXPECTED_JUDGE_COUNT:
        raise ValueError(
            f"J-2 count band FAIL: expected {EXPECTED_JUDGE_COUNT} true judge profiles, "
            f"got {len(judges)} (excluded {aux_count} auxiliary)"
        )

    statuses = [j["bio_status"] for j in judges]
    provenance = {
        "schema_version": "1.0",
        "source": "judges.json (Hamilton County court judge profiles, hamiltoncountycourts.org, via Firecrawl)",
        "crawl_date": "2026-09-20",
        "ingested_utc": datetime.now(timezone.utc).isoformat(),
        "ingested_by": operator,
        "counts": {
            "total": len(judges),
            "common_pleas": sum(1 for j in judges if j["court"] == "Common Pleas"),
            "municipal": sum(1 for j in judges if j["court"] == "Municipal"),
            "auxiliary_excluded": aux_count,
            "bio_clean": statuses.count("clean"),
            "bio_needs_review": statuses.count("needs_review"),
            "bio_omitted": statuses.count("omitted"),
        },
        "max_age_days": 365,
    }
    return {"_provenance": provenance, "judges": judges}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bond-source", help="Path to structured bond_schedule.json")
    ap.add_argument("--judges-source", help="Path to structured judges.json")
    ap.add_argument("--operator", default="operator", help="Operator name for provenance")
    ap.add_argument("--acknowledge-warnings", action="store_true", help="Acknowledge warnings and proceed")
    args = ap.parse_args()

    if not args.bond_source and not args.judges_source:
        ap.error("one of --bond-source or --judges-source is required")

    if args.bond_source:
        dataset = ingest_bond_schedule(Path(args.bond_source), operator=args.operator)
        out = DATA_DIR / "court_bond_schedule.json"
        _atomic_write(out, dataset)
        print(f"Wrote {out} with {dataset['_provenance']['counts']}")

    if args.judges_source:
        dataset = ingest_judges(Path(args.judges_source), operator=args.operator)
        out = DATA_DIR / "court_judges.json"
        _atomic_write(out, dataset)
        print(f"Wrote {out} with {dataset['_provenance']['counts']}")


if __name__ == "__main__":
    main()
