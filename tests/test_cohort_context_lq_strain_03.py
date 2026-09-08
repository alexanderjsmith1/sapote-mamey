"""LQ-STRAIN-03 (v9.7.330): cohort-aware strain Mode B S5.

Tests the aggregation (private vs shared, KNOWN/NOVEL, neighbours), the S5 rendering, the cross-card
GCF index, and graceful degradation with no cohort source — using a synthetic cohort context so the
1.2 GB BiG-SCAPE DB is not needed.
"""
import os
import sys
import types
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mamey.cohort_context as cc  # noqa: E402
from mamey.bigscape_namespace import build_family_identity  # noqa: E402


def _membership(family):
    identity = build_family_identity(1, "0.5", family)
    return {"family_id": identity.family_id, "run_id": identity.run_id,
            "normalized_cutoff": identity.normalized_cutoff,
            "qualified_family_id": identity.qualified_family_id,
            "gcf_namespace": identity.gcf_namespace}


def test_no_source_returns_none(tmp_path):
    assert cc.strain_cohort_summary(tmp_path, "AS-40") is None


def test_render_s5_single_strain_fallback():
    lines = cc.render_s5(None, "AS-40")
    assert lines and "No cohort context" in lines[0]


def test_is_private():
    assert cc._is_private({"n_strains": 1}) is True
    assert cc._is_private({"n_strains": 3}) is False
    assert cc._is_private({"cross_strain_members": []}) is True
    assert cc._is_private({"cross_strain_members": ["AS-190"]}) is False


def test_cross_card_gcf_index_links_bgcs_across_strains():
    idx = cc.cross_card_gcf_index({
        "AS-40": {"per_bgc": {"058": _membership(127), "038": {"family_id": None}}},
        "AS-190": {"per_bgc": {"031": _membership(127)}},
        "SID1046": {"per_bgc": {"012": _membership(999)}},
    })
    key = "bigscape-gcf:v1/run/1/cutoff/0.5/family/127"
    assert idx[key] == [("AS-190", "031"), ("AS-40", "058")]
    assert "bigscape-gcf:v1/run/1/cutoff/0.5/family/999" not in idx
    assert "None" not in idx  # missing family_id is dropped


def test_summary_aggregation_with_synthetic_ctx(tmp_path, monkeypatch):
    # Fake the tools bridge: gcf_context returns a synthetic cohort keyed by strain:locator.
    fake_ctx = {
        "AS-40:NODE_43.region001": {**_membership(1), "status": "KNOWN", "n_strains": 3,
                                    "cross_strain_members": ["AS-190", "SID1046"],
                                    "nearest_mibig": ("BGC0000034", "candicidin", 0.2)},
        "AS-40:NODE_1.region001": {**_membership(2), "status": "NOVEL", "n_strains": 1,
                                   "cross_strain_members": []},
        "AS-40:NODE_9.region001": {**_membership(3), "status": "NOVEL", "n_strains": 2,
                                   "cross_strain_members": ["AS-190"], "nearest_mibig": None},
        "AS-999:NODE_5.region001": {**_membership(4), "status": "KNOWN", "n_strains": 2,
                                    "cross_strain_members": ["AS-40"]},  # other strain, must be excluded
    }
    fake = types.SimpleNamespace(
        load_mibig_names=lambda idx: {},
        gcf_context=lambda db, cutoff, names, run_id=None: fake_ctx,
        tsv_context=lambda tsv, strain, cutoff: fake_ctx,
        load_triage=lambda p: {},
    )
    monkeypatch.setattr(cc, "_tools_mod", lambda: fake)

    summ = cc.strain_cohort_summary(tmp_path, "AS-40", cohort_db="/dev/null", run_id="1")
    assert summ["n_with_gcf"] == 3            # only AS-40:* entries
    assert summ["n_private"] == 1             # NODE_1 (n_strains=1)
    assert summ["n_shared"] == 2
    assert summ["n_known"] == 1 and summ["n_novel"] == 2
    assert summ["neighbours"]["AS-190"] == 2  # shares two GCFs
    assert summ["co_members_available"] is True

    lines = cc.render_s5(summ, "AS-40")
    body = "\n".join(lines)
    assert "2 private" not in body and "1 private" in body
    assert "AS-190 (2)" in body
    assert "candicidin" in body  # nearest-MIBiG name surfaced in the shared table
