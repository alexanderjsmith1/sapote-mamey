"""BC2 .399 audit: mamey/wise_fragmented_pks.py::write_wise_batches() hardcoded the queue_id's
own "85K" segment to the DEFAULT target_residues literal, regardless of the actual
target_residues value the call was given. Reproduced directly: write_wise_batches(...,
target_residues=EXTRA_SAFE_TARGET_RESIDUES) [50_000] still emitted a queue_id claiming "85K".
No downstream code parses queue_id (verified: no tools/*.py or mamey/*.py other than this
module's own test files reads it), so this is purely human-facing -- but this module's own
docstring frames the queue system as "a stable queue ledger" a human operator relies on.
"""
from pathlib import Path
import csv

from mamey.wise_fragmented_pks import (
    RankedProteinRecord, write_wise_batches, EXTRA_SAFE_TARGET_RESIDUES, DEFAULT_TARGET_RESIDUES,
)


def _rec(rank, n=1000):
    return RankedProteinRecord(rank=rank, header=f"AS-X|rank={rank}", sequence="M" * n)


def test_queue_id_reflects_a_custom_target_residues(tmp_path):
    records = [_rec(i) for i in range(1, 4)]
    write_wise_batches(records, tmp_path, target_residues=EXTRA_SAFE_TARGET_RESIDUES)
    rows = list(csv.DictReader((tmp_path / "ACTIVE_AND_DEFERRED_QUEUE_FILES.csv").open()))
    assert rows, "no batch rows emitted"
    for r in rows:
        assert "85K" not in r["queue_id"], f"queue_id still claims 85K with a 50K target: {r['queue_id']}"
        assert "50K" in r["queue_id"], f"queue_id doesn't reflect the real 50K target: {r['queue_id']}"


def test_queue_id_still_says_85k_for_the_real_default(tmp_path):
    """No regression: the default target_residues (85_000) still produces '85K'."""
    records = [_rec(i) for i in range(1, 4)]
    write_wise_batches(records, tmp_path, target_residues=DEFAULT_TARGET_RESIDUES)
    rows = list(csv.DictReader((tmp_path / "ACTIVE_AND_DEFERRED_QUEUE_FILES.csv").open()))
    assert all("85K" in r["queue_id"] for r in rows)
