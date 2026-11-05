"""BiG-SCAPE family readers stay inside one run.

A BiG-SCAPE database can hold several runs, each with its own family rows. The matrix and
clinker widgets, bigscape_clinker_html and bigscape_family_figures filtered on cutoff only,
so a database with four runs gave four times the families. Readers now use
mamey.bigscape_namespace.select_family_run: a given run_id must exist, and with none the
database must hold exactly one run.
"""
import importlib.util
import pathlib
import sqlite3
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "deliverable_tools"))
sys.path.insert(0, str(ROOT / "tools"))

from mamey.bigscape_namespace import NamespaceError, select_family_run  # noqa: E402


def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _db(path, runs=(1, 2), unfinished=()):
    """Two runs that clustered the same two regions into one family each."""
    con = sqlite3.connect(path)
    con.executescript(
        "create table run(id integer primary key, label text, end_time text);"
        "create table gbk(id integer primary key, path text, organism text);"
        "create table bgc_record(id integer primary key, gbk_id integer, product text, nt_start integer,"
        " nt_stop integer, record_type text);"
        "create table family(id integer primary key, run_id integer, cutoff real);"
        "create table bgc_record_family(record_id integer, family_id integer);"
        "insert into gbk values (1, '/x/STRA-1_NODE_1.region001.gbk', 'Streptomyces sp.');"
        "insert into gbk values (2, '/x/STRB-2_NODE_4.region002.gbk', 'Streptomyces sp.');"
        "insert into bgc_record values (1, 1, 'NRPS', 0, 1000, 'region');"
        "insert into bgc_record values (2, 2, 'NRPS', 0, 1200, 'region');"
    )
    for n, run in enumerate(runs, start=1):
        con.execute("insert into run values (?, ?, ?)",
                    (run, f"run{run}", None if run in unfinished else "2026-08-04 21:29:11"))
        con.execute("insert into family values (?, ?, 0.3)", (n, run))
        con.execute("insert into bgc_record_family values (1, ?)", (n,))
        con.execute("insert into bgc_record_family values (2, ?)", (n,))
    con.commit()
    con.close()
    return str(path)


def test_selector_refuses_two_runs_without_run_id(tmp_path):
    con = sqlite3.connect(_db(tmp_path / "bs.db"))
    with pytest.raises(NamespaceError) as err:
        select_family_run(con)
    assert err.value.code == "RUN_AMBIGUOUS"
    assert select_family_run(con, "2") == 2
    with pytest.raises(NamespaceError) as err:
        select_family_run(con, 7)
    assert err.value.code == "RUN_NOT_IN_DB"


def test_selector_single_run_and_unscoped_table(tmp_path):
    con = sqlite3.connect(_db(tmp_path / "one.db", runs=(5,)))
    assert select_family_run(con) == 5
    bare = sqlite3.connect(":memory:")
    bare.execute("create table family(id integer primary key, cutoff real)")
    assert select_family_run(bare) is None


def test_widget_reader_counts_one_run(tmp_path):
    data = _load("deliverable_tools/_bigscape_data.py", "_bigscape_data_463run")
    con = sqlite3.connect(_db(tmp_path / "bs.db"))
    with pytest.raises(NamespaceError):
        data.family_members(con, 0.3)
    fam = data.family_members(con, 0.3, run_id=2)
    assert list(fam) == [2]
    assert len(fam[2]) == 2


def test_clinker_html_reader_counts_one_run(tmp_path):
    ch = _load("tools/bigscape_clinker_html.py", "bigscape_clinker_html_463run")
    con = sqlite3.connect(_db(tmp_path / "bs.db"))
    fam = ch.family_members(con, 0.3, {}, run=1)
    assert list(fam) == [1]
    recs, m = ch.strain_family_map(con, "STRA-1", 0.3, run=1)
    assert recs == [1] and m == {1: 1}


def test_family_figures_reader_counts_one_run(tmp_path):
    ff = _load("tools/bigscape_family_figures.py", "bigscape_family_figures_463run")
    db = _db(tmp_path / "bs.db")
    with pytest.raises(NamespaceError):
        ff.family_table(db, 0.3)
    fam = ff.family_table(db, 0.3, "1")
    assert list(fam) == [1]
    assert len(fam[1]) == 2


def test_matrix_payload_uses_selected_run_label(tmp_path):
    mw = _load("deliverable_tools/bigscape_matrix_widget.py", "bigscape_matrix_widget_463run")
    con = sqlite3.connect(_db(tmp_path / "bs.db"))
    payload = mw.build_payload(con, 0.3, run_id=2)
    assert payload["run"] == "run2"
    assert len(payload["families"]) <= 1


def test_unfinished_runs_are_refused_and_skipped(tmp_path):
    # The real Nocardia clade database: runs 1-3 have no end_time but 868 family rows each.
    con = sqlite3.connect(_db(tmp_path / "bs.db", runs=(1, 2, 3, 4), unfinished=(1, 2, 3)))
    assert select_family_run(con) == 4
    with pytest.raises(NamespaceError) as err:
        select_family_run(con, 2)
    assert err.value.code == "RUN_UNFINISHED"
    none_done = sqlite3.connect(_db(tmp_path / "bs2.db", runs=(1,), unfinished=(1,)))
    with pytest.raises(NamespaceError) as err:
        select_family_run(none_done)
    assert err.value.code == "RUN_UNFINISHED"
