"""v9.7.410 hostile audit, round 2 — two admission gates that accepted text they should not.

1. tools/gen_release_manifest.py::counts_from_log searched `(\\d+)\\s+passed` over the whole
   file, so a log made of the prose "Note: 7783 passed, 0 failed" was stamped into the release
   manifest as a receipt-bound green run. Counts now come only from pytest's own summary line.
2. mamey/blastp_ingest.py::parse_hit_table admitted a header line of an outfmt-10 export as a
   hit row (query_locus "query", pct_identity "pident"), and nan/inf/overflowing numbers.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

import mamey
from mamey import blastp_ingest as bi

ROOT = Path(mamey.__file__).resolve().parent.parent


def _grm():
    spec = importlib.util.spec_from_file_location("grm", ROOT / "tools" / "gen_release_manifest.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------- gen_release_manifest log gate

@pytest.mark.parametrize("text", [
    "Note: 7783 passed, 0 failed (operator note)\n",
    "hello\n",
    "",
    "7783 passed\n",                      # no `in <seconds>s` — not a pytest summary
])
def test_manifest_refuses_a_log_without_a_real_pytest_summary(tmp_path, text):
    log = tmp_path / "x.log"
    log.write_text(text, encoding="utf-8")
    with pytest.raises(SystemExit, match="no pytest summary line"):
        _grm().counts_from_log(log)


@pytest.mark.parametrize("text,expected", [
    ("........\n7783 passed, 1013 skipped, 30 warnings in 324.57s (0:05:24)\n", (7783, 1013)),
    ("===== 12 passed, 1 skipped in 0.42s =====\n", (12, 1)),
    ("5 passed in 0.10s\n", (5, 0)),
    # prose BEFORE the real summary must not win
    ("Note: 99999 passed earlier\n12 passed in 0.5s\n", (12, 0)),
])
def test_manifest_reads_counts_only_from_the_summary_line(tmp_path, text, expected):
    log = tmp_path / "x.log"
    log.write_text(text, encoding="utf-8")
    assert _grm().counts_from_log(log) == expected


# ------------------------------------------------------------------------- HitTable header/numeric

GOOD = "BGC001_ctg1_2,WP_1,66.1,340,115,0,1,340,1,340,8.8e-152,441,75.2\n"


def test_hit_table_header_row_is_rejected_not_admitted_as_a_hit(tmp_path):
    p = tmp_path / "h.csv"
    p.write_text("query,subject,pident,length,mismatch,gapopen,qstart,qend,sstart,send,evalue,bitscore,ppos\n" + GOOD)
    with pytest.raises(bi.BlastpHitTableError, match="header row detected at line 1"):
        bi.parse_hit_table(p)


@pytest.mark.parametrize("row,col", [
    ("q1,WP_1,nan,340,115,0,1,340,1,340,8.8e-152,441,75.2\n", "pct_identity"),
    ("q1,WP_1,66.1,inf,115,0,1,340,1,340,8.8e-152,441,75.2\n", "align_len"),
    ("q1,WP_1,66.1," + "9" * 400 + ",115,0,1,340,1,340,8.8e-152,441,75.2\n", "align_len"),
    ("q1,WP_1,66.1,340,115,0,1,340,1,340,8.8e-152,441,abc\n", "positives_pct"),
])
def test_hit_table_rejects_non_finite_or_non_numeric_measurements(tmp_path, row, col):
    p = tmp_path / "h.csv"
    p.write_text(row)
    with pytest.raises(bi.BlastpHitTableError, match="non-numeric or non-finite"):
        bi.parse_hit_table(p)


def test_hit_table_still_admits_real_rows_including_blank_positives(tmp_path):
    p = tmp_path / "h.csv"
    p.write_text(GOOD + "q2,WP_2,55.0,200,90,1,1,200,1,200,1e-80,300\n")
    rows = bi.parse_hit_table(p)
    assert len(rows) == 2 and rows[1]["positives_pct"] == ""
