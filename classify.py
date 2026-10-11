#!/usr/bin/env python3
"""
Classify every tracked file in HCJC repo into Current / Stale / Irrelevant.
Generates inventory.csv and audit-report.md in the repo root.
"""
import csv
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone

AS_OF = "2026-10-11"
REPO = r"C:\Users\jared\.kilo\repo-audit"
COMMIT_SHA = "7e7470d105002bc406e6cccbd8815bbbd4746c05"
REMOTE = "https://github.com/aicincy/hcjc.git"

# ---- Git file enumeration ----
def git_files():
    out = subprocess.check_output(["git", "ls-files", "-z"], text=True, cwd=REPO)
    return [f for f in out.split("\x00") if f]

def git_all_modes():
    """Get all file modes in one call. Format: '<mode> <sha> <stage>\t<path>' per null entry."""
    out = subprocess.check_output(["git", "ls-files", "-s", "-z"], text=True, cwd=REPO)
    result = {}
    for entry in out.split("\x00"):
        if not entry:
            continue
        parts = entry.split("\t")
        if len(parts) >= 2:
            header_parts = parts[0].split()
            if len(header_parts) >= 3:
                result[parts[1]] = header_parts[0]
    return result

def file_size(path):
    r = subprocess.run(["git", "cat-file", "-s", f"HEAD:{path}"], capture_output=True, text=True, cwd=REPO)
    if r.returncode == 0:
        try:
            return int(r.stdout.strip())
        except:
            return -1
    return -1

def git_grep(pattern, paths=None):
    cmd = ["git", "grep", "-l", pattern]
    if paths:
        cmd.extend(paths)
    else:
        cmd.append("--")
        cmd.append(".")
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    return [l.strip() for l in r.stdout.strip().split("\n") if l.strip()]

def git_grep_code(pattern, paths=None):
    """Count occurrences of a pattern (fixed string) in the repo."""
    cmd = ["git", "grep", "--count", "-F", pattern, "--", "."]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    results = {}
    for line in r.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split(":")
        if len(parts) >= 2:
            results[parts[0]] = int(parts[1])
    return results

# ---- Classification rules ----
# Files that are Stale (reference deploy_fix.py which doesn't exist in repo)
STALE_DEPLOYMENT_FILES = {
    "README.md",
    "DEPLOYMENT_FLOW.md",
    "DEPLOYMENT_SPEC.md",
    "DEPLOYMENT_OVERVIEW.md",
    "README_DEPLOY.md",
}

# Directories whose files are archived stubs / dated historical records
STALE_DIRS = {"audit-output", "audit"}

# Gitlink / symlink entries that point to external paths
def find_gitlinks(files, modes):
    result = {}
    for f in files:
        if modes.get(f) == "120000":
            target = subprocess.check_output(["git", "cat-file", "-p", f"HEAD:{f}"], text=True, cwd=REPO).strip()
            result[f] = target
    return result

