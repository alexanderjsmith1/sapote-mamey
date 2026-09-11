"""Explicit reference metadata input and omitted-input notice regressions."""
import os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCER = os.path.join(ROOT, "tools", "build_placement_ggtree_inputs.py")
DOC = os.path.join(ROOT, "docs", "EPA_NG_PLACEMENT_WORKFLOW.md")

NEWICK = "((AS_1:0.01,NR_042115_1_Actinomadura_fulvescens_strain_DSM_43923:0.01):0.02,NR_025002_1_Actinomadura_vinacea_strain_JCM_3325:0.03);"


def _run(tmp_path, *extra):
    graft = tmp_path / "g.nwk"; graft.write_text(NEWICK)
    cmd = [sys.executable, PRODUCER, "--graft", str(graft), "--group", "Actinomadura",
           "--keep-all-refs", "--out-prefix", str(tmp_path / "o"), *extra]
    return subprocess.run(cmd, capture_output=True, text=True)


def test_a_run_without_the_flag_announces_that_references_will_be_bare(tmp_path):
    r = _run(tmp_path)
    assert r.returncode == 0, r.stderr
    assert "--ref-source-db" in r.stderr and "NOT_REQUESTED" in r.stderr, r.stderr


def test_the_notice_is_not_emitted_when_the_flag_is_supplied(tmp_path):
    import sqlite3
    db = tmp_path / "s.sqlite"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE record (acc_base TEXT, isolation_source TEXT, host TEXT, country TEXT)")
    con.execute("INSERT INTO record VALUES ('NR_042115','soil','','Turkmenistan')")
    con.commit(); con.close()
    r = _run(tmp_path, "--ref-source-db", str(db))
    assert r.returncode == 0, r.stderr
    assert "no --ref-source-db" not in r.stderr, r.stderr


def test_the_notice_is_non_fatal_and_the_annotation_is_still_written(tmp_path):
    r = _run(tmp_path)
    ann = tmp_path / "o_ggtree_annotation.tsv"
    assert r.returncode == 0 and ann.exists()
    assert "reference_source_status" in ann.read_text().splitlines()[0]


def test_the_documented_command_passes_the_flag_it_promises_output_for():
    doc = open(DOC, encoding="utf-8").read()
    i = doc.index("build_placement_ggtree_inputs.py --graft")
    block = doc[i:i + 900]
    assert "isolation-source on refs" in block, "the promise this test guards has moved"
    assert "--ref-source-db" in block, "the documented command cannot deliver isolation-source on refs"

def test_insdc_placeholders_do_not_render_as_deposited_fact(tmp_path):
    """"not applicable" / "not determined" are placeholders, not metadata: Preserve real metadata beside missing-value placeholders."""
    import importlib.util, sqlite3
    spec = importlib.util.spec_from_file_location("bpgi", PRODUCER)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    db = tmp_path / "n.sqlite"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE record (acc_base TEXT, isolation_source TEXT, host TEXT, country TEXT)")
    con.execute("INSERT INTO record VALUES ('NR_114755','','not applicable','Nigeria')")
    con.execute("INSERT INTO record VALUES ('NR_026344','','not applicable','not determined')")
    con.commit(); con.close()
    src = m._load_ref_sources(str(db))
    assert src["NR114755"] == "Nigeria", src["NR114755"]      # the real country survives
    assert src["NR026344"] == "", src["NR026344"]             # nothing real left -> METADATA_ABSENT
