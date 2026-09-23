#!/usr/bin/env bash
# Commit generated repository changes, rebase onto the current target branch,
# and push without silently merging or dropping concurrent data updates.
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 TARGET_BRANCH COMMIT_MESSAGE PATH..." >&2
  exit 64
fi

target_branch=$1
commit_message=$2
shift 2

if [[ $# -eq 0 ]]; then
  echo "no paths supplied" >&2
  exit 64
fi

# Stage only the outputs owned by the invoking workflow.
git add -- "$@"
if git diff --cached --quiet; then
  echo "no changes"
  exit 0
fi

git config user.name "${GIT_COMMIT_NAME:-jcstream-bot}"
git config user.email "${GIT_COMMIT_EMAIL:-noreply@github.com}"
git commit -m "$commit_message"

git fetch --no-tags origin "$target_branch:refs/remotes/origin/$target_branch"
if ! git rebase "origin/$target_branch"; then
  conflicts=$(git diff --name-only --diff-filter=U || true)
  echo "::error::Rebase conflict while publishing generated changes; refusing merge fallback." >&2
  if [ -n "$conflicts" ]; then
    echo "conflicting paths:" >&2
    printf '%s\n' "$conflicts" | sed 's/^/  /' >&2
  fi
  echo "hint: re-run this workflow from the fresh $target_branch tip; the next scheduled sweep also self-heals." >&2
  git rebase --abort 2>/dev/null || true
  exit 1
fi

git push origin "HEAD:$target_branch"
