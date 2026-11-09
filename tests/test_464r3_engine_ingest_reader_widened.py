"""The ingest binding reads location claims as widely as the widget does.

`physical_assertions` read a fixed set of exact-case column names and `key=value` tokens
preceded by `|` or a space. A raw BLASTp row naming another contig as `CONTIG=`, `contig_id`,
`[contig=…]`, `contig:…` or a bare `NODE_9` after a space was read as making no physical claim,
so ingest admitted it at legacy (tag + length) depth. It now holds such rows; location text the
reader cannot interpret holds the row as `QUERY_PHYSICAL_UNPARSED`.
"""
import csv

import pytest

import mamey.cli as cli
from mamey.blastp_physical_binding import PhysicalAuthority, physical_assertions


@pytest.fixture
def package(tmp_path, synthetic_single_contig_full_locus_zip):
    strain = "SYNINGEST"
    cli.run_one_strain(
        strain_id=strain, display_name=strain,
        input_zip=str(synthetic_single_contig_full_locus_zip), outdir=str(tmp_path), mode="full",
        taxonomy="", source="", bioactivity="", master_path=None, json_mode="off",
    )
    pkg = tmp_path / strain / "package"
    gene = next(csv.DictReader(open(next(pkg.glob("*_gene_by_gene_all_bgcs.csv")), newline="")))
    return pkg, strain, gene


def _check(pkg, strain, gene, row):
    authority = PhysicalAuthority(pkg, strain)
    return authority.check(row, gene["bgc_id"], gene["locus_tag"])[1]


def test_new_location_forms_are_now_claims():
    for row in ({"CONTIG": "X"}, {"contig_id": "X"}, {"record_id": "X"},
                {"query_title": "S|BGC001|g1 [contig=X]"}, {"query_title": "S|BGC001|g1 contig:X"},
                {"query_title": "S|BGC001|g1 NODE_9"}, {"region_number": "2"}):
        assert physical_assertions(row), row


def test_ingest_holds_a_conflicting_claim_it_used_to_miss(package):
    pkg, strain, gene = package
    for row in ({"CONTIG": "OTHER_CONTIG.1"}, {"contig_id": "OTHER_CONTIG.1"},
                {"query_title": f"{strain}|{gene['bgc_id']}|{gene['locus_tag']} [contig=OTHER_CONTIG.1]"},
                {"query_title": f"{strain}|{gene['bgc_id']}|{gene['locus_tag']} contig:OTHER_CONTIG.1"}):
        assert _check(pkg, strain, gene, row) == "QUERY_NODE_CONFLICT", row


def test_ingest_holds_unreadable_location_text(package):
    pkg, strain, gene = package
    row = {"query_title": f"{strain}|{gene['bgc_id']}|{gene['locus_tag']} region_unknown_form"}
    assert _check(pkg, strain, gene, row) == "QUERY_PHYSICAL_UNPARSED"


def test_ingest_still_admits_a_matching_claim_and_a_plain_row(package):
    pkg, strain, gene = package
    assert _check(pkg, strain, gene, {"CONTIG": gene["contig"]}) == ""
    assert _check(pkg, strain, gene, {"region_number": str(int(gene["region"][6:]))}) == ""
    assert _check(pkg, strain, gene, {"gene": gene["locus_tag"]}) == ""


def test_ingest_keeps_the_leading_strain_slot_grammar():
    # `X BGCnnn …` / `X|BGCnnn|…`: X is the strain slot at ingest, not a location claim.
    assert physical_assertions({"query_id": "NODE_1 BGC001 gene=ctg1_1 aa=30"}) == []
    assert all(c["role"] != "node" for c in physical_assertions({"query_id": "NODE_9|BGC001|ctg1_1"}))
