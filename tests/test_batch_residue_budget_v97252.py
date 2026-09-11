"""v9.7.252 — batches were capped by protein COUNT, never by cumulative RESIDUES.

Two contradictory field observations were on record:
  * the AS-705 archive: five clean 30-protein batches, zero all-zero batches
  * the docs lineage: a 30-protein batch returning zero alignments, reproduced 3x

the Developer or User, 2026-07-10: "batches of 30 worked fine except for very large proteins, and the submissions
needed temporal spacing." Both observations are true. The variable was never the count; it was the
payload. Giants (>2500 aa) already ran solo, but thirty 2,400-aa proteins is 72,000 residues in one
submission and not one of them is a giant.

So `MAX_BATCH = 30` stays -- lowering it would have been the wrong fix for the right symptom.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mamey.blastp_online import (chunk_proteins, batch_shape, MAX_BATCH, DEFAULT_BATCH,
                                 RESIDUE_BUDGET, GIANT_AA, SUBMIT_GAP_S)


def _aa(batch):
    return sum(len(s) for _, s in batch)


def test_small_proteins_still_fill_a_batch_of_thirty():
    """The count limit is real and unchanged; 30 x 350 aa is well inside the budget."""
    batches = chunk_proteins([(f"q{i}", "M" * 350) for i in range(60)], 30)
    assert [len(b) for b in batches] == [30, 30]
    assert all(_aa(b) <= RESIDUE_BUDGET for b in batches)


def test_large_proteins_split_by_residue_budget_not_count():
    """The exact case the Developer or User hit: 30 merely-large proteins, none a giant, 72,000 residues."""
    batches = chunk_proteins([(f"q{i}", "M" * 2400) for i in range(30)], 30)
    assert len(batches) > 1, "one 72,000-residue submission is what returned zero alignments"
    assert all(_aa(b) <= RESIDUE_BUDGET for b in batches)
    assert sum(len(b) for b in batches) == 30, "no protein may be dropped"


def test_giants_still_run_solo():
    batches = chunk_proteins([("g", "M" * (GIANT_AA + 1))] + [(f"q{i}", "M" * 300) for i in range(5)], 30)
    assert [len(b) for b in batches] == [1, 5]


def test_max_batch_is_not_lowered():
    """Lowering MAX_BATCH would have been the wrong fix: the count was never the variable."""
    assert MAX_BATCH == 30 and DEFAULT_BATCH == 10


def test_no_protein_is_lost_or_duplicated():
    prots = [(f"q{i}", "M" * (100 + i * 137)) for i in range(97)]
    flat = [lt for b in chunk_proteins(prots, 30) for lt, _ in b]
    assert sorted(flat) == sorted(lt for lt, _ in prots)


def test_batch_shape_reports_the_three_numbers_that_matter():
    """The v9.7.250 guard refused an all-empty batch and said nothing about why. Two lineages and
    three reproductions later, the cause was still unknown. Print n, max_aa, total_aa."""
    s = batch_shape([(f"q{i}", "M" * 2400) for i in range(30)])
    assert "n=30" in s and "max_aa=2400" in s and "total_aa=72000" in s and "OVER BUDGET" in s
    ok = batch_shape([(f"q{i}", "M" * 350) for i in range(30)])
    assert "OVER BUDGET" not in ok


def test_submissions_are_temporally_spaced():
    assert SUBMIT_GAP_S > 0, "submissions need spacing, not just retries"
