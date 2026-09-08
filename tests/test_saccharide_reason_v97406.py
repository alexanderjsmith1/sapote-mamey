"""E6: saccharide downgrade reason distinguishes class labels from tailoring context."""
from mamey.models import BGCRecord
from mamey.scoring import standing_rule_for, standing_rule_reason, triage_bgcs


def test_saccharide_reason_names_the_own_product_class_and_three_context_families():
    flag = standing_rule_for("saccharide", "saccharide Glycos_transf_1 Epimerase_2 RmlD_sub_bind")
    reason = standing_rule_reason(flag)
    assert flag == "saccharide-exclusion"
    assert "OWN_PRODUCT_CLASS_SACCHARIDE" in reason
    assert "glycosyltransferase=transfer/decorating capacity only" in reason
    assert "epimerase=deoxysugar-pathway context only" in reason
    assert "deoxysugar_reductase=deoxysugar-pathway context only" in reason


def test_tailoring_terms_alone_do_not_trigger_the_saccharide_rule():
    full = "NRPS glycosyltransferase Epimerase_2 RmlD_sub_bind"
    assert standing_rule_for("NRPS", full) == ""


def test_saccharide_triage_rationale_surfaces_reason_without_identity_claim():
    bgc = BGCRecord("BGC001", "synthetic_node", 1, 1, 30000, 50000,
                    products=["saccharide"], edge_status="Interior")
    result = triage_bgcs([bgc])[0]
    assert result.standing_rule_flag == "saccharide-exclusion"
    assert "reason=OWN_PRODUCT_CLASS_SACCHARIDE" in result.rationale
    assert "capacity only" in result.rationale
