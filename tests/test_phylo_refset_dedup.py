"""Unit tests for the phylo_refset dedup logic + outgroup_registry parsing.

Hermetic: Tier-2 (sequence) dedup needs the blast env, so these tests force BLAST_BIN to a bogus path so
only Tier-1 (metadata) + the pure helpers are exercised deterministically. Tier-2 is covered by the
end-to-end validation recorded in the PATCH_CARD (Streptomyces committee 34->25).

Run: pytest candidate_files/tests/test_phylo_refset_dedup.py -q
"""
import importlib.util
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, "..", "tools")


def _load(name):
    path = os.path.join(TOOLS, name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_parse_header():
    rs = _load("phylo_refset")
    assert rs._parse_header("Streptomyces_mashuensis_strain_DSM_40221_NR_026174") == \
        ("Streptomyces", "mashuensis", "DSM40221", "NR_026174")
    # no strain token
    assert rs._parse_header("Streptomyces_albiaxialis_NR_043378")[:2] == ("Streptomyces", "albiaxialis")
    assert rs._parse_header("Streptomyces_albiaxialis_NR_043378")[3] == "NR_043378"
    # versioned accession
    assert rs._parse_header("Kitasatospora_setae_KM_6054T_NR_112082.2")[3] == "NR_112082.2"


def test_rep_score_prefers_type_collection_then_length():
    rs = _load("phylo_refset")
    dsm = ("Streptomyces_x_strain_DSM_100_NR_1", "A" * 1400)
    nrrl = ("Streptomyces_x_strain_NRRL_B_5_NR_2", "A" * 1400)
    # DSM outranks NRRL in the collection priority
    assert rs._rep_score(dsm) > rs._rep_score(nrrl)
    # longer sequence wins within the same (absent) collection
    short = ("Streptomyces_y_NR_3", "A" * 900)
    longer = ("Streptomyces_y_NR_4", "A" * 1400)
    assert rs._rep_score(longer) > rs._rep_score(short)


def test_tier1_collapses_duplicate_accession(monkeypatch):
    rs = _load("phylo_refset")
    monkeypatch.setattr(rs, "BLAST_BIN", "/nonexistent/bin")  # force Tier-2 skip -> deterministic
    recs = [
        ("Streptomyces_mashuensis_strain_DSM_40221_NR_026174", "ACGT" * 350),
        ("Streptomyces_mashuensis_strain_DSM_40221_NR_116638", "ACGT" * 350),   # same strain, dup accession
        ("Streptomyces_coelicolor_strain_DSM_40233_NR_116633", "TTTT" * 350),
    ]
    kept, collapses = rs.dedup(recs, report=None, verbose=False)
    kept_names = {h for h, _ in kept}
    assert len(kept) == 2
    assert "Streptomyces_coelicolor_strain_DSM_40233_NR_116633" in kept_names
    # exactly one mashuensis survives, and it is the kept one recorded in the collapse
    mash = [h for h in kept_names if "mashuensis" in h]
    assert len(mash) == 1
    assert any(c["tier"] == 1 for c in collapses)


def test_no_strain_token_not_collapsed_by_tier1(monkeypatch):
    rs = _load("phylo_refset")
    monkeypatch.setattr(rs, "BLAST_BIN", "/nonexistent/bin")
    # two different species with no strain token must both survive Tier-1
    recs = [
        ("Streptomyces_albiaxialis_NR_043378", "ACGT" * 300),
        ("Streptomyces_champavatii_NR_115669", "TTGG" * 300),
    ]
    kept, _ = rs.dedup(recs, report=None, verbose=False)
    assert len(kept) == 2


def test_outgroup_registry_parses_locked_rows():
    og = _load("outgroup_registry")
    # OUTGROUP_REGISTRY.tsv is governed workspace data, not redistributed with the bundle
    # (docs/EXTERNAL_DATA.md). Absent registry => NOT MEASURED, not a failure.
    if not os.path.exists(og.REGISTRY):
        pytest.skip(f"governed outgroup registry not provisioned: {og.REGISTRY}")
    # find_row should resolve the LOCKED genus rows the cohorts depend on
    strep = og.find_row("Streptomyces", scope="genus")
    assert strep is not None and strep["outgroup_genus"] == "Kitasatospora"
    noc = og.find_row("Nocardia", scope="genus")
    assert noc is not None and noc["outgroup_genus"] == "Rhodococcus"
    # family scope differs from genus scope for Streptomycetaceae
    fam = og.find_row("Streptomycetaceae", scope="family")
    assert fam is not None and fam["tree_scope"] == "family"
