"""v9.7.88 9.7.88-J: E2 comparative-pairs populator produces cross-strain similarity rows."""
from __future__ import annotations
from mamey.comparative_pairs import build_comparative_pairs


def _bank():
    return {
        "strains": {"AS-901": {}, "AS-902": {}},
        "bgcs": [
            {"sid": "AS-901", "bgc_id": "BGC005", "products": "phosphonate;NRPS",
             "kcb_top": "fosfazinomycin", "length_kb": 42.0, "contig": "NODE_13"},
            {"sid": "AS-902", "bgc_id": "BGC041", "products": "phosphonate;NRPS",
             "kcb_top": "fosfazinomycin", "length_kb": 39.0, "contig": "NODE_55"},
            {"sid": "AS-901", "bgc_id": "BGC010", "products": "terpene",
             "kcb_top": "hopene", "length_kb": 20.0, "contig": "NODE_2"},
        ],
    }


def test_cross_strain_pair_emitted_with_shared_class():
    rows = build_comparative_pairs(_bank())
    # the two phosphonate NRPS BGCs in different strains should pair
    assert any(r["bgc_a"] in ("BGC005", "BGC041") and r["bgc_b"] in ("BGC005", "BGC041")
               for r in rows), rows
    # the terpene (no cross-strain match) must NOT pair
    assert not any("BGC010" in (r["bgc_a"], r["bgc_b"]) for r in rows)


def test_same_strain_pairs_excluded():
    rows = build_comparative_pairs(_bank())
    for r in rows:
        assert r["strain_a"] != r["strain_b"], "E2 is cross-strain only"


def test_a_domain_match_populated_with_gene_context():
    bank = _bank()
    # gene context: both phosphonate BGCs share AMP-binding (an adenylation-family domain)
    gc = {
        "AS-901": {"BGC005": [{"sec_met_domains": ["AMP-binding", "Condensation"]}]},
        "AS-902": {"BGC041": [{"sec_met_domains": ["AMP-binding", "PCP"]}]},
    }
    rows = build_comparative_pairs(bank, gene_context_by_strain=gc)
    pair = next(r for r in rows if {r["bgc_a"], r["bgc_b"]} == {"BGC005", "BGC041"})
    assert pair["a_domain_match"] not in ("not_computed", ""), pair
    assert int(pair["a_domain_match"]) >= 1            # AMP-binding shared


def test_reserved_columns_not_computed_without_alignment():
    rows = build_comparative_pairs(_bank())
    assert rows, "expected at least one pair"
    # the alignment-backed columns must read 'not_computed', never blank or 0
    for r in rows:
        assert r["mean_pct_id_core"] == "not_computed"
        assert r["mean_pct_id_all"] == "not_computed"


def test_single_strain_yields_no_pairs():
    bank = {"strains": {"AS-901": {}},
            "bgcs": [{"sid": "AS-901", "bgc_id": "B1", "products": "NRPS", "kcb_top": "x"}]}
    assert build_comparative_pairs(bank) == []
