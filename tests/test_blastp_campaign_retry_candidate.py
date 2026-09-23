import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "blastp_campaign_retry", ROOT / "tools" / "blastp_campaign.py"
)
assert SPEC and SPEC.loader
bc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bc)


def _args(tmp_path):
    batches = tmp_path / "batches"
    batches.mkdir(exist_ok=True)
    (batches / "query.faa").write_text(
        ">GENERIC|node_1|gene=protein_a\nMAA\n"
        ">GENERIC|node_1|gene=protein_b\nMKKK\n",
        encoding="utf-8",
    )
    return SimpleNamespace(
        batches=str(batches),
        out=str(tmp_path / "run"),
        database="nr",
        hits=6,
        submit_gap=0,
        confirm_public_upload=True,
    )


def _write_records(tmp_path, records):
    run = tmp_path / "run"
    run.mkdir()
    (run / "rids.json").write_text(json.dumps(records), encoding="utf-8")


def _records(tmp_path):
    return json.loads((tmp_path / "run" / "rids.json").read_text(encoding="utf-8"))


def test_failed_records_are_retried_and_replaced(tmp_path, monkeypatch):
    _write_records(
        tmp_path,
        [
            {"locus": "GENERIC|node_1|protein_a", "rid": None, "status": "SUBMIT_FAIL"},
            {"locus": "GENERIC|node_1|protein_b", "rid": None, "status": "SUBMIT_ERR:TimeoutError"},
        ],
    )
    calls = []

    def accepted(fields, timeout=45):
        calls.append(fields["QUERY"].splitlines()[0][1:])
        return f"RID = RID{len(calls)}"

    monkeypatch.setattr(bc, "_post", accepted)
    assert bc.cmd_submit(_args(tmp_path)) == 0
    assert calls == ["GENERIC|node_1|protein_a", "GENERIC|node_1|protein_b"]
    assert _records(tmp_path) == [
        {"locus": "GENERIC|node_1|protein_a", "rid": "RID1", "status": "WAITING"},
        {"locus": "GENERIC|node_1|protein_b", "rid": "RID2", "status": "WAITING"},
    ]


def test_accepted_rid_is_not_resubmitted_while_failure_is_retried(tmp_path, monkeypatch):
    _write_records(
        tmp_path,
        [
            {"locus": "GENERIC|node_1|protein_a", "rid": "RID_A", "status": "WAITING"},
            {"locus": "GENERIC|node_1|protein_b", "rid": None, "status": "SUBMIT_FAIL"},
        ],
    )
    calls = []

    def accepted(fields, timeout=45):
        calls.append(fields["QUERY"].splitlines()[0][1:])
        return "RID = RID_B"

    monkeypatch.setattr(bc, "_post", accepted)
    assert bc.cmd_submit(_args(tmp_path)) == 0
    assert calls == ["GENERIC|node_1|protein_b"]
    assert _records(tmp_path) == [
        {"locus": "GENERIC|node_1|protein_a", "rid": "RID_A", "status": "WAITING"},
        {"locus": "GENERIC|node_1|protein_b", "rid": "RID_B", "status": "WAITING"},
    ]


def test_repeated_transport_failure_remains_retriable_without_duplicate_rows(
    tmp_path, monkeypatch
):
    args = _args(tmp_path)
    calls = []

    def unavailable(fields, timeout=45):
        locus = fields["QUERY"].splitlines()[0][1:]
        calls.append(locus)
        if locus.endswith("protein_a"):
            raise TimeoutError("offline")
        return "RID = RID_B"

    monkeypatch.setattr(bc, "_post", unavailable)
    assert bc.cmd_submit(args) == 0
    assert bc.cmd_submit(args) == 0
    assert calls.count("GENERIC|node_1|protein_a") == 2
    assert calls.count("GENERIC|node_1|protein_b") == 1
    records = _records(tmp_path)
    assert len(records) == 2
    failed = next(row for row in records if row["locus"].endswith("protein_a"))
    assert failed == {
        "locus": "GENERIC|node_1|protein_a",
        "rid": None,
        "status": "SUBMIT_ERR:TimeoutError",
    }
