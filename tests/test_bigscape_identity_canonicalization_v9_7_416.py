"""Portable regression coverage for .416 command and identity contracts."""
import importlib
import os
import sys

_TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_ROOT, _TOOLS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

ingest = importlib.import_module("bigscape_ingest_to_mamey")
cross = importlib.import_module("bigscape_cross_strain")


def test_ingest_parse_locator_does_not_oversplit_underscore_reference():
    # underscore-joined organism name + a GCF accession: naive split("_")[0] -> "Streptomyces"
    path = "/runs/x/gbk_input/Streptomyces_coelicolor_A3_GCF_000203835.1.region001.gbk"
    strain, loc, is_mibig = ingest.parse_locator(path)
    assert is_mibig is False
    assert strain == "Streptomyces_coelicolor_A3", strain
    # the locator must be measured from the CORRECT prefix, so the accession contig survives intact
    assert loc == "GCF_000203835.1.region001", loc


def test_ingest_parse_locator_stable_on_as_and_space_names():
    # regression guard: AS ids and space-named references are unchanged by the fix
    s1, l1, m1 = ingest.parse_locator(
        "/x/REF-001_NODE_25_length_90404_cov_51.797192.region001.gbk")
    assert (s1, m1) == ("REF-001", False)
    assert l1 == "NODE_25_length_90404.region001"  # cov-independent canon
    s2, _, m2 = ingest.parse_locator(
        "/x/Micromonospora sp. WMMA1998_CP114911.1.region015.gbk")
    assert (s2, m2) == ("Micromonospora sp. WMMA1998", False)
    s3, i3, m3 = ingest.parse_locator("/x/BGC0001234.gbk")
    assert (s3, i3, m3) == ("MIBiG", "BGC0001234", True)


def test_cross_strain_mibig_in_path_does_not_swallow_a_cohort_bgc():
    # a real REF-001 BGC staged under a dir whose name contains "mibig"
    path = "/runs/curated_clean_mibig_anchored/gbk_input/" \
           "REF-001_NODE_25_length_90404_cov_51.797192.region001.gbk"
    strain, locator, is_mibig = cross.parse(path)
    assert is_mibig is False, "cohort BGC under a mibig-named dir must NOT be treated as MIBiG"
    assert strain == "REF-001", strain


def test_cross_strain_still_recognizes_a_real_mibig_anchor():
    strain, locator, is_mibig = cross.parse("/anything/mibig/BGC0001234.gbk")
    assert is_mibig is True and strain == "MIBiG"
