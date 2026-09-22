"""Verify an evidence archive against its self-described manifest.

This check is intentionally independent of Git history and external storage:
run it after downloading an archive from a release or object store.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a prepared HCJC evidence archive.")
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    root = args.archive
    manifest_path = root / "ARCHIVE-MANIFEST.json"
    checksum_path = root / "SHA256SUMS"
    if not manifest_path.is_file() or not checksum_path.is_file():
        print("ERROR: archive requires ARCHIVE-MANIFEST.json and SHA256SUMS")
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for artifact in manifest.get("artifacts", []):
        path = root / artifact["name"]
        if not path.is_file():
            errors.append(f"missing artifact: {artifact['name']}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != artifact["sha256"]:
            errors.append(f"manifest hash mismatch: {artifact['name']}")
        if path.stat().st_size != artifact["bytes"]:
            errors.append(f"manifest size mismatch: {artifact['name']}")

    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, _, name = line.partition("  ")
        path = root / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            errors.append(f"checksum mismatch: {name}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"evidence archive OK: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
