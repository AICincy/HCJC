"""Verify the public JSON compatibility contract and generated mirrors.

The manifest is intentionally small and reviewable: it records every JSON path
published below /data/, whether it is copied from canonical pipeline data or
computed during the build, and its privacy class.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


DEFAULT_MANIFEST = Path("config/public-data-manifest.json")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root: Path, manifest_path: Path) -> list[str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest["files"]
    errors: list[str] = []
    public_dir = root / "docs" / "data"
    source_root = root

    expected = {entry["path"] for entry in entries}
    actual = {p.name for p in public_dir.glob("*.json")}
    for name in sorted(expected - actual):
        errors.append(f"missing published JSON: docs/data/{name}")
    for name in sorted(actual - expected):
        errors.append(f"unregistered published JSON: docs/data/{name}")

    sums_path = public_dir / "SHA256SUMS"
    sums = sums_path.read_text(encoding="utf-8") if sums_path.exists() else ""
    for entry in entries:
        name = entry["path"]
        public_path = public_dir / name
        if not public_path.exists():
            continue
        if f"  {name}\n" not in sums:
            errors.append(f"missing checksum entry: {name}")
        source = entry.get("source")
        if entry.get("mode") == "copy" and source:
            source_path = source_root / source
            if not source_path.exists():
                errors.append(f"missing canonical source: {source}")
            elif sha256(source_path) != sha256(public_path):
                errors.append(f"source/public mismatch: {source} != docs/data/{name}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify published JSON data paths and mirrors.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    errors = verify(args.root.resolve(), args.manifest)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("public data manifest and source mirrors: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