def classify(path, ftype, gitlinks):
    """Return (classification, purpose, operability_effect, flag, evidence, basis)"""

    # Irrelevant: gitlinks to external paths
    if path in gitlinks:
        target = gitlinks[path]
        refs = git_grep_code(path)
        total_refs = sum(refs.values()) if refs else 0
        return (
            "Irrelevant",
            "gitlink/symlink to external path",
            "None",
            "external-link",
            f"Gitlink mode 120000; target '{target}' is outside the repository working tree; {total_refs} in-repo references",
            "Gitlink entries pointing to paths not within the repository are excluded from the inventory scope"
        )

    # Irrelevant: .git/ internals
    if path == ".git":
        return (
            "Irrelevant",
            "Git internal metadata",
            "None",
            "git-internal",
            "Directory containing git object store, refs, and config; not part of the project source tree",
            ".git/ is repository management metadata, not project source"
        )

    # Stale: audit-output/ (archived stubs per AGENTS.md)
    if path == "audit-output" or path.startswith("audit-output/"):
        return (
            "Stale",
            "Dated audit record (archived stub)",
            "Low",
            "archived",
            "AGENTS.md states 'Dated files under audit-output/ are archived stubs, not current inventory'; audit-output/README.md says 'ARCHIVED — not current'",
            "audit-output/README.md explicitly declares contents archived/not-current; AGENTS.md confirms"
        )

    # Stale: audit/ (dated audit records 2026-05 through 2026-10)
    if path == "audit" or path.startswith("audit/"):
        return (
            "Stale",
            "Dated audit record",
            "Low",
            "dated",
            f"Directory contains dated audit records (2026-05 through 2026-10); audit/README.md references dated session IDs with [VERIFY] tags",
            "audit/ contains dated audit trail documents, not live project source"
        )

    # Stale: root files that reference deploy_fix.py (not tracked in repo)
    if path == "CLAUDE.md":
        return (
            "Stale",
            "Working notes referencing operational remediation flow dependent on non-existent deploy_fix.py",
            "Medium",
            "stale-reference",
            "CLAUDE.md documents an 'Operational remediation' flow directing to README_DEPLOY.md and DEPLOYMENT_SPEC.md, which reference deploy_fix.py — a script not tracked in git ls-files and absent from the working tree. Also contains time-stamped claims (>=464 tests as of 2026-07-09, nine feeds as of 2026-07) requiring re-verification",
            "Files whose operational remediation section depends on a script absent from the repository are stale; deploy_fix.py existence was confirmed absent from git ls-files"
        )

    if path in STALE_DEPLOYMENT_FILES:
        return (
            "Stale",
            "Documentation referencing non-existent deploy_fix.py",
            "Medium",
            "stale-reference",
            f"References 'deploy_fix.py' (e.g. 'python deploy_fix.py -v') but the file is not tracked in git ls-files and not present in the working tree",
            "Files that reference a script not present in the repository are stale; deploy_fix.py existence was confirmed absent from git ls-files"
        )

    # Current: root-level config and metadata files
    root_files = {
        ".gitignore": ("Ignore rules for build tools, Python, Node, and generated artifacts", "High", "root-config"),
        ".gitattributes": ("Git path attribute rules", "Low", "root-config"),
        "pyproject.toml": ("Python project metadata, dependencies, and dev tool config", "High", "root-config"),
        "requirements.txt": ("Pinned Python runtime dependencies", "High", "root-config"),
        "LICENSE": ("MIT license", "Low", "root-metadata"),
        "SECURITY.md": ("Vulnerability reporting policy", "Low", "root-metadata"),
        "AUDIT-CONTRACT.md": ("Defines audit scope and authority", "Low", "root-contract"),
        "AGENTS.md": ("Agent working guidance; declares audit-output/ as archived stubs", "Medium", "root-guidance"),
        "DECISIONS.md": ("Architecture decision records", "Medium", "root-decisions"),
        "handoff.md": ("Session handoff notes", "Low", "root-metadata"),
    }
    if path in root_files:
        purpose, effect, flag_base = root_files[path]
        flag = "root-config" if "config" in flag_base or "contract" in flag_base else "root-metadata"
        return ("Current", purpose, effect, flag, f"Tracked in git; referenced by CI or agent tooling", "Root-level configuration and metadata files are live project artifacts")

    # Current: .github/ workflows and templates
    if path == ".github" or path.startswith(".github/"):
        return (
            "Current",
            "GitHub Actions workflow or issue template",
            "High",
            "ci",
            "Workflow files are executed by GitHub Actions on push/PR/schedule; tests/test_full_stack_audit.py EXPECTED_WORKFLOWS validates this set",
            ".github/ workflows drive CI/CD and are validated by test_full_stack_audit.py"
        )

    # Current: scraper/ Python source
    if path == "scraper" or path.startswith("scraper/"):
        return (
            "Current",
            "Scraper pipeline source (Python)",
            "High",
            "source",
            "scraper/sweep.py is the primary entry point (python -m scraper.sweep); referenced by .github/workflows/sweep.yml and ci.yml",
            "scraper/ contains the HCSO roster scraping pipeline; sweep.py is the documented entry point and CI execution target"
        )

    # Current: web/ source and templates
    if path == "web" or path.startswith("web/"):
        return (
            "Current",
            "Static site build pipeline (Python/Jinja templates/static assets)",
            "High",
            "source",
            "web/build.py is the static site builder (python -m web.build); templates in web/templates/ are rendered by Jinja2; static assets served by built docs/",
            "web/ contains the static site generator invoked by sweep.yml and ci.yml"
        )

    # Current: scripts/
    if path == "scripts" or path.startswith("scripts/"):
        return (
            "Current",
            "Operational script",
            "Medium",
            "operational",
            "Scripts are invoked by CI workflows (e.g. verify_public_data.py in pages.yml) and by CLAUDE.md/README.md runbooks",
            "scripts/ contains verifier and helper scripts referenced by CI and documentation"
        )

    # Current: tests/
    if path == "tests" or path.startswith("tests/"):
        return (
            "Current",
            "Test suite file",
            "High",
            "test",
            "Executed by CI (ci.yml runs pytest); conftest.py isolates evidence-log writes",
            "tests/ is the pytest suite run by CI on every push"
        )

    # Current: backend/
    if path == "backend" or path.startswith("backend/"):
        return (
            "Current",
            "Node.js backend service source",
            "Medium",
            "source",
            "backend/ is tested by ci.yml's 'Backend (Node)' job; node --check src/index.js and npm audit gate",
            "backend/ contains the Supabase-backed Node service with a dedicated CI job"
        )

    # Current: config/
    if path == "config" or path.startswith("config/"):
        return (
            "Current",
            "Public data manifest configuration",
            "Medium",
            "config",
            "config/public-data-manifest.json is verified by scripts/verify_public_data.py in pages.yml CI",
            "config/ contains the public JSON data compatibility contract"
        )

    # Current: data/ (canonical pipeline snapshots + photos cache)
    if path == "data" or path.startswith("data/"):
        if path == "data/photos" or path.startswith("data/photos/"):
            purpose = "Cached booking photos (JPEG evidence)"
        elif path.endswith(".json") or path == "data/surnames.txt":
            if path == "data/surnames.txt":
                purpose = "Surname input list (A-Z single letters)"
            else:
                purpose = "Canonical pipeline data snapshot (JSON)"
        else:
            purpose = "Pipeline data artifact"
        return (
            "Current",
            purpose,
            "High",
            "data",
            "data/ is the single source of truth for the scraper and builder; current.json is the active roster; CI verifies WAF evidence chain in data/waf_block_log.json",
            "data/ contains canonical pipeline outputs consumed by web/build.py and verified by CI"
        )

    # Current: docs/ (generated output, committed by sweep.yml)
    if path == "docs" or path.startswith("docs/"):
        if path == "docs/CNAME":
            return (
                "Current",
                "Custom domain CNAME (generated + preserved)",
                "High",
                "generated",
                "docs/CNAME contains 'www.aretheyinjail.com'; ci.yml checks docs/CNAME exists and contains aretheyinjail.com",
                "docs/CNAME is both generated by web/build.py and verified by CI"
            )
        if path == "docs/.nojekyll":
            return (
                "Current",
                "Jekyll bypass marker (empty file, GitHub Pages)",
                "Low",
                "generated",
                "Empty file (git blob e69de29bb2d1d6434b8b29ae775ad8c2e48c5391) disables Jekyll processing on GitHub Pages",
                "docs/.nojekyll is a standard GitHub Pages convention"
            )
        if path == "docs/FRAMEWORK-REVIEW-2026-09-20.md":
            return (
                "Current",
                "Preserved framework review document",
                "Low",
                "preserved",
                "Listed in web/build.py PRESERVED_FILES = ('FRAMEWORK-REVIEW-2026-09-20.md', 'CNAME'); copied across output swap",
                "docs/FRAMEWORK-REVIEW-2026-09-20.md is explicitly preserved by web/build.py"
            )
        if path.endswith(".html"):
            return (
                "Current",
                "Generated static HTML page",
                "High",
                "generated",
                f"Generated by web/build.py from Jinja2 templates in web/templates/; committed by sweep.yml and rebuild.yml",
                "docs/*.html files are generated site output written to docs/ by the build pipeline"
            )
        if path.endswith(".json"):
            return (
                "Current",
                "Generated JSON data for the public site",
                "High",
                "generated",
                f"Generated by web/build.py; published under docs/data/ as the public JSON contract",
                "docs/data/*.json files are generated from data/ snapshots and served on the live site"
            )
        if path.endswith(".jpg") or path.endswith(".png") or path.endswith(".ico") or path.endswith(".woff2"):
            return (
                "Current",
                "Static asset (image/icon/font)",
                "Medium",
                "generated",
                "Static assets served by the built site; committed to docs/ for branch-serve publishing",
                "docs/ static assets are generated output served by GitHub Pages"
            )
        if path in ("docs/robots.txt", "docs/manifest.webmanifest", "docs/humans.txt", "docs/feed.xml", "docs/booked.xml", "docs/released.xml", "docs/search.json", "docs/404.html", "docs/dispatches.json"):
            return (
                "Current",
                "Generated site artifact",
                "Medium",
                "generated",
                f"Written by web/build.py to docs/ for branch-serve publishing",
                "docs/ top-level artifacts are generated by web/build.py"
            )
        if path == "docs/SHA256SUMS":
            return (
                "Current",
                "Checksums for generated docs/data/ files",
                "Low",
                "generated",
                "Generated by web/build.py to docs/data/SHA256SUMS",
                "docs/SHA256SUMS is a generated verification artifact"
            )
        if path.endswith(".css") or path.endswith(".js") or path.endswith(".xsl") or path.endswith(".xml"):
            return (
                "Current",
                "Generated web asset",
                "Medium",
                "generated",
                "Written by web/build.py to docs/ for the live site",
                "Generated CSS/JS/assets are written to docs/ by the build pipeline"
            )
        if path.endswith("/SHA256SUMS"):
            return (
                "Current",
                "Checksum manifest for generated artifacts",
                "Low",
                "generated",
                "Generated by web/build.py for verification of docs/data/",
                "Generated checksum manifest"
            )
        return (
            "Current",
            "Generated static site output",
            "High",
            "generated",
            "Written to docs/ by web/build.py; committed by sweep.yml for branch-serve publishing",
            "docs/ contains generated site output"
        )

    # Current: HAMCO/ cached web pages
    if path == "HAMCO" or path.startswith("HAMCO/"):
        return (
            "Current",
            "Cached courtclerk.org HCSO list HTML (HAMCO cache)",
            "Medium",
            "cache",
            "Referenced by scraper/orc.py ('HAMCO') and scraper/update_orc_offenses.py for ORC offense normalization",
            "HAMCO/ contains cached web pages consumed by the ORC enrichment pipeline"
        )

    # Current: evidence/ (outage evidence)
    if path == "evidence" or path.startswith("evidence/"):
        return (
            "Current",
            "HCSO outage evidence (2026-09-19)",
            "High",
            "evidence",
            "Evidence from the 2026-09-19 HCSO outage; referenced by CI WAF-block evidence verification and audit/14_hcso_waf.md",
            "evidence/ contains dated operational evidence that is still actively verified"
        )

    # Current: pra_requests/ (PRA packet drafts)
    if path == "pra_requests" or path.startswith("pra_requests/"):
        return (
            "Current",
            "PRA packet draft",
            "Medium",
            "operational",
            "pra_requests/ is referenced by .github/workflows/clerk_pra_packets.yml; PACKET.md and PACKET.docx files are tracked per .gitignore exceptions",
            "pra_requests/ contains PRA packet drafts produced by the clerk_pra_packets workflow"
        )

    # Current: archive-manifests/
    if path == "archive-manifests" or path.startswith("archive-manifests/"):
        return (
            "Current",
            "Evidence archive manifest",
            "Low",
            "operational",
            "archive-manifests/ referenced by scripts/create_evidence_archive.sh and archive-evidence.yml",
            "archive-manifests/ defines evidence archive contents"
        )

    # Current: runbooks/
    if path == "runbooks" or path.startswith("runbooks/"):
        return (
            "Current",
            "Operational runbook",
            "Medium",
            "operational",
            "runbooks/live-parity-failure.md is referenced by CLAUDE.md and live-parity.yml workflow",
            "runbooks/ contains incident response procedures"
        )

    # Current: design/
    if path == "design" or path.startswith("design/"):
        return (
            "Current",
            "Design document",
            "Low",
            "design",
            "design/ contains system architecture and UI remediation docs",
            "design/ contains architectural design documentation"
        )

    # Current: docs-reference/
    if path == "docs-reference" or path.startswith("docs-reference/"):
        return (
            "Current",
            "Reference documentation",
            "Medium",
            "reference",
            "docs-reference/ contains controlled reference docs referenced by tests/test_repo_guidance_integrity.py",
            "docs-reference/ is the controlled reference documentation tree"
        )

    # Current: .claude/agents/ and .claude/skills/
    if path.startswith(".claude/"):
        return (
            "Current",
            "Claude agent/skill definition",
            "Low",
            "agent-config",
            "Auto-discovered by Claude Code sessions; .claude/skills/ and .claude/agents/ are explicitly un-ignored in .gitignore",
            ".claude/skills/ and .claude/agents/ contain shipped specialist definitions"
        )

    # Fallback for any unclassified files
    return ("Current", "Tracked file", "Low", "uncategorized", "Tracked in git", "Default classification for unclassified tracked files")

