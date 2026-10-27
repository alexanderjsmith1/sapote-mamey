"""Prevalence denominators count each strain once.

domain_prevalence read the strain list from every census attempt row, and scan_prevalence from
every source row. A retried strain counted twice in the denominator and lowered every prevalence.
"""
import importlib.util
import json
import os
import pathlib
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_fx = _load(ROOT / "tests" / "test_domain_prevalence_v97413.py", "_prev_fixture_458")


class _Args:
    pass


def test_domain_prevalence_counts_a_retried_strain_once(tmp_path):
    cen, gbk, out = tmp_path / "c.sqlite", tmp_path / "g.sqlite", tmp_path / "out"
    _fx._census(str(cen))
    _fx._gbk(str(gbk))
    c = sqlite3.connect(cen)
    c.execute("insert into attempt values(3,'AS-1','COMPLETE',0,'retry')")
    c.commit()
    c.close()
    a = _Args()
    a.census, a.gbk_domains, a.out = str(cen), str(gbk), str(out)
    a.nr = a.cnr = a.sp = None
    a.host_tsv, a.host_strain_col, a.host_source_col, a.host_class_col = None, "strain", "source", None
    a.exclude, a.host_override, a.rare_loci_max = None, None, 5
    _fx._load().build(a)
    r = json.load(open(out / "domain_prevalence_ranking.json"))
    assert r["scope"]["strains"] == 2
    row = {x["domain_label"]: x for x in r["rows"]}["CommonDom"]
    assert row["strain_prevalence"] == 1.0


def test_scan_prevalence_counts_a_repeated_source_once(tmp_path):
    db = tmp_path / "scan.sqlite"
    c = sqlite3.connect(db)
    c.execute("create table source(strain)")
    c.executemany("insert into source values(?)", [("S1",), ("S1",), ("S2",)])
    c.execute("create table locus(locus_key,strain,exact_identity)")
    c.executemany("insert into locus values(?,?,?)", [("L1", "S1", "S1 / n / r / B1"), ("L2", "S2", "S2 / n / r / B2")])
    c.execute("create table gene(locus_key,locus_tag,protein_sha256,groups_json)")
    c.executemany("insert into gene values(?,?,?,?)", [("L1", "g1", "a", '["G"]'), ("L2", "g1", "b", '["G"]')])
    c.commit()
    c.close()
    a = _Args()
    a.scan_db, a.dataset_name, a.out = str(db), "fixture", str(tmp_path / "out")
    a.host_tsv, a.host_strain_col, a.host_source_col = None, "strain", "source"
    a.exclude, a.host_override, a.rare_loci_max = None, None, 5
    rows = _load(ROOT / "tools" / "scan_prevalence.py", "_scan_prev_458").build(a)
    assert rows[0]["strain_prevalence"] == 1.0
    r = json.load(open(os.path.join(a.out, "domain_prevalence_ranking.json")))
    assert r["scope"]["strains"] == 2
