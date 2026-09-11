"""Tests for mamey.report_mode (W7/W24 — terse default, full on demand)."""
from mamey import report_mode as RM


REC = {"bgc_id": "BGC003", "contig": "NODE_3", "user_label": "BGC003 / NODE_3",
       "architecture_capacity": "NRPS", "products": ["NRPS"], "edge_status": "Interior",
       "architecture_confidence": "B", "antismash_region": "region003", "kcb_top": None}
VER = {"bgc_id": "BGC003", "lead_tier": "Medium", "claim_confidence": "Moderate",
       "kcb_similarity_band": "moderate", "standing_rule_flag": "", "primary_metabolism_flag": False,
       "misanchor_flag": ""}


def test_default_is_terse():
    assert RM.DEFAULT_MODE == "terse"


def test_terse_is_one_line_with_contig_and_band():
    line = RM.render_terse(REC, VER)
    assert "\n" not in line
    assert "NODE_3" in line                      # never a bare BGC id
    assert "similarity, not identity" in line    # W26 disclaimer travels
    assert "moderate" in line and "%" not in line  # band, not a number


def test_full_scaffold_has_all_eight_sections():
    md = RM.render_full_scaffold(REC, VER)
    for sec in RM.MODE_B_SECTIONS:
        assert sec in md


def test_board_terse_by_default_full_on_demand():
    recs = [REC, {**REC, "bgc_id": "BGC004", "user_label": "BGC004 / NODE_4"}]
    vers = [VER, {**VER, "bgc_id": "BGC004"}]
    terse = RM.render_board(recs, vers)              # default
    assert "legacy compact Mode B scaffold (not Full §1–§20)" not in terse
    expanded = RM.render_board(recs, vers, full_ids={"BGC004"})
    assert "BGC004 / NODE_4 — legacy compact Mode B scaffold (not Full §1–§20)" in expanded
    assert expanded.count("legacy compact Mode B scaffold (not Full §1–§20)") == 1        # only the requested one expanded


def test_downgrade_flag_shows_in_terse():
    v = {**VER, "standing_rule_flag": "saccharide-exclusion"}
    assert "DOWNGRADE:saccharide-exclusion" in RM.render_terse(REC, v)
