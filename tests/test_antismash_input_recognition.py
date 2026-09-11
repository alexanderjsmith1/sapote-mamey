"""Tests for mamey.antismash_input — recognising antiSMASH archives by content, not by name.

Fixtures are built in-process so the suite stays offline and ships no data. Where a real archive is
available the test asserts against it; otherwise it skips (the house convention: a skip means gated,
not broken).
"""
import io
import json
import os
import zipfile

import pytest

from mamey.antismash_input import (
    AntismashInput,
    VALID_STRICTNESS,
    detect_strictness,
    identify,
    is_antismash_archive,
)

GBK_HEADER = """LOCUS       NODE_1_length_100000    20747 bp    DNA     linear   BCT 08-JUN-2026
DEFINITION  Streptomyces coelicolor A3(2) chromosome.
ACCESSION   CP999999
VERSION     CP999999.1
SOURCE      Streptomyces coelicolor A3(2)
  ORGANISM  {organism}
            Bacteria; Bacillati; Actinomycetota; Actinomycetes; Kitasatosporales;
            Streptomycetaceae; Streptomyces.
COMMENT     ##antiSMASH-Data-START##
            Version      :: 8.0.4
            Run date     :: 2026-06-08 03:02:24
            ##antiSMASH-Data-END##
FEATURES             Location/Qualifiers
     source          1..20747
                     /organism="{organism}"
ORIGIN
//
"""


def _make_zip(tmp_path, name, *, regions=2, strictness="loose", organism="Streptomyces coelicolor A3(2)",
              markers=True, json_payload=True):
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as zf:
        for i in range(1, regions + 1):
            zf.writestr(f"NODE_1_length_100000.region{i:03d}.gbk",
                        GBK_HEADER.format(organism=organism))
        if markers:
            zf.writestr("regions.js", "var recordData = [];")
            zf.writestr("index.html", "<html></html>")
        if json_payload:
            # pad so the strictness token does not sit in the first bytes, exercising streaming
            blob = {"version": "8.0.4", "padding": "x" * 200_000,
                    "records": [{"modules": {"antismash.detection.hmm_detection":
                                             {"strictness": strictness}}}]}
            zf.writestr("results.json", json.dumps(blob))
    return str(path)


class TestRecognition:
    def test_recognises_antismash_regardless_of_filename(self, tmp_path):
        for name in ("CP025018.1.zip", "my results (1).zip", "FINAL_v2 copy.zip", "результаты.zip"):
            info = identify(_make_zip(tmp_path, name))
            assert info.is_antismash, f"should recognise {name}"
            assert info.n_regions == 2

    def test_non_antismash_zip_is_rejected_with_a_reason(self, tmp_path):
        path = tmp_path / "notes.zip"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("notes.txt", "just some notes")
        info = identify(str(path))
        assert info.is_antismash is False
        assert info.warnings and "antiSMASH" in info.warnings[0]

    def test_missing_file_and_non_zip_never_raise(self, tmp_path):
        assert identify(str(tmp_path / "nope.zip")).is_antismash is False
        plain = tmp_path / "plain.txt"
        plain.write_text("hello")
        info = identify(str(plain))
        assert info.is_antismash is False
        assert "not a ZIP archive" in info.warnings

    def test_corrupt_zip_is_reported_not_raised(self, tmp_path):
        bad = tmp_path / "broken.zip"
        bad.write_bytes(b"PK\x03\x04corrupt-not-really-a-zip")
        info = identify(str(bad))
        assert info.is_antismash is False

    def test_markers_without_regions_flags_zero_regions(self, tmp_path):
        info = identify(_make_zip(tmp_path, "empty.zip", regions=0))
        assert info.is_antismash is True
        assert info.n_regions == 0
        assert any("zero region GBKs" in w for w in info.warnings)


