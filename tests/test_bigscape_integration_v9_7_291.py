"""test_bigscape_integration_v9_7_291.py

Self-contained tests for bigscape_ingest_to_mamey.py: builds a minimal BiG-SCAPE-2-shaped
SQLite DB (a KNOWN family with a MIBiG ref + two strains, and a NOVEL family), a triage board
that bridges BGC number -> node.region, and two Mode B card stubs, then verifies the ingest
writes a correct, idempotent, capacity-worded GCF context block onto the right card.
"""
import os, sqlite3, tempfile, importlib.util, textwrap

HERE = os.path.dirname(__file__)
TOOL = os.path.join(HERE, "..", "tools", "bigscape_ingest_to_mamey.py")
spec = importlib.util.spec_from_file_location("ingest", TOOL)
ingest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingest)


def _build_db(path):
    c = sqlite3.connect(path)
    c.executescript(
        """
        create table run(id integer primary key);
        create table gbk(id integer primary key, path text);
        create table bgc_record(id integer primary key, gbk_id integer, record_type text);
        create table family(id integer primary key, run_id integer, cutoff real);
        create table bgc_record_family(record_id integer, family_id integer);
        create table distance(record_a_id integer, record_b_id integer, distance real);
        """
    )
    c.execute("insert into run(id) values (1)")
    # gbk + records: two strain BGCs + one MIBiG in a KNOWN family; one strain BGC in a NOVEL family
    rows = [
        (1, "AS-705_NODE_1_length_100.region001.gbk"),   # known-family strain A
        (2, "SID3343_NODE_9_length_200.region002.gbk"),  # known-family strain B
        (3, "BGC0000271.gbk"),                            # MIBiG ref in known family
        (4, "AS-705_NODE_2_length_50.region003.gbk"),    # novel-family strain A
    ]
    for gid, p in rows:
        c.execute("insert into gbk(id,path) values (?,?)", (gid, p))
        c.execute("insert into bgc_record(id,gbk_id,record_type) values (?,?, 'region')", (gid, gid))
    # families at cutoff 0.5: fam 10 = KNOWN (records 1,2,3), fam 11 = NOVEL (record 4)
    c.execute("insert into family(id,run_id,cutoff) values (10,1,0.5)")
    c.execute("insert into family(id,run_id,cutoff) values (11,1,0.5)")
    for rid in (1, 2, 3):
        c.execute("insert into bgc_record_family(record_id,family_id) values (?,10)", (rid,))
    c.execute("insert into bgc_record_family(record_id,family_id) values (4,11)")
    # distances: strain A (rec1) near MIBiG (rec3); novel rec4 far from MIBiG
    c.execute("insert into distance values (1,3,0.20)")
    c.execute("insert into distance values (4,3,0.95)")
    c.commit(); c.close()


def _build_pkg(root):
    cards = os.path.join(root, "cards"); os.makedirs(cards, exist_ok=True)
    with open(os.path.join(root, "triage_board.csv"), "w") as fh:
        fh.write("strain,bgc,locator,product\n")
        fh.write("AS-705,BGC001,NODE_1_length_100.region001,T2PKS\n")
        fh.write("SID3343,BGC002,NODE_9_length_200.region002,T2PKS\n")
        fh.write("AS-705,BGC003,NODE_2_length_50.region003,other\n")
    for name, body in [
        ("AS-705_BGC001_ModeB.md", "# AS-705 BGC001\n\n## §8 Comparator/KCB interpretation\n\nKCB partial.\n\n## §9 x\n"),
        ("AS-705_BGC003_ModeB.md", "# AS-705 BGC003\n\n## §8 Comparator/KCB interpretation\n\nno KCB hit.\n\n## §9 x\n"),
    ]:
        with open(os.path.join(cards, name), "w") as fh:
            fh.write(body)
    return cards


def test_ingest_known_and_novel(tmp_path=None):
    d = tempfile.mkdtemp()
    db = os.path.join(d, "anchored.db")
    _build_db(db)
    _build_pkg(d)
    names = {}  # no index -> compound names show as accessions; fine for the test
    ctx = ingest.gcf_context(db, "0.5", names, run_id="1")
    # known-family strain BGC (AS-705:...region001) present, KNOWN, anchors to BGC0000271
    kkey = "AS-705:NODE_1_length_100.region001"
    assert kkey in ctx, ctx.keys()
    assert ctx[kkey]["status"] == "KNOWN"
    assert any(a == "BGC0000271" for a, _ in ctx[kkey]["mibig"])
    assert "SID3343" in ctx[kkey]["cross_strain_members"]
    assert ctx[kkey]["nearest_mibig"][2] == 0.20
    # novel-family strain BGC is NOVEL with no anchor
    nkey = "AS-705:NODE_2_length_50.region003"
    assert ctx[nkey]["status"] == "NOVEL"
    assert ctx[nkey]["mibig"] == []

    # run the CLI end to end
    import sys
    argv = sys.argv[:]
    sys.argv = ["x", "--db", db, "--package", d, "--run-id", "1", "--cutoff", "0.5"]
    try:
        ingest.main()
    finally:
        sys.argv = argv
    known_card = os.path.join(d, "cards", "AS-705_BGC001_ModeB.md")
    txt = open(known_card).read()
    assert ingest.BEGIN in txt and ingest.END in txt
    assert "**KNOWN**" in txt
    assert "BGC0000271" in txt
    assert "capacity" in txt.lower()  # discipline wording present
    # idempotent
    sys.argv = ["x", "--db", db, "--package", d, "--run-id", "1", "--cutoff", "0.5"]
    try:
        ingest.main()
    finally:
        sys.argv = argv
    assert open(known_card).read().count(ingest.BEGIN) == 1

    novel_card = open(os.path.join(d, "cards", "AS-705_BGC003_ModeB.md")).read()
    assert "**NOVEL**" in novel_card
    print("PASS test_ingest_known_and_novel")


if __name__ == "__main__":
    test_ingest_known_and_novel()