def get_ftype(path, mode):
    if mode == "120000":
        return "gitlink"
    if path == ".git":
        return "directory"
    parts = path.rsplit(".", 1)
    if len(parts) > 1:
        ext = parts[1].lower()
        if ext in ("py",): return "python"
        if ext in ("js",): return "javascript"
        if ext in ("html",): return "html"
        if ext in ("css",): return "css"
        if ext in ("json",): return "json"
        if ext in ("md",): return "markdown"
        if ext in ("yml", "yaml"): return "yaml"
        if ext in ("txt",): return "text"
        if ext in ("sh",): return "shell"
        if ext in ("cjs",): return "javascript"
        if ext in ("jsonl",): return "jsonl"
        if ext in ("xml",): return "xml"
        if ext in ("xsl",): return "xsl"
        if ext in ("tsv",): return "tsv"
        if ext in ("jpg", "jpeg"): return "image"
        if ext in ("png",): return "image"
        if ext in ("ico",): return "image"
        if ext in ("woff2",): return "font"
        if ext in ("docx",): return "docx"
        if ext in ("zip",): return "archive"
        if ext in ("toml",): return "config"
        if ext in ("gitignore",): return "config"
        if ext in ("gitattributes",): return "config"
        return "file"
    # No extension
    if "/" in path:
        parent = path.rsplit("/", 1)[0]
        if parent == "tests/fixtures":
            return "fixture"
    return "file"

