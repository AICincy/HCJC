#!/usr/bin/env bash
#
# peek_hcso.sh - one-shot diagnostic: fetch an HCSO inmate-detail page and
# report response size + photo tag shape. Useful for confirming whether
# the local network is currently being served full-size responses or
# WAF-blocked truncated ones, without running a full sweep.
#
# Usage:
#   scripts/peek_hcso.sh 14809523        # fetch one inmate id
#   scripts/peek_hcso.sh 14809523 2643322 14536455   # fetch several
#
# Exit codes:
#   0  every URL returned a "valid-looking" response (>=5 KB with photo
#      markers OR no-photo markers)
#   1  one or more URLs returned a WAF-block-shaped response (<5 KB)
#   2  bad arguments / network failure
#
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "usage: $(basename "$0") <inmate_id> [inmate_id ...]" >&2
    exit 2
fi

BASE="https://www.hcso.org/justice-center-services/inmate-search/inmate-detail/"
# Match the User-Agent the scraper uses so the WAF treats us identically.
UA="JCStream/0.1 (+https://github.com/AICincy/JCStream; Hamilton County OH public-records mirror; peek)"

OVERALL_RC=0
for id in "$@"; do
    if ! [[ "$id" =~ ^[0-9]+$ ]]; then
        echo "skipping non-numeric id: $id" >&2
        OVERALL_RC=2
        continue
    fi
    tmp=$(mktemp)
    trap 'rm -f "$tmp"' EXIT

    # `?id=N` is the canonical detail URL form (verified via the 2026-05-19
    # Claude.ai HCSO check). Path-style `/inmate-detail/N/` returns an empty
    # WordPress shell.
    http_code=$(curl -s -o "$tmp" \
                     -A "$UA" \
                     -w "%{http_code}" \
                     --max-time 30 \
                     "${BASE}?id=${id}" || echo "000")

    size_bytes=$(wc -c < "$tmp" | tr -d ' ')

    # Heuristics that match the parser's hooks.
    has_data_photo="no"
    has_274px="no"
    has_charges_label="no"
    if [[ "$size_bytes" -gt 0 ]]; then
        grep -q 'src="data:image' "$tmp" && has_data_photo="yes"
        grep -q '274px' "$tmp" && has_274px="yes"
        grep -qi 'Charges' "$tmp" && has_charges_label="yes"
    fi

    # Classify.
    verdict="unknown"
    if [[ "$http_code" != "200" ]]; then
        verdict="non-200 ($http_code)"
        OVERALL_RC=2
    elif [[ "$size_bytes" -lt 5000 ]]; then
        verdict="WAF-block-shaped (<5KB)"
        OVERALL_RC=1
    elif [[ "$has_data_photo" == "yes" && "$has_274px" == "yes" ]]; then
        verdict="full-photo OK"
    elif [[ "$has_charges_label" == "yes" ]]; then
        verdict="no-photo OK (page exists, no mug shot)"
    else
        verdict="parsed-but-shape-unfamiliar"
    fi

    printf "id=%-10s status=%-3s size=%-7s data-photo=%-3s 274px=%-3s charges=%-3s verdict=%s\n" \
        "$id" "$http_code" "$size_bytes" \
        "$has_data_photo" "$has_274px" "$has_charges_label" "$verdict"

    rm -f "$tmp"
done

exit "$OVERALL_RC"
