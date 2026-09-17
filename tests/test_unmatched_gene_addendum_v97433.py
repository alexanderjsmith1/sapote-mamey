from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from mamey import BUNDLE_VERSION
from mamey.unmatched_gene_addendum import (
    ADJUDICATION_FIELDS,
    UnmatchedGeneAddendumHold,
    build_unmatched_gene_addendum,
)

STRAIN = "SYNTH-001"
NODE = "NODE_7_length_120000_cov_42.5"
REGION = "region002"
ALIAS = "BGC007"
IDENTITY = f"{STRAIN} / {NODE} / {REGION} / {ALIAS}"
TOKEN = f"{STRAIN}__{NODE}__{REGION}__{ALIAS}__SapoteMamey_v{BUNDLE_VERSION}"


def _write_csv(path: Path, fields, rows, delimiter=","):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=delimiter, lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def _package(tmp_path: Path) -> Path:
    package = tmp_path / "package"; package.mkdir()
    manifest = {
        "strain_id": STRAIN,
        "bundle_version": "9.7.432",
        "bgcs": [{"bgc_id": ALIAS, "contig": NODE, "region_number": 2,
                  "antismash_region": REGION, "products": ["NRPS"], "edge_status": "Interior"}],
    }
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    gene_fields = ["bgc_id", "rank", "locus_tag", "contig", "cds_start", "cds_end", "strand",
                   "aa_length", "product_qualifier", "gene_function_inference", "sec_met_domains"]
    genes=[]
    for order in range(1, 7):
        genes.append({"bgc_id":ALIAS,"rank":order,"locus_tag":f"syn_gene_{order:03d}","contig":NODE,
                      "cds_start":100*order,"cds_end":100*order+89,"strand":"+" if order%2 else "-",
                      "aa_length":100+order,"product_qualifier":"hypothetical protein",
                      "gene_function_inference":"unknown","sec_met_domains":"AMP-binding" if order==2 else ""})
    _write_csv(package/f"{STRAIN}_gene_by_gene_all_bgcs.csv",gene_fields,genes)
    mibig_fields=["bgc_id","query_gene","subject_gene","mibig_accession","mibig_compound"]
    hits=[]
    for accession in ("BGC0000001","BGC0000002","BGC0000003"):
        hits.append({"bgc_id":ALIAS,"query_gene":"syn_gene_001","subject_gene":"ref","mibig_accession":accession,"mibig_compound":"synthetic"})
    hits.append({"bgc_id":ALIAS,"query_gene":"syn_gene_002","subject_gene":"ref","mibig_accession":"BGC0000001","mibig_compound":"synthetic"})
    for accession in ("BGC0000002","BGC0000003"):
        hits.append({"bgc_id":ALIAS,"query_gene":"syn_gene_005","subject_gene":"ref","mibig_accession":accession,"mibig_compound":"synthetic"})
    _write_csv(package/f"{STRAIN}_3_mibig_per_gene.csv",mibig_fields,hits)
    return package


def _run(package: Path, out: Path, **kwargs):
    return build_unmatched_gene_addendum(package=package,strain=STRAIN,full_node=NODE,region=REGION,
                                         bgc_alias=ALIAS,out=out,max_reference_matches=1,**kwargs)


