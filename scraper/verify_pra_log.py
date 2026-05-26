"""Verify the PRA send log's hash chain (``data/pra_requests.json``).

Exits 0 when the chain is intact (or the log is empty/absent), 1 on a
broken link. Intended as a CI step so an out-of-band edit to the committed
PRA send log fails the build.

Run: ``python -m scraper.verify_pra_log`` (optionally a path argument).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .pra_log import PRA_LOG_PATH, load_pra_log, verify_pra_chain


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify the PRA send log hash chain."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=str(PRA_LOG_PATH),
        help="Path to the PRA log JSON (default: data/pra_requests.json).",
    )
    args = parser.parse_args(argv)
    path = Path(args.path)

    entries = load_pra_log(path)
    if not entries:
        print(f"{path}: no records (file missing or empty); nothing to verify.")
        return 0
    problems = verify_pra_chain(entries)
    if problems:
        print(
            f"{path}: hash chain BROKEN "
            f"({len(problems)} of {len(entries)} records affected):"
        )
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"{path}: hash chain intact across {len(entries)} records.")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
