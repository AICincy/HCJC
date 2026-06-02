"""Append-only PRA (Public Records Act) send log with SHA-256 hash chain.

Mirrors the WAF-block evidence log pattern in ``scraper.store``: every PRA
email sent (or dry-run logged) is appended to ``data/pra_requests.json``
with a ``prev_sha256`` field linking to the prior record. This produces a
tamper-evident chain that proves *when* each request was transmitted, which
is critical for statutory-damages timelines under ORC § 149.43(C)(2).

The log also carries ``response_received_utc`` and ``response_notes``
fields (initially null) so a human operator can record responses via
``python -m scraper.pra_log record-response``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

PRA_LOG_PATH = Path("data/pra_requests.json")

_pra_lock = threading.Lock()


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


_MUTABLE_FIELDS = {"response_received_utc", "response_notes"}


def _record_sha256(record: dict) -> str:
    immutable = {k: v for k, v in record.items() if k not in _MUTABLE_FIELDS}
    canonical = json.dumps(immutable, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_pra_log(path: Path = PRA_LOG_PATH) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def append_pra_record(record: dict, path: Path = PRA_LOG_PATH) -> None:
    """Append one PRA send record with hash chain linkage.

    Thread-safe via a module-level lock. The caller supplies the record
    dict (without ``prev_sha256``, ``sent_utc``, or ``request_id``);
    this function populates those fields and writes atomically.
    """
    with _pra_lock:
        entries = load_pra_log(path)
        now = datetime.now(timezone.utc)
        record["sent_utc"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        seq = len(entries) + 1
        date_tag = now.strftime("%Y%m%d")
        record["request_id"] = f"pra-{date_tag}-{record['module']}-{seq:03d}"
        record["prev_sha256"] = _record_sha256(entries[-1]) if entries else None
        entries.append(record)
        _atomic_write_text(path, json.dumps(entries, indent=2) + "\n")


def verify_pra_chain(entries: list[dict]) -> list[str]:
    """Verify the ``prev_sha256`` hash chain. Returns a list of problems
    (empty = intact). Same contract as ``store.verify_block_chain``."""
    problems: list[str] = []
    for i, rec in enumerate(entries):
        expected = _record_sha256(entries[i - 1]) if i > 0 else None
        actual = rec.get("prev_sha256")
        if actual != expected:
            problems.append(
                f"record {i} (request_id={rec.get('request_id')!r}, "
                f"sent_utc={rec.get('sent_utc')!r}): "
                f"prev_sha256={actual!r}, expected {expected!r}"
            )
    return problems


def make_pra_record(
    *,
    module: str,
    to: str,
    subject: str,
    window_since: str,
    window_until: str,
    status: str,
) -> dict:
    """Build a PRA log record dict ready for ``append_pra_record``.

    ``sent_utc`` and ``request_id`` are populated by ``append_pra_record``
    under the thread lock, not here.
    ``status`` is one of: ``"sent"``, ``"dry_run"``, ``"failed"``."""
    return {
        "module": module,
        "to": to,
        "subject": subject,
        "window_since": window_since,
        "window_until": window_until,
        "status": status,
        "response_received_utc": None,
        "response_notes": None,
    }


def record_response(
    request_id: str,
    notes: str,
    path: Path = PRA_LOG_PATH,
) -> bool:
    """Mark a PRA request as having received a response.

    Finds the record by ``request_id``, sets ``response_received_utc`` to
    now and ``response_notes`` to the supplied string. Returns True on
    success, False if not found. Does NOT re-chain (the hash chain covers
    the original send record, not the mutable response fields).
    """
    with _pra_lock:
        entries = load_pra_log(path)
        for rec in entries:
            if rec.get("request_id") == request_id:
                rec["response_received_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                rec["response_notes"] = notes
                _atomic_write_text(path, json.dumps(entries, indent=2) + "\n")
                return True
        return False


def _list_pending(path: Path = PRA_LOG_PATH) -> list[dict]:
    """Return PRA records that have status='sent' but no response."""
    entries = load_pra_log(path)
    return [r for r in entries if r.get("status") == "sent" and not r.get("response_received_utc")]


# ---------------------------------------------------------------------------
# CLI: python -m scraper.pra_log {verify,record-response,pending}
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="PRA send log management (hash chain, response tracking).")
    sub = parser.add_subparsers(dest="command")

    # verify
    v = sub.add_parser("verify", help="Verify the PRA log hash chain.")
    v.add_argument("path", nargs="?", default=str(PRA_LOG_PATH))

    # record-response
    rr = sub.add_parser("record-response", help="Record a response to a PRA request.")
    rr.add_argument("request_id", help="The request_id from the PRA log.")
    rr.add_argument("notes", help="Description of the response received.")

    # pending
    sub.add_parser("pending", help="List sent PRA requests with no response.")

    args = parser.parse_args(argv)

    if args.command == "verify":
        entries = load_pra_log(Path(args.path))
        if not entries:
            print(f"{args.path}: no records; nothing to verify.")
            return 0
        problems = verify_pra_chain(entries)
        if problems:
            print(f"{args.path}: hash chain BROKEN ({len(problems)} of {len(entries)} records):")
            for p in problems:
                print(f"  - {p}")
            return 1
        print(f"{args.path}: hash chain intact across {len(entries)} records.")
        return 0

    if args.command == "record-response":
        ok = record_response(args.request_id, args.notes)
        if ok:
            print(f"Recorded response for {args.request_id}.")
            return 0
        print(f"request_id {args.request_id!r} not found in PRA log.")
        return 1

    if args.command == "pending":
        pending = _list_pending()
        if not pending:
            print("No pending PRA requests (all sent requests have responses).")
            return 0
        print(f"{len(pending)} pending PRA request(s):")
        for r in pending:
            print(f"  {r['request_id']}  sent={r['sent_utc']}  to={r['to']}  module={r['module']}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
