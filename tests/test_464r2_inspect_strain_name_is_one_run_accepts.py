"""`inspect` prints a `--strain` value that `run` accepts.

A long public ZIP name used to give a 73- or 87-character suggestion, and `run` refuses anything
over 64 characters with exit 2.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mamey import package_inspector as pi
from mamey.strain_identity import looks_like_accession, validate_strain_id


@pytest.mark.parametrize("name", [
    "Actinomadura_atramentaria_DSM_43919_SF2197__GCA_000381885.1__antiSMASH8.0.4_loose.zip",
    "CP003275__Streptomyces_hygroscopicus_subsp._jinggangensis_5008__results_round9_2026-10-08.zip",
    "X" * 120 + ".zip",
])
def test_a_long_file_name_gives_a_name_run_accepts(monkeypatch, name):
    monkeypatch.setattr("mamey.strain_identity._from_archive", lambda _zip: (None, None))
    strain, note = pi._inspect_strain_name(Path(name))
    assert validate_strain_id(strain) == strain
    assert len(strain) <= 64
    assert "64 characters" in note


def test_the_archive_suggestion_is_preferred_when_the_file_name_is_too_long(monkeypatch):
    monkeypatch.setattr("mamey.strain_identity._from_archive",
                        lambda _zip: ("Streptomyces_example_ABC1", "Streptomyces example ABC1"))
    strain, note = pi._inspect_strain_name(Path("Q" * 80 + ".zip"))
    assert strain == "Streptomyces_example_ABC1"
    assert "--strain auto" in note


def test_an_accession_file_name_is_replaced_when_the_archive_names_an_organism(monkeypatch):
    monkeypatch.setattr("mamey.strain_identity._from_archive",
                        lambda _zip: ("Streptomyces_example_CP000001", "Streptomyces example"))
    strain, note = pi._inspect_strain_name(Path("CP000001.1.zip"))
    assert strain == "Streptomyces_example_CP000001"
    assert not looks_like_accession(strain)
    assert note


def test_a_short_valid_file_name_is_kept_unchanged(monkeypatch):
    monkeypatch.setattr("mamey.strain_identity._from_archive",
                        lambda _zip: ("Something_else", "Something else"))
    assert pi._inspect_strain_name(Path("Streptomyces_luteoverticillatus_CP034587.zip")) == (
        "Streptomyces_luteoverticillatus_CP034587", "")


def test_shortening_cuts_at_a_token_boundary():
    out = pi._shorten_strain_guess("Actinomadura_atramentaria_DSM_43919_SF2197_GCA_000381885.1_antiSMASH8.0.4")
    assert out == "Actinomadura_atramentaria_DSM_43919_SF2197_GCA_000381885.1"


@pytest.mark.parametrize("name,expected", [
    ("Strep..dotdot.zip", "Strep.dotdot"),
    ("A..B_strain_7.zip", "A.B_strain_7"),
])
def test_double_dots_collapse_instead_of_becoming_isolate(monkeypatch, name, expected):
    monkeypatch.setattr("mamey.strain_identity._from_archive", lambda _zip: (None, None))
    strain, note = pi._inspect_strain_name(Path(name))
    assert strain == expected
    assert "64 characters" not in note
    assert "removed" in note


@pytest.mark.parametrize("name", ["Streptomyces_é_ünicode_strain.zip", "-leading_dash.zip"])
def test_a_changed_name_always_gets_a_note(monkeypatch, name):
    monkeypatch.setattr("mamey.strain_identity._from_archive", lambda _zip: (None, None))
    strain, note = pi._inspect_strain_name(Path(name))
    assert validate_strain_id(strain) == strain
    assert note


def test_an_accession_prefixed_name_uses_the_archive_suggestion(monkeypatch):
    monkeypatch.setattr("mamey.strain_identity._from_archive",
                        lambda _zip: ("Streptomyces_sp_EX1_GCA_000000001_1", "Streptomyces sp. EX1"))
    strain, note = pi._inspect_strain_name(Path("GCA_000000001.1_ASM1v1_genomic.zip"))
    assert strain == "Streptomyces_sp_EX1_GCA_000000001_1"
    assert "database accession" in note


def test_inspect_command_prints_the_safe_name(tmp_path, monkeypatch, capsys):
    """End to end: fails if inspect_command stops calling _inspect_strain_name."""
    import zipfile
    from types import SimpleNamespace
    import mamey.parsers as parsers
    monkeypatch.setattr(parsers, "_gbk_size_guard", lambda *a: None)
    monkeypatch.setattr(parsers, "extract_antismash_version", lambda *a, **kw: "8.0.4")
    monkeypatch.setattr("mamey.strain_identity._from_archive", lambda _zip: (None, None))
    path = tmp_path / ("Streptomyces_example_" + "long_name_part_" * 5 + "results_round1.zip")
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("EXAMPLE.region001.gbk", "LOCUS x\n")
    assert pi.inspect_command(SimpleNamespace(zip=str(path))) == 0
    out = capsys.readouterr().out
    line = next(l for l in out.splitlines() if l.strip().startswith("--strain "))
    strain = line.split()[1]
    assert len(Path(path).stem) > 64
    assert len(strain) <= 64 and validate_strain_id(strain) == strain
    assert "    Strain name: " in out
