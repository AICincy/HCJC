"""Guards that root-level agent guidance stays a document, not a patch.

Commit e2e378f ("Revise CLAUDE.md for clarity and accuracy", 2026-09-24) did not
apply a revision -- it replaced CLAUDE.md with the *text of a unified diff*:

    --- CLAUDE.md (original - STALE)
    +++ CLAUDE.md (corrected - 2026-09-24)
    @@ -137,14 +137,31 @@

467 lines became 72 and all 36 headings vanished, taking four operational
runbooks with them, including "Pages deploy: branch-serving is the live path"
(the authoritative root-cause statement behind issues #483/#487/#496) and
"Deterministic Build Contract" (the contract PR #503 implemented). Nothing
noticed, because no gate reads these files.

The content was recoverable from git history; the silent loss was the problem.
These checks are deliberately shallow -- structure only, no prose policy -- so
they catch a pasted patch or a truncated file without dictating wording.

See audit/25_pages_stale_artifact_misdiagnosis.md (addendum).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Root-level markdown that agents read as operating instructions. A pasted diff
# or an accidental truncation here silently removes guidance with no test
# failure, which is what happened to CLAUDE.md.
GUIDANCE_FILES = ("CLAUDE.md", "AGENTS.md", "README.md")

# Unified-diff furniture. Legitimate prose may mention a diff in a fenced block,
# so these are asserted against the *first* lines and the heading count rather
# than anywhere in the file.
DIFF_HEADER = re.compile(r"^(\+\+\+|---)\s+\S+")
HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@")


@pytest.mark.parametrize("name", GUIDANCE_FILES)
def test_guidance_file_is_a_document_not_a_patch(name: str) -> None:
    path = REPO_ROOT / name
    assert path.is_file(), f"{name} is missing from the repository root"

    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines, f"{name} is empty"

    # A real document opens with a heading, front matter, or prose -- not the
    # `--- a` / `+++ b` pair of a patch.
    head = [ln for ln in lines[:5] if ln.strip()]
    assert head, f"{name} has no content in its first five lines"
    assert not DIFF_HEADER.match(head[0]), (
        f"{name} begins with a unified-diff header ({head[0]!r}); it looks like a "
        f"patch was pasted over the document. Restore from git history, e.g. "
        f"`git show <last-good-sha>:{name}`."
    )

    hunks = [ln for ln in lines if HUNK_HEADER.match(ln)]
    assert not hunks, (
        f"{name} contains {len(hunks)} unified-diff hunk header(s), e.g. "
        f"{hunks[0]!r}; the file is a patch, not guidance."
    )


def test_claude_md_retains_its_runbook_structure() -> None:
    """CLAUDE.md must keep a document's worth of headings.

    Asserted as a floor, not an exact list, so ordinary edits are free but a
    truncation or a patch-overwrite is not. 36 headings existed at 5d90340; the
    corrupted revision had none.
    """
    text = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    headings = [ln for ln in text.splitlines() if ln.startswith("#")]

    assert len(headings) >= 20, (
        f"CLAUDE.md has {len(headings)} heading(s); the pre-corruption document "
        f"had 36. A large loss usually means the file was truncated or replaced "
        f"by a patch -- restore it rather than editing forward."
    )
    assert headings[0].startswith("# "), "CLAUDE.md must open with an H1 title"


def test_claude_md_keeps_pages_and_determinism_runbooks() -> None:
    """The two sections whose loss would most damage the next incident response.

    "Branch-serving is the live path" is the only place recording that Pages is
    build_type=legacy and that a /tmp-only build commits a frozen docs/ skeleton
    while reporting success -- the root cause of the recurring staleness alerts.
    "Deterministic Build Contract" is the contract tests/test_build_determinism.py
    enforces. Matched on stable phrase fragments, not exact heading text.
    """
    text = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8").lower()

    assert "branch-serv" in text or "deploy from a branch" in text, (
        "CLAUDE.md lost the branch-serve Pages guidance (build_type=legacy, "
        "sweep/rebuild must commit docs/). Restore the section."
    )
    assert "deterministic" in text, (
        "CLAUDE.md lost the deterministic build contract. Restore the section."
    )
