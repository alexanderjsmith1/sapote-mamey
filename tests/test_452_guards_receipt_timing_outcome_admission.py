"""Draft public reconstruction/export/parity controls. NOT RUN."""
import csv
import json
from pathlib import Path
import pytest
from mamey.timing import TimingRecorder

def receipts(root, statuses, phase="source_scans"):
    rows=[{"phase":phase,"status":status,"mono_ns":(i+1)*1_000_000_000}
          for i,status in enumerate(statuses)]
    rows.append({"phase":"terminal","status":"MAMEY_COMPLETE","mono_ns":(len(rows)+1)*1_000_000_000})
    (root/"run_phase_receipts.jsonl").write_text("\n".join(map(json.dumps,rows))+"\n")

@pytest.mark.parametrize("statuses,expected",[
    (["START","END"],"COMPLETE"),(["END"],"COMPLETE"),
    (["START","ERROR"],"ERROR"),(["START","TIMEOUT"],"TIMEOUT"),
    (["START","SKIP"],"SKIP"),(["START","SKIPPED"],"SKIPPED"),
    (["START"],"OUTCOME_UNVERIFIED"),(["START","ERROR","END"],"ERROR"),
    (["START","END","START"],"ATTEMPT_ROSTER_UNVERIFIED"),
    (["END","START"],"ATTEMPT_ROSTER_UNVERIFIED"),
    (["START","END","START","END"],"ATTEMPT_ROSTER_UNVERIFIED"),
    (["START","TIMEOUT","ERROR"],"OUTCOME_UNVERIFIED"),
])
def test_public_reconstruction_preserves_observed_outcome(tmp_path,statuses,expected):
    receipts(tmp_path,statuses)
    rec=TimingRecorder("S","test","x")
    assert rec.populate_from_receipts(tmp_path)==1
    phase=rec.phases[0]
    assert phase.status==expected and "elapsed inferred" in phase.notes
    assert "observed="+",".join(statuses) in phase.notes
    assert phase.elapsed_seconds==len(statuses)

def test_public_write_carries_failure_into_all_three_formats(tmp_path):
    receipts(tmp_path,["START","TIMEOUT"])
    rec=TimingRecorder("S","test","x");result=rec.write(tmp_path)
    assert result["phases"][0]["status"]=="TIMEOUT"
    assert json.loads((tmp_path/"S_timing_breakdown.json").read_text())["phases"][0]["status"]=="TIMEOUT"
    with (tmp_path/"S_timing_breakdown.csv").open() as fh: rows=list(csv.DictReader(fh))
    assert rows[0]["status"]=="TIMEOUT"
    assert "| TIMEOUT |" in (tmp_path/"S_timing_breakdown.md").read_text()

def test_sequential_gap_duration_contract_stays_separate_from_outcome(tmp_path):
    rows=[{"phase":name,"status":status,"mono_ns":mono} for name,status,mono in
          [("a","START",1_000_000_000),("b","START",3_000_000_000),("terminal","MAMEY_COMPLETE",6_000_000_000)]]
    (tmp_path/"run_phase_receipts.jsonl").write_text("\n".join(map(json.dumps,rows))+"\n")
    rec=TimingRecorder("S","test","x");assert rec.populate_from_receipts(tmp_path)==2
    assert [p.elapsed_seconds for p in rec.phases]==[2.0,3.0]
    assert all(p.status=="OUTCOME_UNVERIFIED" for p in rec.phases)
