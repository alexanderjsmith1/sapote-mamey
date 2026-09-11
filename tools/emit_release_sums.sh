#!/usr/bin/env bash
# emit_release_sums.sh -- emit SHA256SUMS.txt over the cut tier zips at the release root (PC-04).
# Restores the bundle-root integrity file that v9.7.34 dropped. Run after cutting + zipping all four tiers.
# Usage: tools/emit_release_sums.sh <release_dir>   (default: .)
set -euo pipefail
ROOT="${1:-.}"
cd "$ROOT"
shopt -s nullglob
# v9.7.409 portability: macOS ships `shasum -a 256`, not GNU `sha256sum`. Fall back to it
# (matches the blessed idiom in release.sh:66). `shasum -a 256 -c` verifies just like `-c`.
sha256() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi; }
zips=( sapote-mamey-v*.zip )
if (( ${#zips[@]} == 0 )); then echo "no sapote-mamey-v*.zip found in $ROOT" >&2; exit 1; fi
sha256 "${zips[@]}" > SHA256SUMS.txt
echo "wrote SHA256SUMS.txt over ${#zips[@]} tier zip(s)"
sha256 -c SHA256SUMS.txt
