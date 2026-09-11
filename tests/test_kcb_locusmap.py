"""Tests for mamey/kcb_locusmap.py — offline KnownClusterBlast comparative locus maps.

FEATURE (sign-off), non-scoring figure. These tests cover:
  * parsing a synthetic knownclusterblast .txt (query genes + per-hit BLAST gene pairs),
  * rendering PNG + SVG + the reproducible data CSV sidecar,
  * graceful degradation when matplotlib is absent.
"""
from __future__ import annotations

import csv

import pytest

from mamey import kcb_locusmap as kl


SYNTHETIC_KCB = """ClusterBlast scores for NODE_9_length_31000_cov_40.0

Table of genes, locations, strands and annotations of query cluster:
ctg9_1\t100\t900\t+\t\t
ctg9_2\t950\t1800\t-\t\t
ctg9_3\t1850\t3200\t+\t\t
ctg9_4\t3250\t4100\t+\t\t


Significant hits:
1. BGC0000001.1\tmyxochelin
2. BGC0000002.1\tcoelichelin


Details:

>>
1. BGC0000001.1
Source: myxochelin
Type: NRPS
Number of proteins with BLAST hits to this cluster: 3
Cumulative BLAST score: 5000.0

Table of genes, locations, strands and annotations of subject cluster:

Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):
ctg9_1\tSUBJ_001\t92\t600\t100.0\t1e-100
ctg9_2\tSUBJ_002\t80\t500\t95.0\t1e-80
ctg9_3\tSUBJ_003\t70\t900\t88.0\t0.0



>>
2. BGC0000002.1
Source: coelichelin
Type: NRPS
Number of proteins with BLAST hits to this cluster: 2
Cumulative BLAST score: 2000.0

Table of genes, locations, strands and annotations of subject cluster:

Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):
ctg9_2\tCOE_02\t55\t300\t70.0\t1e-40
ctg9_3\tCOE_03\t48\t700\t102.5\t0.0



"""


def test_parse_query_genes():
    region = kl.parse_kcb_txt(SYNTHETIC_KCB)
    assert region.contig == "NODE_9_length_31000_cov_40.0"
    assert len(region.query_genes) == 4
    g2 = {g.gene_id: g for g in region.query_genes}["ctg9_2"]
    assert (g2.start, g2.end, g2.strand) == (950, 1800, "-")
    g1 = {g.gene_id: g for g in region.query_genes}["ctg9_1"]
    assert g1.strand == "+"


def test_parse_blast_pairs():
    region = kl.parse_kcb_txt(SYNTHETIC_KCB)
    assert len(region.hits) == 2
    top = region.hits[0]
    assert top.bgc_id == "BGC0000001.1"
    assert top.compound == "myxochelin"
    assert len(top.pairs) == 3
    p = {x.query_gene: x for x in top.pairs}
    assert p["ctg9_1"].subject_gene == "SUBJ_001"
    assert p["ctg9_1"].pct_identity == 92.0
    assert p["ctg9_3"].pct_identity == 70.0
    # median identity of 92/80/70 -> 80
    assert top.median_identity == 80.0


def test_coverage_capped_at_100():
    region = kl.parse_kcb_txt(SYNTHETIC_KCB)
    # ctg9_3 vs coelichelin reports 102.5% raw coverage -> capped to 100
    coe = region.hits[1]
    p = {x.query_gene: x for x in coe.pairs}
    assert p["ctg9_3"].pct_coverage == 100.0


@pytest.mark.skipif(not kl._HAVE_MPL, reason="matplotlib not installed")
def test_render_outputs(tmp_path):
    metrics = kl.render_from_text(
        SYNTHETIC_KCB, tmp_path, stem="NODE_9", top_n=6,
        strain_id="AS-TEST", bgc_id="BGC001", products="NRPS")
    png = tmp_path / "NODE_9_kcb_locusmap.png"
    svg = tmp_path / "NODE_9_kcb_locusmap.svg"
    data = tmp_path / "NODE_9_kcb_locusmap_data.csv"
    assert png.exists() and png.stat().st_size > 0
    assert svg.exists() and svg.stat().st_size > 0
    assert data.exists()
    assert metrics["reference_clusters"] == 2
    assert metrics["gene_pairs"] == 5
    assert metrics["top_anchor"] == "BGC0000001.1"

    with data.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 5
    assert {"query_gene", "ref_bgc", "subject_gene", "pct_identity", "pct_coverage"} <= set(rows[0])
    first = rows[0]
    assert first["query_gene"] == "ctg9_1"
    assert first["ref_bgc"] == "BGC0000001.1"


def test_whitespace_delimited_fallback():
    # some antiSMASH cuts use spaces, not tabs
    text = SYNTHETIC_KCB.replace("\t", "  ")
    region = kl.parse_kcb_txt(text)
    assert len(region.query_genes) == 4
    assert region.hits and len(region.hits[0].pairs) == 3
