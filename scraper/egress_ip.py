"""Snapshot the GitHub Actions egress IP evidence for the WAF-block record.

Records, for a single moment, the runner's public IP and GitHub's published
Actions egress CIDR ranges (from api.github.com/meta), and whether the runner
IP falls within them. This documents that the source HCSO's WAF blocked is a
GitHub Actions address inside GitHub's own published range. Stdlib only; safe
read-only GET requests, no evasion.

Run: ``python -m scraper.egress_ip [runner_ip] [--out PATH]``
Prints the snapshot JSON; with ``--out`` it also writes the file (git history
is the durable, timestamped log).
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import sys
import urllib.request
from pathlib import Path

from .models import utcnow_iso

META_URL = "https://api.github.com/meta"
IPIFY_URL = "https://api.ipify.org?format=json"


def _get_json(url: str, timeout: float = 30.0) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def github_actions_ranges() -> list[str]:
    """The CIDR ranges GitHub publishes for Actions egress."""
    return list(_get_json(META_URL).get("actions", []))


def runner_public_ip() -> str | None:
    """Best-effort public IP of the current host; None on lookup failure."""
    try:
        return _get_json(IPIFY_URL).get("ip")
    except Exception:
        return None


def ip_in_ranges(ip: str, ranges: list[str]) -> bool:
    """True when ``ip`` falls within any CIDR in ``ranges``."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for cidr in ranges:
        try:
            if addr in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def snapshot(runner_ip: str | None) -> dict:
    """One egress-evidence record: the runner IP, the published Actions range
    count, and whether the IP is inside that range."""
    ranges = github_actions_ranges()
    ip = runner_ip or runner_public_ip()
    return {
        "captured_utc": utcnow_iso(),
        "runner_ip": ip,
        "actions_range_count": len(ranges),
        "runner_ip_in_actions_range": ip_in_ranges(ip, ranges) if ip else None,
        "source": META_URL,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Snapshot GitHub Actions egress IP evidence.")
    parser.add_argument("runner_ip", nargs="?",
                        help="Runner public IP to check (default: best-effort lookup).")
    parser.add_argument("--out", help="Also write the snapshot JSON to this path.")
    args = parser.parse_args(argv)

    rec = snapshot(args.runner_ip)
    print(json.dumps(rec, indent=2))
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
