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

if [ ! -f "$output_dir/primes.txt" ]; then
  echo "Error: '$output_dir/primes.txt' not found. Please run generate-primes.sh first." >&2
  exit 1
fi

cat "$output_dir/primes.txt"
