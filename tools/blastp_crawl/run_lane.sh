#!/bin/bash
# Start one ClusteredNR gap lane with the crawl's house settings. Usage: bash run_lane.sh AS-<n>
# Needs SAPOTE_WORKSPACE_ROOT: the folder that holds `Blastp RESULTS/`.
# Runs in the foreground; start it as a background task, one lane at a time, a minute apart.
set -euo pipefail
: "${SAPOTE_WORKSPACE_ROOT:?set SAPOTE_WORKSPACE_ROOT to the folder that holds Blastp RESULTS}"
S="${1:?give a strain, e.g. AS-1}"
N="${S#AS-}"
Q="_QUERIES_GAP_AS-${N}_K"
[ -d "$SAPOTE_WORKSPACE_ROOT/Blastp RESULTS/$Q" ] || { echo "no query tree $Q under $SAPOTE_WORKSPACE_ROOT/Blastp RESULTS" >&2; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"
export SAPOTE_WORKSPACE_ROOT
RID_DATABASE=nr_cluster_seq RID_BASE="_STRAINGAP_SINGLE_CLNR_GAP_AS${N}" RID_QUERIES="$Q" \
  exec nice -n 15 python3 "$HERE/nr_rid_runner.py" run --hours 24 --sleep 300 --max-inflight 2
