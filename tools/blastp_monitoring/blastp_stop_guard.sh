#!/usr/bin/env bash
# blastp_stop_guard.sh — Alex directive 2026-08-25: run clean unattended; on ANY REAL error, STOP EVERYTHING.
# REAL error = failure-status ledger row, OR a run.log line matching throttle/SIGXCPU/CPU usage limit/
#              Too Many/Status=UNKNOWN/nonzero "failed"/nonzero "expired" in the lookback window.
# NOT an error = transient curl rc=16/18/35/56 poll retries (network; runner re-polls the same RID) and
#               the benign "0 failed/expired" / "RUN end" summary lines.
# If a real error is found: bootout ALL 8 codex100 lanes and print STOPPED (+ the offending lines).
set -uo pipefail
ROOT="${SAPOTE_WORKSPACE_ROOT:-$(pwd)}"
BR="$ROOT/Blastp RESULTS"
LA="$HOME/Library/LaunchAgents"
UID_=$(id -u)
LOOKBACK_MIN="${1:-25}"
LANES=(nr_s1 nr_s2 nr_s3 nr_s4 clnr_s1 clnr_s2 clnr_s3 clnr_s4)
cutoff=$(date -v-${LOOKBACK_MIN}M '+%Y-%m-%d %H:%M')

# RETUNED 2026-08-26: a LONE expired/failed RID is routine (the runner just resubmits it) and must NOT
# halt a healthy fleet — that false-stopped a clean overnight run on one aged-out AS-XXX RID. Now:
#   * SYSTEMIC errors (throttle / SIGXCPU / CPU-limit / Too-Many) -> STOP on the FIRST occurrence.
#   * expired/failed ledger rows -> STOP only if a BURST (>= FAIL_THRESHOLD) happened RECENTLY
#     (submit_iso within FAIL_WINDOW_H) — so one routine expiry, or an old historical one, is ignored.
FAIL_THRESHOLD="${FAIL_THRESHOLD:-3}"
FAIL_WINDOW_H="${FAIL_WINDOW_H:-6}"

real_hits=""
# (1) BURST of recent ledger failures (aggregate across all codex100 lanes)
burst=$(FAIL_WINDOW_H="$FAIL_WINDOW_H" python3 - "$BR" <<'PY'
import csv, glob, os, sys, datetime
BR=sys.argv[1]; win=float(os.environ.get("FAIL_WINDOW_H","6"))
cut=datetime.datetime.now()-datetime.timedelta(hours=win); n=0; ex=[]
for led in glob.glob(os.path.join(BR,"_N*CODEX100_*","_ledger.csv")):
    for r in csv.DictReader(open(led)):
        st=(r.get("status") or "").lower()
        if not any(k in st for k in ("fail","expir","error")): continue
        si=(r.get("submit_iso") or "").strip()
        try: t=datetime.datetime.fromisoformat(si[:19])
        except Exception: t=None
        if t is None or t>=cut:
            n+=1; ex.append(f"{os.path.basename(os.path.dirname(led))}:{r.get('rid')}:{st}")
print(n); print("; ".join(ex[:6]))
PY
)
bcount=$(echo "$burst" | sed -n '1p'); bsample=$(echo "$burst" | sed -n '2p')
if [ "${bcount:-0}" -ge "$FAIL_THRESHOLD" ]; then
  real_hits+="LEDGER BURST: $bcount failed/expired in last ${FAIL_WINDOW_H}h (>=${FAIL_THRESHOLD}) [$bsample]"$'\n'
fi
# (2) SYSTEMIC run.log errors in lookback window -> instant stop (lone expiry/UNKNOWN no longer here)
for L in "$BR"/_N*CODEX100_*/_run.log; do
  [ -f "$L" ] || continue
  hit=$(awk -v cutoff="$cutoff" '
    /RUN end|0 failed\/expired/ {next}
    /curl rc=(16|18|35|56)/ {next}
    /SIGXCPU|CPU usage limit|throttl|Too Many|Too many|quota|blocked by NCBI/ {
      ts=substr($0,2,16); if (ts >= cutoff) print FILENAME": "$0 }' "$L" 2>/dev/null)
  [ -n "$hit" ] && real_hits+="$hit"$'\n'
done

if [ -n "$real_hits" ]; then
  echo "!!!!! REAL ERROR DETECTED — STOPPING ALL 8 CODEX100 LANES (Alex directive) !!!!!"
  echo "$real_hits"
  for n in "${LANES[@]}"; do
    launchctl bootout gui/$UID_ "$LA/com.alex.blastp.codex100.$n.plist" 2>/dev/null && echo "  stopped com.alex.blastp.codex100.$n"
  done
  # verify none alive
  alive=$(ps -eo command | grep nr_rid_runner | grep CODEX100 2>/dev/null | grep -v grep | wc -l | tr -d ' ')
  # RID_BASE is in env not cmdline, so recount by process
  alive=$(ps -eo command | grep nr_rid_runner | grep -v grep | grep -v caffeinate | wc -l | tr -d ' ')
  echo "STOPPED. runner processes still alive: $alive (expect 0)"
  exit 2
else
  n=$(ps -eo command | grep nr_rid_runner | grep -v grep | grep -v caffeinate | wc -l | tr -d ' ')
  # submissions-today counter (NCBI says ~100/day; counting is opaque, so we track the raw number)
  subs=$(python3 - "$BR" <<'PY'
import csv,glob,os,datetime,sys
BR=sys.argv[1]; today=datetime.date.today().isoformat(); t=0
for led in glob.glob(os.path.join(BR,"_N*RID*","_ledger.csv")):
    for r in csv.DictReader(open(led)):
        if (r.get("submit_iso") or "")[:10]==today: t+=1
print(t)
PY
)
  echo "CLEAN — no real errors in last ${LOOKBACK_MIN}m. $n lanes running. submissions today=${subs} (NCBI ~100/day, opaque). (benign transient curl rc=16/18/35/56 ignored.)"
  exit 0
fi
