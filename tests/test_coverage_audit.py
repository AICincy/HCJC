"""The coverage audit (audit/coverage_audit.py) must stay clean: every shaper
field and stored data file either reaches a public surface or carries a stated
reason. A new dead data path fails here instead of waiting for a manual audit."""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_coverage_audit_reports_no_unsurfaced_items():
    out = subprocess.run(
        [sys.executable, str(REPO / "audit" / "coverage_audit.py"), str(REPO)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "0 UNSURFACED-NO-REASON" in out
    assert "0 STORED-BUT-UNPUBLISHED" in out
    assert "Hidden  : 0 published files" in out
