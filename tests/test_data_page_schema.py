"""Anti-drift gate for the /data/ portal's documented schemas.

The Published Files table on web/templates/data.html documents field names
for the JSON mirrors. Those docs are hand-written; this test pins them to
the Pydantic models (and, for transparency_metrics.json, to the computed
dict) so a model change that renames or removes a field fails CI until the
portal page is updated to match.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from scraper.models import (
    AnonChangelogEntry,
    BlockLogEntry,
    ChangeEvent,
    Charge,
    HistoryRecord,
    Inmate,
    Snapshot,
)
from web.transparency import compute_transparency_metrics

TEMPLATE = (Path(__file__).parent.parent / "web" / "templates" / "data.html").read_text(encoding="utf-8")

# Documented file -> models whose fields may appear in its schema docs.
MODEL_CASES = {
    "current.json": (Snapshot, Inmate, Charge),
    "changelog.json": (ChangeEvent,),
    "anon_changelog.json": (AnonChangelogEntry,),
    "history.json": (HistoryRecord,),
    "waf_block_log.json": (BlockLogEntry,),
}


def _documented_fields(filename: str) -> set[str]:
    """Field names documented in the Published Files row for ``filename``.

    Scans the row's ``<code>`` blocks (only those that look like schema, i.e.
    contain a brace, bracket, or comma-separated field list), drops quoted
    literal values and ``key: value``
    descriptions, and returns the remaining identifiers with any optional
    marker (``?``) stripped.
    """
    m = re.search(rf'<tr><td><a href="{re.escape(filename)}">.*?</tr>', TEMPLATE, re.S)
    assert m, f"data.html has no Published Files row for {filename}"
    row = html.unescape(m.group(0))
    fields: set[str] = set()
    for code in re.findall(r"<code>(.*?)</code>", row, re.S):
        if "{" not in code and "[" not in code and "," not in code:
            continue  # a command or inline literal, not a schema block
        code = re.sub(r'"[^"]*"', "", code)  # literal values like "booked"
        code = re.sub(r":\s*[^,}]*", ":", code)  # value-position descriptions
        fields.update(tok.rstrip("?") for tok in re.findall(r"[a-z][a-z0-9_]*", code))
    assert fields, f"no schema fields parsed from the {filename} row"
    return fields


def test_documented_fields_exist_in_models():
    for filename, models in MODEL_CASES.items():
        actual = {name for model in models for name in model.model_fields}
        documented = _documented_fields(filename)
        unknown = documented - actual
        assert not unknown, f"{filename} docs mention fields absent from {[m.__name__ for m in models]}: {sorted(unknown)}"


def test_transparency_metrics_docs_match_computed_keys():
    documented = _documented_fields("transparency_metrics.json")
    actual = set(compute_transparency_metrics([], "2026-01-01T00:00:00Z"))
    assert documented == actual, (
        f"transparency_metrics.json docs drifted: extra={sorted(documented - actual)}, "
        f"missing={sorted(actual - documented)}"
    )
