#!/usr/bin/env bash
set -euo pipefail

output_dir="prime-numbers"

while getopts ":d:" opt; do
  case "$opt" in
    d) output_dir="$OPTARG" ;;
    *) exit 1 ;;
  esac
done

mkdir -p "$output_dir"

python3 - "$output_dir/primes.txt" <<'PY'
import sys

limit = 100
primes = []
for candidate in range(2, limit + 1):
    for prime in primes:
        if prime * prime > candidate:
            primes.append(candidate)
            break
        if candidate % prime == 0:
            break
    else:
        primes.append(candidate)

with open(sys.argv[1], "w", encoding="utf-8") as handle:
    handle.write("\n".join(str(prime) for prime in primes) + "\n")
PY
