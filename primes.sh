#!/usr/bin/env bash
set -euo pipefail

output_dir="prime-numbers"

while getopts ":d:" opt; do
  case "$opt" in
    d) output_dir="$OPTARG" ;;
    *) exit 1 ;;
  esac
done

cat "$output_dir/primes.txt"
