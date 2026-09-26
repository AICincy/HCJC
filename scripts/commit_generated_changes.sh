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

published_paths=("$@")

is_published_path() {
  local file=$1
  local published
  for published in "${published_paths[@]}"; do
    if [[ "$file" == "$published" || "$file" == "$published"/* ]]; then
      return 0
    fi
  done
  return 1
}

generated_utc_of() {
  python3 -c 'import json,sys
p=sys.argv[1]
try:
    with open(p,encoding="utf-8") as f:
        data=json.load(f)
except Exception:
    print("")
    raise SystemExit
print(data.get("generated_utc") or "")
' "$1" 2>/dev/null || true
}

resolve_generated_rebase_conflicts() {
  local conflicts file stage2 stage3 pick
  conflicts=$(git diff --name-only --diff-filter=U || true)
  if [[ -z "$conflicts" ]]; then
    return 1
  fi
  while IFS= read -r file; do
    if ! is_published_path "$file"; then
      echo "non-generated conflict: $file" >&2
      return 1
    fi
  done <<< "$conflicts"

  pick="theirs"
  if git diff --name-only --diff-filter=U | grep -qx "data/current.json"; then
    stage2=$(mktemp)
    stage3=$(mktemp)
    git show :2:data/current.json > "$stage2"
    git show :3:data/current.json > "$stage3"
    ours_utc=$(generated_utc_of "$stage2")
    theirs_utc=$(generated_utc_of "$stage3")
    rm -f "$stage2" "$stage3"
    # Stage 2 is upstream (origin tip). Stage 3 is this run.
    # Keep the newer roster; equal timestamps keep this run.
    if [[ -n "$ours_utc" && -n "$theirs_utc" && "$ours_utc" > "$theirs_utc" ]]; then
      pick="ours"
    fi
  fi

  while IFS= read -r file; do
    git checkout --"$pick" -- "$file"
    git add -- "$file"
  done <<< "$conflicts"
  echo "resolved generated rebase conflicts using $pick"
  GIT_EDITOR=true git rebase --continue
}

# Stage only the outputs owned by the invoking workflow.
git add -- "${published_paths[@]}"
if git diff --cached --quiet; then
  echo "no changes"
  exit 0
fi

git config user.name "${GIT_COMMIT_NAME:-jcstream-bot}"
git config user.email "${GIT_COMMIT_EMAIL:-noreply@github.com}"
git commit -m "$commit_message"

git fetch --no-tags origin "$target_branch:refs/remotes/origin/$target_branch"
if ! git rebase "origin/$target_branch"; then
  if resolve_generated_rebase_conflicts; then
    :
  else
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
fi

git push origin "HEAD:$target_branch"
