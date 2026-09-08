"""test_two_pathway.py — gene-only multi-pathway detection (v9.7.127).

Validated across six strains (six reference strains): flag rates 0–3 per strain,
every flag a RiPP/terpene pairing (mechanistically distinct from NR machinery), zero PKS-NRPS
hybrid false positives. These tests lock the key behaviours that validation established.
"""
from mamey.two_pathway import (
    detect_two_pathway, two_pathway_flag_cell, _is_disconnect_pair, _classify, _split_domains,
)


def _gene(lt, start, end, doms):
    return {"locus_tag": lt, "cds_start": start, "cds_end": end, "sec_met_domains": doms}


def test_classify_core_domains():
    assert _classify(["PKS_KS", "PKS_AT"]) == "PKS"
    assert _classify(["Condensation", "AMP-binding"]) == "NRPS"
    assert _classify(["YcaO"]) == "RiPP"
    assert _classify(["Terpene_synth"]) == "terpene"
    assert _classify(["p450"]) is None  # tailoring, not a core engine


def test_split_domains_handles_list_and_string():
    assert _split_domains(["PKS_KS", "PKS_AT"]) == ["PKS_KS", "PKS_AT"]
    assert _split_domains("PKS_KS;PKS_AT") == ["PKS_KS", "PKS_AT"]
    assert _split_domains("['YcaO', 'LANC_like']") == ["YcaO", "LANC_like"]
    assert _split_domains("") == []
    assert _split_domains("—") == []


def test_pks_nrps_hybrid_is_not_two_pathway():
    """PKS<->NRPS is the canonical hybrid — one pathway, must NOT flag."""
    genes = [
        _gene("g1", 1000, 5000, "PKS_KS;PKS_AT"),
        _gene("g2", 8000, 8500, ""),       # support gene in the gap
        _gene("g3", 20000, 25000, "Condensation;AMP-binding"),
    ]
    assert detect_two_pathway(genes)["two_pathway"] is False
    assert _is_disconnect_pair("PKS", "NRPS") is False


def test_nrps_ripp_is_two_pathway():
    """RiPP (ribosomal) next to NRPS (non-ribosomal) across a gap is a genuine two-pathway signal."""
    genes = [
        _gene("g1", 1000, 5000, "Condensation;AMP-binding"),
        _gene("g2", 8000, 8500, ""),
        _gene("g3", 20000, 25000, "YcaO;LANC_like"),
    ]
    v = detect_two_pathway(genes)
    assert v["two_pathway"] is True
    assert "NRPS" in v["classes"] and "RiPP" in v["classes"]
    assert _is_disconnect_pair("NRPS", "RiPP") is True


def test_terpene_nrps_is_two_pathway():
    genes = [
        _gene("g1", 1000, 5000, "Terpene_synth"),
        _gene("g2", 9000, 9500, ""),
        _gene("g3", 25000, 30000, "Condensation;AMP-binding"),
    ]
    assert detect_two_pathway(genes)["two_pathway"] is True


def test_single_engine_is_not_two_pathway():
    assert detect_two_pathway([_gene("g1", 1000, 5000, "PKS_KS;PKS_AT")])["two_pathway"] is False


def test_gap_below_floor_is_one_pathway():
    """Two different-class engines closer than GAP_MIN are one assembly line, not two pathways."""
    genes = [
        _gene("g1", 1000, 5000, "Condensation;AMP-binding"),
        _gene("g2", 6000, 11000, "YcaO"),   # gap only ~1000bp
    ]
    assert detect_two_pathway(genes)["two_pathway"] is False


def test_gap_above_ceiling_is_not_flagged():
    """Engines separated by more than GAP_MAX are likely separate clusters / aggregation."""
    genes = [
        _gene("g1", 1000, 5000, "Condensation;AMP-binding"),
        _gene("g2", 8000, 8500, ""),
        _gene("g3", 200000, 205000, "YcaO"),   # ~195kb gap
    ]
    assert detect_two_pathway(genes)["two_pathway"] is False


def test_flag_cell_format():
    genes = [
        _gene("g1", 1000, 5000, "Condensation;AMP-binding"),
        _gene("g2", 8000, 8500, ""),
        _gene("g3", 20000, 25000, "YcaO"),
    ]
    v = detect_two_pathway(genes)
    cell = two_pathway_flag_cell(v)
    assert cell.startswith("TWO_PATHWAY:")
    assert two_pathway_flag_cell({"two_pathway": False}) == ""
    assert two_pathway_flag_cell(None) == ""
