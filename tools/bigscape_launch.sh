#!/usr/bin/env bash
# bigscape_launch.sh — run BiG-SCAPE 2 on a staged region-GBK folder with the guards a cohort run needs.
#
# Usage:
#   bigscape_launch.sh <input_dir> <out_dir> [--label L] [--cutoffs 0.3,0.5,0.7] [--cores 4]
#                      [--mibig-dir <dir of BGC*.gbk>] [--mibig-name localNNNN]
#
# Environment (or edit the two lines below): BIGSCAPE_ENV_BIN = the conda env's bin folder holding `bigscape`,
# `fasttree` and friends; PFAM_HMM = pressed Pfam-A.hmm. Both are checked before anything runs.
#
# Guards, each one a failure that has cost a whole run before:
#   1. The env bin is put on PATH. Calling the bigscape binary by absolute path does NOT activate the env, so its
#      subprocess tools (fasttree, hmmsearch, diamond) are not found at the per-family TREE step, which comes AFTER the
#      hours of clustering; the run then dies with the database half-written.
#   2. MIBiG loads ONLY through `-m <name>`. `-i` and `-r` filter file names to "region"/"cluster" and silently drop
#      every BGC*.gbk. The `-m` slot is a folder inside the installed package, `big_scape/MIBiG/mibig_antismash_<name>_gbk`;
#      `--mibig-dir` links the given folder there and verifies the link resolves to >= 2,000 files. A dead link loads
#      0 references silently, so the loaded counts are printed from the log at the end and must be read.
#   3. The input folder must be non-empty, and the run log is kept next to the database.
set -euo pipefail
ENVBIN="${BIGSCAPE_ENV_BIN:?set BIGSCAPE_ENV_BIN to the conda env bin folder that holds bigscape}"
PFAM="${PFAM_HMM:?set PFAM_HMM to the pressed Pfam-A.hmm path}"
BS="$ENVBIN/bigscape"
[ -x "$BS" ] || { echo "ERROR: $BS not executable" >&2; exit 2; }
[ -f "$PFAM" ] && [ -f "$PFAM.h3i" ] || { echo "ERROR: Pfam not pressed at $PFAM (need .h3f/.h3i/.h3m/.h3p)" >&2; exit 2; }
export PATH="$ENVBIN:$PATH"
for dep in fasttree hmmsearch diamond; do
  command -v "$dep" >/dev/null || echo "WARN: '$dep' not on PATH (env bin=$ENVBIN); BiG-SCAPE 2 runs HMMs in-process, fasttree is required for trees" >&2
done
command -v fasttree >/dev/null || { echo "ERROR: fasttree missing; the per-family tree step will crash after clustering" >&2; exit 2; }

IN="${1:?need input_dir}"; OUT="${2:?need out_dir}"; shift 2 || true
LABEL="run_$(date +%Y-%m-%d)"; CUTOFFS="0.3,0.5,0.7"; CORES=4; MIBIG_DIR=""; MIBIG_NAME=""; INCLUDE_SINGLETONS=0
while [ $# -gt 0 ]; do case "$1" in
  --label) LABEL="$2"; shift;;
  --cutoffs) CUTOFFS="$2"; shift;;
  --cores) CORES="$2"; shift;;
  --mibig-dir) MIBIG_DIR="$2"; shift;;
  --mibig-name) MIBIG_NAME="$2"; shift;;
  --include-singletons) INCLUDE_SINGLETONS=1;;
  *) echo "unknown arg $1" >&2; exit 2;;
esac; shift; done

[ -d "$IN" ] || { echo "ERROR: input dir not found: $IN" >&2; exit 2; }
NIN=$(find "$IN" -name '*.gbk' | wc -l | tr -d ' ')
echo "input region GBKs: $NIN"; [ "$NIN" -gt 0 ] || { echo "ERROR: no gbks in input" >&2; exit 2; }

MIBIG_ARGS=()
if [ -n "$MIBIG_DIR" ]; then
  [ -n "$MIBIG_NAME" ] || { echo "ERROR: --mibig-dir needs --mibig-name (e.g. local2088)" >&2; exit 2; }
  PKG=$("$ENVBIN/python" -c "import big_scape, os; print(os.path.dirname(big_scape.__file__))")
  SLOT="$PKG/MIBiG/mibig_antismash_${MIBIG_NAME}_gbk"
  mkdir -p "$PKG/MIBiG"; ln -sfn "$(cd "$MIBIG_DIR" && pwd)" "$SLOT"
  N=$(find -L "$SLOT" -name '*.gbk' | wc -l | tr -d ' ')
  echo "MIBiG slot $SLOT -> $MIBIG_DIR ($N gbks)"
  [ "$N" -ge 2000 ] || { echo "ERROR: MIBiG slot resolves to $N gbks (< 2000): dead link or wrong folder" >&2; exit 3; }
  MIBIG_ARGS=(-m "$MIBIG_NAME")
fi

[ "$INCLUDE_SINGLETONS" -eq 1 ] && MIBIG_ARGS+=(--include-singletons)

mkdir -p "$OUT"
echo "BiG-SCAPE: $("$BS" --version 2>&1 | head -1) | label=$LABEL cutoffs=$CUTOFFS cores=$CORES mibig=${MIBIG_NAME:-none}"
set +e
"$BS" cluster -i "$IN" -p "$PFAM" "${MIBIG_ARGS[@]}" --gcf-cutoffs "$CUTOFFS" -c "$CORES" \
  -o "$OUT" --db-path "$OUT/${LABEL}.db" -l "$LABEL" > "$OUT/run.log" 2>&1
RC=$?
set -e
echo "BIGSCAPE_EXIT=$RC"
echo "=== loaded counts (with MIBiG the mibig line must be > 0) ==="
grep -aiE "Loading [0-9]+ (query|mibig|reference) GBKs|new GBKs to process" "$OUT/run.log" | grep -aivE "Saving|GBK/s" || true
grep -aiE "Traceback|FileNotFoundError|Error" "$OUT/run.log" | head -5 || true
# A populated MIBiG slot is only an input check. The external program can still load zero
# references and exit successfully; refuse an anchored result unless the run log proves
# a positive MIBiG count. Unknown log formats fail closed rather than imply a match-free run.
if [ "$RC" -eq 0 ] && [ -n "$MIBIG_DIR" ]; then
  LOADED_MIBIG=$(grep -aiEo 'Loading [0-9]+ mibig GBKs' "$OUT/run.log" | awk '{print $2}' | tail -1 || true)
  if [ -z "$LOADED_MIBIG" ] || [ "$LOADED_MIBIG" -eq 0 ]; then
    echo "ERROR: MIBiG input was requested but the BiG-SCAPE log did not prove a positive loaded MIBiG GBK count" >&2
    exit 4
  fi
fi
exit $RC