def test_low_match_selection_groups_neighborhoods_and_keeps_channels_separate(tmp_path):
    package=_package(tmp_path); out=tmp_path/"out"; out.mkdir()
    nr=tmp_path/"nr.tsv"; cnr=tmp_path/"clustered.tsv"
    channel_fields=["exact_identity","gene","subject_def"]
    _write_csv(nr,channel_fields,[{"exact_identity":IDENTITY,"gene":"syn_gene_002","subject_def":"nr enzyme"}],"\t")
    _write_csv(cnr,channel_fields,[{"exact_identity":IDENTITY,"gene":"syn_gene_003","subject_def":"clustered enzyme"}],"\t")
    receipt=_run(package,out,nr=nr,clustered_nr=cnr)
    dest=out/TOKEN
    rows=list(csv.DictReader((dest/f"{TOKEN}__UNMATCHED_GENE_FUNCTIONS.tsv").open(),delimiter="\t"))
    assert [row["locus_tag"] for row in rows] == ["syn_gene_002","syn_gene_003","syn_gene_004","syn_gene_006"]
    assert [row["neighborhood_id"] for row in rows] == ["UGN001","UGN001","UGN001","UGN002"]
    assert rows[0]["nr_subject"] == "nr enzyme"
    assert rows[0]["clustered_nr_subject"] == "NO_ADMITTED_CLUSTERED_NR_ROW"
    assert rows[1]["nr_subject"] == "NO_ADMITTED_NR_ROW"
    assert rows[1]["clustered_nr_subject"] == "clustered enzyme"
    assert receipt["counts"] == {"target_genes":6,"included_low_match_genes":4,"neighborhoods":2,
                                  "adjudicated_genes":0,"nr_bound_genes":1,"clustered_nr_bound_genes":1}
    assert receipt["channel_contract"].startswith("nr and clustered_nr are retained separately")
    assert receipt["status"] == "AUTHOR_JUDGMENT_REQUIRED"
    assert set(p.name for p in dest.iterdir()) == {
        f"{TOKEN}__UNMATCHED_GENE_FUNCTIONS.tsv",
        f"{TOKEN}__UNMATCHED_GENE_NEIGHBORHOODS.tsv",
        f"{TOKEN}__UNMATCHED_GENE_FUNCTIONS_ADDENDUM.md",
        f"{TOKEN}__UNMATCHED_GENE_FUNCTIONS_RECEIPT.json",
        f"{TOKEN}__UNMATCHED_GENE_ADJUDICATION_TEMPLATE.tsv",
    }


def test_complete_adjudication_renders_claim_safe_addendum(tmp_path):
    package=_package(tmp_path); out=tmp_path/"out"; out.mkdir(); adjudication=tmp_path/"judgments.tsv"
    rows=[]
    for gene in ("syn_gene_002","syn_gene_003","syn_gene_004","syn_gene_006"):
        rows.append({"exact_identity":IDENTITY,"locus_tag":gene,"possible_function":"candidate accessory enzyme",
                     "alternative_explanation":"adjacent pathway","pathway_relevance_tier":"MODERATE",
                     "discriminating_test":"product-linked deletion metabolomics"})
    _write_csv(adjudication,ADJUDICATION_FIELDS,rows,"\t")
    receipt=_run(package,out,adjudication=adjudication)
    text=(out/TOKEN/f"{TOKEN}__UNMATCHED_GENE_FUNCTIONS_ADDENDUM.md").read_text()
    assert receipt["status"] == "ADJUDICATED_SCAFFOLD"
    assert receipt["counts"]["adjudicated_genes"] == 4
    assert "candidate accessory enzyme" in text
    assert "adjacent pathway" in text
    assert "do not replace the original report in place" in text


def test_foreign_channel_identity_refuses_before_output(tmp_path):
    package=_package(tmp_path); out=tmp_path/"out"; out.mkdir(); nr=tmp_path/"nr.tsv"
    _write_csv(nr,["exact_identity","gene","subject_def"],[{
        "exact_identity":f"{STRAIN} / NODE_8_length_120000_cov_42.5 / {REGION} / {ALIAS}",
        "gene":"syn_gene_002","subject_def":"foreign"}],"\t")
    with pytest.raises(UnmatchedGeneAddendumHold,match="nr exact identity conflicts"):
        _run(package,out,nr=nr)
    assert list(out.iterdir()) == []


def test_shortened_node_refuses_before_output(tmp_path):
    package=_package(tmp_path); out=tmp_path/"out"; out.mkdir()
    with pytest.raises(UnmatchedGeneAddendumHold,match="shortened NODE token"):
        build_unmatched_gene_addendum(package=package,strain=STRAIN,full_node="NODE_7",region=REGION,
                                      bgc_alias=ALIAS,out=out,max_reference_matches=1)
    assert list(out.iterdir()) == []


def test_reference_subset_must_exist_in_target_evidence(tmp_path):
    package=_package(tmp_path); out=tmp_path/"out"; out.mkdir()
    with pytest.raises(UnmatchedGeneAddendumHold,match="selected accessions absent"):
        _run(package,out,reference_accessions=["BGC9999999"])
    assert list(out.iterdir()) == []
