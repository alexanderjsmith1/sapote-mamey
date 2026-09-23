#!/usr/bin/env bash
# release_cut.sh — one-command, gate-enforced release cut.
#
# Sequence (each step is easy to get wrong by hand):
#   1. author writes the CHANGELOG entry (bold-bullet headlines) BEFORE running this
#   2. atomically bump SSOT version + BUILD_STAMP + TIER_MANIFEST stamp
#   3. sync_version propagates the version everywhere
#   4. sync the README release footer (verify_release_identity checks README carries ver+build)
#   5. refresh source-stage membership/checksums after all source mutations
#   6. run the suite once to measure the stale-manifest baseline
#   7. converge RELEASE_MANIFEST, refresh integrity, then require a final green suite
#   8. bind the final green log and refresh source integrity one last time
#   9. fail closed if backup/editor debris exists; never silently delete it
#  10. gates: sync --check, manifest --check, verify_release_identity
#  11. cut all five tiers (each runs its own leak-audit / parity / checksum gates)
#  12. emit SHA256SUMS + a per-tier receipt
#
# Usage:  tools/release_cut.sh <bundle_version> <src_dir> <out_dir> [build_letter] [--skip-tests]
#         --skip-tests additionally requires PYTEST_RECEIPT=/absolute/receipt.json and
#         PYTEST_RECEIPT_SHA256=<sha256>; a free-text PYTEST_LOG is never sufficient.
# Date:   pinned via RELEASE_DATE=YYYYMMDD (defaults to today) so a rolled clock can't desync a cut.
# Example: RELEASE_DATE=20260710 tools/release_cut.sh 9.7.258 . ../cut258 a
set -euo pipefail

VER="${1:?bundle version, e.g. 9.7.258}"; SRC="${2:?source tree root}"; OUT="${3:?output dir}"
LETTER="${4:-a}"; SKIP_TESTS=0; [[ "${5:-}" == "--skip-tests" ]] && SKIP_TESTS=1
DATE="${RELEASE_DATE:-$(date +%Y%m%d)}"
STAMP="${DATE}v$(echo "$VER" | tr -d '.')${LETTER}"
cd "$SRC"; SRC="$(pwd)"; OUT="$(cd "$(dirname "$OUT")" && pwd)/$(basename "$OUT")"
say(){ printf '\n=== %s ===\n' "$*"; }; die(){ printf '\nABORT: %s\n' "$*" >&2; exit 1; }

assert_no_backup_debris(){
  local offender
  offender="$(find . -type f \( -name '*-E' -o -name '*.orig' -o -name '*.rej' -o -name '*.bak' -o -name '*~' \) ! -path './.git/*' -print -quit)"
  [[ -z "$offender" ]] || die "backup/editor debris present: $offender — remove or adjudicate it before cutting."
}

# Source integrity necessarily becomes stale after a patch, version sync, generated-surface update,
# or RELEASE_MANIFEST rewrite. Regenerate both records from the tier builder's tracked-file policy;
# SOURCE_CHECKSUMS includes TIER_MANIFEST, excludes itself, and is written last.
refresh_source_integrity(){
  local tier_tmp
  tier_tmp="$(mktemp)"
  python3 tools/tracked_file_policy.py --emit-manifest . code "$VER" "$STAMP" > "$tier_tmp"
  mv "$tier_tmp" TIER_MANIFEST.txt
  python3 - "$SRC" <<'PY'
import hashlib
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / "tools"))
from tracked_file_policy import tracked_paths

paths = [p[2:] if p.startswith("./") else p for p in tracked_paths(root)]
paths.append("TIER_MANIFEST.txt")
rows = []
for rel in sorted(set(paths), key=lambda value: value.encode()):
    digest = hashlib.sha256((root / rel).read_bytes()).hexdigest()
    rows.append(f"{digest}  ./{rel}\n")
tmp = root / "SOURCE_CHECKSUMS_SHA256.txt.tmp"
tmp.write_text("".join(rows), encoding="utf-8")
tmp.replace(root / "SOURCE_CHECKSUMS_SHA256.txt")
PY
  python3 tools/check_release_manifest.py --root . --quiet
}

