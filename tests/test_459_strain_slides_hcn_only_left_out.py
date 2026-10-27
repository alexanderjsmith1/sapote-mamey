"""Hydrogen-cyanide-only regions get no region slide, with the same split-link safeguard as ectoine.

The owner ruled that HCN-only regions get the ectoine treatment in strain decks. The test is the
existing one: every antiSMASH product type of the region is an omitted type. A hybrid keeps its
slide, and so does a region with split-link evidence.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import strain_slides as ss  # noqa: E402


def D(products, rgg=()):
    return {"inv": {"B1": {"Products": products, "KCB_top": "BGC0002285.2 | aborycin | 1",
                           "Contig": "NODE_1_length_9_cov_1"}},
            "rgg": list(rgg), "twoproof": {}, "gap": {}, "gap_root": None}


def test_hcn_only_is_left_out():
    assert ss.left_out(D("hydrogen-cyanide"), "B1") == "hydrogen-cyanide only"
    assert ss.left_out(D("ectoine; hydrogen-cyanide"), "B1") == "ectoine and hydrogen-cyanide only"


def test_hcn_hybrid_keeps_its_slide():
    for p in ("hydrogen-cyanide; indole", "hydrogen-cyanide; saccharide", "halogenated; hydrogen-cyanide"):
        assert ss.left_out(D(p), "B1") == "", p


def test_hcn_with_a_high_rggmci_link_keeps_its_slide():
    link = {"bgc_a": "B1", "bgc_b": "B2", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE"}
    assert ss.left_out(D("hydrogen-cyanide", rgg=[link]), "B1") == ""


def test_hcn_with_a_supported_gap_rescue_on_another_contig_keeps_its_slide(monkeypatch):
    st = {"table": [{"partner_verdict": "SUPPORTED", "best_contig": "NODE_7_length_5_cov_2"}]}
    monkeypatch.setattr(ss, "gap_stats", lambda D_, b: ({}, st))
    assert ss.left_out(D("hydrogen-cyanide"), "B1") == ""
