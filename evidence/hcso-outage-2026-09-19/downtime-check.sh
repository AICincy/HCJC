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
DETAIL_PATH="justice-center-services/inmate-search/inmate-detail/"
LIST_URL="$BASE/justice-center-services/inmate-search/"
# Cincinnati open-data portal (Socrata): comparator site for the HCSO outage.
# Monitored by the same watch so any downtime is recorded the same way.
CINCY_PORTAL_URL="https://data.cincinnati-oh.gov/"
CINCY_API_URL="https://api.us.socrata.com/api/catalog/v1?domains=data.cincinnati-oh.gov&limit=1"

# Recovery rule (see the hcso-outage-watch cron doc): "recovered" means a
# detail probe returning HTTP 200 with a body above RECOVERY_BYTES_FLOOR.
# HCSO's empty-page block mode serves HTTP 200 with a ~162 B body, so code
# alone is not a recovery signal. A real detail page is ~100 KB.
RECOVERY_BYTES_FLOOR=5000

# Detail probe IDs (M-2): prefer up to 3 inmate IDs from the current roster so
# a single release cannot turn the probe into a permanent false "still down"
# (one 404 while the service is fully up would hide a real recovery).
# Falls back to the historic ID when the roster is unavailable.
DETAIL_IDS="$(python3 -c "
import json
try:
    snap = json.load(open('$DIR/../../data/current.json', encoding='utf-8'))
    ids = [i['inmate_number'] for i in snap.get('inmates', [])[:3]]
    print(' '.join(ids) if ids else '1261360')
except Exception:
    print('1261360')
" 2>/dev/null)"
[ -n "$DETAIL_IDS" ] || DETAIL_IDS="1261360"

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
n=0
for id in $DETAIL_IDS; do
  n=$((n + 1))
  [ "$n" -gt 3 ] && break
  probe "detail[$id]" "$BASE/$DETAIL_PATH?id=$id"
done
probe "list" "$LIST_URL"
probe "cincy-portal" "$CINCY_PORTAL_URL"
probe "cincy-api" "$CINCY_API_URL"
echo ""
echo "appended to $TSV"
