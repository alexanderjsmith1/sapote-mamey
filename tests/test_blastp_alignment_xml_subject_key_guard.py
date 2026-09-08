"""Reject ambiguous XML Hit keys before query admission or governed output mutation."""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import openpyxl
import pytest

from mamey import blastp_ingest as bi


ROOT = Path(__file__).resolve().parents[1]


def _hit(accession: str, versioned_id: str, description: str) -> str:
    return f"""<Hit><description><HitDescr><id>ref|{versioned_id}|</id>
<accession>{accession}</accession><title>{description}</title>
<sciname>Streptomyces testensis</sciname></HitDescr></description><len>90</len></Hit>"""


def _search(*hits: str, qid: str = "Query_one", title: str = "gene_one") -> str:
    return f"""<Search><query-id>{qid}</query-id><query-title>{title}</query-title>
<query-len>100</query-len><hits>{''.join(hits)}</hits></Search>"""


def _write_xml(tmp_path: Path, *searches: str) -> Path:
    path = tmp_path / "alignment.xml"
    path.write_text("<BlastOutput2>" + "".join(searches) + "</BlastOutput2>", encoding="utf-8")
    return path


def _ordered(pair: tuple[str, str], reverse: bool) -> tuple[str, str]:
    return tuple(reversed(pair)) if reverse else pair


@pytest.mark.parametrize("reverse", [False, True])
def test_duplicate_bare_accession_conflict_is_rejected_in_both_hit_orders(tmp_path, reverse):
    pair = (
        _hit("SUBJECT_A", "SUBJECT_A.1", "alpha"),
        _hit("SUBJECT_A", "SUBJECT_A.2", "beta"),
    )
    xml = _write_xml(tmp_path, _search(*_ordered(pair, reverse)))
    with pytest.raises(bi.BlastpAlignmentSubjectKeyConflictError, match="SUBJECT_A"):
        bi.parse_alignment_xml(xml)


@pytest.mark.parametrize("reverse", [False, True])
def test_bare_versioned_cross_collision_is_rejected_in_both_hit_orders(tmp_path, reverse):
    pair = (
        _hit("SUBJECT_A", "SUBJECT_A.1", "alpha"),
        _hit("SUBJECT_A.1", "SUBJECT_B.1", "beta"),
    )
    xml = _write_xml(tmp_path, _search(*_ordered(pair, reverse)))
    with pytest.raises(bi.BlastpAlignmentSubjectKeyConflictError, match=r"SUBJECT_A\.1"):
        bi.parse_alignment_xml(xml)


@pytest.mark.parametrize("reverse", [False, True])
def test_shared_versioned_id_is_rejected_in_both_hit_orders(tmp_path, reverse):
    pair = (
        _hit("SUBJECT_A", "SHARED.1", "alpha"),
        _hit("SUBJECT_B", "SHARED.1", "beta"),
    )
    xml = _write_xml(tmp_path, _search(*_ordered(pair, reverse)))
    with pytest.raises(bi.BlastpAlignmentSubjectKeyConflictError, match=r"SHARED\.1"):
        bi.parse_alignment_xml(xml)


def test_identical_repeated_hit_is_accepted_deterministically(tmp_path):
    hit = _hit("SUBJECT_A", "SUBJECT_A.1", "alpha")
    parsed = bi.parse_alignment_xml(_write_xml(tmp_path, _search(hit, hit)))
    subjects = parsed["Query_one"]["subjects"]
    assert set(subjects) == {"SUBJECT_A", "SUBJECT_A.1"}
    assert subjects["SUBJECT_A"] == subjects["SUBJECT_A.1"]


def test_repeated_search_with_reordered_unique_hits_is_accepted(tmp_path):
    hit_a = _hit("SUBJECT_A", "SUBJECT_A.1", "alpha")
    hit_b = _hit("SUBJECT_B", "SUBJECT_B.1", "beta")
    parsed = bi.parse_alignment_xml(_write_xml(
        tmp_path,
        _search(hit_a, hit_b),
        _search(hit_b, hit_a),
    ))
    assert set(parsed["Query_one"]["subjects"]) == {
        "SUBJECT_A", "SUBJECT_A.1", "SUBJECT_B", "SUBJECT_B.1",
    }


def _tree_receipt(root: Path) -> list[tuple[str, int, str]]:
    return [
        (str(path.relative_to(root)), path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest())
        for path in sorted(root.rglob("*")) if path.is_file()
    ]


def test_cli_subject_rejection_leaves_master_and_package_byte_identical(tmp_path):
    workbook = tmp_path / "master.xlsx"
    wb = openpyxl.Workbook()
    wb.active.title = "sentinel"
    wb.active["A1"] = "unchanged"
    wb.save(workbook)

    package = tmp_path / "package"
    package.mkdir()
    (package / "sentinel.txt").write_text("unchanged\n", encoding="utf-8")
    hits = tmp_path / "hits.csv"
    hits.write_text("gene_one,SUBJECT_A.1,50,90,1,0,1,90,1,90,1e-5,80,60\n", encoding="utf-8")
    xml = _write_xml(tmp_path, _search(
        _hit("SUBJECT_A", "SUBJECT_A.1", "alpha"),
        _hit("SUBJECT_A.1", "SUBJECT_B.1", "beta"),
    ))
    master_before = workbook.read_bytes()
    package_before = _tree_receipt(package)

    proc = subprocess.run(
        [sys.executable, str(ROOT / "mamey_run.py"), "ingest-blastp",
         "--master", str(workbook), "--strain", "TEST-01", "--hit-table", str(hits),
         "--xml", str(xml), "--package", str(package)],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )

    assert proc.returncode != 0
    assert "BLASTP_ALIGNMENT_SUBJECT_KEY_CONFLICT" in proc.stderr
    assert "Traceback" not in proc.stderr
    assert workbook.read_bytes() == master_before
    assert _tree_receipt(package) == package_before
