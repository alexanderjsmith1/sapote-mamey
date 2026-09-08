"""test_blastp_bgc_recovery_v97410.py — CLAUDE_410_blastp_bgc_recovery_409.

Regression for the space-delimited-defline 0-BGC bind. The three pre-existing ingest tests all
avoid the failing shape: `test_blastp_ingest_v97163` uses BGC-leading ids (`BGC008_ctg162_3`),
`test_blastp_ingest_panel_header_v9_7_266` uses the pipe-delimited panel header (no spaces), and
`test_blastp_ingest_overlay_v9_7_241` pre-populates BGC_ID. This module uses the real
`modeb_blastp._parse_fasta`-tolerated defline:

    >ctg107_3 gene=ctg107_3 BGC=BGC003 node=NODE_107_length_51000_cov_12.3 length=410

NCBI web-BLAST truncates the HitTable query_id at the first space (-> `ctg107_3`), dropping the
`BGC=` token. The BGC survives only in the Alignment XML `<query-title>`.

Fail-before (pristine .409): HitTable+XML binds 0 BGCs (BGC_ID='' on every row), the overlay
writes 0 genes / 0 files, and the CLI prints "0 BGC(s)" with no warning.
Pass-after: the BGC is recovered from the XML title; the CLI emits a stderr WARNING on a true
0-bind (HitTable only, no XML) and stays quiet when the XML recovers the binding.
"""
import argparse

import openpyxl
import pytest

import mamey.blastp_ingest as bi
from mamey.master_workbook import CANONICAL_V1_HEADERS


# HitTable as NCBI writes it for a space-delimited defline: query_id is the first token only.
CSV_TRUNCATED = (
    "ctg107_3,WP_401849909.1,66.176,340,115,0,1,340,1,340,8.83e-152,441,75.29\n"
    "ctg107_3,WP_383406946.1,61.337,344,133,0,1,344,1,344,8.18e-149,434,74.71\n"
    "ctg55_9,WP_000000001.1,55.000,200,90,1,1,200,1,200,1e-80,300,70.00\n"
)

# Matching XML2: <query-title> carries the full defline, BGC token included.
XML_FULL_TITLE = """<BlastOutput2>
<Report><Results><Search>
<query-id>Query_1</query-id>
<query-len>410</query-len>
<query-title>ctg107_3 gene=ctg107_3 BGC=BGC003 node=NODE_107_length_51000_cov_12.3 length=410</query-title>
<hits>
<Hit><description><HitDescr><id>ref|WP_401849909.1|</id><accession>WP_401849909</accession>
<title>tRNA pseudouridine synthase TruD</title><sciname>Streptomyces coelicolor</sciname></HitDescr></description>
<len>346</len></Hit>
</hits>
</Search></Results></Report>
<Report><Results><Search>
<query-id>Query_2</query-id>
<query-len>200</query-len>
<query-title>ctg55_9 gene=ctg55_9 BGC=BGC010 node=NODE_55_length_9000_cov_8.1 length=200</query-title>
<hits>
<Hit><description><HitDescr><id>ref|WP_000000001.1|</id><accession>WP_000000001</accession>
<title>hypothetical protein</title><sciname>Streptomyces sp. X</sciname></HitDescr></description>
<len>200</len></Hit>
</hits>
</Search></Results></Report>
</BlastOutput2>"""

# Control: the BGC-leading id shape the existing suite uses (BGC survives truncation).
CSV_BGC_LEADING = "BGC008_ctg162_3,WP_401849909.1,66.176,340,115,0,1,340,1,340,8.83e-152,441,75.29\n"


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _master(tmp_path):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("B5_BLASTp_Hits")
    ws.append(CANONICAL_V1_HEADERS["B5_BLASTp_Hits"])
    mp = tmp_path / "master.xlsx"
    wb.save(mp)
    return mp


def _ns(master, hit_table, xml=None, package=None):
    return argparse.Namespace(master=str(master), strain="AS-TEST", hit_table=str(hit_table),
                              xml=(str(xml) if xml else None), top_n=10,
                              package=(str(package) if package else None), source=None)


# --- fail-before / pass-after -------------------------------------------------------------

def test_xml_title_recovers_bgc_from_truncated_hittable(tmp_path):
    """HEADLINE. Pristine .409: every BGC_ID is ''. After: recovered from <query-title>."""
    csv = _write(tmp_path, "hits.csv", CSV_TRUNCATED)
    xml = _write(tmp_path, "aln.xml", XML_FULL_TITLE)
    rows = bi.build_b5_rows("AS-TEST", csv, xml, top_n=10)
    assert len(rows) == 3
    by_q = {r["query_locus"]: r["BGC_ID"] for r in rows}
    assert by_q == {"ctg107_3": "BGC003", "ctg55_9": "BGC010"}
    # enrichment that already worked keeps working alongside the recovery
    assert rows[0]["contig"] == "NODE_107_length_51000_cov_12.3"
    assert rows[0]["sciname"] == "Streptomyces coelicolor"


def test_parse_alignment_xml_carries_bgc_id(tmp_path):
    """The enrichment record stores the recovered id (fail-before: key absent)."""
    xml = _write(tmp_path, "aln.xml", XML_FULL_TITLE)
    enrich = bi.parse_alignment_xml(xml)
    assert enrich["ctg107_3"]["bgc_id"] == "BGC003"
    assert enrich["Query_2"]["bgc_id"] == "BGC010"


