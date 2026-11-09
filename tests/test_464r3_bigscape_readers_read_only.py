"""Round 3c: BiG-SCAPE readers never create or write a database; the network figure output set is fresh;
family verdicts need an explicit run when several finished runs exist."""
import importlib.util
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))


def _load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shared_opener_refuses_missing_and_is_read_only(tmp_path):
    from mamey.bigscape_namespace import open_database_read_only
    with pytest.raises(FileNotFoundError):
        open_database_read_only(tmp_path / "absent.db")
    assert not (tmp_path / "absent.db").exists()
    db = tmp_path / "x.db"
    sqlite3.connect(db).execute("create table t(a)").connection.commit()
    con = open_database_read_only(db)
    with pytest.raises(sqlite3.OperationalError):
        con.execute("insert into t values (1)")


def test_mibig_anchors_missing_db_creates_no_file(tmp_path):
    tool = _load("tools/bigscape_mibig_anchors.py", "_bma_464r3")
    missing = tmp_path / "absent.db"
    assert tool.main(["--db", str(missing), "--out", str(tmp_path / "o.tsv"), "--run-id", "1", "--cutoff", "0.3"]) == 2
    assert not missing.exists() and not (tmp_path / "o.tsv").exists()


def test_family_domains_missing_db_creates_no_file(tmp_path):
    missing = tmp_path / "absent.db"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "bigscape_family_domains.py"), "--db", str(missing),
                        "--cutoff", "0.3", "--run-id", "1"], capture_output=True, text=True)
    assert r.returncode != 0 and "not an existing BiG-SCAPE database" in r.stderr
    assert not missing.exists()


def test_gcf_network_missing_db_creates_no_file(tmp_path):
    pytest.importorskip("networkx"); pytest.importorskip("matplotlib")
    from mamey import bigscape_figures
    missing = tmp_path / "absent.db"
    res = bigscape_figures.gcf_network(str(missing), "RB68", run=1, cutoff=0.5, out=str(tmp_path / "n.png"))
    assert res["status"] == "DB_NOT_FOUND"
    assert not missing.exists()


def test_gcf_network_refuses_existing_outputs_and_db_alias(tmp_path):
    pytest.importorskip("networkx"); pytest.importorskip("matplotlib")
    from mamey import bigscape_figures
    from test_409_figure_provenance import _build_bigscape_db
    db = tmp_path / "run.db"
    _build_bigscape_db(db)
    out = tmp_path / "net.png"
    assert bigscape_figures.gcf_network(str(db), "RB68", run=1, cutoff=0.5, out=str(out))["status"] == "WRITTEN"
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    again = bigscape_figures.gcf_network(str(db), "RB68", run=1, cutoff=0.5, out=str(out))
    assert again["status"] == "OUTPUT_REFUSED"
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before
    # a leftover sidecar alone blocks the set
    (tmp_path / "net2_scope.json").write_text("{}")
    assert bigscape_figures.gcf_network(str(db), "RB68", run=1, cutoff=0.5,
                                        out=str(tmp_path / "net2.png"))["status"] == "OUTPUT_REFUSED"
    assert not (tmp_path / "net2.png").exists()
    db_bytes = db.read_bytes()
    assert bigscape_figures.gcf_network(str(db), "RB68", run=1, cutoff=0.5, out=str(db))["status"] == "OUTPUT_REFUSED"
    assert db.read_bytes() == db_bytes


def test_verdicts_refuse_two_finished_runs_without_run_id_and_record_run(tmp_path):
    from test_452_bigscape_family_verdicts_run_id import _db
    bfv = _load("tools/bigscape_family_verdicts.py", "_bfv_464r3c")
    db = _db(tmp_path)
    with pytest.raises(SystemExit, match="RUN_AMBIGUOUS"):
        bfv.main([str(db), str(tmp_path / "v.tsv")])
    assert not (tmp_path / "v.tsv").exists()
    assert bfv.main([str(db), str(tmp_path / "v1.tsv"), "--run-id", "1"]) == 0
    header, row = (tmp_path / "v1.tsv").read_text().splitlines()[:2]
    assert header.split("\t")[-1] == "run_id" and row.split("\t")[-1] == "1"
    placement = (tmp_path / "v1.tsv.placement.tsv").read_text().splitlines()
    assert placement[0].split("\t")[-1] == "run_id" and placement[1].split("\t")[-1] == "1"


def test_verdicts_refuse_named_unfinished_run(tmp_path):
    from test_452_bigscape_family_verdicts_run_id import _db
    bfv = _load("tools/bigscape_family_verdicts.py", "_bfv_464r3c_unf")
    db = _db(tmp_path)
    con = sqlite3.connect(db)
    con.executescript("create table run(id integer primary key, end_time text);"
                      "insert into run values (1, '2026-01-01'); insert into run values (2, NULL);")
    con.commit(); con.close()
    with pytest.raises(SystemExit, match="RUN_UNFINISHED"):
        bfv.main([str(db), str(tmp_path / "v.tsv"), "--run-id", "2"])
    # only run 1 finished: no --run-id is unambiguous
    assert bfv.main([str(db), str(tmp_path / "w.tsv")]) == 0
