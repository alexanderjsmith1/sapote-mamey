#!/usr/bin/env bash
# release.sh — single fail-closed build entrypoint for a Sapote-Mamey release (v9.7.97).
#
# Closes two orphaned pieces by orchestrating them in the one place a build happens:
#   - log_release.py runs ONCE here (build-prep), before any tier is cut, so the source
#     RELEASES_LOG.md is identical across all four tiers (no mid-build tier-parity break).
#   - check_tier_parity.py runs ONCE here, AFTER all four tiers exist, as the final gate
#     (it needs all four zips, so it cannot live inside the per-tier make_public_tier.sh).
#
# Usage:  tools/release.sh <stamp> <out_dir> [src_dir] [--with-public]
#         SKIP_INTIER_PYTEST=1 tools/release.sh ...   # skip the heavy per-tier suite (verify out-of-band)
set -euo pipefail
STAMP="${1:?stamp, e.g. 20260620-(n)}"; OUT="${2:?output dir}"
shift 2
SRC="."
SRC_SET=0
WITH_PUBLIC=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --with-public) WITH_PUBLIC=1 ;;
    *)
      if [ "$SRC_SET" -eq 1 ]; then
        echo "unknown option or extra source directory: $1" >&2
        exit 2
      fi
      SRC="$1"
      SRC_SET=1
      ;;
  esac
  shift
done
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$OUT"

echo "== build-prep: log the release row (idempotent) =="
python3 "$HERE/log_release.py" --stamp "$STAMP"

TIERS=(merged code clean sid)
if [ "$WITH_PUBLIC" -eq 1 ]; then
  # make_public_tier.sh performs the authoritative GOV-001 ACTIVE,
  # signed, non-invalidated check before staging the promotion.
  TIERS+=(public)
fi

echo "== cut requested tiers =="
# Order matters: merged first (parity reference for code/clean tier-derivation gate),
# code/clean next (redacted views, parity-checked against merged), sid last (SID-specific anonymization).
for TIER in "${TIERS[@]}"; do
  echo "-- $TIER --"
  BUILD_STAMP="$STAMP" bash "$HERE/make_public_tier.sh" "$TIER" "$SRC" "$OUT"
done

echo "== post-build gate: release identity / LLM bootstrap freshness =="
python3 "$HERE/verify_release_identity.py" --root "$SRC" --tiers-dir "$OUT" \
  || { echo "FATAL: release identity / LLM bootstrap freshness FAILED — do not publish this build." >&2; exit 8; }

echo "== post-build gate: cross-tier parity (check_tier_parity) =="
PARITY_ARGS=(--tiers-dir "$OUT")
if [ "$WITH_PUBLIC" -eq 1 ]; then PARITY_ARGS+=(--with-public); fi
python3 "$HERE/check_tier_parity.py" "${PARITY_ARGS[@]}" \
  || { echo "FATAL: cross-tier parity FAILED — do not publish this build." >&2; exit 7; }

# P6 (v9.7.101): restore the bundle-root SHA256SUMS over the four tier zips (dropped in v9.7.100).
# Per-tier SOURCE_CHECKSUMS still ship inside each zip; this is the convenience cross-tier verify.
echo "== emit top-level SHA256SUMS_$STAMP.txt =="
( cd "$OUT" && { command -v sha256sum >/dev/null 2>&1 && sha256sum *.zip || shasum -a 256 *.zip; } > "SHA256SUMS_$STAMP.txt" ) \
  && echo "  wrote $OUT/SHA256SUMS_$STAMP.txt ($(wc -l < "$OUT/SHA256SUMS_$STAMP.txt") entries)" \
  || echo "  WARN: could not write SHA256SUMS (no sha256sum/shasum?)" >&2

echo "== release build OK: $STAMP -> $OUT =="
