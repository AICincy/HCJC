#!/usr/bin/env python3
"""Repo file triage inventory for AICincy/HCJC.

Enumerates every tracked + untracked file (excluding .git/), annotates
manifest/workflow/build references, and emits triage-ledger.csv with a
heuristic category pre-fill. Read-only. Never mutates data/waf_block_log.json.

Usage:
    python -m claude.skills.repo-file-triage-workflow.scripts.inventory
    python .claude/skills/repo-file-triage-workflow/scripts/inventory.py --out triage-ledger.csv
    python .claude/skills/repo-file-triage-workflow/scripts/inventory.py --out triage-ledger.csv --root .

Heuristic categories are advisory; Phase 2 (classification rubric) is
authoritative. Rows marked of-concern always require manual review.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

MANIFEST_REL = Path("config/public-data-manifest.json")
SCHEMA_VERSION = 1

# Stale-doc candidates that contradict live truth per AUDIT-CONTRACT.md.
STALE_DOC_EXACT = {
    "AGENTS.md",
    "CLAUDE.md",
    "handoff.md",
}
STALE_DOC_PREFIXES = (
    "DEPLOYMENT",
    "AUDIT-CONTRACT.md",  # keep per se, but flag dated copies under audit-output/docs-reference
)

# Irrelevant surfaces not on sweep->build->Pages->manifest path.
IRRELEVANT_PREFIXES = (
    "HAMCO/",
    "evidence/",
    "archive-manifests/",
    "audit-output/.taskmaster/",
    "pra_requests/scratch/",
)

# audit-output and docs-reference/supporting/audits are stale duplicates.
STALE_PREFIXES = (
    "audit-output/",
    "docs-reference/supporting/audits/",
    "pra_requests/",  # PACKET triples not in publish path
    "docs-reference/supporting/",
)

KEEP_PREFIXES = (
    "scraper/",
    "web/",
    "config/",
    ".github/workflows/",
    "scripts/",
    "tests/",
    "backend/",
    ".claude/skills/",
    ".claude/agents/",
)

KEEP_EXACT = {
    "LICENSE",
    "LICENSE.md",
    ".gitignore",
    ".gitattributes",
    "requirements.txt",
    "pyproject.toml",
    ".python-version",
    "README.md",
    "SECURITY.md",
    "AUDIT-CONTRACT.md",
    "DECISIONS.md",
}


def git_ls_files(root: Path) -> list[str]:
    try:
        out = subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=str(root),
        )
        parts = [p.decode("utf-8", errors="surrogateescape") for p in out.split(b"\0") if p]
        return sorted(parts)
    except Exception:
        return []


def physical_walk(root: Path) -> list[str]:
    out: list[str] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel.startswith(".git/") or rel == ".git":
            continue
        out.append(rel)
    return sorted(out)


def load_manifest_sources(root: Path) -> tuple[set[str], set[str]]:
    """Return (manifest_paths, manifest_sources) as posix strings."""
    mf = root / MANIFEST_REL
    if not mf.exists():
        return set(), set()
    try:
        data = json.loads(mf.read_text(encoding="utf-8"))
    except Exception:
        return set(), set()
    paths: set[str] = set()
    sources: set[str] = set()
    for entry in data.get("files", []):
        p = entry.get("path")
        s = entry.get("source")
        if isinstance(p, str) and p:
            paths.add(f"docs/data/{p}")
            paths.add(p)
        if isinstance(s, str) and s:
            sources.add(s)
    return paths, sources


def workflow_refs(root: Path) -> set[str]:
    """Approximate set of paths referenced by live workflows."""
    refs: set[str] = set()
    wf_dir = root / ".github" / "workflows"
    if not wf_dir.is_dir():
        return refs
    token_re = re.compile(r"[a-zA-Z0-9_./-]+\.(?:py|json|yml|yaml|sh|js|ts|md)")
    for wf in wf_dir.glob("*.yml"):
        try:
            text = wf.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in token_re.findall(text):
            # Keep only repo-relative looking tokens
            if "/" in m and not m.startswith("http"):
                refs.add(m)
    return refs


def heuristic_category(
    rel: str,
    manifest_sources: set[str],
    manifest_paths: set[str],
) -> tuple[str, str, str]:
    """Return (category, reason_code, evidence)."""
    posix = rel.replace("\\", "/")

    # Never triage the SHA-256 chain for deletion
    if posix == "data/waf_block_log.json":
        return ("keep", "KEEP-MANIFEST", "config/public-data-manifest.json + scraper/verify_block_log.py (SHA-256 chain, append-only)")

    # Manifest sources/paths are keep
    if posix in manifest_sources or posix in manifest_paths:
        return ("keep", "KEEP-MANIFEST", "config/public-data-manifest.json")

    # Keep prefixes that are load-bearing for sweep->build->Pages
    for pre in KEEP_PREFIXES:
        if posix.startswith(pre):
            if posix.startswith("scraper/"):
                return ("keep", "KEEP-SWEEP", "scraper/sweep.py + tests/test_architectural_compliance.py")
            if posix.startswith("web/"):
                return ("keep", "KEEP-BUILD", "web/build.py")
            if posix.startswith(".github/workflows/"):
                return ("keep", "KEEP-WORKFLOW", ".github/workflows/sweep.yml + ci.yml live publish loop")
            if posix.startswith("scripts/"):
                return ("keep", "KEEP-VERIFY", "ci.yml / sweep.yml invocation")
            if posix.startswith("tests/"):
                return ("keep", "KEEP-TEST", "pytest + tests/conftest.py evidence isolation")
            if posix.startswith("backend/"):
                return ("keep", "KEEP-BACKEND", "backend/ is the only Supabase consumer")
            if posix.startswith(".claude/"):
                return ("keep", "KEEP-SKILL", ".claude/skills + .claude/agents active skill infrastructure")
            if posix.startswith("config/"):
                return ("keep", "KEEP-MANIFEST", "config/public-data-manifest.json")

    if posix in KEEP_EXACT:
        return ("keep", "KEEP-TEST" if posix in {"SECURITY.md", "AUDIT-CONTRACT.md"} else "KEEP-BUILD", "root keep per classification rubric")

    # docs/ is derivable but is the live branch-serve artifact - keep
    if posix.startswith("docs/"):
        return ("keep", "KEEP-BUILD", "branch-serve live artifact (derivable via python -m web.build)")

    # data/ keep set - roster + history + orc refs that are manifest sources or load-bearing
    if posix.startswith("data/"):
        # Build-input reference data read by web/classify.py and web/pages.py
        # (not published to docs/data/ per manifest, but required for build).
        BUILD_INPUT = {
            "data/explainers.json",        # web/classify.py _load_explainers
            "data/orc_caselaw.json",       # web/classify.py _load_caselaw
            "data/court_judges.json",      # scraper/ingest_court_content.py -> web/pages.py Firecrawl corpus
            "data/court_bond_schedule.json",  # scraper/ingest_court_content.py
            "data/orc_offenses.json",      # manifest-published, also classify reference
            "data/orc_caselaw.json",
            "data/surnames.txt",           # scraper sweep seed
            "data/takedowns.json",         # web/build.py redaction list if present
        }
        if posix in BUILD_INPUT:
            return ("keep", "KEEP-BUILD", "build input read by web/classify.py or web/pages.py (not manifest-published)")
        # Operational / empty sweep state - irrelevant, not published
        IRRELEVANT_DATA = {
            "data/court_bond_corrections.json",  # one-off correction table, not read by build
            "data/egress_evidence.json",         # scraper/egress_ip.py operational IP probe (410b)
            "data/freeze_alert_state.json",      # scraper/freeze_alert.py dedup state (58b)
            "data/incidents_recent.json",        # frozen empty feed k59e-2pvf (111b)
            "data/oi_shootings_recent.json",     # frozen empty feed r6q4-muts (111b)
        }
        if posix in IRRELEVANT_DATA:
            return ("irrelevant", "IRR-SWEEP-STATE", "sweep state / frozen empty feed - not in manifest, not read by web/build.py publish path")
        # data/*.json already handled via manifest_sources above; any remaining
        # data JSON is genuinely of-concern until proven build-input or sweep-state
        if posix.endswith(".json"):
            return ("of-concern", "CONCERN-MANIFEST-LEAK", "data/ JSON not in manifest and not whitelisted as build input - verify not copied to docs/data/")
        return ("keep", "KEEP-SWEEP", "data/ load-bearing (verify against manifest)")

    # Stale exact docs
    if posix in STALE_DOC_EXACT:
        return ("stale", "STALE-DOC", "AUDIT-CONTRACT.md live-truth ranking supersedes this doc")
    for pre in ("DEPLOYMENT",):
        if posix.startswith(pre):
            return ("stale", "STALE-DOC", "branch-serve truth in .github/workflows/pages.yml + AUDIT-CONTRACT.md")

    # Stale prefixes (dated packets, duplicated audits)
    for pre in STALE_PREFIXES:
        if posix.startswith(pre):
            if posix.startswith("audit-output/") or "supporting/audits" in posix:
                return ("stale", "STALE-AUDIT-DUP", "AUDIT-CONTRACT.md archived-stub rule; duplicate audit lineage")
            return ("stale", "STALE-PACKET", "not in manifest, not read by web/build.py, not in live workflows")

    for pre in IRRELEVANT_PREFIXES:
        if posix.startswith(pre):
            if posix.startswith("HAMCO/"):
                return ("irrelevant", "IRR-HAMCO", "not imported by scraper/ or web/build.py (one-off court-site scrape)")
            if posix.startswith("evidence/"):
                return ("irrelevant", "IRR-EVIDENCE", "waf_block_log.json is the evidence; HTMLs beyond retention")
            return ("irrelevant", "IRR-ARCHIVE", "not on sweep->build->Pages path")

    # audit/ historical notes
    if posix.startswith("audit/"):
        return ("stale", "STALE-DOC", "superseded by AUDIT-CONTRACT.md unless cited as live claim ledger")

    # Fallback - keep conservatively; human triage should downgrade if warranted
    return ("keep", "KEEP-BUILD", "no higher-priority rule matched; verify workflow/build/test refs before reclassifying")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="HCJC repo file triage inventory (read-only).")
    ap.add_argument("--root", default=".", help="Repository root (default: .).")
    ap.add_argument("--out", default="triage-ledger.csv", help="Output CSV path.")
    ap.add_argument("--notes", default="discovery-notes.md", help="Discovery notes output path.")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    out_csv = Path(args.out)
    if not out_csv.is_absolute():
        out_csv = (Path.cwd() / out_csv).resolve()
    notes_path = Path(args.notes)
    if not notes_path.is_absolute():
        notes_path = (Path.cwd() / notes_path).resolve()

    tracked = git_ls_files(root)
    physical = physical_walk(root)
    # Ledger source of truth is git ls-files; physical is for ignored residue detection
    all_paths = tracked if tracked else physical
    ignored_only = sorted(set(physical) - set(all_paths))

    manifest_paths, manifest_sources = load_manifest_sources(root)
    wf_refs = workflow_refs(root)

    waf_path = root / "data" / "waf_block_log.json"
    waf_sha = sha256_file(waf_path) if waf_path.exists() else "MISSING"
    waf_bytes = waf_path.stat().st_size if waf_path.exists() else 0

    rows: list[dict[str, str]] = []
    for rel in all_paths:
        # Skip the ledger itself if it lives inside the repo
        if Path(rel).resolve() == out_csv:
            continue
        abs_path = root / rel
        try:
            size = abs_path.stat().st_size if abs_path.exists() else 0
        except Exception:
            size = 0
        cat, reason, evidence = heuristic_category(rel, manifest_sources, manifest_paths)
        # Flag ignored-but-present residue
        notes = ""
        if rel in ignored_only:
            notes = "present on disk but git-ignored"
        action = {
            "keep": "keep",
            "stale": "rewrite-or-delete (requires approval)",
            "irrelevant": "delete (requires approval)",
            "of-concern": "manual review (do not auto-delete)",
            "inoperable": "fix or delete (requires approval)",
        }.get(cat, "review")

        rows.append(
            {
                "path": rel,
                "bytes": str(size),
                "category": cat,
                "reason_code": reason,
                "evidence": evidence,
                "action": action,
                "notes": notes,
            }
        )

    # Also emit ignored-only extras as informational rows at end
    for rel in ignored_only:
        if rel in {r["path"] for r in rows}:
            continue
        abs_path = root / rel
        try:
            size = abs_path.stat().st_size if abs_path.exists() else 0
        except Exception:
            size = 0
        rows.append(
            {
                "path": rel,
                "bytes": str(size),
                "category": "irrelevant",
                "reason_code": "IRR-SCRATCH",
                "evidence": ".gitignore / untracked residue",
                "action": "delete (requires approval)",
                "notes": "git-ignored, present on disk only",
            }
        )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["path", "bytes", "category", "reason_code", "evidence", "action", "notes"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["category"], r["path"])))

    # Size ranking by top-level dir
    from collections import Counter

    dir_bytes: Counter[str] = Counter()
    for r in rows:
        top = r["path"].split("/")[0] if "/" in r["path"] else "(root)"
        try:
            dir_bytes[top] += int(r["bytes"])
        except Exception:
            pass
    ranked = sorted(dir_bytes.items(), key=lambda kv: kv[1], reverse=True)

    notes_lines = [
        "# Discovery Notes (read-only)",
        "",
        f"- Root: `{root.as_posix()}`",
        f"- Tracked files: {len(tracked)}  Physical files: {len(physical)}  Ignored-only: {len(ignored_only)}",
        f"- Manifest: {len(manifest_paths)} paths, {len(manifest_sources)} sources ({MANIFEST_REL.as_posix()})",
        f"- Workflow refs approximated: {len(wf_refs)} tokens",
        f"- data/waf_block_log.json: {waf_bytes} bytes, sha256={waf_sha[:16]}...",
        "",
        "## Size ranking (top-level)",
        "",
        "| Directory | Bytes | Approx MB |",
        "|---|---|---|",
    ]
    for d, b in ranked[:20]:
        notes_lines.append(f"| `{d}` | {b} | {b / (1<<20):.2f} |")
    notes_lines += [
        "",
        "## Publish-loop checks (manual verification required)",
        "",
        "- `sweep.yml` builds into `docs/` (default --out) and commits both `data/` + `docs/` - verify via `tests/test_publish_workflows.py::test_branch_serve_publishers_commit_docs`.",
        "- `pages.yml` is secondary artifact path; branch-serve `build_type=legacy` Source `main /docs` is live.",
        "- `ci.yml` gates `ruff`, `mypy scraper web`, `pytest`, `verify_block_log`, `verify_public_data`, `web.build` determinism.",
        "",
        "## Ignored-only residue (present on disk, not tracked)",
        "",
    ]
    if ignored_only:
        for r in ignored_only[:50]:
            notes_lines.append(f"- `{r}`")
        if len(ignored_only) > 50:
            notes_lines.append(f"- ... and {len(ignored_only) - 50} more")
    else:
        notes_lines.append("- (none)")

    notes_path.write_text("\n".join(notes_lines) + "\n", encoding="utf-8")

    print(f"Wrote {len(rows)} rows to {out_csv}")
    print(f"Wrote discovery notes to {notes_path}")
    print(f"waf_block_log sha256: {waf_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
