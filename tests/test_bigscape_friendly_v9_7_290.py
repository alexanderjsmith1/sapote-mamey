"""
Tests for the BiG-SCAPE-friendly patch set (target v9.7.290):
  - bigscape_prep.py skips macOS AppleDouble (._*) files
  - bigscape_known_novel.py builds a KNOWN/NOVEL table from a single anchored DB
  - bigscape_family_domains.py surfaces Pfam domains per family
Fixtures are built inline (a tiny zip; a minimal BiG-SCAPE-shaped SQLite) so the tests are
self-contained and need no gold package.
"""
import os, sys, zipfile, sqlite3, subprocess, tempfile, textwrap, csv

TOOLS = os.path.join(os.path.dirname(__file__), "..", "tools")


def _run(script, *args):
    return subprocess.run([sys.executable, os.path.join(TOOLS, script), *args],
                          capture_output=True, text=True)


def test_prep_skips_appledouble(tmp_path):
    prep = os.path.join(TOOLS, "bigscape_prep.py")
    if not os.path.exists(prep):
        import pytest; pytest.skip("bigscape_prep.py not present")
    z = tmp_path / "AS-999.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("AS-999_NODE_1_length_100_cov_1.0.region001.gbk", "LOCUS real\n//\n")
        zf.writestr("._AS-999_NODE_1_length_100_cov_1.0.region001.gbk", b"\x00\x05\x16")  # AppleDouble
    out = tmp_path / "staged"
    # v9.7.370 (announced change, AMBER strictness-aware rework): --strictness is now
    # REQUIRED — the tool refuses possibly-mixed-flavor inputs unless the flavor is declared.
    # The inline fixture zip has no antiSMASH JSON, so its flavor is undetectable and must
    # additionally be forced with --assume-strictness (the tool otherwise SKIPs it loudly).
    r = _run("bigscape_prep.py", "--inputs", str(z), "--out", str(out),
             "--strictness", "relaxed", "--assume-strictness", "relaxed")
    # the rework also writes a STRICTNESS_MANIFEST.tsv provenance record; count only region GBKs
    staged = [f for f in os.listdir(out) if f.endswith(".gbk")] if out.exists() else []
    assert r.returncode == 0, r.stderr
    assert len(staged) == 1, f"expected 1 real region, got {staged}"
    assert not any(f.startswith("._") or "._" in f for f in staged)
    assert (out / "STRICTNESS_MANIFEST.tsv").exists()


def _minimal_db(path):
    c = sqlite3.connect(path)
    c.executescript(textwrap.dedent("""
        create table run(id integer primary key);
        create table gbk(id integer primary key, path text);
        create table bgc_record(id integer primary key, gbk_id int, nt_start int, nt_stop int, product text, category text);
        create table cds(id integer primary key, gbk_id int, nt_start int, nt_stop int);
        create table hsp(id integer primary key, cds_id int, accession text, env_start int, env_stop int, bit_score real);
        create table family(id integer primary key, newick text, cutoff real, bin_label text, run_id int);
        create table bgc_record_family(record_id int, family_id int);
    """))
    c.execute("insert into run(id) values (1)")
    # two strain BGCs + one MIBiG ref, all in one family (=> KNOWN)
    gbks = [(1, "AS-101_NODE_1_length_9_cov_1.region001.gbk"),
            (2, "AS-102_NODE_2_length_9_cov_2.region001.gbk"),
            (3, "BGC0000001.gbk")]
    c.executemany("insert into gbk(id,path) values (?,?)", gbks)
    for rid, gid in [(1, 1), (2, 2), (3, 3)]:
        c.execute("insert into bgc_record(id,gbk_id,nt_start,nt_stop,product) values (?,?,0,100,'NRPS')", (rid, gid))
    # a second, MIBiG-free family (=> NOVEL) with the same two strains
    c.execute("insert into gbk(id,path) values (4,'AS-101_NODE_9_length_9_cov_1.region002.gbk')")
    c.execute("insert into gbk(id,path) values (5,'AS-102_NODE_9_length_9_cov_2.region002.gbk')")
    c.execute("insert into bgc_record(id,gbk_id,nt_start,nt_stop,product) values (4,4,0,100,'halogenated')")
    c.execute("insert into bgc_record(id,gbk_id,nt_start,nt_stop,product) values (5,5,0,100,'halogenated')")
    # cds + hsp for record 4 (domain content)
    c.execute("insert into cds(id,gbk_id,nt_start,nt_stop) values (10,4,0,50)")
    for acc in ("PF01494", "PF04055"):
        c.execute("insert into hsp(cds_id,accession,env_start,env_stop,bit_score) values (10,?,0,50,99)", (acc,))
    # families
    c.execute("insert into family(id,newick,cutoff,bin_label,run_id) values (1,'(1:0.0,2:0.0,3:0.0);',0.5,'NRPS',1)")
    c.execute("insert into family(id,newick,cutoff,bin_label,run_id) values (2,'(4:0.0,5:0.0);',0.5,'other',1)")
    c.executemany("insert into bgc_record_family(record_id,family_id) values (?,?)",
                  [(1, 1), (2, 1), (3, 1), (4, 2), (5, 2)])
    c.commit(); c.close()


def test_known_novel_from_single_db(tmp_path):
    db = tmp_path / "mini.db"; _minimal_db(str(db))
    out = tmp_path / "kn.tsv"
    r = _run("bigscape_known_novel.py", "--db", str(db), "--out", str(out), "--run-id", "1", "--cutoff", "0.5")
    assert r.returncode == 0, r.stderr
    body = list(csv.DictReader(out.open(), delimiter="\t"))
    assert len(body) == 2  # two cross-strain families
    statuses = {row["status"] for row in body}
    assert statuses == {"KNOWN", "NOVEL"}
    # the KNOWN family reports its MIBiG match
    known = [row for row in body if row["status"] == "KNOWN"][0]
    assert "BGC0000001" in known["mibig_matches"]
    assert known["qualified_family_id"] == "bigscape-gcf:v1/run/1/cutoff/0.5/family/1"


def test_family_domains_surfaces_pfam(tmp_path):
    db = tmp_path / "mini.db"; _minimal_db(str(db))
    r = _run("bigscape_family_domains.py", "--db", str(db), "--run-id", "1", "--cutoff", "0.5",
             "--qualified-family", "bigscape-gcf:v1/run/1/cutoff/0.5/family/2")
    assert r.returncode == 0, r.stderr
    assert "PF01494" in r.stdout and "halogenase" in r.stdout.lower()
    assert "NOVEL" in r.stdout
