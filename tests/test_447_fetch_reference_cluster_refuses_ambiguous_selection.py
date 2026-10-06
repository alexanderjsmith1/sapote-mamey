"""Audit D15: a reference/cohort selection must bind exactly one gbk record; the first LIKE match is never taken."""
import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _db(path, paths):
    c = sqlite3.connect(path)
    c.executescript("CREATE TABLE gbk(id INTEGER PRIMARY KEY, path TEXT);"
                    "CREATE TABLE cds(id INTEGER PRIMARY KEY, gbk_id INT, nt_start INT, nt_stop INT, strand INT,"
                    " aa_seq TEXT, orf_num INT);"
                    "CREATE TABLE hsp(cds_id INT, accession TEXT, bit_score REAL);")
    for i, p in enumerate(paths, 1):
        c.execute("INSERT INTO gbk(id,path) VALUES(?,?)", (i, p))
        c.execute("INSERT INTO cds(gbk_id,nt_start,nt_stop,strand,aa_seq,orf_num) VALUES(?,1,90,1,'MK',1)", (i,))
    c.commit()
    c.close()


TWO = ["/x/AS-1_NODE_4_len.region001.gbk", "/x/AS-1_NODE_4_len.region002.gbk"]


@pytest.mark.parametrize("tool", ["fetch_reference_cluster", "bgc_reference_align"])
def test_two_matches_are_refused(tmp_path, tool):
    db = tmp_path / "d.db"
    _db(db, TWO)
    m = _load(tool)
    args = (str(db), "AS-1_NODE_4", "x") if tool == "fetch_reference_cluster" else (str(db), "AS-1_NODE_4")
    with pytest.raises(ValueError, match="matches 2 records"):
        m.ref_from_db(*args)


@pytest.mark.parametrize("tool", ["fetch_reference_cluster", "bgc_reference_align"])
def test_an_exact_region_substring_binds_one_record(tmp_path, tool):
    db = tmp_path / "d.db"
    _db(db, TWO)
    m = _load(tool)
    args = (str(db), "region002", "x") if tool == "fetch_reference_cluster" else (str(db), "region002")
    assert len(m.ref_from_db(*args)) == 1


def test_underscore_is_literal_not_a_wildcard(tmp_path):
    db = tmp_path / "d.db"
    _db(db, ["/x/AS-1xNODE_4.region001.gbk"])
    m = _load("fetch_reference_cluster")
    with pytest.raises(KeyError):
        m.ref_from_db(str(db), "AS-1_NODE_4", "x")
