"""v9.7.376 Tier-0 follow-up: one canonical is_lead_excluded() for all excluded-BGC-leak surfaces."""
from mamey.scoring import is_lead_excluded


def test_all_three_signals_trigger_exclusion():
    assert is_lead_excluded({"standing_rule_flag": True})
    assert is_lead_excluded({"primary_metabolism_flag": True})
    assert is_lead_excluded({"mobile_element_flag": True})


def test_render_brief_schema_variants_also_trigger():
    assert is_lead_excluded({"standing_rule": "SACCHARIDE->Inventory"})
    assert is_lead_excluded({"primary_metab_flag": "PIGMENT"})
    assert is_lead_excluded({"mobile_element": "ICE"}), "mobile-element must exclude on any schema"


def test_clean_bgc_is_not_excluded():
    assert not is_lead_excluded({"standing_rule": "", "primary_metab_flag": "NONE",
                                 "mobile_element_flag": "FALSE", "products": "T1PKS"})
    assert not is_lead_excluded({})


def test_falsey_sentinels_do_not_exclude():
    for s in ("", "NONE", "FALSE", "0", "none", "false"):
        assert not is_lead_excluded({"standing_rule_flag": s})
