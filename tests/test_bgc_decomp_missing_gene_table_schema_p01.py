"""SCHEMA-P01 (v9.7.329): run_bgc_decomp must not report a *silent all-PASS* when it never saw a
gene table. Previously a None / missing / wrong gene_table_csv left genes_by_bgc empty, so every
BGC fell to ONE_MODEL_CONSISTENT and the run reported status=PASS with "0 TWO_MODEL_STRONG" — a
clean-looking negative for an analysis that never actually ran (the caller derives gene_table_csv
from a package glob that returns None if the table wasn't written).
"""
import os
import sys
import csv
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey.bgc_decomp import run_bgc_decomp


def _bgc(bid, contig="c1", start=0, end=5000, products=("NRPS",)):
    return types.SimpleNamespace(
        bgc_id=bid, contig=contig, start=start, end=end, products=list(products),
        node_id=contig, source_gbk="", region_number=1, antismash_region="")


def test_none_gene_table_is_incomplete_not_silent_pass():
    bgcs = [_bgc("AS-X.BGC001"), _bgc("AS-X.BGC002")]
    r = run_bgc_decomp(bgcs, None)
    assert r["status"] == "INCOMPLETE"
    assert r["gene_table_status"] == "MISSING"
    assert "NOT MEANINGFUL" in r["summary_line"]
    # every row must name the true cause, not "fewer than 2 anchor genes"
    for row in r["rows"]:
        assert row["null_reason"].startswith("GENE_TABLE_MISSING")


def test_nonexistent_gene_table_is_not_found():
    r = run_bgc_decomp([_bgc("AS-X.BGC001")], "/no/such/path/gene_table.csv")
    assert r["status"] == "INCOMPLETE"
    assert r["gene_table_status"] == "NOT_FOUND"


def test_empty_gene_table_is_flagged_empty(tmp_path):
    p = tmp_path / "AS-X_gene_by_gene_all_bgcs.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["bgc_id", "locus_tag", "cds_start", "cds_end", "sec_met_domains"])
    r = run_bgc_decomp([_bgc("AS-X.BGC001")], str(p))
    assert r["status"] == "INCOMPLETE"
    assert r["gene_table_status"] == "EMPTY"


def test_real_gene_table_still_passes(tmp_path):
    p = tmp_path / "AS-X_gene_by_gene_all_bgcs.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bgc_id", "locus_tag", "cds_start", "cds_end", "sec_met_domains"])
        w.writerow(["AS-X.BGC001", "ctg1_1", "100", "1200", "Condensation"])
        w.writerow(["AS-X.BGC001", "ctg1_2", "1300", "2400", "AMP-binding"])
    r = run_bgc_decomp([_bgc("AS-X.BGC001")], str(p))
    assert r["status"] == "PASS"
    assert r["gene_table_status"] == "OK"
