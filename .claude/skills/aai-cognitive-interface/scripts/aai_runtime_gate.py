#!/usr/bin/env python3
"""AAI deterministic package/response gate.

This gate may establish STATIC-PASS only. INSTALL/RUNTIME/ADVERSARIAL status
requires a trusted controller operating on the actual target host.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED_PREFIXES = (
    "aai-",
    "authority-",
    "claim-",
    "forensic-",
    "personal-",
    "practitioner-",
    "prompt-",
    "record-",
    "reddit-",
    "register-",
    "regulatory-",
    "research-",
    "sorta-",
    "subreddit-",
)


def parse_frontmatter(text: str):
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) != 3:
        return {}
    out = {}
    for line in parts[1].splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def package_gate(skill_dir: Path):
    errs = []
    if not skill_dir.is_dir():
        errs.append("SKILL_DIRECTORY_MISSING")
    md = skill_dir / "SKILL.md"
    if not md.exists():
        errs.append("SKILL_MD_MISSING")
    fm = parse_frontmatter(md.read_text(encoding="utf-8")) if md.exists() else {}
    if not fm.get("name"):
        errs.append("NAME_MISSING")
    if not fm.get("description"):
        errs.append("DESCRIPTION_MISSING")
    if md.exists() and any(ch in md.read_text(encoding="utf-8") for ch in ("\x00", "\ufffd")):
        errs.append("TEXT_CORRUPTION_MARKER")
    return {
        "status": "PASS" if not errs else "FAIL",
        "errors": errs,
        "skill_name": fm.get("name"),
        "skill_dir": str(skill_dir.resolve()),
    }


def response_gate(draft: Path, evidence: Path | None):
    if not draft.exists():
        return {"status": "FAIL", "errors": ["DRAFT_MISSING"]}
    errors = []
    if evidence:
        if not evidence.exists():
            errors.append("EVIDENCE_LEDGER_MISSING")
        else:
            try:
                ledger = json.loads(evidence.read_text(encoding="utf-8"))
            except Exception:
                errors.append("EVIDENCE_LEDGER_INVALID")
            else:
                text = json.dumps(ledger)
                for label in (
                    "INSTALLED",
                    "RUNTIME-SMOKE-PASS",
                    "RUNTIME-VERIFIED",
                    "ADVERSARIAL-PASS",
                ):
                    if label in text and not any(
                        k in text for k in ("trusted_controller", "controller_signature", "runtime_receipt")
                    ):
                        errors.append(f"UNSUPPORTED_STATUS:{label}")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("package")
    q.add_argument("skill_dir")
    r = sub.add_parser("response")
    r.add_argument("draft")
    r.add_argument("--evidence-file")
    a = p.parse_args(argv)
    if a.cmd == "package":
        out = package_gate(Path(a.skill_dir))
    else:
        out = response_gate(
            Path(a.draft), Path(a.evidence_file) if a.evidence_file else None
        )
    print(json.dumps(out, indent=2))
    return 0 if out["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
