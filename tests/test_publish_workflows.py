"""Guards for the data-publishing workflows' checkout step.

Run 35800597032 (2026-09-23) failed at the publish step: the scheduled sweep
checked out its trigger SHA while a previous sweep's push had already landed,
so scripts/commit_generated_changes.sh had to rebase wholesale-rewritten
data/*.json onto the newer commit and died on textual conflicts. Checking out
the fresh tip (ref: ${{ github.ref }}) makes each queued run scrape from
current main, so the publish rebase fast-forwards instead of conflicting.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Workflows that push generated data via scripts/commit_generated_changes.sh
# after a long-running job. Each must check out the tip at step time rather
# than the (possibly stale) trigger SHA.
FRESH_TIP_WORKFLOWS = ("sweep.yml", "rebuild.yml", "refresh_caselaw.yml")


def _first_checkout_sets_ref(text: str) -> bool:
    """True when the first actions/checkout step pins `ref:` in its block."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "actions/checkout@" not in line:
            continue
        base_indent = len(line) - len(line.lstrip(" "))
        for nxt in lines[i + 1 :]:
            stripped = nxt.strip()
            if stripped == "":
                continue
            indent = len(nxt) - len(nxt.lstrip(" "))
            if indent <= base_indent and (stripped.startswith("- ") or re.match(r"^\\S", nxt)):
                break
            if re.match(r"^\\s*ref\\s*:", nxt):
                return True
        return False
    raise AssertionError("no actions/checkout step found")


def test_publishing_workflows_check_out_fresh_tip() -> None:
    for name in FRESH_TIP_WORKFLOWS:
        text = (REPO_ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        assert _first_checkout_sets_ref(text), f"{name}: checkout must pin ref: to the fresh tip"


def test_pages_deploy_gated_to_main() -> None:
    """Branch Pages dispatches must skip the protected deploy, not fail it.

    The github-pages environment rejects non-main branches (run 35799476988),
    so the deploy job carries a main-only gate while build+verify still run.
    """
    text = (REPO_ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    header = text.split("Deploy Pages artifact", 1)[1].split("steps:", 1)[0]
    assert "github.ref == 'refs/heads/main'" in header


def test_publisher_still_refuses_merge_fallback() -> None:
    """The shared publisher must never `git merge` a conflicted rebase."""
    script = (REPO_ROOT / "scripts" / "commit_generated_changes.sh").read_text(encoding="utf-8")
    assert "git rebase --abort" in script
    assert "refusing merge fallback" in script
    assert "git merge" not in script
    assert "resolve_generated_rebase_conflicts" in script
    assert "generated_utc" in script


def test_branch_serve_publishers_commit_docs() -> None:
    """Legacy Pages publishes the committed docs/ tree; publishers must write it.

    Issue #496: sweep/rebuild built into /tmp and committed only data/, so every
    pages-build-deployment \"success\" republished the frozen docs/ skeleton while
    main's roster stayed current. Guard both the build out path and the commit
    path list.
    """
    for name in ("sweep.yml", "rebuild.yml"):
        text = (REPO_ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        assert "python -m web.build --out /tmp/" not in text, (
            f"{name}: must build into docs/ (default out), not a discarded /tmp tree"
        )
        assert "python -m web.build" in text, f"{name}: missing site build step"
        # The publisher argv must include docs/ so the branch-serve deploy
        # receives the rebuilt site, not only source data/.
        assert re.search(
            r"commit_generated_changes\\.sh\\s+\\S+\\s+\"[^\"]+\"\\s+.*\\bdocs/",
            text,
        ), f"{name}: commit_generated_changes.sh must publish docs/"
