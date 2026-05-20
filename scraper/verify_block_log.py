"""Verify the WAF-block evidence log's hash chain (`data/waf_block_log.json`).

Walks the append-only log and checks every record's ``prev_sha256`` link
against the canonical SHA-256 of the record before it. Intended as an on-demand
integrity proof for counsel: a clean run shows the committed evidence file has
not been edited or had records removed out of band. Wholesale file deletion is
caught by git history, not by the chain.

Exits 0 when the chain is intact (or the log is empty), 1 when a link is broken.

Run: ``python -m scraper.verify_block_log`` (optionally a path argument).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .store import WAF_BLOCK_LOG_PATH, load_block_log, verify_block_chain


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the WAF-block evidence log hash chain.")
    parser.add_argument("path", nargs="?", default=str(WAF_BLOCK_LOG_PATH),
                        help="Path to the block log JSON (default: data/waf_block_log.json).")
    args = parser.parse_args(argv)
    path = Path(args.path)

    entries = load_block_log(path)
    if not entries:
        print(f"{path}: no records (file missing or empty); nothing to verify.")
        return 0
    problems = verify_block_chain(entries)
    if problems:
        print(f"{path}: hash chain BROKEN ({len(problems)} of {len(entries)} records affected):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"{path}: hash chain intact across {len(entries)} records.")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
