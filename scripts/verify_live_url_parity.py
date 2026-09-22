"""Probe published JSON URLs and compare them with a local build contract.

Default mode deliberately checks availability and JSON shape, not byte equality:
the live site may contain a newer data vintage than a pull-request build. Use
``--compare-bytes`` only when validating a frozen release candidate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def fetch(url: str, timeout: float) -> tuple[int, str, bytes]:
    request = Request(url, headers={"User-Agent": "HCJC-live-parity/1.0", "Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        return response.status, response.headers.get("content-type", ""), response.read()


def shape(value: object) -> str:
    if isinstance(value, dict):
        return "object:" + ",".join(sorted(value))
    if isinstance(value, list):
        return "array"
    return type(value).__name__


def main() -> int:
    parser = argparse.ArgumentParser(description="Check that live public JSON URLs remain compatible.")
    parser.add_argument("--site", default="https://www.aretheyinjail.com")
    parser.add_argument("--manifest", type=Path, default=Path("config/public-data-manifest.json"))
    parser.add_argument("--local", type=Path, default=Path("docs/data"))
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--compare-bytes", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors: list[str] = []
    checked = 0
    for entry in manifest["files"]:
        name = entry["path"]
        local_path = args.local / name
        if not local_path.is_file():
            errors.append(f"local artifact missing: {local_path}")
            continue
        try:
            local_bytes = local_path.read_bytes()
            local_value = json.loads(local_bytes)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"local JSON invalid: {name}: {exc}")
            continue
        url = args.site.rstrip("/") + "/data/" + name
        try:
            status, content_type, remote_bytes = fetch(url, args.timeout)
            remote_value = json.loads(remote_bytes)
        except HTTPError as exc:
            errors.append(f"{name}: HTTP {exc.code} from {url}")
            continue
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append(f"{name}: live probe failed: {exc}")
            continue
        if status < 200 or status >= 300:
            errors.append(f"{name}: unexpected HTTP status {status}")
        if "json" not in content_type.lower():
            errors.append(f"{name}: unexpected content type {content_type!r}")
        if shape(local_value) != shape(remote_value):
            errors.append(f"{name}: local/live JSON shape differs ({shape(local_value)} vs {shape(remote_value)})")
        if args.compare_bytes and local_bytes != remote_bytes:
            errors.append(f"{name}: local/live bytes differ")
        checked += 1

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"live URL parity failed: {len(errors)} error(s), {checked} file(s) checked")
        return 1
    print(f"live URL parity OK: {checked} published JSON URL(s) checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