def main():
    files = git_files()
    modes = git_all_modes()
    gitlinks = find_gitlinks(files, modes)

    # Add .git/ as a single row
    files_for_inventory = [".git"] + files

    rows = []
    for path in files_for_inventory:
        if path == ".git":
            mode = "100644"
        else:
            mode = modes.get(path, "100644")
        ftype = get_ftype(path, mode)

        classification, purpose, effect, flag, evidence, basis = classify(path, ftype, gitlinks)

        rows.append({
            "classification": classification,
            "path": path,
            "type": ftype,
            "purpose": purpose,
            "operability_effect": effect,
            "flag": flag,
            "evidence": evidence,
            "basis": basis,
            "as_of": AS_OF,
        })

    # Write inventory.csv
    csv_path = os.path.join(REPO, "inventory.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["classification", "path", "type", "purpose", "operability_effect", "flag", "evidence", "basis", "as_of"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {csv_path}")

    # Summary
    classifications = defaultdict(int)
    for r in rows:
        classifications[r["classification"]] += 1
    print("\n=== CLASSIFICATION SUMMARY ===")
    for c, n in sorted(classifications.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")

    # Flag distribution
    flags = defaultdict(int)
    for r in rows:
        flags[r["flag"]] += 1
    print("\n=== FLAG DISTRIBUTION ===")
    for fl, n in sorted(flags.items(), key=lambda x: -x[1]):
        print(f"  {fl}: {n}")

if __name__ == "__main__":
    main()
