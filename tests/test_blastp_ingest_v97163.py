"""test_blastp_ingest_v97163.py — B5_BLASTp_Hits ingest from NCBI web-BLAST output.

Fixtures mirror the real NCBI -outfmt 10 HitTable CSV (13 cols) and BLAST XML2 shape.
"""
import openpyxl
import pytest

import mamey.blastp_ingest as bi
from mamey.master_workbook import CANONICAL_V1_HEADERS


CSV_FIXTURE = (
    "BGC008_ctg162_3,WP_401849909.1,66.176,340,115,0,1,340,1,340,8.83e-152,441,75.29\n"
    "BGC008_ctg162_3,WP_383406946.1,61.337,344,133,0,1,344,1,344,8.18e-149,434,74.71\n"
    "BGC010_ctg5_12,WP_000000001.1,55.000,200,90,1,1,200,1,200,1e-80,300,70.00\n"
)

XML_FIXTURE = """<BlastOutput2>
<Report><Results><Search>
<query-id>Query_1</query-id>
<query-len>363</query-len>
<query-title>BGC008_ctg162_3 contig=NODE_162_length_14250_cov_63.7 node=NODE_162 start=2859</query-title>
<hits>
<Hit><description><HitDescr><id>ref|WP_401849909.1|</id><accession>WP_401849909</accession>
<title>MULTISPECIES: tRNA pseudouridine synthase TruD</title><sciname>unclassified Streptomyces</sciname></HitDescr></description>
<len>346</len></Hit>
</hits>
</Search></Results></Report>
</BlastOutput2>"""


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_parse_bgc_id_and_contig():
    assert bi.parse_bgc_id("BGC008_ctg162_3") == "BGC008"
    assert bi.parse_short_contig("BGC008_ctg162_3") == "ctg162"
    assert bi.parse_bgc_id("no_bgc_here") == ""


def test_build_rows_csv_only(tmp_path):
    csv = _write(tmp_path, "hits.csv", CSV_FIXTURE)
    rows = bi.build_b5_rows("AS-TEST", csv, None, top_n=10)
    assert len(rows) == 3
    r = rows[0]
    assert r["BGC_ID"] == "BGC008"
    assert r["pct_identity"] == "66.176"
    assert r["positives_pct"] == "75.29"     # similarity
    assert r["bitscore"] == "441"
    assert r["hit_rank"] == 1
    assert r["contig"] == "ctg162"           # short form without XML
    assert r["subject_desc"] == ""           # no enrichment without XML


def test_build_rows_xml_enrichment(tmp_path):
    csv = _write(tmp_path, "hits.csv", CSV_FIXTURE)
    xml = _write(tmp_path, "aln.xml", XML_FIXTURE)
    rows = bi.build_b5_rows("AS-TEST", csv, xml, top_n=10)
    b008 = [r for r in rows if r["query_locus"] == "BGC008_ctg162_3"]
    assert b008[0]["contig"] == "NODE_162"                       # full node from XML
    assert "TruD" in b008[0]["subject_desc"]                     # versioned acc matched
    assert b008[0]["sciname"] == "unclassified Streptomyces"
    assert b008[0]["subject_len"] == "346"
    assert b008[0]["query_len"] == "363"


def test_top_n_caps_per_query(tmp_path):
    # 3 hits for one query, cap at 2 -> only 2 rows for it
    many = "".join(f"BGCX_ctg1_1,WP_{i}.1,50,100,10,0,1,100,1,100,1e-5,80,60\n" for i in range(5))
    csv = _write(tmp_path, "many.csv", many)
    rows = bi.build_b5_rows("AS-TEST", csv, None, top_n=2)
    assert len(rows) == 2
    assert [r["hit_rank"] for r in rows] == [1, 2]


def test_ingest_appends_and_pk_unique(tmp_path):
    # build a minimal workbook with just B5 to test append + PK
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("B5_BLASTp_Hits")
    ws.append(CANONICAL_V1_HEADERS["B5_BLASTp_Hits"])
    mp = tmp_path / "m.xlsx"
    wb.save(mp)
    csv = _write(tmp_path, "hits.csv", CSV_FIXTURE)
    res = bi.ingest_blastp(mp, "AS-TEST", csv, None, top_n=10)
    assert res["rows"] == 3
    assert res["bgcs"] == 2                    # BGC008 + BGC010
    wb2 = openpyxl.load_workbook(mp, read_only=True)
    ws2 = wb2["B5_BLASTp_Hits"]
    hdr = [c.value for c in next(ws2.iter_rows(max_row=1))]
    data = list(ws2.iter_rows(min_row=2, values_only=True))
    assert len(data) == 3
    pk_i = [hdr.index(c) for c in ("strain", "BGC_ID", "query_locus", "hit_rank")]
    pks = [tuple(row[i] for i in pk_i) for row in data]
    assert len(pks) == len(set(pks))           # primary key unique


def test_b5_header_defined():
    cols = CANONICAL_V1_HEADERS["B5_BLASTp_Hits"]
    for required in ("strain", "BGC_ID", "contig", "query_locus", "hit_rank",
                     "subject_acc", "pct_identity", "positives_pct", "evalue", "bitscore"):
        assert required in cols
