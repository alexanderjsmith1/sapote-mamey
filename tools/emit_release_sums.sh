#!/usr/bin/env bash
# emit_release_sums.sh — write and verify SHA256SUMS.txt for matching release ZIPs in one selected directory.
# Matches sapote-mamey-v*.zip; no four-tier set is required. This checks listed file digests, not archive contents or release authority.
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
