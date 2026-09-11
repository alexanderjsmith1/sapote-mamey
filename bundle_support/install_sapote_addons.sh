#!/usr/bin/env bash
# bundle_support/install_sapote_addons.sh — install the Sapote add-ons stack (wheels + HMM + NP Atlas data) from vendored
# wheels, with NO network access. Run from the bundle root (where sapote_addons/ lives).
#
# What this installs (cp312 / manylinux x86_64):
#   pyrodigal 3.7.1   -> S1 proteome prediction
#   pyfastani 0.6.1   -> S2 whole-genome ANI
#   pyswrd 0.3.1 + pyopal + scoring_matrices -> S4/S5 fast Smith-Waterman alignment backend
#   biopython 1.87 + numpy -> S3/S5/S7 parsing + alignment
#   archspec          -> pyrodigal runtime dep
#
# DIAMOND is intentionally NOT here (needs a C++ compile; see sapote_addons/DIAMOND_STATUS.md).
# the compare module uses the pyswrd backend by default and auto-upgrades to DIAMOND only if a `diamond`
# binary is on PATH. The pyswrd backend is the PROVEN path (reproduced NCBI BLASTp to the decimal).

set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# The wheels ship SEPARATELY from the lean Sapote-Mamey bundle. They can arrive in ANY of these
# shapes — the loader accepts all of them, so you can split a big addon into several smaller zips
# that upload in parallel (faster than one 118 MB file):
#   * one combined addon dir            (sapote_addons/wheels)
#   * split addon dirs                  (sapote_addons_core/wheels + sapote_addons_figures/wheels)
#   * loose .whl files                  (dropped anywhere under the search roots below)
#   * an explicit path                  (bash bundle_support/install_sapote_addons.sh /path/to/wheels)
#
# Discovery: gather every directory that contains .whl files from a set of search roots, pool the
# wheels into one staging dir, and install from there. Core deps are REQUIRED; figure/analysis deps
# are best-effort (installed if their wheels are present, skipped cleanly if not).

# Collect candidate roots to scan for wheels (explicit arg first, then the usual neighbours).
SEARCH_ROOTS=()
if [ "${1:-}" != "" ]; then SEARCH_ROOTS+=("$1"); fi
SEARCH_ROOTS+=(
  "$HERE/.." "$HERE" "$HERE/../sm_addons" "$HERE/sapote_addons"
  "$HERE/../uploads" "$HERE/../../uploads" "/mnt/user-data/uploads" "."
)

POOL="$(mktemp -d)"
trap 'rm -rf "$POOL"' EXIT
found=0
for root in "${SEARCH_ROOTS[@]}"; do
  [ -d "$root" ] || continue
  # find any .whl under this root (max depth keeps it fast and avoids scanning the whole FS)
  while IFS= read -r whl; do
    [ -f "$whl" ] || continue
    cp -n "$whl" "$POOL/" 2>/dev/null || true
    found=1
  done < <(find "$root" -maxdepth 4 -name '*.whl' 2>/dev/null)
done

if [ "$found" -eq 0 ]; then
  echo "ERROR: no .whl files found in any addon location." >&2
  echo "The wheels ship SEPARATELY from the lean bundle. Attach the addon — as one zip, as split" >&2
  echo "zips (core + figures), or as loose wheels — alongside this bundle, or pass a path:" >&2
  echo "  bash bundle_support/install_sapote_addons.sh /path/to/wheels" >&2
  exit 1
fi

WHEELS="$POOL"
n_wheels="$(find "$POOL" -name '*.whl' | wc -l | tr -d ' ')"
echo "[sapote-addons] pooled $n_wheels wheel(s) from the attached addon(s) -> installing offline"

# Install in two passes: CORE deps (required) then FIGURE/analysis deps (best-effort). This way a
# core-only addon (~27 MB, all runtime function) installs and verifies even when the heavy figure
# wheels (scipy/pandas/matplotlib/logomaker, ~83 MB) were not attached this session.
CORE_PKGS="pyrodigal pyfastani pyswrd pyopal scoring_matrices biopython archspec pytest ijson \
  pyhmmer pyskani pyfamsa pytrimal pytantan pyrodigal-gv gb-io pyfastx dendropy taxopy"
FIGURE_PKGS="numpy matplotlib scipy pandas logomaker pycirclize dna_features_viewer"

echo "[sapote-addons] installing core runtime deps..."
pip install --no-index --find-links "$WHEELS" $CORE_PKGS --break-system-packages

echo "[sapote-addons] installing figure/analysis deps (best-effort; skipped if not attached)..."
pip install --no-index --find-links "$WHEELS" $FIGURE_PKGS --break-system-packages 2>/dev/null \
  && echo "[sapote-addons]   figure stack installed" \
  || echo "[sapote-addons]   figure wheels not present — core is fully functional; attach the figures addon for 'mamey figures'"

echo "[sapote-addons] verifying imports..."
python3 - <<'PY'
import importlib
# CORE — required; a failure here is a real error
core = [("pyrodigal","S1 gene prediction"), ("pyfastani","S2 ANI"),
        ("pyswrd","S4/S5 fast alignment"), ("Bio","S3/S5/S7 parsing"),
        ("pyhmmer","HMM domain scan / adjudication"), ("pyskani","fragmentation-robust ANI")]
ok = True
for m, stage in core:
    try:
        importlib.import_module(m); print(f"  OK   {m:12s} -> {stage}")
    except Exception as e:
        print(f"  FAIL {m:12s} -> {e}"); ok = False
# FIGURES — optional; report presence, never fail the install
for m, stage in [("numpy","figures/math"), ("matplotlib","figure rendering"),
                 ("pandas","figure data"), ("pycirclize","genome atlas")]:
    try:
        importlib.import_module(m); print(f"  OK   {m:12s} -> {stage}")
    except Exception:
        print(f"  --   {m:12s} -> not installed (figures addon not attached; core is fine)")
if not ok:
    raise SystemExit(1)
print("[sapote-addons] core dependencies importable. Gemini/BLASTp/HMM runnable offline.")
PY

echo "[sapote-addons] done. Run a comparison with:  python3 -m mamey compare --help"
