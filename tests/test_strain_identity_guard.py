"""Tests for mamey.strain_identity — a strain ID must be an identity, not an accession.

Regression anchor: on 2026-08-20 a reference run produced packages named CP025018_1, CP029711_1,
CP108695_1, CP109162_1, CP120997_1, CP192113_1 before it was caught by eye.
"""
import json
import zipfile

import pytest

from mamey.strain_identity import (
    StrainIdentity,
    looks_like_accession,
    resolve_strain_id,
)

GBK = """LOCUS       CP108695                20747 bp    DNA     linear   BCT 08-JUN-2026
DEFINITION  Nocardia sp. NBC_01009 chromosome.
SOURCE      Nocardia sp. NBC_01009
  ORGANISM  {organism}
            Bacteria; Bacillati; Actinomycetota; Actinomycetes; Mycobacteriales;
            Nocardiaceae; Nocardia.
COMMENT     ##antiSMASH-Data-START##
            Version      :: 8.0.4
            ##antiSMASH-Data-END##
ORIGIN
//
"""


def _zip(tmp_path, name, organism="Nocardia sp. NBC_01009"):
    p = tmp_path / name
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("NODE_1.region001.gbk", GBK.format(organism=organism))
        zf.writestr("results.json", json.dumps({"strictness": "loose"}))
    return str(p)


class TestAccessionDetection:
    @pytest.mark.parametrize("label", [
        "NC_003888.3", "NZ_QHHY00000000.1", "QHHY00000000", "GCA_009862675.1", "GCF_000147815.2",
        # the sanitised forms that actually appeared on disk
        "CP025018_1", "CP108695_1", "NZ_ARHC00000000_1", "GCA_009862675_1",
    ])
    def test_accessions_are_recognised(self, label):
        assert looks_like_accession(label) is True

    @pytest.mark.parametrize("label", [
        "AS-190", "AS-696_second", "Streptomyces_malaysiensis_CP025018_1",
        "Nocardia_sp_NBC_01009", "Kribbella_albertanoniae", "SID10815",
    ])
    def test_real_identities_are_not_flagged(self, label):
        assert looks_like_accession(label) is False

    def test_empty_is_not_an_accession(self):
        assert looks_like_accession("") is False
        assert looks_like_accession(None) is False


class TestRefusal:
    def test_accession_strain_is_refused_when_a_better_name_exists(self, tmp_path):
        z = _zip(tmp_path, "CP108695.1.zip")
        ident = resolve_strain_id("CP108695_1", z)
        assert ident.refused is True
        assert not ident
        assert ident.suggestion and ident.suggestion.startswith("Nocardia")
        # the message must be actionable, not merely disapproving
        assert "--strain" in ident.message and ident.suggestion in ident.message

    def test_refusal_names_the_organism(self, tmp_path):
        ident = resolve_strain_id("CP108695_1", _zip(tmp_path, "CP108695.1.zip"))
        assert "Nocardia sp. NBC_01009" in ident.message

    def test_never_blocks_without_offering_an_alternative(self, tmp_path):
        # organism unreadable -> proceed with a warning rather than refuse
        z = _zip(tmp_path, "CP108695.1.zip", organism=".")
        ident = resolve_strain_id("CP108695_1", z)
        assert ident.refused is False
        assert ident.strain_id == "CP108695_1"
        assert "proceeding as given" in ident.message

    def test_escape_hatch_allows_the_accession(self, tmp_path):
        z = _zip(tmp_path, "CP108695.1.zip")
        ident = resolve_strain_id("CP108695_1", z, allow_accession=True)
        assert ident.refused is False
        assert ident.strain_id == "CP108695_1"


class TestAutoResolution:
    def test_auto_resolves_from_the_archive(self, tmp_path):
        ident = resolve_strain_id("auto", _zip(tmp_path, "CP108695.1.zip"))
        assert ident and ident.source == "archive"
        assert ident.strain_id.startswith("Nocardia")
        assert not looks_like_accession(ident.strain_id)

    def test_none_behaves_like_auto(self, tmp_path):
        ident = resolve_strain_id(None, _zip(tmp_path, "CP108695.1.zip"))
        assert ident.source == "archive"

    def test_auto_falls_back_to_zip_stem_and_warns_if_that_is_an_accession(self, tmp_path):
        z = _zip(tmp_path, "CP108695.1.zip", organism=".")
        ident = resolve_strain_id("auto", z)
        assert ident.source == "zip_stem"
        assert "accession" in ident.message
        assert "every output file" in ident.message

    def test_a_good_explicit_id_passes_through_untouched(self, tmp_path):
        ident = resolve_strain_id("AS-190", _zip(tmp_path, "whatever.zip"))
        assert ident.strain_id == "AS-190"
        assert ident.source == "supplied"
        assert ident.refused is False

    def test_missing_zip_does_not_raise(self, tmp_path):
        ident = resolve_strain_id("AS-190", str(tmp_path / "nope.zip"))
        assert ident.strain_id == "AS-190"


class TestRegressionAnchor:
    @pytest.mark.parametrize("bad", ["CP025018_1", "CP029711_1", "CP108695_1",
                                     "CP109162_1", "CP120997_1", "CP192113_1"])
    def test_the_six_ids_that_shipped_on_2026_08_20_are_now_caught(self, tmp_path, bad):
        z = _zip(tmp_path, f"{bad.replace('_1', '.1')}.zip")
        ident = resolve_strain_id(bad, z)
        assert ident.refused is True, f"{bad} must not become a strain identity"
