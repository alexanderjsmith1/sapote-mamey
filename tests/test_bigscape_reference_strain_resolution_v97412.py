"""Regression — v9.7.412: bigscape strain resolution handles REFERENCE genomes, not just AS.

The per-tool prefix regex `^(AS-\\d+|SID\\d+|[A-Za-z0-9-]+?)_` could not cross a space or period,
so every reference region GBK (`Genus species strain_ACCESSION.regionNNN.gbk`) collapsed to '?' —
verified: all 2,785 reference region GBKs in a real curated run mapped to '?', silently corrupting
cross-strain counts and KNOWN/NOVEL calls. `mamey.bigscape_namespace.strain_from_gbk_name` fixes it;
the three consumers (bigscape_known_novel / _cross_strain / _family_domains) now call it.

`pytest tests/test_bigscape_reference_strain_resolution_v97412.py`.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mamey.bigscape_namespace import strain_from_gbk_name  # noqa: E402


def test_reference_with_spaces_is_resolved_not_qmark():
    # the exact failing shape: an organism name with spaces + accession
    assert strain_from_gbk_name(
        "Streptomyces liangshanensis_CP050177.1.region017.gbk") == "Streptomyces liangshanensis"
    assert strain_from_gbk_name(
        "Actinomadura macrotermitis_WEGH01000004.1.region003.gbk") == "Actinomadura macrotermitis"


def test_accession_prefix_and_wgs_forms():
    # NZ_ / GCF_ / long WGS-prefix accessions all strip, organism preserved
    assert strain_from_gbk_name(
        "Salinispora arenicola CNX814_NZ_KB896323.1.region001.gbk") == "Salinispora arenicola CNX814"
    assert strain_from_gbk_name(
        "Streptomyces lasiicapitis_GCF_014646335.1.region002.gbk") == "Streptomyces lasiicapitis"
    assert strain_from_gbk_name(
        "Streptomyces odorifer KAI-180_JAANNT010000003.1.region003.gbk") \
        == "Streptomyces odorifer KAI-180"   # strain designator KAI-180 preserved, not read as accession


def test_as_cohort_unchanged():
    assert strain_from_gbk_name("AS-260_NODE_262_length_16635_cov_7.148267.region001.gbk") == "AS-260"
    assert strain_from_gbk_name("AJS-327_NZ_SKBR01000001.1.region001.gbk") == "AJS-327"
    assert strain_from_gbk_name("SID10815_NODE_1.region001.gbk") == "SID10815"


def test_mibig_maps_to_mibig():
    assert strain_from_gbk_name("BGC0001234.gbk") == "MIBiG"


def test_consumers_import_the_helper():
    # the three tools must actually call the shared resolver (no residual dead STRAIN regex)
    tools = pathlib.Path(__file__).resolve().parents[1] / "tools"
    for name in ("bigscape_known_novel.py", "bigscape_cross_strain.py", "bigscape_family_domains.py"):
        src = (tools / name).read_text()
        assert "strain_from_gbk_name" in src, f"{name} should call strain_from_gbk_name"
        assert "[A-Za-z0-9\\-]+?)_" not in src, f"{name} still has the space-blind STRAIN regex"
