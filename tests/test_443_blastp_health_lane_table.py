"""blastp_health per-lane table: held RIDs, blocked lanes, errors by type, --idle (v9.7.443). No network."""
import csv
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

BUNDLE = Path(__file__).resolve().parents[1]
SEQ = "MSTNPKPQRKTKRNTNRRPQDVKFPGGGQIVGGVYLLPRRGPRLGVRATRKTSERSQPRG"
COLS = ["strain", "bgc", "file", "rid", "rtoe", "submit_iso", "status", "fetch_iso", "note"]


def write_ledger(path, rows):
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLS})


def workspace(tmp_path, n=1, genes=("g0", "g1", "g2")):
    br = tmp_path / "ws" / "Blastp RESULTS"
    q = br / f"_QUERIES_GAP_AS-{n}_K" / f"AS-{n}"
    for i, g in enumerate(genes):
        d = q / f"AS-{n}_gapK_p{i:04d}"
        d.mkdir(parents=True)
        (d / f"AS-{n}__gapK__{g}.faa").write_text(f">{g}\n{SEQ}\n")
    lane = br / f"_STRAINGAP_SINGLE_CLNR_GAP_AS{n}"
    lane.mkdir(parents=True)
    rel = f"AS-{n}/AS-{n}_gapK_p0000/AS-{n}__gapK__{genes[0]}.faa"
    write_ledger(lane / "_ledger.csv", [dict(strain=f"AS-{n}", file=rel, rid="R0", status="fetched",
                                             fetch_iso="2026-09-25 10:00:00")])
    return tmp_path / "ws"


HEALTH = BUNDLE / "tools/blastp_monitoring/blastp_health.py"


def health(ws, *flags):
    env = dict(os.environ, SAPOTE_WORKSPACE_ROOT=str(ws))
    return subprocess.run([sys.executable, str(HEALTH), *flags], env=env, capture_output=True, text=True).stdout


def test_health_idle_skips_handed_off_lanes_and_lists_ledgerless_ones(tmp_path):
    ws = workspace(tmp_path, n=1)
    workspace_two = workspace(tmp_path, n=2)            # same ws root, second lane
    assert ws == workspace_two
    q3 = ws / "Blastp RESULTS/_QUERIES_GAP_AS-3_K/AS-3/AS-3_gapK_p0000"
    q3.mkdir(parents=True)
    (q3 / "AS-3__gapK__x.faa").write_text(f">x\n{SEQ}\n")        # no lane folder, no ledger yet
    (ws / "Blastp RESULTS/_STRAINGAP_SINGLE_CLNR_GAP_AS2/_HANDOFF_OUT.txt").write_text("out\n")
    out = health(ws, "--idle")
    assert "Handed off to another machine, not listed (1): AS2" in out
    idle = [l.split()[0] for l in out.splitlines() if l.startswith("_STRAINGAP")]
    assert idle == ["_STRAINGAP_SINGLE_CLNR_GAP_AS1", "_STRAINGAP_SINGLE_CLNR_GAP_AS3"]


def test_health_table_flags_held_rids_and_splits_errors(tmp_path):
    ws = workspace(tmp_path, n=1)
    lane = ws / "Blastp RESULTS/_STRAINGAP_SINGLE_CLNR_GAP_AS1"
    old = (dt.datetime.now() - dt.timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
    rows = list(csv.DictReader((lane / "_ledger.csv").open()))
    for i in range(4):
        rows.append(dict(strain="AS-1", file=f"AS-1/x{i}.faa", rid=f"H{i}", status="submitted", submit_iso=old))
    write_ledger(lane / "_ledger.csv", rows)
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    (lane / "_run.log").write_text(
        f"[{now}]   poll ERROR x1 H0: curl rc=52: \n[{now}]   poll ERROR x1 H1: curl rc=52: \n"
        f"[{now}]   submit ERROR a.faa: curl rc=35: \n[{now}]   submit failed x1 for a.faa; backing off\n")
    out = health(ws, "--all")
    line = next(l for l in out.splitlines() if l.startswith("_STRAINGAP_SINGLE_CLNR_GAP_AS1"))
    assert "4 (3.0 h)" in line and "BLOCKED" in line          # 4 held = the bundle runner's --max-held
    assert "1/1/2/0; rc 52" in line
