"""Stability + schema tests for the packaged MIBiG reference neighborhoods (AMBER_P360-003).

These guard the reference partitions once they are in the bundle: every family present, every neighborhood
has exactly one representative, reps.faa matches the membership, and the known 2026-08-10 counts hold (a
drift here means the panel or the clustering changed and the docs/PROVENANCE must be re-synced).
"""
import os
import pytest

from mamey import mibig_neighborhoods_api as NB

# v9.7.362: the MIBiG-derived neighborhood partitions are user-provisioned (CC BY 4.0, not
# redistributed). These tests assert dataset CONTENT, so they run only where it is provisioned.
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
from mamey import external_data as _xd
pytestmark = pytest.mark.skipif(
    _xd.resolve("mibig_neighborhoods") is None,
    reason="MIBiG neighborhoods not provisioned (see docs/EXTERNAL_DATA.md)",
)

EXPECTED = {"KS": 37, "C": 13, "A": 30, "AT": 30, "glyc": 21, "resi": 23}


def test_all_families_present():
    s = NB.summary()
    assert set(s) == set(EXPECTED), f"packaged families {set(s)} != {set(EXPECTED)}"


@pytest.mark.parametrize("fam,n", EXPECTED.items())
def test_neighborhood_counts_stable(fam, n):
    fams = NB.load_family(fam)
    assert len(fams) == n, f"{fam}: {len(fams)} neighborhoods, expected {n}"


@pytest.mark.parametrize("fam", EXPECTED)
def test_exactly_one_rep_per_neighborhood(fam):
    for nb_id, nb in NB.load_family(fam).items():
        assert nb.rep_tip, f"{nb_id} has no representative"
        assert nb.rep_tip in nb.members, f"{nb_id} rep not among its members"


@pytest.mark.parametrize("fam", EXPECTED)
def test_reps_faa_matches_membership(fam):
    p = NB.reps_faa_path(fam)
    assert os.path.exists(p), p
    ids = {ln[1:].strip() for ln in open(p, encoding="utf-8") if ln.startswith(">")}
    reps = {nb.rep_tip for nb in NB.load_family(fam).values()}
    assert ids == reps, f"{fam}: reps.faa ids != membership reps (missing {reps - ids}; extra {ids - reps})"


@pytest.mark.parametrize("fam", EXPECTED)
def test_reps_carry_metabolite_and_accession(fam):
    for nb_id, nb in NB.load_family(fam).items():
        assert nb.accession.startswith("BGC"), f"{nb_id} rep accession {nb.accession!r} not a BGC id"