pytest_counts(){
  python3 - "$1" <<'PY'
import pathlib
import re
import sys

text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
summary = None
pattern = re.compile(r"\b\d+\s+passed\b.*\bin\s+\d+(?:\.\d+)?s\b")
for line in text.splitlines():
    if pattern.search(line):
        summary = line
if summary is None:
    raise SystemExit("pytest log has no complete terminal summary")
passed = re.search(r"(\d+)\s+passed\b", summary)
skipped = re.search(r"(\d+)\s+skipped\b", summary)
print(passed.group(1), skipped.group(1) if skipped else "0")
PY
}

say "validate CHANGELOG top entry for v$VER"
head -1 CHANGELOG.md | grep -q "v$VER" || die "CHANGELOG top entry is not v$VER — write it first."
awk 'NR>1 && /^# v9/{exit} {print}' CHANGELOG.md | grep -qE '^- \*\*' \
  || die "CHANGELOG v$VER entry has no '- **bold**' bullets (patch-line parser needs them)."

say "preflight: no backup/editor debris"
assert_no_backup_debris

say "atomically bump to $VER / $STAMP"
python3 tools/rewrite_release_identity.py "$VER" "$STAMP" --root .

say "sync_version (propagate)"; python3 tools/sync_version.py >/dev/null
# (sync_version maintains the README "Current bundle: v… / engine … · build …" footer itself)
python3 -c "import sys; sys.path.insert(0,'tools'); import sync_version as sv; sv.sync_build_stamp_patch(check=False)"
python3 tools/render_bootstrap_contract.py --apply >/dev/null
python3 tools/gen_command_catalog.py >/dev/null
python3 tools/generate_deliverables_menu.py --apply >/dev/null
python3 tools/gen_tools_inventory.py >/dev/null

say "gate: version sync"
python3 tools/sync_version.py --check | tail -1 | grep -q "OK" || die "version sync gate failed."
mkdir -p "$OUT"
DEFAULT_PYTEST_LOG="$OUT/pytest_full_suite_${STAMP}.log"
if [[ "$SKIP_TESTS" -eq 0 ]]; then
  BASELINE_PYTEST_LOG="$OUT/pytest_manifest_baseline_${STAMP}.log"
  PYTEST_LOG="${PYTEST_LOG:-$DEFAULT_PYTEST_LOG}"
  say "refresh source-stage integrity before manifest convergence"
  refresh_source_integrity || die "source-stage integrity refresh failed."
  say "measure full-suite baseline (stale-manifest failures may occur only in this run)"
  set +e
  PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider --run-slow --run-network >"$BASELINE_PYTEST_LOG" 2>&1
  BASELINE_RC=$?
  set -e
  read -r BASE_PASSED BASE_SKIPPED < <(pytest_counts "$BASELINE_PYTEST_LOG") \
    || die "could not extract measured counts from baseline pytest log."
  echo "  baseline: $(tail -1 "$BASELINE_PYTEST_LOG") (exit $BASELINE_RC; evidence seed only)"
  say "converge release manifest against its consumer tests"
  python3 tools/gen_release_manifest.py --fixed-point \
    --tests-passed "$BASE_PASSED" --tests-skipped "$BASE_SKIPPED" >/dev/null \
    || die "release manifest fixed-point convergence failed."
  refresh_source_integrity || die "post-convergence source integrity refresh failed."
  say "gate: final full suite"
  if ! PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider --run-slow --run-network >"$PYTEST_LOG" 2>&1; then
    tail -20 "$PYTEST_LOG" >&2
    die "final full suite has failures — fix before cutting."
  fi
