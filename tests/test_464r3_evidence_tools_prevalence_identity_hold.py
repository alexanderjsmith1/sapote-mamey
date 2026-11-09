"""A locus with a NULL or blank exact identity is listed as an explicit hold, never as null."""
import importlib.util
import json
import sqlite3
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def _load(name):
    spec = importlib.util.spec_from_file_location(name + "_464r3", TOOLS / f"{name}.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def test_scan_prevalence_null_identity_is_a_hold(tmp_path):
    db = tmp_path / "scan.sqlite"
    c = sqlite3.connect(db)
    c.executescript("create table source(strain text); create table locus(locus_key text, strain text, exact_identity text);"
                    "create table gene(locus_key text, locus_tag text, protein_sha256 text, groups_json text);")
    c.execute("insert into source values('EXAMPLE')")
    c.execute("insert into locus values('L1','EXAMPLE',NULL)")
    c.execute("insert into locus values('L2','EXAMPLE','EXAMPLE / CTG_A / region001 / BGC001')")
    c.execute("insert into gene values(?,?,?,?)", ("L1", "g1", "a", json.dumps(["groupA"])))
    c.execute("insert into gene values(?,?,?,?)", ("L2", "g2", "b", json.dumps(["groupA"])))
    c.commit(); c.close()
    m = _load("scan_prevalence")
    out = tmp_path / "out"
    assert m.main(["--scan-db", str(db), "--dataset-name", "scan", "--out", str(out)]) == 0
    rows = json.loads((out / "domain_prevalence_ranking.json").read_text())["rows"]
    loci = rows[0]["loci_list"]
    assert None not in loci
    assert "EXAMPLE / CTG_A / region001 / BGC001" in loci
    assert any(x.startswith("IDENTITY_HOLD") and "L1" in x for x in loci)


def test_domain_prevalence_helper_holds_blank_identity():
    m = _load("domain_prevalence")
    assert m.locus_label({"L1": "  "}, "L1").startswith("IDENTITY_HOLD")
    assert m.locus_label({"L1": "S / C / region001 / BGC001"}, "L1") == "S / C / region001 / BGC001"
