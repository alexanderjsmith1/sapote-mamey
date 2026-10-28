"""scan_prevalence writes the AUDIT_RECEIPT.json its widget footer points to.

tools/scan_prevalence.py emits the same ranking JSON as domain_prevalence, so the same widget renders it,
and the widget footer says "Channel coverage: see AUDIT_RECEIPT.json". domain_prevalence writes that file;
scan_prevalence did not, so the footer pointed at nothing.
"""
import json
import os

from tests.test_458_prevalence_denominator_distinct_strains import ROOT, _Args, _load


def _db(tmp_path):
    import sqlite3
    db = tmp_path / "scan.sqlite"
    c = sqlite3.connect(db)
    c.execute("create table source(strain)")
    c.executemany("insert into source values(?)", [("S1",), ("S2",)])
    c.execute("create table locus(locus_key,strain,exact_identity)")
    c.executemany("insert into locus values(?,?,?)", [("L1", "S1", "S1 / n / r / B1"), ("L2", "S2", "S2 / n / r / B2")])
    c.execute("create table gene(locus_key,locus_tag,protein_sha256,groups_json)")
    c.executemany("insert into gene values(?,?,?,?)", [("L1", "g1", "a", '["G"]'), ("L2", "g1", "b", '["H"]')])
    c.commit()
    c.close()
    return db


def test_receipt_is_written_with_the_domain_prevalence_keys(tmp_path):
    a = _Args()
    a.scan_db, a.dataset_name, a.out = str(_db(tmp_path)), "fixture", str(tmp_path / "out")
    a.host_tsv, a.host_strain_col, a.host_source_col = None, "strain", "source"
    a.exclude, a.host_override, a.rare_loci_max = None, None, 5
    _load(ROOT / "tools" / "scan_prevalence.py", "_scan_prev_460").build(a)
    path = os.path.join(a.out, "AUDIT_RECEIPT.json")
    assert os.path.isfile(path)
    r = json.load(open(path))
    for key in ("scope_strains", "distinct_families", "held", "host_distribution", "evidence_channels", "elapsed_s"):
        assert key in r, key
    assert r["scope_strains"] == 2 and r["distinct_families"] == 2
    assert r["evidence_channels"] == []          # a keyword scan has no nr/cnr/sp channels
    assert r["source"]["dataset"] == "fixture" and len(r["source"]["scan_db_sha256"]) == 64
