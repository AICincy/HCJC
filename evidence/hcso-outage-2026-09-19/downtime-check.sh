#!/usr/bin/env bash
# HCSO inmate-detail outage watch: one timestamped TSV row per probe.
# Appends to downtime-checks.tsv in this directory. Never fails hard:
# every outcome (including curl/network errors) is recorded as a row.
# Called by the scheduled "hcso-outage-watch" job and safe to run by hand.
set -u

DIR="$(cd "$(dirname "$0")" && pwd)"
TSV="$DIR/downtime-checks.tsv"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

BASE="https://www.hcso.org"
DETAIL_URL="$BASE/justice-center-services/inmate-search/inmate-detail/?id=1261360"
LIST_URL="$BASE/justice-center-services/inmate-search/"
# Cincinnati open-data portal (Socrata): comparator site for the HCSO outage.
# Monitored by the same watch so any downtime is recorded the same way.
CINCY_PORTAL_URL="https://data.cincinnati-oh.gov/"
CINCY_API_URL="https://api.us.socrata.com/api/catalog/v1?domains=data.cincinnati-oh.gov&limit=1"

if [ ! -f "$TSV" ]; then
  printf "timestamp_utc\tcheck\thttp_code\tbytes\turl\n" > "$TSV"
fi

probe() { # $1 = label, $2 = url
  local out code bytes
  out="$(curl -s -o /dev/null -w "%{http_code} %{size_download}" --max-time 25 "$2" 2>/dev/null)" || out="curl_error 0"
  code="${out%% *}"
  bytes="${out##* }"
  printf "%s\t%s\t%s\t%s\t%s\n" "$TS" "$1" "$code" "$bytes" "$2" >> "$TSV"
  printf "%s=%s(%sB) " "$1" "$code" "$bytes"
}

echo "--- hcso outage watch $TS ---"
probe "detail" "$DETAIL_URL"
probe "list" "$LIST_URL"
probe "cincy-portal" "$CINCY_PORTAL_URL"
probe "cincy-api" "$CINCY_API_URL"
echo ""
echo "appended to $TSV"
