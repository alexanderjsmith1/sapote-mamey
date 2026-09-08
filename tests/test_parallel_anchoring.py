"""Fixture tests for bigscape_mibig_anchors.py + bigscape_merge_anchors.py (no real BiG-SCAPE run).

Builds a tiny SQLite DB mimicking BiG-SCAPE's schema with one strain BGC and one MIBiG BGC in the
same family, checks the extractor emits the 5-col anchor TSV with a clean node.region locator, and
checks the merge unions overlapping edges and tags KNOWN/NOVEL correctly.
"""
import os, sqlite3, subprocess, sys, tempfile, pathlib

HERE = pathlib.Path(__file__).resolve().parent
ANCHORS = HERE.parent / "tools" / "bigscape_mibig_anchors.py"
MERGE = HERE.parent / "tools" / "bigscape_merge_anchors.py"


def _make_db(path):
    c = sqlite3.connect(path)
    c.executescript("""
      create table run(id integer primary key, cutoff real);
      create table gbk(id integer primary key, path text);
      create table bgc_record(id integer primary key, gbk_id int, product text, category text);
      create table family(id integer primary key, run_id int, cutoff real, bin_label text);
      create table bgc_record_family(record_id int, family_id int);
    """)
    # one strain BGC (dotted coverage) + one MIBiG BGC, same family
    c.execute("insert into gbk values (1,'AS-311_NODE_107_length_28859_cov_19.006984.region001.gbk')")
    c.execute("insert into gbk values (2,'BGC0000034.gbk')")
    c.execute("insert into bgc_record values (1,1,'T1PKS','PKS')")
    c.execute("insert into bgc_record values (2,2,'T1PKS','PKS')")
    c.execute("insert into family values (10,1,0.5,'PKS')")
    c.execute("insert into bgc_record_family values (1,10)")
    c.execute("insert into bgc_record_family values (2,10)")
    c.commit()


def test_extractor_emits_clean_locator():
    with tempfile.TemporaryDirectory() as t:
        db = os.path.join(t, "chat.db"); out = os.path.join(t, "a.tsv")
        _make_db(db)
        subprocess.run([sys.executable, str(ANCHORS), "--db", db, "--out", out,
                        "--run-id", "1", "--cutoff", "0.5"], check=True)
        lines = open(out).read().splitlines()
        assert lines[0].split("\t") == ["run_id", "normalized_cutoff", "family_id", "qualified_family_id",
                                           "gcf_namespace", "strain", "node_region", "mibig_accession", "mibig_product"]
        row = lines[1].split("\t")
        assert row[5] == "AS-311"
        assert row[6] == "NODE_107_length_28859_cov_19.006984.region001"  # clean, dotted-cov OK
        assert row[7] == "BGC0000034"


def test_merge_unions_and_tags():
    with tempfile.TemporaryDirectory() as t:
        # two chat anchor TSVs, overlapping on the same edge (should dedup)
        a1 = os.path.join(t, "c1.tsv"); a2 = os.path.join(t, "c2.tsv")
        hdr = "run_id\tnormalized_cutoff\tfamily_id\tqualified_family_id\tgcf_namespace\tstrain\tnode_region\tmibig_accession\tmibig_product\n"
        prefix = "1\t0.5\t10\tbigscape-gcf:v1/run/1/cutoff/0.5/family/10\trun_id=1;cutoff=0.5\t"
        open(a1, "w").write(hdr + prefix + "AS-311\tNODE_107_length_28859_cov_19.006984.region001\tBGC0000034\tT1PKS\n")
        open(a2, "w").write(hdr + prefix + "AS-311\tNODE_107_length_28859_cov_19.006984.region001\tBGC0000034\tT1PKS\n"
                                 + prefix + "AS-311\tNODE_107_length_28859_cov_19.006984.region001\tBGC0000042\tT1PKS\n")
        base = os.path.join(t, "base.tsv")
        open(base, "w").write(
            "cutoff\tfamily_id\trun_id\tnormalized_cutoff\tqualified_family_id\tgcf_namespace\tn_strains\tstrains\tn_members\tbin\tdominant_product\tcontains_MIBiG\tmembers_locators\n"
            "0.5\t10\t1\t0.5\tbigscape-gcf:v1/run/1/cutoff/0.5/family/10\trun_id=1;cutoff=0.5\t2\tAS-311,AS-421\t2\tPKS\tT1PKS\tno\tAS-311:NODE_107_length_28859_cov_19.006984.region001;AS-421:NODE_9_length_5_cov_1.0.region001\n"
            "0.5\t11\t1\t0.5\tbigscape-gcf:v1/run/1/cutoff/0.5/family/11\trun_id=1;cutoff=0.5\t2\tAS-190,AS-424\t2\tsacch\tsaccharide\tno\tAS-190:NODE_1_length_9_cov_2.0.region001;AS-424:NODE_2_length_8_cov_3.0.region001\n")
        out = os.path.join(t, "kn.tsv")
        subprocess.run([sys.executable, str(MERGE), "--anchors", a1, a2,
                        "--base-cross-strain", base, "--out", out], check=True)
        rows = [r.split("\t") for r in open(out).read().splitlines()[1:]]
        by_fam = {r[1]: r for r in rows}
        assert by_fam["10"][-3] == "KNOWN"   # fam 10 has the anchored AS-311 member
        assert by_fam["11"][-3] == "NOVEL"   # fam 11 has no anchored member
        assert by_fam["10"][-1] == "BGC0000034;BGC0000042"  # unioned across the two chat TSVs
