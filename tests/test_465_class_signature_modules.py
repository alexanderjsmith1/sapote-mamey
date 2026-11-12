"""Signature-enzyme class modules in the class-believability engine.

Each class reaches HIGH only with its gateway and committed enzymes plus a downstream marker. A
gateway alone is LOW, a class label without the gateway is SUSPECT, and the polyene module needs its
type I PKS for HIGH.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey import class_believability as CB  # noqa: E402


def _cds(lt, domains=(), gene_functions=""):
    return {"locus_tag": lt, "sec_met_domains": list(domains), "product": "",
            "gene_functions": gene_functions}


def _tier(name, cds):
    mod = CB.REGISTRY[name]
    return CB.classify(CB.scan_bgc(cds, mod), mod)[0]


FULL = {
    "diketopiperazine_cdps": [["CDPS"], ["p450"]],
    "lassopeptide": [["Asn_synthase"], ["PF13471"], ["Stand_Alone_Lasso_RRE"]],
    "lanthipeptide_class_i": [["Lant_dehydr_N", "Lant_dehydr_C"], ["LANC_like"], ["ABC_tran"]],
    "thioamitide": [["YcaO"], ["TfuA"], ["Methyltransf_11"]],
    "polyene_mycosamine": [["GDP_Man_Dehyd"], ["DegT_DnrJ_EryC1"], ["p450"], ["PKS_KS", "PKS_AT"]],
    "aminocyclitol": [["DHQ_synthase"], ["DegT_DnrJ_EryC1"], ["BtrH_N"]],
    "ectoine": [["Ectoine_synth"], ["Aminotran_3"], ["Acetyltransf_1"]],
    "nis_siderophore": [["IucA_IucC"], ["Lys_Orn_oxgnase"], ["FhuF"]],
    "butyrolactone": [["AfsA"], ["adh_short"], ["TetR_N"]],
    "phenazine": [["PhzC-PhzF"], ["PNP_phzG_C"], ["Chorismate_bind"]],
    "melanin": [["Tyrosinase"], ["MelC1"]],
}
GATEWAY_ONLY = {
    "diketopiperazine_cdps": ["CDPS"], "lassopeptide": ["Asn_synthase"],
    "lanthipeptide_class_i": ["Lant_dehydr_N"], "thioamitide": ["YcaO"],
    "polyene_mycosamine": ["GDP_Man_Dehyd"], "aminocyclitol": ["DHQ_synthase"],
    "ectoine": ["Ectoine_synth"], "nis_siderophore": ["IucA_IucC"], "butyrolactone": ["AfsA"],
    "phenazine": ["PhzC-PhzF"], "melanin": ["Tyrosinase"],
}


def test_every_new_class_is_registered():
    assert set(FULL) | {"phosphonate"} == set(CB.REGISTRY)


@pytest.mark.parametrize("name", sorted(FULL))
def test_full_signature_is_high(name):
    cds = [_cds(f"g{i}", d) for i, d in enumerate(FULL[name])]
    assert _tier(name, cds) == "HIGH"


@pytest.mark.parametrize("name", sorted(GATEWAY_ONLY))
def test_gateway_alone_is_not_high(name):
    tier = _tier(name, [_cds("g1", GATEWAY_ONLY[name])])
    # The CDPS is its own committed step, so a lone CDPS is MEDIUM; every other gateway alone is LOW.
    assert tier == ("MEDIUM" if name == "diketopiperazine_cdps" else "LOW")


def test_polyene_cassette_without_pks_is_low():
    cds = [_cds("g1", ["GDP_Man_Dehyd"]), _cds("g2", ["DegT_DnrJ_EryC1"]), _cds("g3", ["p450"])]
    assert _tier("polyene_mycosamine", cds) == "LOW"


def test_lanb_without_lanc_is_low():
    cds = [_cds("g1", ["Lant_dehydr_N", "Lanthipeptide_LanB_RRE"]), _cds("g2", ["YcaO"]), _cds("g3", ["p450"])]
    assert _tier("lanthipeptide_class_i", cds) == "LOW"


def test_class_label_without_gateway_is_suspect():
    cds = [_cds("g1", ["PqqD"], "biosynthetic (rule-based-clusters) lassopeptide: PqqD")]
    assert _tier("lassopeptide", cds) == "SUSPECT"


def test_class_ii_lanthipeptide_label_does_not_flag_class_i():
    cds = [_cds("g1", ["LANC_like"], "biosynthetic (rule-based-clusters) lanthipeptide-class-ii: LANC_like")]
    m = CB.scan_bgc(cds, CB.REGISTRY["lanthipeptide_class_i"])
    assert m["engine_flag"] is False


def test_phosphonate_module_is_unchanged():
    assert CB.PHOSPHONATE.assembly_required is False
    assert CB.PHOSPHONATE.medium_requires_committed is False
    assert CB.REGISTRY["phosphonate"] is CB.PHOSPHONATE


def test_excluded_contig_is_left_out_of_both_passes(tmp_path):
    import json
    pkg = tmp_path / "S-1" / "package"
    pkg.mkdir(parents=True)
    rec = {"bgc_id": "BGC001", "cds": [
        {"locus_tag": "a", "contig": "c_keep", "sec_met_domains": ["Ectoine_synth"], "product": "", "gene_functions": ""},
        {"locus_tag": "b", "contig": "c_drop", "sec_met_domains": ["Aminotran_3"], "product": "", "gene_functions": ""},
        {"locus_tag": "c", "contig": "c_drop", "sec_met_domains": ["Acetyltransf_1"], "product": "", "gene_functions": ""}]}
    (pkg / "S-1_gene_context.jsonl").write_text(json.dumps(rec) + "\n")
    mod = CB.REGISTRY["ectoine"]
    assert CB.scan_package(pkg, mod)["local"][0]["believability"] == "HIGH"
    res = CB.scan_package(pkg, mod, frozenset({("S-1", "c_drop")}))
    assert res["local"][0]["believability"] == "LOW" and res["pooled"]["believability"] == "LOW"


def test_exclusion_list_needs_strain_and_contig_columns(tmp_path):
    bad = tmp_path / "x.tsv"
    bad.write_text("genome\tnode\nS-1\tc1\n")
    with pytest.raises(ValueError):
        CB.read_excluded_contigs(bad)


@pytest.mark.parametrize("name,cds", [
    ("thioamitide", [["YcaO"], ["Radical_SAM"], ["Methyltransf_11"]]),
    ("polyene_mycosamine", [["GDP_Man_Dehyd"], ["Glycos_transf_1"], ["p450"]]),
    ("aminocyclitol", [["DHQ_synthase"], ["Aminotran_1_2"], ["Glycos_transf_2"]]),
])
def test_generic_tailoring_without_committed_enzyme_stays_low(name, cds):
    assert _tier(name, [_cds(f"g{i}", d) for i, d in enumerate(cds)]) == "LOW"



def test_type_ii_pks_is_not_registered():
    # The KS domain names in gene context cannot separate type II PKS from type I PKS and FabF.
    assert "t2pks" not in CB.REGISTRY


def test_aminocyclitol_module_does_not_claim_aminoglycoside():
    assert "aminoglycoside" not in CB.REGISTRY
    assert "AHBA" in CB.REGISTRY["aminocyclitol"].fp_superfamily
