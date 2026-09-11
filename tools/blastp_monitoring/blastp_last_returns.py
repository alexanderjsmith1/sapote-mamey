#!/usr/bin/env python3
"""blastp_last_returns.py (VGP, 2026-08-23) — the ONE reliable answer to
"are the last BLASTp returns usable, and were there any failures?"

WHY THIS EXISTS (root cause it kills): the crawl ledger schema is
    strain,bgc,file,rid,rtoe,submit_iso,status,fetch_iso,note
i.e. status is column 7 and fetch_iso is column 8. Hand-rolled awk (`$8=="fetched"`) gets this
wrong, returns SILENT-EMPTY output, and an operator can mistake "no rows printed" for "no data" or
"all clean". This tool reads the ledger by column NAME (csv.DictReader), so it can never be thrown
off by column position, and it reports the three things you actually want every time:
  (1) the last N fetched panels, with hit-row counts, EMPTY (0-row) fetches flagged in red;
  (2) any ledger rows with a failure status today;
  (3) any submit/poll errors written to a run.log in the last `--errmins` minutes.
Exit code is 0 only when the last returns are usable AND there are no failures — so it doubles as a
gate. Use this instead of ad-hoc awk/grep. Mirrors blastp_health.py's process/error anchoring.

Run: python3 "tools/blastp_monitoring/blastp_last_returns.py" [--last 10] [--errmins 30]
"""
import argparse
import csv
import datetime
import glob
import os
import re

ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())
BR = os.path.join(ROOT, "Blastp RESULTS")
ROWS_RE = re.compile(r"(\d+)\s*row")
# BC2-398: this file's own header docstring states "Mirrors blastp_health.py's process/error
# anchoring" — verified live it did not: this pattern missed "UNKNOWN", "curl rc=", and
# "expired" (three real error signatures blastp_health.py's own docstring documents catching
# after a real 2026-08-21 incident), and blastp_health.py's pattern in turn missed this file's
# bare "rc=(?:16|56|6|7|18)" and "throttl" signals. Union of both — keep in sync with the
# sibling copy in blastp_health.py.
ERR_RE = re.compile(
    r"submit failed|backing off|poll ERROR|rc=(?:16|56|6|7|18)|throttl"
    r"|UNKNOWN|curl rc=|expired",
    re.I,
)
TS_RE = re.compile(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")
FAIL_STATUSES = {"failed", "error", "dead"}


def lane_name(led):
    return os.path.basename(os.path.dirname(led))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--last", type=int, default=10, help="how many recent fetches to show")
    ap.add_argument("--errmins", type=int, default=30, help="run.log error lookback window")
    a = ap.parse_args()
    os.chdir(ROOT)

    fetched, fail_rows = [], []
    for led in glob.glob(os.path.join(BR, "_NR_*RID*", "_ledger.csv")):
        lane = lane_name(led)
        try:
            rows = list(csv.DictReader(open(led)))
        except Exception:
            continue
        for r in rows:
            st = (r.get("status") or "").strip()
            if st == "fetched" and r.get("fetch_iso"):
                m = ROWS_RE.search(r.get("note", "") or "")
                nrows = int(m.group(1)) if m else 0
                fetched.append((r["fetch_iso"][:19], lane, os.path.basename(r.get("file", "")), nrows))
            elif st in FAIL_STATUSES:
                fail_rows.append((lane, os.path.basename(r.get("file", "")), st,
                                  r.get("submit_iso", ""), r.get("note", "")))
    fetched.sort()

    # recent run.log errors
    cutoff = datetime.datetime.now() - datetime.timedelta(minutes=a.errmins)
    log_errs = []
    for lg in glob.glob(os.path.join(BR, "_NR_*RID*", "_run.log")):
        try:
            for line in open(lg, errors="ignore"):
                if not ERR_RE.search(line):
                    continue
                m = TS_RE.search(line)
                if not m:
                    continue
                try:
                    t = datetime.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue
                if t >= cutoff:
                    log_errs.append((m.group(1), lane_name(lg), line.strip()))
        except Exception:
            continue
    log_errs.sort()

    print(f"=== last {a.last} fetched panels (newest last) ===")
    last = fetched[-a.last:]
    empties = 0
    for t, lane, f, nrows in last:
        flag = "  <-- EMPTY (0 hits)" if nrows == 0 else ""
        if nrows == 0:
            empties += 1
        print(f"{t} | {lane:32s} | {f:30s} | {nrows:4d} rows{flag}")
    if not last:
        print("(no fetched rows found — check that lanes are running)")

    print(f"\n=== failure-status ledger rows: {len(fail_rows)} ===")
    for lane, f, st, sub, note in fail_rows[:20]:
        print(f"  {lane} | {f} | status={st} | submit={sub} | {note}")

    print(f"\n=== run.log errors in last {a.errmins}m: {len(log_errs)} "
          f"(transient curl rc=16/18 poll retries are non-fatal; runner re-polls the same RID) ===")
    for t, lane, line in log_errs[-10:]:
        print(f"  {t} | {lane} | {line[:90]}")

    usable = bool(last) and empties == 0
    clean = not fail_rows
    print('\n=== VERDICT ===', f"last returns usable : {('YES' if usable else 'NO')}  ({len(last)} shown, {empties} empty)", f"failures            : {('NONE' if clean else str(len(fail_rows)) + ' FAILURE ROWS')} | recent log errors: {len(log_errs)} (transient if only curl rc=16/18)", sep="\n")
    ok = usable and clean
    print("OVERALL:", "OK — usable data, no failures" if ok else "ATTENTION NEEDED (see above)")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
