"""The domain table retains antiSMASH's /description for each domain feature.

antiSMASH writes a human-readable description on PFAM_domain and on TIGRFAM aSDomain features
(e.g. TIGR03962 -> "mycofact_rSAM: mycofactocin radical SAM maturase"). parsers.py already keeps
the full qualifier dict on DomainFeature.qualifiers; the package writer discarded it, so every
author saw a bare accession. Regression guard for that.
"""
import csv
from mamey.gene_context import write_gene_context
from mamey.models import DomainFeature


class _BGC:
    def __init__(self):
        self.bgc_id = "BGC001"; self.node_id = "NODE_1_length_30212_cov_25"
        self.contig = self.node_id; self.antismash_region = "region001"
        self.region_number = 1; self.start = 11319; self.end = 30212


class _CDS:
    def __init__(self):
        self.locus_tag = "ctg1_19"; self.contig = "NODE_1_length_30212_cov_25"
        self.start = 21320; self.end = 22561; self.strand = -1
        self.translation = "M" * 413; self.product = ""; self.qualifiers = {}


def _domains():
    return [
        DomainFeature("NODE_1_length_30212_cov_25", 21320, 22561, -1, "aSDomain",
                      "ctg1_19", "TIGR03962", "antismash", 657.5, "9.4e-199", "",
                      {"description": ["mycofact_rSAM: mycofactocin radical SAM maturase"]}),
        DomainFeature("NODE_1_length_30212_cov_25", 21400, 22000, -1, "PFAM_domain",
                      "ctg1_19", "Radical_SAM", "35.0", 87.0, "2.8e-27", "",
                      {"description": ["Radical SAM superfamily"], "db_xref": ["PF04055.24"]}),
        DomainFeature("NODE_1_length_30212_cov_25", 21500, 21900, -1, "CDS_motif",
                      "ctg1_19", "no_desc_motif", "", None, "", "", {}),
    ]


def _rows(tmp_path):
    write_gene_context(tmp_path, "TEST-78", [_BGC()], [_CDS()], _domains())
    with open(tmp_path / "TEST-78_domains.csv", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_description_column_exists_and_is_populated(tmp_path):
    rows = _rows(tmp_path)
    assert rows, "no domain rows written"
    assert "description" in rows[0], "domains.csv lost the description column"
    by = {r["domain"]: r["description"] for r in rows}
    assert by["TIGR03962"] == "mycofact_rSAM: mycofactocin radical SAM maturase"
    assert by["Radical_SAM"] == "Radical SAM superfamily"


def test_missing_description_is_empty_not_absent(tmp_path):
    by = {r["domain"]: r["description"] for r in _rows(tmp_path)}
    assert by["no_desc_motif"] == ""


def test_existing_columns_are_preserved(tmp_path):
    rows = _rows(tmp_path)
    older_columns = ("strain", "assembly_locator", "contig", "region", "bgc_id", "locus_tag",
                     "feature_type", "domain", "pfam_acc", "database", "start", "end",
                     "strand", "bitscore", "evalue", "substrate")
    assert list(rows[0]) == [*older_columns, "description"]
    r = {x["domain"]: x for x in rows}["Radical_SAM"]
    assert r["pfam_acc"] == "PF04055.24" and r["evalue"] == "2.8e-27"
