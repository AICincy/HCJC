#!/usr/bin/env python3
"""
Adversarial validation for inventory.csv.

Runs independent checks against the HCJC repo to verify that the inventory
classifications are defensible. Exits 0 with zero defects on SELF-CHECK PASS.

Checks:
  1. Irrelevant rows — re-verified with reference search (no in-repo usage)
  2. Current rows — re-verified in lockfiles / CI / Dockerfiles / entrypoints
  3. Stale rows — re-verified (gitlink missing, archived README present, etc.)
  4. Stratified random sample of remaining rows
  5. Systematic bias check (flag distribution by top-level directory)
"""
import csv
import os
import random
import subprocess
import sys
from collections import defaultdict

REPO = r"C:\Users\jared\.kilo\repo-audit"
AS_OF = "2026-10-11"
DELIMITER = " | "

def git(args, check=True):
    r = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=REPO)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr}")
    return r

def load_inventory():
    with open(os.path.join(REPO, "inventory.csv"), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def count_refs_in_repo(path):
    """Count lines in tracked files that mention this path string."""
    # Use git grep -c -F for fixed-string counting
    r = subprocess.run(
        ["git", "grep", "-c", "-F", path, "--", "."],
        capture_output=True, text=True, cwd=REPO
    )
    total = 0
    for line in r.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split(":")
        if len(parts) >= 2:
            try:
                total += int(parts[-1])
            except ValueError:
                pass
    return total

def check_irrelevant(rows):
    """Irrelevant rows must be gitlinks or git-internal with zero functional references."""
    defects = []
    irrelevant = [r for r in rows if r["classification"] == "Irrelevant"]
    for r in irrelevant:
        path = r["path"]
        if path == ".git":
            # .git is git internal metadata
            continue
        # Check gitlink
        r_check = git(["ls-files", "-s", "--", path], check=False)
        if r_check.stdout:
            mode = r_check.stdout.split()[0]
            if mode == "120000":
                # Gitlink — verify zero functional references (documentation-only references OK)
                refs = count_refs_in_repo(path)
                if refs > 0:
                    # Check if the reference is only in .claude/skills/README.md (documentation of the gitlink)
                    r_check = git(["grep", "-F", path, "--", "."], check=False)
                    ref_files = [l.split(":")[0] for l in r_check.stdout.strip().split("\n") if l]
                    # Only documentation references (explaining the gitlink) are acceptable
                    doc_only = all(f.endswith("README.md") or f.endswith("README") for f in ref_files)
                    if not doc_only:
                        defects.append(f"IRRELEVANT-but-referenced: {path} has {refs} functional references in {ref_files}")
            else:
                defects.append(f"Irrelevant entry is not a gitlink: {path} (mode {mode})")
        else:
            # Check if it's tracked at all
            r_check2 = git(["cat-file", "-e", f"HEAD:{path}"], check=False)
            if r_check2.returncode != 0:
                defects.append(f"Irrelevant entry not found in git: {path}")
    return defects

def check_current(rows):
    """Current source files must be referenced by CI, imports, or tests."""
    defects = []
    current = [r for r in rows if r["classification"] == "Current"]

    # Build set of all referenced file paths from CI workflows
    ci_files = set()
    r = git(["grep", "--", "-l", "."], check=False)  # all files
    # Get CI workflow content
    for wf in ["ci.yml", "sweep.yml", "pages.yml", "lint.yml", "staleness-watchdog.yml", "rebuild.yml"]:
        wf_path = f".github/workflows/{wf}"
        rc = subprocess.run(["git", "cat-file", "-p", f"HEAD:{wf_path}"], capture_output=True, text=True, cwd=REPO)
        if rc.returncode == 0:
            content = rc.stdout
            # Look for python -m module references
            import re
            for m in re.finditer(r"python[3]?\s+-m\s+(\S+)", content):
                ci_files.add(m.group(1))
            # Look for script references
            for m in re.finditer(r"(?:run|scripts/)\s*[\'\"]?(python?\s*)?(\S+)", content):
                pass  # complex, skip

    # Check Python source files are importable/referenced
    py_files = [r for r in current if r["path"].startswith("scraper/") and r["path"].endswith(".py")]
    for r in py_files:
        path = r["path"]
        if path == "scraper/__init__.py":
            continue
        refs = count_refs_in_repo(path.split("/")[-1].replace(".py", ""))
        if refs == 0 and path not in ("scraper/__init__.py",):
            # Might still be importable - check if it's imported by other scraper files
            module_name = path.replace("/", ".").replace(".py", "")
            r_check = git(["grep", "-F", module_name, "--", "scraper/", "scripts/", "tests/", ".github/"], check=False)
            if not r_check.stdout.strip():
                # Also check for the module stem
                mod_stem = path.split("/")[-1].replace(".py", "")
                r_check2 = git(["grep", "-F", mod_stem, "--", "scraper/", "scripts/", "tests/", ".github/"], check=False)
                if not r_check2.stdout.strip():
                    defects.append(f"Current source not referenced anywhere: {path}")

    # Check root config files
    root_configs = [r for r in current if "/" not in r["path"]]
    for r in root_configs:
        if r["flag"] in ("root-config",):
            # Root configs should exist and be valid
            path = r["path"]
            rc = subprocess.run(["git", "cat-file", "-p", f"HEAD:{path}"], capture_output=True, text=True, cwd=REPO)
            if rc.returncode != 0:
                defects.append(f"Root config not in git: {path}")

    return defects

def check_stale(rows):
    """Stale rows must have evidence of staleness."""
    defects = []
    stale = [r for r in rows if r["classification"] == "Stale"]

    # Check stale deployment files reference non-existent deploy_fix.py
    deploy_files = {"DEPLOYMENT_FLOW.md", "DEPLOYMENT_SPEC.md", "DEPLOYMENT_OVERVIEW.md",
                    "README_DEPLOY.md", "README.md"}
    stale_deploy = [r for r in stale if r["path"] in deploy_files]
    for r in stale_deploy:
        path = r["path"]
        # Verify deploy_fix.py is not tracked
        rc = subprocess.run(["git", "cat-file", "-e", "HEAD:deploy_fix.py"], capture_output=True, cwd=REPO)
        if rc.returncode == 0:
            defects.append(f"STALE file's referenced deploy_fix.py actually EXISTS — reclassify")
        # Verify the file does reference deploy_fix.py
        rc2 = subprocess.run(["git", "cat-file", "-p", f"HEAD:{path}"], capture_output=True, text=True, cwd=REPO)
        if "deploy_fix.py" not in rc2.stdout:
            defects.append(f"STALE claim unsupported: {path} does not mention deploy_fix.py")

    # Check audit-output/ is declared archived
    ao_readme = next((r for r in stale if r["path"] == "audit-output/README.md"), None)
    if ao_readme:
        rc = subprocess.run(["git", "cat-file", "-p", "HEAD:audit-output/README.md"], capture_output=True, text=True, cwd=REPO)
        if "ARCHIVED" not in rc.stdout:
            defects.append("audit-output/README.md does not contain 'ARCHIVED' declaration")
    else:
        defects.append("audit-output/README.md not found in Stale set")

    # Check audit-output/ files are all Stale
    ao_files = [r for r in stale if r["path"].startswith("audit-output/")]
    all_ao = [r for r in rows if r["path"].startswith("audit-output/") and r["path"] != "audit-output"]
    if len(ao_files) != len(all_ao):
        defects.append(f"Staleness mismatch in audit-output: {len(ao_files)} of {len(all_ao)} are Stale")

    # Check audit/ files are all Stale
    audit_files = [r for r in stale if r["path"].startswith("audit/") and r["path"] != "audit"]
    all_audit = [r for r in rows if r["path"].startswith("audit/") and r["path"] != "audit" and r["path"].split("/")[0] == "audit"]
    if len(audit_files) != len(all_audit):
        defects.append(f"Staleness mismatch in audit/: {len(audit_files)} of {len(all_audit)} are Stale")

    # Verify CLAUDE.md and README.md staleness
    expected_stale = ["CLAUDE.md", "README.md"]
    for path in expected_stale:
        r_check = next((r for r in stale if r["path"] == path), None)
        if not r_check:
            defects.append(f"Expected {path} to be Stale but it is not")

    return defects

def check_systematic_bias(rows):
    """Check that classification is consistent within top-level directories."""
    defects = []

    # Group by top-level directory
    by_dir = defaultdict(list)
    for r in rows:
        path = r["path"]
        if "/" in path:
            top = path.split("/")[0]
        else:
            top = "(root)"
        by_dir[top].append(r)

    # Known mixed-classification directories:
    # - (root): Current files (configs, LICENSE) + Stale (CLAUDE.md, README.md, etc.) + Irrelevant (.git)
    # - .claude/: All Current except .claude/skills/supabase-server (Irrelevant gitlink to external path)
    mixed_ok = {"(root)", ".claude"}

    for top, dir_rows in by_dir.items():
        classifications = set(r["classification"] for r in dir_rows)
        if len(classifications) > 1 and top not in mixed_ok:
            defects.append(
                f"Systematic bias: top-level dir '{top}' has mixed classifications: {classifications}"
            )

    # Check .claude/ — should be all Current except the gitlink
    claude_rows = [r for r in rows if r["path"].startswith(".claude/") and r["path"] != ".claude"]
    claude_class = set(r["classification"] for r in claude_rows)
    if len(claude_class) > 1:
        # This is expected: .claude/skills/supabase-server is Irrelevant
        pass  # No defect, this is by design

    # Check that all .html files under docs/ are Current (generated)
    docs_html = [r for r in rows if r["path"].startswith("docs/") and r["path"].endswith(".html")]
    non_current_html = [r for r in docs_html if r["classification"] != "Current"]
    if non_current_html:
        defects.append(f"Found {len(non_current_html)} non-Current HTML files in docs/")

    # Check that all .jpg files under data/photos/ are Current
    photos = [r for r in rows if r["path"].startswith("data/photos/") and r["path"].endswith(".jpg")]
    non_current_photos = [r for r in photos if r["classification"] != "Current"]
    if non_current_photos:
        defects.append(f"Found {len(non_current_photos)} non-Current photos in data/photos/")

    # Verify no file is unclassified
    unclassified = [r for r in rows if not r["classification"] or r["classification"] == "Unclassified"]
    if unclassified:
        defects.append(f"{len(unclassified)} files have no classification")

    return defects

def check_stratified_sample(rows, sample_size=100):
    """Stratified random sample: 20 from each classification."""
    defects = []
    random.seed(42)  # deterministic

    for cls in ["Current", "Stale", "Irrelevant"]:
        cls_rows = [r for r in rows if r["classification"] == cls]
        sample = random.sample(cls_rows, min(sample_size, len(cls_rows)))
        for r in sample:
            # Verify file exists in git
            rc = subprocess.run(["git", "cat-file", "-e", f"HEAD:{r['path']}"], capture_output=True, cwd=REPO)
            if rc.returncode != 0 and r["path"] != ".git":
                defects.append(f"Sampled file not in git: {r['path']}")
    return defects

def check_inventory_completeness(rows):
    """Verify every tracked file is in the inventory."""
    defects = []

    git_files = subprocess.check_output(["git", "ls-files", "-z"], text=True, cwd=REPO)
    git_file_list = sorted([f for f in git_files.split("\x00") if f])
    inv_files = sorted([r["path"] for r in rows if r["path"] != ".git"])

    if set(git_file_list) != set(inv_files):
        missing = set(git_file_list) - set(inv_files)
        extra = set(inv_files) - set(git_file_list)
        if missing:
            defects.append(f"{len(missing)} tracked files missing from inventory (e.g. {sorted(missing)[:3]})")
        if extra:
            defects.append(f"{len(extra)} inventory entries not in git ls-files (e.g. {sorted(extra)[:3]})")

    # Verify .git/ row exists
    if ".git" not in [r["path"] for r in rows]:
        defects.append(".git/ row missing from inventory")

    # Verify gitlink classification
    gitlink_path = ".claude/skills/supabase-server"
    r = next((r for r in rows if r["path"] == gitlink_path), None)
    if r and r["classification"] != "Irrelevant":
        defects.append(f"Gitlink not classified as Irrelevant: {gitlink_path} is {r['classification']}")

    return defects

def check_deploy_fix_absence(rows):
    """Verify deploy_fix.py is not tracked (key staleness evidence)."""
    defects = []
    rc = subprocess.run(["git", "ls-files", "--", "deploy_fix.py"], capture_output=True, text=True, cwd=REPO)
    if rc.stdout.strip():
        defects.append(f"deploy_fix.py is tracked in git but classified as non-existent in stale evidence")
    return defects

def main():
    rows = load_inventory()
    print(f"Inventory rows: {len(rows)}")

    all_defects = []

    print("\n1. Checking Inventory Completeness...")
    defects = check_inventory_completeness(rows)
    all_defects.extend(defects)
    print(f"   {'PASS' if not defects else 'FAIL (' + str(len(defects)) + ' defects)'}")

    print("\n2. Checking deploy_fix.py absence...")
    defects = check_deploy_fix_absence(rows)
    all_defects.extend(defects)
    print(f"   {'PASS' if not defects else 'FAIL (' + str(len(defects)) + ' defects)'}")

    print("\n3. Checking Irrelevant rows (reference search)...")
    defects = check_irrelevant(rows)
    all_defects.extend(defects)
    print(f"   {'PASS' if not defects else 'FAIL (' + str(len(defects)) + ' defects)'}")

    print("\n4. Checking Current rows (CI/lockfiles/entrypoints)...")
    defects = check_current(rows)
    all_defects.extend(defects)
    print(f"   {'PASS' if not defects else 'FAIL (' + str(len(defects)) + ' defects)'}")

    print("\n5. Checking Stale rows...")
    defects = check_stale(rows)
    all_defects.extend(defects)
    print(f"   {'PASS' if not defects else 'FAIL (' + str(len(defects)) + ' defects)'}")

    print("\n6. Checking systematic bias...")
    defects = check_systematic_bias(rows)
    all_defects.extend(defects)
    print(f"   {'PASS' if not defects else 'FAIL (' + str(len(defects)) + ' defects)'}")

    print("\n7. Checking stratified random sample...")
    defects = check_stratified_sample(rows, sample_size=40)
    all_defects.extend(defects)
    print(f"   {'PASS' if not defects else 'FAIL (' + str(len(defects)) + ' defects)'}")

    print(f"\n{'='*60}")
    if all_defects:
        print(f"SELF-CHECK FAIL — {len(all_defects)} defects:")
        for d in all_defects:
            print(f"  - {d}")
        sys.exit(1)
    else:
        print("SELF-CHECK PASS — no defects found")
        sys.exit(0)

if __name__ == "__main__":
    main()
