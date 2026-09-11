from mamey.crosswalk import assembly_locator, enrich_bgc_crosswalk
from mamey.models import BGCRecord
from mamey.render_safe import locus_label
from mamey.report_mode import render_terse, render_full_scaffold


def _bgc():
    return BGCRecord(
        bgc_id="BGC013",
        contig="NODE_182_length_22000_cov_12.3",
        region_number=13,
        start=100,
        end=12000,
        contig_length=22000,
        products=["indolocarbazole"],
    )


def test_crosswalk_user_label_is_node_first():
    b = enrich_bgc_crosswalk(_bgc(), "NODE_182_length_22000_cov_12.3.region013.gbk")
    assert b.user_label.startswith("NODE_182_length_22000_cov_12")
    assert "region013" in b.user_label
    assert b.user_label.endswith("(BGC013)")
    assert not b.user_label.startswith("BGC013")


def test_assembly_locator_dict_is_node_first():
    label = assembly_locator({"BGC_ID": "BGC008", "Node_ID": "NODE_162", "antiSMASH_Region": "region008"})
    assert label == "NODE_162 region008 (BGC008)"


def test_render_safe_locus_label_keeps_bgc_as_parenthetical():
    label = locus_label({"bgc_id": "BGC001", "contig": "NODE_105", "region": "region001"}, max_chars=80)
    assert label == "NODE_105 region001 (BGC001)"


def test_report_mode_never_falls_back_to_bare_bgc_first():
    record = {"bgc_id": "BGC026", "contig": "NODE_300", "products": ["lanthipeptide"]}
    verdict = {"lead_tier": "High", "claim_confidence": "MODERATE", "kcb_similarity_band": "low"}
    terse = render_terse(record, verdict)
    full = render_full_scaffold(record, verdict)
    assert terse.startswith("NODE_300 (BGC026)")
    assert "### NODE_300 (BGC026)" in full
