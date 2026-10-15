"""plot_crawl_proteins_24_96h.py counts a fetched row from the query copy whose bytes the runner sent.

On 10 Oct the 14 partner tier 1 lanes plotted 0 of 140 fetched proteins: two superseded queue folders held the
same relative query paths with other bytes, so every row was "conflicting copies" and dropped. The runner's ledger
records query_sha256 for each sent query, so the plot now counts the copy with those bytes. Rows without the
column keep the old rule (one distinct copy, or the row is unknown).
"""
import csv
import datetime as dt
import hashlib
import runpy
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT = Path(__file__).resolve().parents[1] / "tools/blastp_monitoring/plot_crawl_proteins_24_96h.py"
COLS = ("strain", "bgc", "file", "rid", "rtoe", "submit_iso", "status", "fetch_iso", "note", "query_sha256")


def _world(tmp_path, *, with_sha, sent_n=3, other_n=7):
    """One lane; the same relative query path in its own queue and in a superseded queue, with different bytes."""
    res = tmp_path / "Blastp RESULTS"
    sent = "".join(f">q{i}\nMAA\n" for i in range(sent_n)).encode()
    other = "".join(f">old|q{i}\nMAA\n" for i in range(other_n)).encode()
    for root, body in (("_QUERIES_PARTNER_L01", sent), ("_QUERIES_PARTNER_L01_superseded_unsent", other)):
        p = res / root / "AS-1" / "AS-1_ptn_p0001" / "AS-1__ptn__ctg1_1.faa"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)
    lane = res / "_PARTNER_T1_L01_CLNR_TEST"
    lane.mkdir(parents=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with (lane / "_ledger.csv").open("w", newline="") as out:
        w = csv.DictWriter(out, fieldnames=COLS)
        w.writeheader()
        w.writerow({"strain": "AS-1", "bgc": "", "file": "AS-1/AS-1_ptn_p0001/AS-1__ptn__ctg1_1.faa", "rid": "R1",
                    "status": "fetched", "submit_iso": stamp, "fetch_iso": stamp, "note": "",
                    "query_sha256": hashlib.sha256(sent).hexdigest() if with_sha else ""})


def _run(tmp_path, monkeypatch):
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("SAPOTE_BLASTP_PLOT_DIR", str(tmp_path))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    monkeypatch.setattr(matplotlib.figure.Figure, "savefig", lambda *a, **k: None)
    return runpy.run_path(str(SCRIPT), run_name="__main__")


def test_conflicting_copy_elsewhere_does_not_drop_the_lane(tmp_path, monkeypatch):
    _world(tmp_path, with_sha=True)
    state = _run(tmp_path, monkeypatch)
    (comps, _), = state["data"].values()
    assert [n for _t, n in comps] == [3]            # the 3 proteins actually sent, not 0 and not the other copy's 7
    assert state["ambiguous_files"] == 0 and state["missing_files"] == 0
    assert not state["unknown_lanes"]
    plt.close(state["fig"])


def test_rows_without_a_ledger_sha_keep_the_unique_copy_rule(tmp_path, monkeypatch):
    _world(tmp_path, with_sha=False)
    state = _run(tmp_path, monkeypatch)
    (comps, _), = state["data"].values()
    assert [n for _t, n in comps] == [0]
    assert state["ambiguous_files"] == 1 and state["unknown_lanes"]
    plt.close(state["fig"])


def test_a_ledger_sha_matching_no_copy_is_unknown_not_guessed(tmp_path, monkeypatch):
    _world(tmp_path, with_sha=True)
    for p in (tmp_path / "Blastp RESULTS").glob("_QUERIES_PARTNER_L01/**/*.faa"):
        p.write_text(">changed\nMAA\n")
    state = _run(tmp_path, monkeypatch)
    (comps, _), = state["data"].values()
    assert [n for _t, n in comps] == [0]
    assert state["missing_files"] == 1 and state["unknown_lanes"]
    plt.close(state["fig"])
