"""A single protein over the NCBI web BLASTP cap is held, not queued as ready to run.

The splitter isolates it with a warning, but write_wise_batches still marked its batch
`ready_to_run` (with `under_100k` False beside it) and its ledger rows `pending`.
"""
import csv

from mamey.wise_fragmented_pks import RankedProteinRecord, write_wise_batches


def test_oversized_single_sequence_is_held(tmp_path):
    recs = [RankedProteinRecord(rank=1, header="r1", sequence="A" * 300),
            RankedProteinRecord(rank=2, header="r2", sequence="M" * 120_000),
            RankedProteinRecord(rank=3, header="r3", sequence="C" * 300)]
    write_wise_batches(recs, tmp_path, emit_all=True)
    rows = list(csv.DictReader(open(tmp_path / "ACTIVE_AND_DEFERRED_QUEUE_FILES.csv")))
    big = [r for r in rows if r["rank_range"] == "2-2"][0]
    assert big["status"] == "hold_over_web_cap"
    assert all(r["status"] == "ready_to_run" for r in rows if r is not big)
    ledger = {r["rank"]: r for r in csv.DictReader(open(tmp_path / "STABLE_QUEUE_LEDGER.csv"))}
    assert ledger["2"]["status"] == "hold_over_web_cap"
    assert ledger["1"]["status"] == "pending"