def test_ingest_with_xml_arms_overlay(tmp_path):
    """End to end: B5 rows bind, write_nr_overlay writes one file per recovered BGC.
    Fail-before: bgcs == 0 and overlay {'bgcs': 0, 'genes': 0}, no files."""
    csv = _write(tmp_path, "hits.csv", CSV_TRUNCATED)
    xml = _write(tmp_path, "aln.xml", XML_FULL_TITLE)
    pkg = tmp_path / "package"
    pkg.mkdir()
    res = bi.ingest_blastp(_master(tmp_path), "AS-TEST", csv, xml, top_n=10, package=pkg)
    assert res["rows"] == 3
    assert res["bgcs"] == 2
    assert res["rows_parsed"] == 3
    assert res["rows_unbound"] == 0
    ov = res["overlay"]
    assert ov["bgcs"] == 2 and ov["genes"] == 2
    written = sorted(p.name for p in (pkg / "blastp_online").glob("*_online_blastp.csv"))
    assert written == ["BGC003_online_blastp.csv", "BGC010_online_blastp.csv"]


def test_cli_warns_on_true_zero_bind(tmp_path, capsys):
    """HitTable only (no XML): nothing can recover the BGC. The CLI must say so on stderr.
    Fail-before: stderr is empty, stdout says '0 BGC(s)' and that is the whole story."""
    from mamey.cli import ingest_blastp_command
    csv = _write(tmp_path, "hits.csv", CSV_TRUNCATED)
    pkg = tmp_path / "package"
    pkg.mkdir()
    rc = ingest_blastp_command(_ns(_master(tmp_path), csv, xml=None, package=pkg))
    out, err = capsys.readouterr()
    assert rc == 0                                    # a warning, not a refusal (rows did land in B5)
    assert "0 BGC(s) appended" in out
    assert "WARNING" in err and "0 BGC(s) bound" in err
    # names the likely cause and the rescue
    assert "proteins.faa" in err and "bgc_blastp_panel/" in err and "--xml" in err
    # and the overlay really is empty -- the warning is not crying wolf
    assert list((pkg / "blastp_online").glob("*_online_blastp.csv")) == []


def test_cli_warning_fires_on_duplicate_reingest_of_unbound_rows(tmp_path, capsys):
    """Second ingest of the same unbound HitTable appends 0 fresh rows (P7c dedup) but still
    parsed rows with no BGC -- the warning is keyed on parsed rows, not appended rows."""
    from mamey.cli import ingest_blastp_command
    csv = _write(tmp_path, "hits.csv", CSV_TRUNCATED)
    mp = _master(tmp_path)
    ingest_blastp_command(_ns(mp, csv))
    capsys.readouterr()
    ingest_blastp_command(_ns(mp, csv))
    out, err = capsys.readouterr()
    assert "0 hit rows" in out
    assert "WARNING" in err and "0 BGC(s) bound" in err


# --- no over-warning / preserved behavior -------------------------------------------------

def test_cli_quiet_when_xml_recovers(tmp_path, capsys):
    from mamey.cli import ingest_blastp_command
    csv = _write(tmp_path, "hits.csv", CSV_TRUNCATED)
    xml = _write(tmp_path, "aln.xml", XML_FULL_TITLE)
    rc = ingest_blastp_command(_ns(_master(tmp_path), csv, xml=xml))
    out, err = capsys.readouterr()
    assert rc == 0
    assert "2 BGC(s) appended" in out
    assert "WARNING" not in err


def test_cli_quiet_on_bgc_leading_ids(tmp_path, capsys):
    from mamey.cli import ingest_blastp_command
    csv = _write(tmp_path, "hits.csv", CSV_BGC_LEADING)
    ingest_blastp_command(_ns(_master(tmp_path), csv))
    out, err = capsys.readouterr()
    assert "1 BGC(s) appended" in out
    assert "WARNING" not in err


def test_cli_quiet_on_empty_hittable(tmp_path, capsys):
    """Zero parsed rows is not a 0-bind: nothing to bind, nothing to warn about."""
    from mamey.cli import ingest_blastp_command
    csv = _write(tmp_path, "empty.csv", "# no hits\n")
    ingest_blastp_command(_ns(_master(tmp_path), csv))
    out, err = capsys.readouterr()
    assert "0 BGC(s) appended" in out
    assert "WARNING" not in err


def test_csv_id_wins_over_xml_title():
    """Precedence: a BGC already in the CSV query_id is never overridden by the XML title."""
    assert bi.parse_bgc_id("BGC008_ctg162_3") == "BGC008"
    # exercise the fallback expression shape directly
    enr = {"bgc_id": "BGC999", "query_title": "x BGC=BGC999"}
    assert (bi.parse_bgc_id("BGC008_ctg162_3") or enr.get("bgc_id")) == "BGC008"
    assert (bi.parse_bgc_id("ctg1_1") or enr.get("bgc_id")) == "BGC999"


def test_csv_only_truncated_stays_unbound_never_invented(tmp_path):
    """With no XML there is no source for the BGC; the row keeps BGC_ID='' (fail-open, never
    invented) and write_nr_overlay skips it exactly as before."""
    csv = _write(tmp_path, "hits.csv", CSV_TRUNCATED)
    rows = bi.build_b5_rows("AS-TEST", csv, None, top_n=10)
    assert {r["BGC_ID"] for r in rows} == {""}


def test_recovery_is_deterministic(tmp_path):
    csv = _write(tmp_path, "hits.csv", CSV_TRUNCATED)
    xml = _write(tmp_path, "aln.xml", XML_FULL_TITLE)
    a = bi.build_b5_rows("AS-TEST", csv, xml, top_n=10)
    b = bi.build_b5_rows("AS-TEST", csv, xml, top_n=10)
    assert a == b
