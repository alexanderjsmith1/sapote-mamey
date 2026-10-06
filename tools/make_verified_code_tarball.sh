#!/usr/bin/env bash
# Build a CODE tarball only after explicit sealed-ZIP and local seal-receipt verification.
set -euo pipefail

if [ "$#" -ne 4 ] || [ ! -d "$1" ] || [ ! -f "$3" ] || [ ! -f "$4" ]; then
  echo "REFUSED: usage: make_verified_code_tarball.sh FRESH_CODE_DIR OUTDIR SEALED_CODE_ZIP SELECTED_SEAL_RECEIPT" >&2
  exit 2
fi
src="$(cd -- "$1" && pwd -P)"
outdir="$2"
sealed_zip="$3"
seal_receipt="$4"
name="$(basename "$src")"
tool_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
scratch="$(mktemp -d "${TMPDIR:-/tmp}/mamey-code-tarball.XXXXXXXX")"
trap 'rm -rf -- "$scratch"' EXIT

if ! bash "$tool_dir/make_release_tarball.sh" "$src" "$scratch" >/dev/null; then
  echo "REFUSED: CODE tarball producer failed" >&2
  exit 2
fi
archive="$scratch/$name.tar.gz"
sidecar="$scratch/$name.tar.gz.sha256"
# Bind the produced bytes before verification; publish only this exact pair.
archive_sha="$(shasum -a 256 "$archive" | awk '{print $1}')"
sidecar_sha="$(shasum -a 256 "$sidecar" | awk '{print $1}')"
verification_log="$scratch/verification.log"
if ! python3 "$tool_dir/verify_release_tarball.py" "$archive" \
  --zip "$sealed_zip" --seal-receipt "$seal_receipt" >"$verification_log"; then
  cat "$verification_log" >&2
  echo "REFUSED: CODE tarball differs from the selected sealed ZIP/receipt" >&2
  exit 2
fi
if ! (cd "$scratch" && shasum -c -- "$name.tar.gz.sha256" >/dev/null); then
  echo "REFUSED: CODE tarball SHA-256 sidecar failed" >&2
  exit 2
fi
mkdir -p "$outdir"
outdir="$(cd -- "$outdir" && pwd -P)"
if ! python3 "$tool_dir/publish_verified_pair.py" "$archive" "$sidecar" "$outdir" "$archive_sha" "$sidecar_sha"; then
  echo "HOLD: verified pair publication incomplete; read the committed-path receipt above" >&2
  exit 2
fi
printf 'verified CODE tarball: %s\n' "$outdir/$name.tar.gz"
printf 'sha256 sidecar: %s\n' "$outdir/$name.tar.gz.sha256"
