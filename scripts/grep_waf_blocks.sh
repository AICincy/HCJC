#!/usr/bin/env bash
#
# grep_waf_blocks.sh - summarize WAF-block-shaped responses from recent
# sweep workflow runs.
#
# Reads the `WAF-block-shaped response for id=X (N bytes, streak=K)` log
# lines that scraper/sweep.py emits when it detects a WAF / geo-block on
# an HCSO inmate-detail page, and rolls them up by run, by inmate, and
# by streak distribution.
#
# Usage:
#   scripts/grep_waf_blocks.sh           # last 5 sweep runs
#   scripts/grep_waf_blocks.sh 20        # last 20 sweep runs
#   scripts/grep_waf_blocks.sh main      # all sweep runs on main since today
#
# Requires:
#   gh (the GitHub CLI), authenticated against AICincy/HCJC.
#
set -euo pipefail

REPO="AICincy/HCJC"
WORKFLOW="sweep.yml"
ARG="${1:-5}"

# Resolve which runs to inspect.
if [[ "$ARG" =~ ^[0-9]+$ ]]; then
    LIMIT="$ARG"
    BRANCH_FILTER=()
else
    LIMIT=50
    BRANCH_FILTER=(--branch "$ARG")
fi

echo "fetching last $LIMIT sweep runs from $REPO (gh run list --workflow $WORKFLOW)..."
mapfile -t RUN_IDS < <(
    gh run list \
        --repo "$REPO" \
        --workflow "$WORKFLOW" \
        --limit "$LIMIT" \
        "${BRANCH_FILTER[@]}" \
        --json databaseId,status,conclusion,createdAt \
        --jq '.[] | select(.status=="completed") | .databaseId'
)

if [[ "${#RUN_IDS[@]}" -eq 0 ]]; then
    echo "no completed sweep runs found"
    exit 0
fi

echo "scanning ${#RUN_IDS[@]} runs for WAF-block lines..."
echo

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Collect every WAF-block line across all runs into one file.
ALL_LINES="$TMP/all.txt"
: > "$ALL_LINES"
for run_id in "${RUN_IDS[@]}"; do
    log="$TMP/run-$run_id.log"
    # `gh run view --log` is rate-limited; redirect 2>/dev/null to silence
    # transient 502/503 we'd rather just skip past.
    if gh run view --repo "$REPO" --log "$run_id" > "$log" 2>/dev/null; then
        # Tag each line with the run_id for the per-run summary below.
        grep -E "WAF-block-shaped response for id=" "$log" \
            | sed "s/^/run=$run_id /" \
            >> "$ALL_LINES" || true
    fi
done

TOTAL_BLOCKS=$(wc -l < "$ALL_LINES" | tr -d ' ')
echo "## Summary"
echo "Runs scanned:   ${#RUN_IDS[@]}"
echo "WAF blocks:     $TOTAL_BLOCKS"
echo

if [[ "$TOTAL_BLOCKS" -eq 0 ]]; then
    echo "no WAF blocks observed in this window - either HCSO has stopped"
    echo "blocking us or the new WAF guard hasn't deployed yet"
    exit 0
fi

# Top 10 inmate IDs by block count.
echo "## Top 10 inmates by block count"
grep -oE "id=[0-9]+" "$ALL_LINES" \
    | sort | uniq -c | sort -rn | head -10 \
    | awk '{printf "  %5d  %s\n", $1, $2}'
echo

# Block count per run.
echo "## Blocks per run (last 10)"
awk '{print $1}' "$ALL_LINES" | sort | uniq -c | sort -rn | head -10 \
    | awk '{printf "  %5d blocks  %s\n", $1, $2}'
echo

# Streak distribution: how often does the WAF block clustering escalate?
echo "## Streak distribution"
grep -oE "streak=[0-9]+" "$ALL_LINES" \
    | sort | uniq -c | sort -k2 -t= -n \
    | awk '{printf "  %5d  %s\n", $1, $2}'
echo

# Response size distribution.
echo "## Response size distribution (bytes returned during block)"
grep -oE "\\([0-9]+ bytes" "$ALL_LINES" \
    | tr -d '(' \
    | awk '{print $1}' \
    | sort -n \
    | awk 'BEGIN{c=0;s=0;min=99999999;max=0}
           {c++; s+=$1; if($1<min)min=$1; if($1>max)max=$1; v[c]=$1}
           END{
             printf "  count=%d  min=%d  max=%d  mean=%.0f\n", c, min, max, s/c;
             if(c>0){printf "  median=%d\n", v[int(c/2)+1]}
           }'
echo

echo "(Tune the 5000-byte threshold in scraper/sweep.py _fetch_one if the"
echo " min/max distribution suggests a different separator between blocked"
echo " and valid responses.)"
