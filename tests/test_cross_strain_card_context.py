"""Tests for Gap 2 — cross_strain_card_context. Verified against the scored 24-strain master."""
import sys, os, pathlib
import pytest
_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
from mamey.cross_strain_card_context import (
    load_prevalence, registry_size, classify_class, card_context_block, _UBIQUITOUS_FALLBACK,
)

MASTER = str(_ROOT / "private" / "cohort_fixtures" / "_cohort_master_v2.xlsx")
# v9.7.414 (BC2): this was a module-level `pytestmark`, so EVERY test here skipped whenever the
# non-shipped 24-strain scored master was absent — which is always, in this tier. That is exactly
# the pattern TEST-02 removed from the sibling test_cohort_synthesis.py ("hiding the pure-logic and
# self-contained tests too"); this file never received the same treatment. Scope the skip to the
# tests that genuinely need the xlsx, so the self-contained refuse-path test runs in every tier.
needs_master = pytest.mark.skipif(not os.path.exists(MASTER),
                                  reason="scored cohort master fixture not present in this tier")

# The 11 hand-found differentiating capacities (ground truth from the 24-strain analysis)
EXPECTED_UNIQUE = {
    "crocagin", "blactam", "linaridin", "polyyne", "furan", "NAGGN",
    "guanidinotides", "nucleoside", "transAT-PKS-like", "prodigiosin", "lanthipeptide-class-v",
}


@pytest.fixture(scope="module")
def prev():
    return load_prevalence(MASTER)


@pytest.fixture(scope="module")
def N():
    return registry_size(MASTER)


@needs_master
def test_registry_size(N):
    assert N == 24


@needs_master
def test_prevalence_loads(prev):
    assert len(prev) >= 24  # 24 strains' worth of classes


@needs_master
def test_ubiquitous_fallback_classes(prev, N):
    for cls in ["other", "terpene", "saccharide", "NI-siderophore"]:
        assert classify_class(cls, prev, N) == "UBIQUITOUS"


@needs_master
def test_reproduces_11_differentiating_capacities(prev, N):
    """The headline verification: reproduce the hand-found cohort-unique set exactly."""
    found = {c for c in prev if classify_class(c, prev, N) == "UNIQUE"}
    assert EXPECTED_UNIQUE <= found, f"missing: {EXPECTED_UNIQUE - found}"
    # and no spurious extras beyond genuine 1-strain classes
    assert found == EXPECTED_UNIQUE, f"unexpected: {found - EXPECTED_UNIQUE}"


@needs_master
def test_card_block_flags_unique_and_ubiquitous(prev, N):
    blk = card_context_block("AS-900", "BGC015", ["RiPP", "crocagin", "saccharide"], prev, N)
    assert "COHORT-UNIQUE" in blk
    assert "crocagin" in blk
    assert "ubiquitous" in blk.lower()
    assert "saccharide" in blk


@needs_master
def test_all_strain_class_not_called_differentiating(prev, N):
    blk = card_context_block("AS-900", "BGCx", ["RiPP"], prev, N)
    assert "not strain-differentiating" in blk


def test_empty_master_returns_blank():
    """Fail-safe: stale/empty prevalence must not crash or emit wrong context."""
    assert card_context_block("AS-X", "BGC001", ["NRPS"], {}, 0) == ""


@needs_master
def test_unknown_class_silent(prev, N):
    """A class absent from the prevalence sheet is silently skipped, not guessed."""
    blk = card_context_block("AS-X", "BGC001", ["totally_made_up_class_xyz"], prev, N)
    assert "totally_made_up_class_xyz" not in blk


@needs_master
def test_string_products_accepted(prev, N):
    """products may be a bare string, not just a list."""
    blk = card_context_block("AS-901", "BGC007", "blactam", prev, N)
    assert "COHORT-UNIQUE" in blk
