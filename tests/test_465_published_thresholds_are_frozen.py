"""Published scoring thresholds keep their values.

Each constant below sets a cutoff that a benchmark or a methods text reports. On the earlier release, moving any
of them by one step changed no test result, so a change would go unnoticed. This test fails if a value moves. A
deliberate change must update this table, the changelog and every text that quotes the old value, together.
"""
from __future__ import annotations

import importlib

import pytest

FROZEN = [
    ("rggmci", "RGGMCI_SCORE_HIGH", 14),
    ("rggmci", "RGGMCI_SCORE_MODERATE", 9),
    ("rggmci", "OVERLAP_FRACTION_MIN", 0.20),
    ("rggmci", "RGGMCI_MAX_COCLUSTER_MIBIG_REFS", 6),
    ("rggmci", "ST_MIN_AGG_SUBJECTS_PER_SIDE", 3),
    ("rggmci", "ST_MIN_GEOMETRY_FOR_SPLIT", 1),
    ("rggmci", "ST_MAX_SHARED_FRACTION", 0.15),
    ("rggmci", "TT_TERMINUS_MARGIN_BP", 500),
    ("rggmci", "TT_SMALL_PARTNER_BP", 25000),
    ("rggmci", "DEPTH_RATIO_MIN", 0.67),
    ("precision", "KCB_PCT_HIGH", 70),
    ("precision", "KCB_PCT_MODERATE", 40),
    ("mibig_comparator_coverage", "RECOGNIZABLE_MIN_IDENTITY", 30.0),
    ("class_believability", "WEAK_GATEWAY_BIT", 60.0),
    ("clusterblast_genes", "FRC_CORE_FLOOR", 0.35),
    ("residue_tiling", "RESIDUE_MIN_IDENTITY", 30),
    ("residue_tiling", "RESIDUE_MIN_NEW", 60),
    ("residue_tiling", "RESIDUE_MIN_SIDE", 300),
    ("residue_tiling", "RESIDUE_MAX_OVERLAP", 0.10),
    ("split_evidence_layers", "APART_MIN_IDENTITY", 70.0),
    ("ref_completion", "SPLIT_RIVAL_MARGIN", 10.0),
    ("bgc_decomp", "MIN_ANCHORS_CANDIDATE", 1),
    ("dedup_and_guard", "BACKBONE_MIN_KB", 45.0),
    ("pks_ks_scan", "DEFAULT_THRESHOLD", 0.40),
    ("pks_ks_scan", "NEAR_IDENTICAL", 0.75),
    ("pks_ks_scan", "MIN_KS_AA", 100),
    ("comparator_coverage_scoring", "CORE_MIN_FOR_BONUS", 0.5),
    ("compare", "PRESENT_MIN_IDENTITY", 70.0),
    ("compare", "PRESENT_MIN_COVERAGE", 60.0),
    ("scoring", "RIPP_FRAGMENT_MAX_KB", 8.0),
]


@pytest.mark.parametrize("module,name,value", FROZEN, ids=[f"{m}.{n}" for m, n, _ in FROZEN])
def test_published_threshold_keeps_its_value(module, name, value):
    got = getattr(importlib.import_module(f"mamey.{module}"), name)
    assert type(got) is not bool and type(got) is type(value), (module, name, type(got))
    assert got == value, f"mamey.{module}.{name} is {got!r}, frozen at {value!r}"


def test_rggmci_tiers_keep_their_order():
    from mamey import rggmci as R
    assert R.RGGMCI_SCORE_MODERATE < R.RGGMCI_SCORE_HIGH
