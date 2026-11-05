"""Diagnostic domain names must be the names antiSMASH writes.

antiSMASH 8.0.4 region GBKs carry the class I lanthipeptide dehydratase profiles as
``Lant_dehydr_N`` / ``Lant_dehydr_C`` and the type II PKS chain length factor as ``t2clf``.
The lookup is exact, so a misspelled key never annotates a hit.
"""
import zipfile

from mamey.antismash_evidence import DIAGNOSTIC_SEC_MET_DOMAINS, _TIER1_DOMAIN_NAMES, extract_gbk_pfam_hits

# Qualifier text copied from an antiSMASH 8.0.4 public-genome region GBK (wrapped as written).
GBK = """LOCUS       CTG1                    90 bp    DNA     linear   UNK 01-JAN-1980
FEATURES             Location/Qualifiers
     CDS             1..30
                     /locus_tag="T_0001"
                     /sec_met_domain="Lant_dehydr_N (E-value: 4.1e-70, bitscore:
                     235.7, seeds: 73, tool: rule-based-clusters)"
                     /sec_met_domain="Lant_dehydr_C (E-value: 2.0e-40, bitscore:
                     140.1, seeds: 73, tool: rule-based-clusters)"
     CDS             31..60
                     /locus_tag="T_0002"
                     /sec_met_domain="t2clf (E-value: 1.5e-203, bitscore: 675.1,
                     seeds: 26, tool: rule-based-clusters)"
ORIGIN
        1 atgaaaaaaa aaaaaaaaaa aaaaaaaaaa atgaaaaaaa aaaaaaaaaa aaaaaaaaaa
       61 atgaaaaaaa aaaaaaaaaa aaaaaaaaaa
//
"""


def test_antismash_names_are_keys():
    for name in ("Lant_dehydr_N", "Lant_dehydr_C", "t2clf"):
        assert name in DIAGNOSTIC_SEC_MET_DOMAINS
    assert {"Lant_dehydr_N", "Lant_dehydr_C"} <= _TIER1_DOMAIN_NAMES
    assert not {"lant_dehyd_N", "lant_dehyd_C"} & set(DIAGNOSTIC_SEC_MET_DOMAINS)


def test_real_qualifiers_are_annotated(tmp_path):
    z = tmp_path / "as.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("CTG1.region001.gbk", GBK)
    rows = [r for v in extract_gbk_pfam_hits(str(z)).values() for r in v]
    by = {r["domain_name"]: r for r in rows}
    assert by["Lant_dehydr_N"]["pfam_acc"] == "PF04738" and by["Lant_dehydr_N"]["tier1_diagnostic"]
    assert by["Lant_dehydr_C"]["pfam_acc"] == "PF14028" and by["Lant_dehydr_C"]["tier1_diagnostic"]
    assert by["t2clf"]["description"] and "chain length factor" in by["t2clf"]["description"]
