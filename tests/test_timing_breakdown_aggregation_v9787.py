"""v9.7.87 9.7.87-A: the timing breakdown aggregates phase receipts into a real per-phase
table instead of booking 100% overhead."""
from __future__ import annotations
import json, pathlib
from mamey.timing import TimingRecorder


def _write_receipts(pdir, phases):
    # phases: list of (name, status, mono_ns)
    with open(pdir / "run_phase_receipts.jsonl", "w") as fh:
        for name, status, mono in phases:
            fh.write(json.dumps({"phase": name, "status": status,
                                 "time": "00:00:00", "mono_ns": mono,
                                 "version": "test"}) + "\n")


def test_populate_from_receipts_sequential_gaps(tmp_path):
    # four sequential phases at 0s,1s,3s,6s; last runs to a terminal at 10s
    base = 1_000_000_000_000
    _write_receipts(tmp_path, [
        ("environment", "START", base + 0),
        ("antismash_parse", "START", base + 1_000_000_000),
        ("inventory", "START", base + 3_000_000_000),
        ("workbook", "START", base + 6_000_000_000),
        ("terminal", "MAMEY_COMPLETE", base + 10_000_000_000),
    ])
    rec = TimingRecorder(strain_id="T", mamey_version="x", mode="standard")
    n = rec.populate_from_receipts(tmp_path)
    assert n == 4, [p.name for p in rec.phases]   # terminal excluded
    by = {p.name: p.elapsed_seconds for p in rec.phases}
    assert abs(by["environment"] - 1.0) < 0.01
    assert abs(by["antismash_parse"] - 2.0) < 0.01
    assert abs(by["inventory"] - 3.0) < 0.01
    assert abs(by["workbook"] - 4.0) < 0.01   # runs to terminal


def test_phase_sum_close_to_total_not_all_overhead(tmp_path):
    base = 2_000_000_000_000
    _write_receipts(tmp_path, [
        ("a", "START", base + 0),
        ("b", "START", base + 2_000_000_000),
        ("terminal", "MAMEY_COMPLETE", base + 5_000_000_000),
    ])
    rec = TimingRecorder(strain_id="T", mamey_version="x", mode="standard")
    rec.populate_from_receipts(tmp_path)
    phase_sum = sum(p.elapsed_seconds for p in rec.phases)
    assert phase_sum > 0
    # a:2s + b:3s = 5s of accounted time (the whole span), not 0
    assert abs(phase_sum - 5.0) < 0.01


def test_no_receipts_is_safe(tmp_path):
    rec = TimingRecorder(strain_id="T", mamey_version="x", mode="standard")
    assert rec.populate_from_receipts(tmp_path) == 0   # no file → no crash
