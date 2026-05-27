#!/usr/bin/env python3
import json
import hashlib

# Record 29 (index 29): pra-20260527-capias-029
record_29 = {
    "module": "capias",
    "to": "HCAdmin@hamilton-co.org",
    "subject": "Public Records Act Request \u2014 Daily New Capias / Bench Warrant Roster (Clerk of Courts)",
    "window_since": None,
    "window_until": None,
    "status": "dry_run",
    "response_received_utc": None,
    "response_notes": None,
    "sent_utc": "2026-05-27T05:00:11Z",
    "request_id": "pra-20260527-capias-029",
    "prev_sha256": "140986aab416da688922e53d5f2168c4dfa7cec7e4e1a04187a45e571edfe069"
}

canonical = json.dumps(record_29, sort_keys=True, separators=(",", ":"))
hash_value = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
print(f"Hash of record 29: {hash_value}")
