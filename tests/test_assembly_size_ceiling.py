"""The assembly size check must be two-sided without any caller prior.

`assembly_sanity_check` has flagged undersized records via `ACTINOMYCETE_MIN_BP` with no prior.
The only upper bound was check (c), `expected_size_bp`, which the engine never passes, so an
assembly of any size above the floor raised nothing. These tests pin the invariant (the band is
checked from both sides, the flag is advisory, and the engine routes it to its own message), not
the exact constant, which is owner-tunable.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mamey.assembly import ACTINOMYCETE_MAX_BP, ACTINOMYCETE_MIN_BP, assembly_sanity_check

ROOT = Path(__file__).resolve().parents[1]


def _contigs(total_bp: int, n: int) -> dict[str, str]:
    """n equal contigs at ~70% GC, built by repetition so large genomes stay cheap."""
    per = total_bp // n
    unit = "GCGCGCGATA"  # 7 of 10 bases G/C
    seq = (unit * (per // len(unit) + 1))[:per]
    return {f"contig_{i}": seq for i in range(n)}


def test_ceiling_exists_and_sits_above_the_floor():
    assert ACTINOMYCETE_MAX_BP > ACTINOMYCETE_MIN_BP
    assert ACTINOMYCETE_MAX_BP >= 11_500_000


def test_ceiling_matches_the_operator_qc_tool_warn_threshold():
    """The engine and tools/assembly_qc_check.py must not disagree on what is oversized."""
    text = (ROOT / "tools" / "assembly_qc_check.py").read_text(encoding="utf-8")
    assert f"GENOME_WARN={ACTINOMYCETE_MAX_BP:_}" in text


@pytest.mark.parametrize("total_bp", [7_600_000, 11_250_000])
def test_typical_and_large_plausible_genomes_are_not_flagged(total_bp):
    res = assembly_sanity_check(_contigs(total_bp, 200))
    assert "INFLATED_ASSEMBLY_SUSPECT" not in res["flags"]
    assert "PARTIAL_ASSEMBLY_SUSPECT" not in res["flags"]


@pytest.mark.parametrize("total_bp", [13_400_000, 17_900_000, 40_000_000])
def test_oversized_assembly_is_flagged_without_any_caller_prior(total_bp):
    res = assembly_sanity_check(_contigs(total_bp, 400))
    assert "INFLATED_ASSEMBLY_SUSPECT" in res["flags"], res["flags"]


def test_ceiling_is_reported_and_can_be_disabled():
    res = assembly_sanity_check(_contigs(17_900_000, 400))
    assert res["max_genome_bp"] == ACTINOMYCETE_MAX_BP
    off = assembly_sanity_check(_contigs(17_900_000, 400), max_genome_bp=None)
    assert "INFLATED_ASSEMBLY_SUSPECT" not in off["flags"]
    assert off["max_genome_bp"] is None


def test_check_stays_non_blocking():
    res = assembly_sanity_check(_contigs(17_900_000, 400))
    assert res["partial_submission_suspect"] is False
    assert res["n_contigs"] == 400
    assert "claim_safety" in res


def test_floor_and_ceiling_are_mutually_exclusive():
    small = assembly_sanity_check(_contigs(1_000_000, 3))["flags"]
    big = assembly_sanity_check(_contigs(17_900_000, 400))["flags"]
    assert "PARTIAL_ASSEMBLY_SUSPECT" in small and "INFLATED_ASSEMBLY_SUSPECT" not in small
    assert "INFLATED_ASSEMBLY_SUSPECT" in big and "PARTIAL_ASSEMBLY_SUSPECT" not in big


def test_engine_routes_the_ceiling_flag_away_from_the_gc_message():
    """Without this, the flag would land in the GC-dispersion sentence, which reports a GC sd
    that says nothing about size."""
    text = (ROOT / "mamey" / "cli.py").read_text(encoding="utf-8")
    assert '_inflated_flags = [f for f in _sanity["flags"] if f == "INFLATED_ASSEMBLY_SUSPECT"]' in text
    assert 'f != "INFLATED_ASSEMBLY_SUSPECT"]' in text