else
  say "gate: verify exact-source external full-suite receipt"
  [[ -n "${PYTEST_RECEIPT:-}" && "$PYTEST_RECEIPT" = /* ]] \
    || die "--skip-tests requires PYTEST_RECEIPT=/absolute/path/to/a structured external-validation receipt."
  [[ "${PYTEST_RECEIPT_SHA256:-}" =~ ^[0-9a-f]{64}$ ]] \
    || die "--skip-tests requires PYTEST_RECEIPT_SHA256=<64 lowercase hex characters>."
  RECEIPT_VERIFIER="tools/verify_external_validation_receipt.py"
  [[ -f "$RECEIPT_VERIFIER" ]] \
    || die "external-validation receipt verifier is missing: $RECEIPT_VERIFIER"
  if ! PYTEST_LOG="$(python3 "$RECEIPT_VERIFIER" --root . --receipt "$PYTEST_RECEIPT" \
      --expected-receipt-sha256 "$PYTEST_RECEIPT_SHA256" --print-log-path)"; then
    die "external full-suite receipt is invalid; refusing --skip-tests."
  fi
  echo "  external validation receipt: PASS ($PYTEST_RECEIPT)"
  echo "  verified pytest log: $PYTEST_LOG"
fi
grep -qE '[0-9]+ passed' "$PYTEST_LOG" \
  || die "pytest log has no passed-count summary: $PYTEST_LOG"
grep -qE '[1-9][0-9]* (failed|error|errors)' "$PYTEST_LOG" \
  && die "pytest log records failures/errors: $PYTEST_LOG"
echo "  $(tail -1 "$PYTEST_LOG")"

say "generate release manifest from final green suite"
python3 tools/gen_release_manifest.py --apply --pytest-log "$PYTEST_LOG" >/dev/null
refresh_source_integrity || die "final source integrity refresh failed."
python3 tools/gen_release_manifest.py --check --pytest-log "$PYTEST_LOG" >/dev/null \
  || die "release manifest does not match final identity/test log."
python3 tools/render_bootstrap_contract.py --check >/dev/null \
  || die "bootstrap generated surfaces drifted after synchronization."
python3 tools/gen_command_catalog.py --check >/dev/null \
  || die "generated command catalog drifted after synchronization."
python3 tools/generate_deliverables_menu.py --check >/dev/null \
  || die "generated deliverables menu drifted after synchronization."
python3 tools/gen_tools_inventory.py --check >/dev/null \
  || die "generated tools inventory drifted after synchronization."
python3 tools/rewrite_release_identity.py "$VER" "$STAMP" --root . --check >/dev/null \
  || die "cut-owned release identity fields drifted after synchronization."
assert_no_backup_debris

if [[ -f tools/verify_release_identity.py ]]; then
  say "gate: release identity"
  python3 tools/verify_release_identity.py --strict-membership 2>&1 | tail -3
  python3 tools/verify_release_identity.py --strict-membership >/dev/null 2>&1 \
    || die "release identity gate failed after final source integrity refresh."
fi

# NC-004: strict repository health is a hard PRE-PACKAGE gate. It honors the machine-readable, signed
# STRICT_HEALTH_WAIVER.json (NC-005) — a ceiling breach passes ONLY with a complete, applicable, owned
# waiver whose signed `observed` still covers the current count. No waiver / stale waiver / a hard
# failure aborts the cut. Ceilings are never raised to make this green.
say "gate: strict repository health"
python3 tools/repo_health.py --strict 2>&1 | tail -6
python3 tools/repo_health.py --strict >/dev/null 2>&1 \
  || die "strict repo-health gate failed — reduce the metric or record a signed STRICT_HEALTH_WAIVER.json entry (never raise the ceiling)."

say "cut five tiers -> $OUT"
export BUILD_STAMP="$STAMP" SKIP_INTIER_PYTEST=1
for tier in code clean sid merged public; do
  td="$OUT/$tier"; mkdir -p "$td"
  # Write the cutlog to a local tmpfile, then copy it into $td. Redirecting make_public_tier.sh's
  # stdout+stderr *directly* into a file under $OUT (which may be a slow/among-scanned mount such as
  # /mnt/user-data/outputs) can kill the tier cut mid-run — it truncates at the last buffered line
  # ("version-sync gate: OK") and exits non-zero, with the real output never flushed. A local tmpfile
  # sidesteps that; the cutlog still lands in $td for the record.
  _cl="$(mktemp)"
  if bash tools/make_public_tier.sh "$tier" "$SRC" "$td" > "$_cl" 2>&1; then
    cp "$_cl" "$td/_cutlog.txt"; rm -f "$_cl"
    z="$(ls "$td"/*.zip 2>/dev/null | head -1)"
    echo "  $tier: $(basename "$z")  $(grep -o 'parity gate: OK' "$td/_cutlog.txt" | head -1)"
  else
    cp "$_cl" "$td/_cutlog.txt"; tail -5 "$_cl"; rm -f "$_cl"
    die "tier $tier cut failed (see $td/_cutlog.txt)."
  fi
done
# v9.7.409 portability: GNU `sha256sum` is absent on stock macOS; fall back to `shasum -a 256`
# (blessed idiom, release.sh:66). The -exec runs it via `sh -c` so the fallback applies per file.
say "checksums"; ( cd "$OUT" && find . -name '*.zip' -exec sh -c 'if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi' _ {} + | sed 's|\./||' > SHA256SUMS.txt && cat SHA256SUMS.txt )
say "done — v$VER / $STAMP cut into $OUT"
