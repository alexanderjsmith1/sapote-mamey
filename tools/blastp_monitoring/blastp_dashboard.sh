#!/usr/bin/env bash
# blastp_dashboard.sh — one screen of GROUND TRUTH for the BLASTp crawl.
# Run anytime:  bash "tools/blastp_monitoring/blastp_dashboard.sh"
# Everything here reads live processes + run.logs on disk — no cached numbers.
set -uo pipefail
ROOT="${SAPOTE_WORKSPACE_ROOT:-$(pwd)}"
BR="$ROOT/Blastp RESULTS"
echo "==================== BLASTp DASHBOARD  $(date '+%Y-%m-%d %H:%M') ===================="

echo "-- LANES RUNNING (live processes) --"
ps -eo pid,command | grep nr_rid_runner | grep -v grep | grep -v caffeinate | while read pid rest; do
  b=$(ps eww -o command= -p "$pid" 2>/dev/null | grep -o 'RID_BASE=[^ ]*'); b=${b:-RID_BASE=_NR_RID}
  d=$(ps eww -o command= -p "$pid" 2>/dev/null | grep -o 'RID_DATABASE=[^ ]*'); d=${d:-RID_DATABASE=nr}
  i=$(echo "$rest" | grep -o 'max-inflight [0-9]*')
  printf "   pid %-7s %-28s %-24s %s\n" "$pid" "$b" "$d" "$i"
done
N=$(ps -eo command | grep nr_rid_runner | grep -v grep | grep -v caffeinate | wc -l | tr -d ' ')
echo "   => $N lane(s) alive"

echo "-- QUEUE (pending 'to submit', from each lane's latest RUN start) --"
for base in _NR_RID _NR_CLUSTER_RID _NR_RID_PRIORITY3 _NR_CLUSTER_RID_BULK \
            _NR_RID_CODEX100_s1 _NR_RID_CODEX100_s2 _NR_RID_CODEX100_s3 _NR_RID_CODEX100_s4 \
            _NR_CLUSTER_RID_CODEX100_s1 _NR_CLUSTER_RID_CODEX100_s2 _NR_CLUSTER_RID_CODEX100_s3 _NR_CLUSTER_RID_CODEX100_s4; do
  L="$BR/$base/_run.log"
  [ -f "$L" ] || { printf "   %-24s (no log yet)\n" "$base"; continue; }
  last=$(grep "RUN start" "$L" | tail -1)
  printf "   %-24s %s\n" "$base" "$(echo "$last" | sed 's/.*RUN start: //')"
done

echo "-- ERRORS (last 30 min across all lanes) --"
errs=0
for L in "$BR"/_NR*/_run.log; do
  [ -f "$L" ] || continue
  e=$(awk -v cutoff="$(date -v-30M '+%Y-%m-%d %H:%M')" '
    /RUN end|0 failed\/expired/ {next}                       # skip benign summary lines
    /poll ERROR.*curl rc=(16|18|56)/ {next}                  # skip benign transient poll retries (RID appears between ERROR and colon)
    /poll ERROR|SIGXCPU|CPU usage limit|throttl|Too Many|Status=UNKNOWN|[1-9][0-9]* failed|[1-9][0-9]* expired/ {
      ts=substr($0,2,16); if (ts >= cutoff) print }' "$L" 2>/dev/null | wc -l | tr -d ' ')
  if [ "$e" -gt 0 ]; then echo "   $(basename $(dirname "$L")): $e error line(s) in 30m"; errs=$((errs+e)); fi
done
[ "$errs" -eq 0 ] && echo "   none (transient curl rc=16/18/56 poll-retries are benign and re-polled)"

echo "-- FETCHES (last 6, newest last) --"
python3 "$(dirname "$0")/blastp_last_returns.py" 2>/dev/null | grep -E "\| *[0-9]+ rows" | tail -6 | sed 's/^/   /'
echo "======================================================================================"
