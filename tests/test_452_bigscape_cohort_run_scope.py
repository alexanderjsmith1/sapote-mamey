"""The cohort report binds the selected BiG-SCAPE run and cutoff before reporting PASS.

An absent run, an unfinished run or a missing cutoff must refuse instead of exporting
an empty report with a PASS receipt. A finished run that declared the cutoff but has no
families is the only admitted empty state. A database without a run table cannot prove
completion, so its receipt is not PASS.
"""
import csv
import importlib.util
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "bigscape_cohort_report_452", ROOT / "tools" / "bigscape_cohort_report.py"
)
report = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(report)


def _tsv(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _fixture(tmp_path, *, run_rows=None, families=True, family_cutoff=0.3):
    database = tmp_path / "cohort.db"
    connection = sqlite3.connect(database)
    connection.executescript(
        "create table family(id integer,bin_label text,run_id integer,cutoff real);"
        "create table bgc_record_family(family_id integer,record_id integer);"
        "create table bgc_record(id integer,gbk_id integer,product text,category text,contig_edge integer);"
        "create table gbk(id integer,path text);"
    )
    if run_rows is not None:
        connection.execute(
            "create table run(id integer primary key,label text,start_time text,end_time text,cutoffs text)"
        )
        connection.executemany("insert into run values(?,?,?,?,?)", run_rows)
    if families:
        connection.execute("insert into family values(12,'NRPS',7,?)", (family_cutoff,))
        connection.execute("insert into gbk values(1,'/input/DEMO-A_NODE_1_length_100_cov_2.region001.gbk')")
        connection.execute("insert into bgc_record values(1,1,'NRPS','NRPS',0)")
        connection.execute("insert into bgc_record_family values(12,1)")
    connection.commit()
    connection.close()
    host = tmp_path / "host.tsv"
    _tsv(host, [{"strain": "DEMO-A", "genus": "GenusA", "host_as_deposited": "Example host"}])
    crosswalk = tmp_path / "crosswalk.tsv"
    _tsv(crosswalk, [{"strain": "DEMO-A", "node_num": "1", "region": "001", "legacy_bgc": "BGC001"}])
    return database, host, crosswalk


FINISHED = (7, "demo", "2026-01-01 00:00:00", "2026-01-01 01:00:00", "0.3,0.5")


def test_absent_run_is_refused(tmp_path):
    database, host, crosswalk = _fixture(tmp_path, run_rows=[FINISHED])
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="RUN_SCOPE_GATE"):
        report.build(database, 99, 0.3, host, crosswalk, out)
    assert not (out / "BIGSCAPE_COHORT_REPORT_RECEIPT.json").exists()


def test_unfinished_run_is_refused(tmp_path):
    unfinished = (7, "demo", "2026-01-01 00:00:00", "", "0.3")
    database, host, crosswalk = _fixture(tmp_path, run_rows=[unfinished])
    with pytest.raises(ValueError, match="RUN_SCOPE_GATE.*end_time"):
        report.build(database, 7, 0.3, host, crosswalk, tmp_path / "out")


def test_missing_cutoff_is_refused(tmp_path):
    database, host, crosswalk = _fixture(tmp_path, run_rows=[FINISHED])
    with pytest.raises(ValueError, match="RUN_SCOPE_GATE.*cutoff"):
        report.build(database, 7, 0.5, host, crosswalk, tmp_path / "out")


def test_completed_run_with_families_passes(tmp_path):
    database, host, crosswalk = _fixture(tmp_path, run_rows=[FINISHED])
    receipt = report.build(database, 7, 0.3, host, crosswalk, tmp_path / "out")
    assert receipt["status"] == "PASS"
    assert receipt["run_scope_state"] == "COMPLETED_RUN_WITH_FAMILIES"
    assert receipt["families"] == 1


def test_genuine_empty_completed_run_is_explicit(tmp_path):
    database, host, crosswalk = _fixture(tmp_path, run_rows=[FINISHED], families=False)
    receipt = report.build(database, 7, 0.3, host, crosswalk, tmp_path / "out")
    assert receipt["status"] == "PASS"
    assert receipt["run_scope_state"] == "VALID_EMPTY_COMPLETED_RUN"
    assert receipt["families"] == 0


def test_no_run_table_is_not_pass(tmp_path):
    database, host, crosswalk = _fixture(tmp_path, run_rows=None)
    receipt = report.build(database, 7, 0.3, host, crosswalk, tmp_path / "out")
    assert receipt["status"] == "RUN_COMPLETION_UNVERIFIED"
    assert receipt["run_scope_state"] == "UNVERIFIED_RUN_TABLE_ABSENT"


def test_no_run_table_and_no_families_is_refused(tmp_path):
    database, host, crosswalk = _fixture(tmp_path, run_rows=None)
    with pytest.raises(ValueError, match="RUN_SCOPE_GATE"):
        report.build(database, 8, 0.3, host, crosswalk, tmp_path / "out")
