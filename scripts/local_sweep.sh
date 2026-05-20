#!/usr/bin/env bash
#
# local_sweep.sh - run a sweep from a residential / non-GH-Actions IP.
#
# Per audit/14_hcso_waf.md option 2: when HCSO's WAF blocks the GitHub
# Actions runner IP range, the on-code defenses preserve previous-good
# data but can't add NEW photos for inmates the GH runner has never
# successfully fetched. This script lets the maintainer run a sweep
# from their own machine (residential ISP, more likely to clear the
# WAF), commit the resulting current.json + photos, and push to main.
# The next GH Actions cron picks up incremental updates as normal.
#
# Usage:
#   scripts/local_sweep.sh                    # full sweep, commit, push
#   scripts/local_sweep.sh --dry-run          # sweep + show diff; no commit
#   scripts/local_sweep.sh --refresh-known    # re-fetch known-inmate detail pages
#
# Requirements:
#   - python (with the requirements.txt deps installed)
#   - git authenticated to push to AICincy/HCJC
#   - a clean working tree (refuses to clobber uncommitted edits)
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# --- Safety: refuse to run with uncommitted changes ---
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "error: working tree has uncommitted changes; refusing to run."
    echo "       commit, stash, or revert before running local_sweep.sh."
    git status --short
    exit 1
fi

# --- Sync with origin/main first so we're not racing the cron ---
echo "fetching origin/main..."
git fetch origin main --quiet
if [[ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]]; then
    echo "rebasing local main onto origin/main..."
    git checkout main --quiet
    git reset --hard origin/main --quiet
fi

# --- Pre-flight: tests must pass on current code ---
echo "running pytest..."
if ! python -m pytest -q > /dev/null; then
    echo "error: tests are red. Aborting before the sweep."
    python -m pytest -q
    exit 1
fi

# --- Sweep ---
DRY_RUN=""
REFRESH_KNOWN=""
for arg in "$@"; do
    case "$arg" in
        --dry-run)        DRY_RUN="--dry-run" ;;
        --refresh-known)  REFRESH_KNOWN="--refresh-known" ;;
        *) echo "warning: unknown argument $arg (ignored)" ;;
    esac
done

echo "running scraper.sweep $DRY_RUN $REFRESH_KNOWN ..."
# JCSTREAM_SITE_BASE_URL and JCSTREAM_CNAME are needed by the build, not
# the sweep, but exporting them now keeps the env consistent with the
# production cron in case the maintainer chains a `python -m web.build`.
JCSTREAM_SITE_BASE_URL="" \
JCSTREAM_CNAME="www.aretheyinjail.com" \
python -m scraper.sweep ${DRY_RUN} ${REFRESH_KNOWN}

# --- Build (only on real sweep) ---
if [[ -z "$DRY_RUN" ]]; then
    echo "running web.build ..."
    JCSTREAM_SITE_BASE_URL="" \
    JCSTREAM_CNAME="www.aretheyinjail.com" \
    python -m web.build
fi

# --- Commit + push if there's anything to ship ---
if [[ -n "$DRY_RUN" ]]; then
    echo "(dry-run) showing changes that would be committed:"
    git status --short data/ docs/
    exit 0
fi

if git diff --quiet data/ docs/; then
    echo "no changes to data/ or docs/; nothing to commit."
    exit 0
fi

echo "committing..."
git add data/ docs/
git commit -m "data+site: local sweep $(date -u +%Y-%m-%dT%H:%MZ) (residential IP)"

echo "pushing to origin/main..."
git push origin main

echo "done. local sweep committed and pushed."
