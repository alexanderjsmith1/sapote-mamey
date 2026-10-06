"""Ectoine, NAPAA and geosmin regions get no region slide unless they carry split-link evidence (3 Oct)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import strain_slides as ss  # noqa: E402


def D(products, kcb="", rgg=(), table=None):
    d = {"inv": {"B1": {"Products": products, "KCB_top": kcb, "Contig": "NODE_1_length_9_cov_1"}}, "rgg": list(rgg),
         "twoproof": {}, "gap": {}, "gap_root": None}
    return d


def test_ectoine_and_napaa_only_are_left_out():
    assert ss.left_out(D("ectoine"), "B1") == "ectoine only"
    assert ss.left_out(D("NAPAA"), "B1") == "NAPAA only"


def test_geosmin_is_a_terpene_with_a_geosmin_best_match():
    assert ss.left_out(D("terpene", "x | geosmin (BGC0001181) | 100"), "B1").startswith("terpene")
    assert ss.left_out(D("terpene", "x | hopene (BGC0000663) | 69"), "B1") == ""


def test_hybrids_terpene_and_saccharide_keep_their_slide():
    for p in ("ectoine; saccharide", "NAPAA; NRPS", "saccharide", "betalactone; terpene"):
        assert ss.left_out(D(p, "x | geosmin (BGC0001181) | 100"), "B1") == ""
    assert ss.left_out(D("terpene", "x | 2-methylisoborneol (BGC0000658) | 100"), "B1") == ""


def test_a_high_rggmci_link_keeps_the_slide():
    link = {"bgc_a": "B1", "bgc_b": "B2", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE"}
    assert ss.left_out(D("NAPAA", rgg=[link]), "B1") == ""
