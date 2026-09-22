# Evidence archive manifests

These manifests record the exact bytes selected for immutable archival before any
tracked source file is removed. They are intentionally small enough to review in
Git. Each corresponding archive must contain `ARCHIVE-MANIFEST.json` and
`SHA256SUMS`; verify a downloaded bundle with:

```bash
python scripts/verify_evidence_archive.py /path/to/archive
```

Prepare a new bundle without changing the repository with:

```bash
bash scripts/create_evidence_archive.sh /path/to/archive
```

The WAF log must also pass its chain verifier before archival. The public
compatibility URL remains `/data/waf_block_log.json`; an archive is additive
until URL-parity and deployment checks have passed.
