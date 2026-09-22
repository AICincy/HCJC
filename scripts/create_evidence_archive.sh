#!/usr/bin/env bash
# Prepare a content-addressed evidence bundle without changing tracked files.
# The output directory can be uploaded to immutable storage or a release asset.
set -euo pipefail

output_dir=${1:-"archive-output/$(date -u +%Y-%m-%d)"}
mkdir -p "$output_dir"

python -m scraper.verify_block_log data/waf_block_log.json
cp data/waf_block_log.json "$output_dir/waf_block_log.json"
cp audit-output/ui-ux-remediation-2026-09-22.zip "$output_dir/ui-ux-remediation-2026-09-22.zip"

python - "$output_dir" <<'PY'
import hashlib
import json
import subprocess
import sys
from pathlib import Path

out = Path(sys.argv[1])
artifacts = []
for path in sorted(out.iterdir()):
    if path.name in {"ARCHIVE-MANIFEST.json", "SHA256SUMS"}:
        continue
    artifacts.append({
        "name": path.name,
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    })
try:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
except subprocess.CalledProcessError:
    commit = "unknown"
manifest = {
    "schema_version": 1,
    "created_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z"),
    "source_repository": "https://github.com/AICincy/HCJC",
    "source_commit": commit,
    "public_compatibility_url": "https://www.aretheyinjail.com/data/waf_block_log.json",
    "verification": ["python -m scraper.verify_block_log data/waf_block_log.json", "sha256sum -c SHA256SUMS"],
    "artifacts": artifacts,
}
(out / "ARCHIVE-MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
lines = []
for path in sorted(out.iterdir()):
    if path.name == "SHA256SUMS":
        continue
    lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
(out / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

printf 'Evidence archive prepared at %s\n' "$output_dir"
cat "$output_dir/ARCHIVE-MANIFEST.json"