class TestStrictness:
    @pytest.mark.parametrize("flavor", VALID_STRICTNESS)
    def test_each_strictness_is_detected(self, tmp_path, flavor):
        info = identify(_make_zip(tmp_path, f"{flavor}.zip", strictness=flavor))
        assert info.strictness == flavor
        assert info.strictness_evidence

    def test_strictness_found_deep_in_a_large_json(self, tmp_path):
        # the real token sits ~15 MB in; ensure streaming crosses chunk boundaries
        path = tmp_path / "big.zip"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("NODE_1.region001.gbk", GBK_HEADER.format(organism="Streptomyces sp."))
            padding = "y" * (9 * 1024 * 1024)
            zf.writestr("results.json",
                        '{"pad":"' + padding + '","strictness": "relaxed"}')
        info = identify(str(path))
        assert info.strictness == "relaxed"

    def test_unknown_when_absent_and_warns_against_pooling(self, tmp_path):
        info = identify(_make_zip(tmp_path, "nojson.zip", json_payload=False))
        assert info.strictness == "unknown"
        assert any("pooled" in w for w in info.warnings)

    def test_unrecognised_value_does_not_become_a_guess(self, tmp_path):
        path = tmp_path / "weird.zip"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("NODE_1.region001.gbk", GBK_HEADER.format(organism="Streptomyces sp."))
            zf.writestr("results.json", '{"strictness": "banana"}')
        assert identify(str(path)).strictness == "unknown"

    def test_comparable_key_separates_strictness(self, tmp_path):
        a = identify(_make_zip(tmp_path, "a.zip", strictness="loose"))
        b = identify(_make_zip(tmp_path, "b.zip", strictness="relaxed"))
        assert a.comparable_key != b.comparable_key


class TestOrganism:
    def test_organism_from_gbk_beats_filename(self, tmp_path):
        info = identify(_make_zip(tmp_path, "CP025018.1.zip"))
        assert info.organism_source == "gbk_organism"
        assert info.organism.startswith("Streptomyces coelicolor")

    def test_placeholder_dot_is_not_an_organism_and_filename_is_used(self, tmp_path):
        # antiSMASH over a bare GCA assembly writes "ORGANISM  ."
        path = _make_zip(tmp_path, "Streptomyces_avermitilis_GCA_000009765.2.zip", organism=".")
        info = identify(path)
        assert info.organism_source == "filename"
        assert info.organism.startswith("Streptomyces avermitilis")

    def test_accession_only_filename_with_placeholder_leaves_organism_unresolved(self, tmp_path):
        info = identify(_make_zip(tmp_path, "CP108695.1.zip", organism="."))
        assert info.organism is None
        assert any("organism could not be resolved" in w for w in info.warnings)

    def test_suggested_strain_id_is_never_a_bare_accession(self, tmp_path):
        info = identify(_make_zip(tmp_path, "CP025018.1.zip"))
        assert info.suggested_strain_id
        assert not info.suggested_strain_id.upper().startswith("CP0")
        assert info.suggested_strain_id.startswith("Streptomyces")

    def test_lineage_gives_phylum_and_actinomycete_flag(self, tmp_path):
        info = identify(_make_zip(tmp_path, "x.zip"))
        assert info.is_actinomycete is True
        assert "Actinomycetota" in info.lineage

    def test_non_actinomycete_is_flagged(self, tmp_path):
        header = GBK_HEADER.replace(
            "Bacteria; Bacillati; Actinomycetota; Actinomycetes; Kitasatosporales;",
            "Bacteria; Pseudomonadati; Pseudomonadota; Betaproteobacteria; Burkholderiales;")
        path = tmp_path / "burk.zip"
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("NODE_1.region001.gbk", header.format(organism="Burkholderia gladioli"))
            zf.writestr("results.json", '{"strictness": "loose"}')
        info = identify(str(path))
        assert info.is_actinomycete is False
        assert info.phylum == "Pseudomonadota"


class TestMetadata:
    def test_antismash_version_is_read(self, tmp_path):
        assert identify(_make_zip(tmp_path, "v.zip")).antismash_version == "8.0.4"

    def test_summary_is_human_readable(self, tmp_path):
        text = identify(_make_zip(tmp_path, "s.zip")).summary()
        assert "antiSMASH" in text and "strictness=loose" in text

    def test_is_antismash_archive_convenience(self, tmp_path):
        assert is_antismash_archive(_make_zip(tmp_path, "c.zip")) is True


REAL = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                    "strain_data", "_ANTISMASH_CANONICAL")


@pytest.mark.skipif(not os.path.isdir(REAL), reason="canonical antiSMASH home not present")
class TestAgainstRealArchives:
    def test_known_loose_and_relaxed_cohort_zips_disagree(self):
        loose = os.path.join(REAL, "loose", "AS-190.zip")
        relaxed = os.path.join(REAL, "relaxed", "AS-190.zip")
        if not (os.path.isfile(loose) and os.path.isfile(relaxed)):
            pytest.skip("AS-190 pair not present")
        a, b = identify(loose), identify(relaxed)
        assert a.strictness == "loose" and b.strictness == "relaxed"
        # loose detects more regions than relaxed for the same genome
        assert a.n_regions > b.n_regions
