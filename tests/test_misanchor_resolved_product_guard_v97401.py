"""Resolved MIBiG products must participate in class-mismatch guarding.

The parser can retain a genome self-hit in ``kcb_top`` while placing the
specific MIBiG product in ``closest_candidate_kcb_product``.  That source-bound
resolved product is part of the KCB similarity anchor; it must not bypass the
same class-compatibility check applied to a product named directly in kcb_top.
"""

from mamey.models import BGCRecord
from mamey.source_scans import scan_misanchor_guards


def _bgc(products, resolved_product):
    node = "NODE_1_length_50000_cov_10"
    return BGCRecord(
        bgc_id="BGC001",
        contig=node,
        node_id=node,
        region_number=1,
        antismash_region="region001",
        user_label=f"TEST-STRAIN / {node} / region001 / BGC001",
        start=100,
        end=9000,
        contig_length=50000,
        products=list(products),
        edge_status="Interior",
        architecture_confidence="A",
        kcb_top="Example organism chromosome",
        closest_mibig_accession="BGC0000236.5",
        closest_candidate_kcb_product=resolved_product,
        closest_product_provenance="MIBIG_REFERENCE_LINE",
    )


def test_resolved_mibig_product_cannot_bypass_class_mismatch_guard():
    bgc = _bgc(["NI-siderophore", "other"], "kinamycin")
    guard = scan_misanchor_guards([], [bgc])["per_bgc"][bgc.bgc_id]

    assert guard["class_mismatch"] is True
    assert "T2PKS" in guard["class_mismatch_reason"]


def test_resolved_mibig_product_keeps_compatible_class_unflagged():
    bgc = _bgc(["T2PKS", "other"], "kinamycin")
    guard = scan_misanchor_guards([], [bgc])["per_bgc"][bgc.bgc_id]

    assert guard["class_mismatch"] is False
    assert guard["class_mismatch_reason"] == ""


def test_unresolved_product_sentinel_does_not_create_a_mismatch():
    bgc = _bgc(["NI-siderophore", "other"], "UNRESOLVED")
    guard = scan_misanchor_guards([], [bgc])["per_bgc"][bgc.bgc_id]

    assert guard["class_mismatch"] is False
