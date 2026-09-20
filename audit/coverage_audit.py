#!/usr/bin/env python3
"""
JCStream data coverage audit.

Answers one question: of everything we compute or pull, what reaches a public
surface, what is deliberately withheld, and what is dropped on the floor with no
stated reason?

Three inputs:
  1. Shaper-produced fields   web/shape/*.py dict-literal keys (AST, not regex)
  2. Template-consumed vars    web/templates/* Jinja references (all files, not
                               just *.html, so feed XML templates count)
  3. Published data files      data/*.json vs docs/data/*.json (the public surface)

Buckets per item:
  SURFACED              consumed by a template or published to docs/data/
  WITHHELD_BY_DESIGN    matched against a known suppression rationale
  INTERNAL_KEY          dict key that is a lookup/grouping key, not an output field
  UNSURFACED_NO_REASON  produced/stored, no consumer, no rationale  <-- the backlog

The declared-on-/data/-page list is parsed from the templates, not hardcoded,
so new feeds never show up as false "hidden" findings.

Deterministic. No network. Reads the repo as-is.
Verified against source 2026-07-05: the original regex version flagged 19
items; 15 were extraction noise fixed by this revision.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
SHAPE = ROOT / "web" / "shape"
TEMPLATES = ROOT / "web" / "templates"
DATA = ROOT / "data"
DOCS_DATA = ROOT / "docs" / "data"

# Known deliberate-withholding rationales. A produced field or stored file that
# matches one of these is bucket 2, not the backlog. Keyed by substring match.
WITHHOLD_RULES = {
    "my_bond":        "per-person value; only shown on that person's own detail page",
    "my_percentile":  "per-person value; only shown on that person's own detail page",
    "pra_requests":   "internal PRA request log; may contain requester PII pre-redaction",
    "egress_evidence":"internal network-egress evidence; operational, not a public feed",
}

# Dict keys that are lookup-table / grouping keys rather than output fields.
# Exact match only. Each carries the verified reason it is not a coverage gap.
INTERNAL_KEYS = {
    "civil":     "case-category lookup key (_CASE_CAT_LABEL); groupings render on the court page",
    "criminal":  "case-category lookup key (_CASE_CAT_LABEL); groupings render on the court page",
    "traffic":   "case-category lookup key (_CASE_CAT_LABEL); groupings render on the court page",
    "date_text": "raw source date string carried beside parsed_date; the date renders via parsed_date",
}

# Files whose absence from docs/data is expected (internal build inputs, not feeds,
# or artifacts of retired feeds kept as historical record).
INTERNAL_ONLY = {
    "orc_caselaw.json":  "build input for statute pages; content is rendered into HTML, not served raw",
    "explainers.json":   "build input for statute explainer text; rendered into HTML",
    "incidents_recent.json":    "retired feed, last written 2026-05-19 (scraper removed); kept in data/ as historical record, not served",
    "oi_shootings_recent.json": "retired feed, last written 2026-05-18; kept in data/ as historical record, not served",
}

def produced_fields() -> dict[str, set[str]]:
    """Extract dict-literal string keys produced by each shaper, via the AST.
    Unlike a quoted-string-before-colon regex, this cannot pick up if-statement
    colons (`if sys.platform == "win32":`) or slice colons."""
    out = {}
    for py in sorted(SHAPE.glob("*.py")):
        if py.name == "__init__.py":
            continue
        tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"))
        keys = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for k in node.keys:
                    if isinstance(k, ast.Constant) and isinstance(k.value, str) and k.value.isidentifier():
                        keys.add(k.value)
        keys = {k for k in keys if not k.startswith("_")}
        out[py.name] = keys
    return out

def _strip_jinja_comments(text: str) -> str:
    """Drop {# ... #} blocks so commented-out references don't count as consumers."""
    return re.sub(r'\{#.*?#\}', '', text, flags=re.S)

def template_vars() -> set[str]:
    """Every identifier referenced inside {{ }} or {% %} across all template
    files (any extension, so RSS/XML templates count as consumers)."""
    vs = set()
    for tpl in TEMPLATES.glob("*"):
        if not tpl.is_file():
            continue
        text = _strip_jinja_comments(tpl.read_text(encoding="utf-8", errors="replace"))
        for m in re.findall(r'\{\{(.*?)\}\}|\{%(.*?)%\}', text, re.S):
            chunk = (m[0] or "") + (m[1] or "")
            # attribute access r.spread, inm.full_name, metrics.status -> capture the leaf too
            for ident in re.findall(r'\b(\w+)\b', chunk):
                vs.add(ident)
    return vs

def declared_files() -> set[str]:
    """Every *.json filename mentioned anywhere in the templates. If a template
    names the file, a link/mention tells the public it exists."""
    names = set()
    for tpl in TEMPLATES.glob("*"):
        if not tpl.is_file():
            continue
        text = _strip_jinja_comments(tpl.read_text(encoding="utf-8", errors="replace"))
        names.update(re.findall(r'\b([\w-]+\.json)\b', text))
    return names

def published_files() -> tuple[set[str], set[str]]:
    stored = {p.name for p in DATA.glob("*.json")} if DATA.exists() else set()
    public = {p.name for p in DOCS_DATA.glob("*.json")} if DOCS_DATA.exists() else set()
    return stored, public

def classify_field(field: str, tvars: set[str]) -> tuple[str, str]:
    for key, reason in WITHHOLD_RULES.items():
        if key in field:
            return "WITHHELD_BY_DESIGN", reason
    if field in INTERNAL_KEYS:
        return "INTERNAL_KEY", INTERNAL_KEYS[field]
    if field in tvars:
        return "SURFACED", "consumed by a template"
    return "UNSURFACED_NO_REASON", ""

def classify_file(name: str, public: set[str]) -> tuple[str, str]:
    if name in public:
        return "SURFACED", "published to docs/data/"
    if name in INTERNAL_ONLY:
        return "WITHHELD_BY_DESIGN", INTERNAL_ONLY[name]
    for key, reason in WITHHOLD_RULES.items():
        if key in name:
            return "WITHHELD_BY_DESIGN", reason
    return "UNSURFACED_NO_REASON", ""

def main():
    prod = produced_fields()
    tvars = template_vars()
    stored, public = published_files()

    print("=" * 70)
    print("JCStream DATA COVERAGE AUDIT")
    print("=" * 70)

    # ---- Part A: shaper-produced fields ----
    print("\n## A. SHAPER-PRODUCED FIELDS\n")
    field_buckets = {"SURFACED": [], "WITHHELD_BY_DESIGN": [], "INTERNAL_KEY": [], "UNSURFACED_NO_REASON": []}
    for shaper, fields in prod.items():
        for f in sorted(fields):
            bucket, reason = classify_field(f, tvars)
            field_buckets[bucket].append((shaper, f, reason))

    for bucket in ("UNSURFACED_NO_REASON", "WITHHELD_BY_DESIGN", "INTERNAL_KEY", "SURFACED"):
        items = field_buckets[bucket]
        print(f"[{bucket}]  {len(items)} fields")
        if bucket == "SURFACED":
            print("   (consumed by templates -- list suppressed for brevity)")
        else:
            for shaper, f, reason in items:
                tail = f"  <- {reason}" if reason else ""
                print(f"   {shaper:16s} {f}{tail}")
        print()

    # ---- Part B: stored vs published JSON ----
    print("\n## B. DATA FILES: stored in data/ vs published to docs/data/\n")
    file_buckets = {"SURFACED": [], "WITHHELD_BY_DESIGN": [], "UNSURFACED_NO_REASON": []}
    for name in sorted(stored):
        bucket, reason = classify_file(name, public)
        file_buckets[bucket].append((name, reason))

    for bucket in ("UNSURFACED_NO_REASON", "WITHHELD_BY_DESIGN", "SURFACED"):
        items = file_buckets[bucket]
        print(f"[{bucket}]  {len(items)} files")
        for name, reason in items:
            tail = f"  <- {reason}" if reason else ""
            print(f"   {name}{tail}")
        print()

    # Published-but-undeclared: in docs/data yet not named by any template
    undeclared = sorted(public - declared_files())
    print("[PUBLISHED BUT NOT NAMED IN ANY TEMPLATE]  %d files" % len(undeclared))
    print("   (served at a URL, but no link tells the public they exist)")
    for name in undeclared:
        print(f"   {name}")
    print()

    # ---- Summary ----
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    fb = field_buckets
    xb = file_buckets
    print(f"Fields  : {len(fb['SURFACED'])} surfaced, "
          f"{len(fb['WITHHELD_BY_DESIGN'])} withheld-by-design, "
          f"{len(fb['INTERNAL_KEY'])} internal-key, "
          f"{len(fb['UNSURFACED_NO_REASON'])} UNSURFACED-NO-REASON")
    print(f"Files   : {len(xb['SURFACED'])} published, "
          f"{len(xb['WITHHELD_BY_DESIGN'])} internal-by-design, "
          f"{len(xb['UNSURFACED_NO_REASON'])} STORED-BUT-UNPUBLISHED")
    print(f"Hidden  : {len(undeclared)} published files not named in any template")

if __name__ == "__main__":
    main()
