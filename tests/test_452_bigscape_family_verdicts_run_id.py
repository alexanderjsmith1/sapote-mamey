"""v9.7.452: family verdicts read one BiG-SCAPE run.

A BiG-SCAPE 2 database reused for a later run (the documented way to add genomes) keeps every run's families. Reading all
of them counted each family once per run, so verdict tables from a reused database were exactly doubled. The tool now
reads the latest run by default, or the run named with --run-id. Synthetic SYN-* names only.
"""
import importlib.util
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("bfv_452_run_id", ROOT / "tools" / "bigscape_family_verdicts.py")
bfv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bfv)

FILES = {1: "SYN-971_NODE_1_length_9000_cov_1.0.region001.gbk", 2: "SYN-972_NODE_2_length_9000_cov_1.0.region001.gbk",
         3: "Genus_other__GCF_1__NZ_A01.1.region001.gbk", 4: "BGC0000001.gbk"}


def _db(tmp_path, with_run_id=True):
    p = tmp_path / ("runs.db" if with_run_id else "plain.db")
    con = sqlite3.connect(p)
    fam_cols = "id integer primary key, cutoff real, newick text" + (", run_id int" if with_run_id else "")
    con.executescript(f"""
    create table gbk(id integer primary key, path text, organism text);
    create table bgc_record(id integer primary key, gbk_id int, record_type text, product text, nt_start int, nt_stop int);
    create table family({fam_cols});
    create table bgc_record_family(record_id int, family_id int);""")
    for gid, f in FILES.items():
        con.execute("insert into gbk values (?,?,?)", (gid, f"/x/gbk_input/{f}", "Genus sp."))
        con.execute("insert into bgc_record values (?,?,?,?,?,?)", (gid, gid, "region", "NRPS", 0, 9000))
    # run 1: one family {1, 3}; run 2 (the same database reused with more genomes): {1, 3} again and {2, 4}
    fams = [(10, 1, [1, 3]), (30, 2, [1, 3]), (31, 2, [2, 4])]
    for fid, run, rids in fams:
        if with_run_id:
            con.execute("insert into family values (?,?,?,?)", (fid, 0.3, "(1:0.1,2:0.1);", run))
        elif run == 2:
            con.execute("insert into family values (?,?,?)", (fid, 0.3, "(1:0.1,2:0.1);"))
        else:
            continue
        for rid in rids:
            con.execute("insert into bgc_record_family values (?,?)", (rid, fid))
    con.commit(); con.close()
    return p


def _build(p, run_id=None):
    import re
    return bfv.build(str(p), 0.3, re.compile(r"^([A-Za-z]+-\d+)_"), ("SID_", "TYPE_"), run_id=run_id)


def test_reused_database_reads_the_latest_run_only(tmp_path):
    rows, placement = _build(_db(tmp_path))
    assert sorted(r["family_id"] for r in rows) == [30, 31]                 # not 10: run 1's copy is not counted again
    assert {r["verdict"] for r in rows} == {"QUERY_SHARED_REFERENCE", "QUERY_PRIVATE_MIBIG_MATCHED"}
    assert placement == [{"cutoff": 0.3, "region_records": 4, "records_with_family_row": 4, "singleton_records": 0}]
    assert bfv.build.last_run == (2, [1, 2])


def test_run_id_selects_an_earlier_run(tmp_path):
    rows, placement = _build(_db(tmp_path), run_id=1)
    assert [r["family_id"] for r in rows] == [10]
    assert placement[0]["records_with_family_row"] == 2 and placement[0]["singleton_records"] == 2


def test_unknown_run_id_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="RUN_ID_NOT_FOUND"):
        _build(_db(tmp_path), run_id=7)


def test_database_without_run_column_is_read_as_before(tmp_path):
    db = _db(tmp_path, with_run_id=False)
    rows, _ = _build(db)
    assert sorted(r["family_id"] for r in rows) == [30, 31]
    with pytest.raises(SystemExit, match="RUN_ID_UNAVAILABLE"):
        _build(db, run_id=1)


def test_cli_reports_the_run_it_read(tmp_path, capsys):
    out = tmp_path / "v.tsv"
    assert bfv.main([str(_db(tmp_path)), str(out)]) == 0
    text = capsys.readouterr()
    assert "run 2 of 2 run(s)" in (text.out + text.err)
    assert out.read_text().count("\n") == 3                                 # header + 2 families
