#!/usr/bin/env bash
set -euo pipefail

output_dir="prime-numbers"

usage() {
  echo "Usage: $0 [-d <output_dir>]" >&2
  exit 1
}

while getopts ":d:" opt; do
  case "$opt" in
    d) output_dir="$OPTARG" ;;
    *) usage ;;
  esac
done

shift $((OPTIND - 1))
if [ $# -ne 0 ]; then
  usage
fi

mkdir -p "$output_dir"

python3 - "$output_dir/primes.txt" <<'PY'
import sys

limit = 100
primes = []
for candidate in range(2, limit + 1):
    is_prime = True
    for prime in primes:
        if prime * prime > candidate:
            break
        if candidate % prime == 0:
            is_prime = False
            break
    if is_prime:
        primes.append(candidate)

with open(sys.argv[1], "w", encoding="utf-8") as handle:
    handle.write("\n".join(str(prime) for prime in primes) + "\n")
PY
