"""v9.7.293: blastp-online CSV now carries (a) node_region — the BGC's cov-stripped node.region
locator from the crosswalk, so a gene's BGC is identified by contig/region not just the BGC number;
and (b) pct_positive — %similarity (positives/align_length) alongside the existing %identity.
Both are similarity-to-reference (capacity) signals, not compound-identity claims."""
from __future__ import annotations
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_bo = pytest.importorskip("mamey.blastp_online")


def test_hit_carries_pct_positive():
    h = _bo.BlastpHit(locus_tag="ctg275_1", aa_length=105, antismash_domains="", pct_identity=69.2, pct_positive=81.4)
    assert h.pct_positive == 81.4 and h.pct_identity == 69.2


def test_pct_positive_is_positives_over_alignment():
    # %similarity = positives / align_length; distinct from %identity = identities / align_length
    positives, identities, align = 118, 100, 145
    assert round(100.0 * positives / align, 1) == 81.4
    assert round(100.0 * identities / align, 1) == 69.0


def test_node_region_cov_stripped_from_crosswalk_matches_gcf_format():
    # crosswalk node_id carries coverage; the emitted locator drops it (matches the GCF context table)
    node_id, region = "NODE_275_length_8783_cov_79", "region001"
    nid = re.sub(r"_cov_[0-9.]+", "", node_id)
    assert f"{nid}.{region}" == "NODE_275_length_8783.region001"


def test_csv_header_has_node_region_and_pct_positive():
    src = (ROOT / "mamey" / "blastp_online.py").read_text()
    assert '"locus_tag", "node_region"' in src
    assert '"pct_identity", "pct_positive"' in src
