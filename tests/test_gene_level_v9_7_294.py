"""test_gene_level_v9_7_294.py -- tests for the gene-level toolset, incl. the floor enforcement."""
import os, tempfile, importlib.util

HERE = os.path.dirname(__file__)
def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, "..", "tools", name + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

GAL = load("gene_assembly_line")
NS = load("nrps_substrate")
PKS = load("pks_product_class")
MB = load("gene_modeb_enrichment")

# minimal synthetic GBK: one gene ctg1_5 with 2 Condensation (subtyped), 2 AMP-binding, 2 PCP
SYNTH = '''LOCUS       NODE_1_length_40000    40000 bp
FEATURES             Location/Qualifiers
     aSDomain        1..100
                     /aSDomain="Condensation"
                     /domain_id="nrpspksdomains_ctg1_5_Condensation_LCL.1"
     aSDomain        200..300
                     /aSDomain="AMP-binding"
                     /domain_id="nrpspksdomains_ctg1_5_AMP-binding.1"
                     /specificity="substrate consensus: Hpg"
     aSDomain        400..500
                     /aSDomain="PCP"
                     /domain_id="nrpspksdomains_ctg1_5_PCP.1"
     aSDomain        600..700
                     /aSDomain="Condensation"
                     /domain_id="nrpspksdomains_ctg1_5_Condensation_DCL.2"
     aSDomain        800..900
                     /aSDomain="AMP-binding"
                     /domain_id="nrpspksdomains_ctg1_5_AMP-binding.2"
                     /specificity="substrate consensus: Dhpg"
     aSDomain        1000..1100
                     /aSDomain="PCP"
                     /domain_id="nrpspksdomains_ctg1_5_PCP.2"
     PFAM_domain     1..100
                     /aSDomain="Condensation"
                     /domain_id="clusterhmmer_ctg1_5_0001"
ORIGIN
//
'''


def _write(txt, name="NODE_1_length_40000_cov_1.region001.gbk"):
    d = tempfile.mkdtemp(); p = os.path.join(d, name)
    open(p, "w").write(txt); return p


def test_pfam_duplicate_not_counted():
    p = _write(SYNTH)
    genes = GAL.parse_genes(p)
    # 2 real Condensation (LCL+DCL), NOT the PFAM_domain duplicate
    C = GAL.gene_modules(genes["ctg1_5"])[0]
    assert C == 2, f"expected 2 condensation (subtypes summed, PFAM excluded), got {C}"
    print("PASS test_pfam_duplicate_not_counted")


def test_completeness_and_kind():
    p = _write(SYNTH)
    rows = GAL.catalog_region(p)
    assert len(rows) == 1 and rows[0]["kind"] == "NRPS" and rows[0]["complete"], rows
    print("PASS test_completeness_and_kind")


def test_15kb_floor():
    # >=15kb + complete -> very likely; <15kb -> fragment
    assert MB.confidence_tier("NODE_1_length_40000.region001", True) == "very likely"
    assert MB.confidence_tier("NODE_1_length_9000.region001", True) == "fragment"
    assert MB.confidence_tier("NODE_1_length_40000.region001", False) == "likely"
    print("PASS test_15kb_floor")


def test_modeb_enforces_rules():
    p = _write(SYNTH)
    sec = MB.make_section(p, blastp_pct=75.3, blastp_hit="BGC0001462", blastp_producer="A. coloradensis")
    assert "similarity, not identity" in sec
    assert "capacity" in sec.lower()
    assert "produces" not in sec.lower()
    assert "very likely" in sec  # 40kb + complete
    assert "\u2014" not in sec   # no em-dash
    assert "NAPAA is excluded" in sec
    print("PASS test_modeb_enforces_rules")


def test_pks_product_class():
    order = ["PKS_KS", "PKS_AT", "PKS_KR", "PKS_DH", "PKS_ER", "ACP",
             "PKS_KS", "PKS_AT", "PKS_KR", "PKS_DH", "ACP"]
    states = PKS.module_states(order)
    assert states == ["saturated", "enoyl"], states
    print("PASS test_pks_product_class")


if __name__ == "__main__":
    test_pfam_duplicate_not_counted()
    test_completeness_and_kind()
    test_15kb_floor()
    test_modeb_enforces_rules()
    test_pks_product_class()
