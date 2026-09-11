"""Nocardia genus reference bank invariants (v9.7.99).

Locks the shipped bank: well-formed, single-engine, public-only, standing exclusions honored, and the
computed prevalence baseline internally consistent. Also pins the version-discipline refusal.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
import mamey.genus_reference as g

EXPECTED_COLS = {"strain_id", "accession", "organism", "species", "release_flag", "engine_version",
                 "strain_total_bgcs", "bgc_class", "n_bgcs_in_class", "ab_max", "ab_mean",
                 "af_max", "af_mean", "comparative_eligible"}


def test_bank_loads_and_is_well_formed():
    rows = g.load_nocardia_reference(comparative_only=False)
    assert rows, "Nocardia reference bank is empty"
    assert EXPECTED_COLS <= set(rows[0].keys())
    assert len({r["strain_id"] for r in rows}) == 7
    assert {r["release_flag"] for r in rows} == {"PUBLIC"}, "bank must be public-only (ships in all tiers)"


def test_single_engine_version():
    assert g.reference_engine_version() == "1.9.96"


def test_comparative_filter_drops_exclusions():
    comp = g.load_nocardia_reference(comparative_only=True)
    classes = {r["bgc_class"] for r in comp}
    assert not (classes & g.STANDING_EXCLUSIONS), f"standing exclusions leaked into comparative set: {classes & g.STANDING_EXCLUSIONS}"
    assert all(r["comparative_eligible"] == "True" for r in comp)
    assert len(comp) < len(g.load_nocardia_reference(comparative_only=False))


def test_prevalence_baseline_consistent():
    prev = g.nocardia_class_prevalence()
    assert prev
    for r in prev:
        n, tot = int(r["n_strains_carrying"]), int(r["n_strains_total"])
        assert tot == 7
        assert 1 <= n <= tot
        assert (r["genus_core_7of7"] == "True") == (n == tot)


def test_genus_core_is_nonempty_and_recurrent():
    core = g.genus_core_classes()
    # the README-predicted core members must be present (claim-safe: recurrent capacity, not shared product)
    for expected in ("NRPS", "PKS", "RiPP", "siderophore/metallophore", "terpene"):
        assert expected in core, f"{expected} expected in genus core"


def test_genus_core_excludes_other_residual():
    # P16 (v9.7.101): the 'other' catch-all is not a real shared biosynthetic class,
    # so it must not be reported as genus-core even when it appears in 7/7 strains.
    assert "other" not in g.genus_core_classes()


def test_version_discipline_refuses_boundary_mismatch():
    g.assert_comparable_with("1.9.96")  # same engine: OK
    with pytest.raises(ValueError):
        g.assert_comparable_with("1.9.97")  # boundary: capacity-score pooling refused
