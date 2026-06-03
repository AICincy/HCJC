"""Utility to auto-populate and update data/orc_offenses.json with missing codes

extracted from Clerk of Courts JSON files in HAMCO/ and the inmate roster in data/current.json.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
OFFENSES_PATH = ROOT_DIR / "data" / "orc_offenses.json"
CURRENT_PATH = ROOT_DIR / "data" / "current.json"
HAMCO_DIR = ROOT_DIR / "HAMCO"

from scraper.orc import normalize_code

# Regex patterns
_CODE_END_RE = re.compile(r"(\d+(?:[-.]\w+)*|PBR-?\d+|OVERTRAF)$", re.IGNORECASE)
_DEGREE_RE = re.compile(r"\b(F[1-5]|M[1-4]|MM)\b\s*$", re.IGNORECASE)
_DEGREE_CONCAT_RE = re.compile(r"(F[1-5]|M[1-4]|MM)$", re.IGNORECASE)


def extract_degree(desc: str) -> tuple[str, str]:
    """Extract degree suffix (e.g. M1, F4, MM) from description if present.

    Returns (cleaned_description, degree). Defaults to "MM" if not found.
    """
    desc = desc.strip()
    m = _DEGREE_RE.search(desc)
    if m:
        return desc[:m.start()].strip(), m.group(1).upper()
    m = _DEGREE_CONCAT_RE.search(desc)
    if m:
        return desc[:m.start()].strip(), m.group(1).upper()
    return desc, "MM"


def clean_description(desc: str) -> str:
    """Format and clean description."""
    desc = desc.strip()
    # Strip Turnstile/Cloudflare challenge text if present
    if any(k in desc.lower() for k in ("turnstile", "cloudflare", "troubleshoot", "checking your browser")):
        return ""
    if desc.isupper():
        return desc.capitalize()
    return desc


def update_orc_offenses() -> None:
    """Read HAMCO listings and current.json, merge new mappings into data/orc_offenses.json."""
    if not OFFENSES_PATH.exists():
        log.warning(f"{OFFENSES_PATH} does not exist. Cannot update.")
        return

    # Load existing offenses
    try:
        data = json.loads(OFFENSES_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        log.error(f"Failed to read {OFFENSES_PATH}: {e}")
        return

    offenses = data.setdefault("offenses", {})

    extracted: dict[str, dict] = {}

    # 1. Parse HAMCO files
    criminal_file = HAMCO_DIR / "www.courtclerk.org_records-search_criminal-case-listings-section-number_.json"
    traffic_file = HAMCO_DIR / "www.courtclerk.org_records-search_traffic-case-listings-section-number_.json"

    for file_path in (criminal_file, traffic_file):
        if not file_path.exists():
            continue
        try:
            raw_data = json.loads(file_path.read_text(encoding="utf-8"))
            markdown = raw_data.get("markdown", "")
            parts = re.split(r"\s*(ORCN|CMCN)\s*", markdown)
            if len(parts) > 1:
                first_text = parts[0].strip()
                m = _CODE_END_RE.search(first_text)
                first_code = m.group(1) if m else (first_text.split()[-1] if first_text.split() else "")

                for i in range(1, len(parts), 2):
                    jur = parts[i]
                    desc_and_next_code = parts[i+1].strip() if i+1 < len(parts) else ""

                    if i+1 == len(parts) - 1:
                        desc = desc_and_next_code
                        next_code = ""
                    else:
                        m = _CODE_END_RE.search(desc_and_next_code)
                        if m:
                            next_code = m.group(1)
                            desc = desc_and_next_code[:-len(next_code)].strip()
                        else:
                            words = desc_and_next_code.split()
                            if words:
                                next_code = words[-1]
                                desc = " ".join(words[:-1])
                            else:
                                next_code = ""
                                desc = ""

                    norm_code = normalize_code(first_code)
                    if norm_code:
                        clean_desc = clean_description(desc)
                        if clean_desc:
                            title, deg = extract_degree(clean_desc)
                            if jur == "CMCN":
                                deg = "MM"
                            if title:
                                # Overwrite only if not yet set or empty
                                if norm_code not in extracted:
                                    extracted[norm_code] = {"title": title, "degree": deg}

                    first_code = next_code
        except Exception as e:
            log.warning(f"Error parsing HAMCO file {file_path.name}: {e}")

    # 2. Parse current.json
    if CURRENT_PATH.exists():
        try:
            raw_data = json.loads(CURRENT_PATH.read_text(encoding="utf-8"))
            inmates = raw_data.get("inmates", [])
            for inmate in inmates:
                for charge in inmate.get("charges", []):
                    code = charge.get("orc_code", "")
                    desc = charge.get("description", "")
                    norm_code = normalize_code(code)
                    if norm_code and desc:
                        clean_desc = clean_description(desc)
                        if clean_desc:
                            title, deg = extract_degree(clean_desc)
                            if title and norm_code not in extracted:
                                extracted[norm_code] = {"title": title, "degree": deg}
        except Exception as e:
            log.warning(f"Error parsing current.json: {e}")

    # 3. Merge extracted offenses into existing offenses
    merged_count = 0
    for code, info in extracted.items():
        if code not in offenses or not offenses[code].get("title"):
            offenses[code] = info
            merged_count += 1

    if merged_count > 0:
        # Sort offenses by key
        sorted_offenses = {k: offenses[k] for k in sorted(offenses.keys())}
        data["offenses"] = sorted_offenses

        # Write back to file with clean formatting
        try:
            OFFENSES_PATH.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8"
            )
            log.info(f"Auto-populated {merged_count} missing ORC offenses in {OFFENSES_PATH}")
        except Exception as e:
            log.error(f"Failed to write to {OFFENSES_PATH}: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    update_orc_offenses()
