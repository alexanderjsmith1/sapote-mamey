"""Reject ambiguous BLAST XML2 query keys before ingest mutates governed outputs."""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import openpyxl
import pytest

from mamey import blastp_ingest as bi


ROOT = Path(__file__).resolve().parents[1]


def _search(qid: str, title: str, *, qlen: str = "100", accession: str = "WP_TEST") -> str:
    return f"""<Search>
<query-id>{qid}</query-id><query-title>{title}</query-title><query-len>{qlen}</query-len>
<hits><Hit><description><HitDescr><id>ref|{accession}.1|</id>
<accession>{accession}</accession><title>{title} subject</title>
<sciname>Streptomyces testensis</sciname></HitDescr></description><len>90</len></Hit></hits>
</Search>"""


def _write_xml(tmp_path: Path, *searches: str) -> Path:
    path = tmp_path / "alignment.xml"
    path.write_text("<BlastOutput2>" + "".join(searches) + "</BlastOutput2>", encoding="utf-8")
    return path


def _ordered(pair: tuple[str, str], reverse: bool) -> tuple[str, str]:
    return tuple(reversed(pair)) if reverse else pair


@pytest.mark.parametrize("reverse", [False, True])
def test_conflicting_query_id_is_rejected_in_both_xml_orders(tmp_path, reverse):
    pair = (
        _search("Query_shared", "gene_alpha node=NODE_1", qlen="100"),
        _search("Query_shared", "gene_beta node=NODE_2", qlen="200"),
    )
    xml = _write_xml(tmp_path, *_ordered(pair, reverse))
    with pytest.raises(bi.BlastpAlignmentKeyConflictError, match="Query_shared"):
        bi.parse_alignment_xml(xml)


@pytest.mark.parametrize("reverse", [False, True])
def test_conflicting_first_title_token_is_rejected_in_both_xml_orders(tmp_path, reverse):
    pair = (
        _search("Query_alpha", "gene_shared node=NODE_1", qlen="100"),
        _search("Query_beta", "gene_shared node=NODE_1", qlen="100"),
    )
    xml = _write_xml(tmp_path, *_ordered(pair, reverse))
    with pytest.raises(bi.BlastpAlignmentKeyConflictError, match="gene_shared"):
        bi.parse_alignment_xml(xml)


@pytest.mark.parametrize("reverse", [False, True])
def test_query_id_title_key_cross_collision_is_rejected_in_both_orders(tmp_path, reverse):
    pair = (
        _search("Query_alpha", "Query_beta first-record", qlen="100"),
        _search("Query_beta", "gene_beta second-record", qlen="200"),
    )
    xml = _write_xml(tmp_path, *_ordered(pair, reverse))
    with pytest.raises(bi.BlastpAlignmentKeyConflictError, match="Query_beta"):
        bi.parse_alignment_xml(xml)


def test_identical_repeated_search_record_is_deterministic(tmp_path):
    search = _search("Query_same", "gene_same node=NODE_7", qlen="123")
    parsed = bi.parse_alignment_xml(_write_xml(tmp_path, search, search))
    assert set(parsed) == {"Query_same", "gene_same"}
    assert parsed["Query_same"] == parsed["gene_same"]
    assert parsed["Query_same"]["query_len"] == "123"


def test_unique_search_records_keep_both_lookup_keys(tmp_path):
    parsed = bi.parse_alignment_xml(_write_xml(
        tmp_path,
        _search("Query_one", "gene_one node=NODE_1", qlen="101"),
        _search("Query_two", "gene_two node=NODE_2", qlen="202"),
    ))
    assert set(parsed) == {"Query_one", "gene_one", "Query_two", "gene_two"}
    assert parsed["Query_one"]["query_len"] == "101"
    assert parsed["Query_two"]["query_len"] == "202"


def _tree_receipt(root: Path) -> list[tuple[str, int, str]]:
    return [
        (str(path.relative_to(root)), path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest())
        for path in sorted(root.rglob("*")) if path.is_file()
    ]


def test_cli_rejection_leaves_master_and_package_byte_identical(tmp_path):
    workbook = tmp_path / "master.xlsx"
    wb = openpyxl.Workbook()
    wb.active.title = "sentinel"
    wb.active["A1"] = "unchanged"
    wb.save(workbook)

    package = tmp_path / "package"
    package.mkdir()
    (package / "sentinel.txt").write_text("unchanged\n", encoding="utf-8")
    hits = tmp_path / "hits.csv"
    hits.write_text("gene_alpha,WP_TEST.1,50,90,1,0,1,90,1,90,1e-5,80,60\n", encoding="utf-8")
    xml = _write_xml(
        tmp_path,
        _search("Query_shared", "gene_alpha node=NODE_1", qlen="100"),
        _search("Query_shared", "gene_beta node=NODE_2", qlen="200"),
    )
    master_before = workbook.read_bytes()
    package_before = _tree_receipt(package)

    proc = subprocess.run(
        [sys.executable, str(ROOT / "mamey_run.py"), "ingest-blastp",
         "--master", str(workbook), "--strain", "TEST-01", "--hit-table", str(hits),
         "--xml", str(xml), "--package", str(package)],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )

    assert proc.returncode != 0
    assert "BLASTP_ALIGNMENT_QUERY_KEY_CONFLICT" in proc.stderr
    assert "Traceback" not in proc.stderr
    assert workbook.read_bytes() == master_before
    assert _tree_receipt(package) == package_before
