"""The strain id that `--strain auto` resolves to must pass validate_strain_id, even for a long organism name."""
from __future__ import annotations

from mamey.antismash_input import _suggest_strain_id
from mamey.strain_identity import validate_strain_id


def test_long_organism_suggestion_is_accepted_by_the_validator():
    organism = "Streptomyces " + "verylongspeciesepithet" * 3 + " strain ABCDEFGHIJ0123456789"
    got = _suggest_strain_id(organism, "/x/JAAAAA010000000.1.zip")
    assert got is not None and len(got) <= 64
    assert validate_strain_id(got) == got


def test_suggestion_with_appended_accession_stays_within_the_limit():
    organism = "Micromonospora " + "a" * 60
    got = _suggest_strain_id(organism, "/x/GCF_000123456.1.zip")
    assert len(got) <= 64 and not got.endswith("_")
    assert validate_strain_id(got) == got


def test_short_names_are_unchanged():
    assert _suggest_strain_id("Streptomyces sp. ABC-1", "/x/ABC1.zip") == "Streptomyces_sp_ABC_1"
