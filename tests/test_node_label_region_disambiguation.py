"""Regression (audit Worst #8 hardening): domain-figure titles must disambiguate
two BGCs on the SAME contig by including the antiSMASH region.

Before: _node_label dropped the region, so NODE_6/region002 (BGC041) and
NODE_6/region003 (BGC042) both rendered as "NODE_6 (BGC0xx)" — a node-scoped
title that reads as one locus. After: the region is included when present.
"""
from mamey.domain_figures import _node_label


def test_same_node_two_bgcs_get_distinct_labels():
    a = _node_label("NODE_6_length_340027_cov_84.228413 region002", "BGC041")
    b = _node_label("NODE_6_length_340027_cov_84.228413 region003", "BGC042")
    assert a != b
    assert "region002" in a and "region003" in b
    assert "BGC041" in a and "BGC042" in b


def test_region_included_when_present():
    lbl = _node_label("NODE_6_length_340027_cov_84.228413 region002", "BGC041")
    assert lbl == "NODE_6 region002 (BGC041)"


def test_graceful_fallback_without_region():
    assert _node_label("NODE_70_length_42747", "BGC050") == "NODE_70 (BGC050)"


def test_bgc_id_always_present():
    assert "BGC099" in _node_label("", "BGC099")
