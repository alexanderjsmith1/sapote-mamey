"""test_bigscape_integration_v9_7_292.py

Regression tests for the v9.7.292 join fixes in bigscape_ingest_to_mamey.py. The v9.7.291
test used an idealized triage board (had a `strain` column, a clean `locator` column, no
coverage in the node name) and so never exercised the real Mamey triage format -- which is
why the join silently produced ZERO matches on a real package. These tests use the REAL
shape:
  - triage board with NO strain column,
  - locator carried as Contig + antiSMASH_Region (not an explicit `locator` column),
  - coverage present in the node name, INCLUDING a leading-zero cov (cov_73.020183) that the
    engine renders lossily as cov_73.20183,
  - the trap `Assembly_Locator` display column ("NODE_.. region001 (BGC###)") present.
"""
import os, sqlite3, tempfile, importlib.util, sys

HERE = os.path.dirname(__file__)
TOOL = os.path.join(HERE, "..", "tools", "bigscape_ingest_to_mamey.py")
spec = importlib.util.spec_from_file_location("ingest", TOOL)
ingest = importlib.util.module_from_spec(spec); spec.loader.exec_module(ingest)


def test_canon_locator_is_cov_independent():
    full  = "NODE_402_length_4883_cov_73.020183.region001"   # DB/TSV form (correct)
    engbug= "NODE_402_length_4883_cov_73.20183.region001"    # triage form (leading-zero dropped)
    nodeid= "NODE_402_length_4883_cov_73.region001"          # Node_ID form (cov int only)
    want  = "NODE_402_length_4883.region001"
    assert ingest.canon_locator(full)   == want
    assert ingest.canon_locator(engbug) == want, "leading-zero cov must not change the key"
    assert ingest.canon_locator(nodeid) == want
    print("PASS test_canon_locator_is_cov_independent")


def test_load_triage_realistic_strainless_board():
    d = tempfile.mkdtemp()
    tb = os.path.join(d, "AS-705_4_triage_board.csv")
    with open(tb, "w") as fh:
        # real column order; NO strain column; Assembly_Locator is the display trap
        fh.write("Rank,Assembly_Locator,BGC_ID,Contig,Node_ID,antiSMASH_Region\n")
        fh.write("1,NODE_275_length_8783_cov_79 region001 (BGC025),BGC025,"
                 "NODE_275_length_8783_cov_79.456007,NODE_275_length_8783_cov_79,region001\n")
        # leading-zero cov row -- the one that broke cov-exact joins
        fh.write("5,NODE_402_length_4883_cov_73 region001 (BGC039),BGC039,"
                 "NODE_402_length_4883_cov_73.20183,NODE_402_length_4883_cov_73,region001\n")
    bridge = ingest.load_triage(tb)
    # strain-less board -> key ("", num); locator canon'd from Contig+Region, cov-free
    assert bridge[("", "25")] == "NODE_275_length_8783.region001", bridge
    assert bridge[("", "39")] == "NODE_402_length_4883.region001", bridge
    # and it must NOT have used the display Assembly_Locator (which has spaces + "(BGC###)")
    assert all("(" not in v and " " not in v for v in bridge.values())
    print("PASS test_load_triage_realistic_strainless_board")


def _build_db(path):
    c = sqlite3.connect(path)
    c.executescript(
        "create table run(id integer primary key);"
        "create table gbk(id integer primary key, path text);"
        "create table bgc_record(id integer primary key, gbk_id integer, record_type text);"
        "create table family(id integer primary key, run_id integer, cutoff real);"
        "create table bgc_record_family(record_id integer, family_id integer);"
        "create table distance(record_a_id integer, record_b_id integer, distance real);")
    c.execute("insert into run(id) values (1)")
    rows = [
        (1, "AS-705_NODE_275_length_8783_cov_79.456007.region001.gbk"),  # KNOWN fam, strain A
        (2, "AS-810_NODE_9_length_200_cov_40.5.region002.gbk"),          # KNOWN fam, strain B
        (3, "BGC0000271.gbk"),                                           # MIBiG ref
        (4, "AS-705_NODE_402_length_4883_cov_73.020183.region001.gbk"),  # NOVEL fam, leading-zero cov
    ]
    for gid, p in rows:
        c.execute("insert into gbk(id,path) values (?,?)", (gid, p))
        c.execute("insert into bgc_record(id,gbk_id,record_type) values (?,?,'region')", (gid, gid))
    c.execute("insert into family(id,run_id,cutoff) values (10,1,0.5)")
    c.execute("insert into family(id,run_id,cutoff) values (11,1,0.5)")
    for rid in (1, 2, 3):
        c.execute("insert into bgc_record_family(record_id,family_id) values (?,10)", (rid,))
    c.execute("insert into bgc_record_family(record_id,family_id) values (4,11)")
    c.execute("insert into distance values (1,3,0.20)")
    c.execute("insert into distance values (4,3,0.95)")
    c.commit(); c.close()


def _triage_and_cards(root):
    tb = os.path.join(root, "AS-705_4_triage_board.csv")
    with open(tb, "w") as fh:
        fh.write("Rank,Assembly_Locator,BGC_ID,Contig,Node_ID,antiSMASH_Region\n")
        fh.write("1,x,BGC025,NODE_275_length_8783_cov_79.456007,NODE_275_length_8783_cov_79,region001\n")
        # triage carries the ENGINE-CORRUPTED cov here; DB carries the correct one -> must still join
        fh.write("5,x,BGC039,NODE_402_length_4883_cov_73.20183,NODE_402_length_4883_cov_73,region001\n")
    cards = os.path.join(root, "cards"); os.makedirs(cards, exist_ok=True)
    for n, b in [("AS-705_BGC025_ModeB.md", "# c\n\n## §8 Comparator/KCB interpretation\n\nk.\n\n## §9 x\n"),
                 ("AS-705_BGC039_ModeB.md", "# c\n\n## §8 Comparator/KCB interpretation\n\nk.\n\n## §9 x\n")]:
        open(os.path.join(cards, n), "w").write(b)
    return tb, cards


def test_end_to_end_real_triage_shape():
    d = tempfile.mkdtemp()
    db = os.path.join(d, "anchored.db"); _build_db(db)
    tb, cards = _triage_and_cards(d)
    argv = sys.argv[:]
    sys.argv = ["x", "--db", db, "--triage", tb, "--cards-dir", cards,
                "--run-id", "1", "--cutoff", "0.5"]
    try:
        ingest.main()
    finally:
        sys.argv = argv
    known = open(os.path.join(cards, "AS-705_BGC025_ModeB.md")).read()
    novel = open(os.path.join(cards, "AS-705_BGC039_ModeB.md")).read()
    # KNOWN card joined (this is the 0->N regression) with co-member AS-810
    assert "**KNOWN**" in known and "AS-810" in known, known
    # NOVEL card joined DESPITE the triage cov being corrupted vs the DB cov
    assert "**NOVEL**" in novel, novel
    assert known.count(ingest.BEGIN) == 1
    print("PASS test_end_to_end_real_triage_shape")


def test_from_tsv_path_states_comembers_unavailable():
    d = tempfile.mkdtemp()
    tsv = os.path.join(d, "AS_per_BGC_annotation.tsv")
    with open(tsv, "w") as fh:
        fh.write("strain\tlocator\tantismash_class\tfamily_status\tMIBiG_family_anchors\tnearest_MIBiG\tnearest_distance\n")
        fh.write("AS-705\tNODE_11_length_51215_cov_55.161915.region001\tphenazine\tKNOWN\t"
                 "BGC0002010 (streptophenazine B)\tBGC0002010 (streptophenazine B)\t0.318\n")
    tb, cards = _triage_and_cards(d)
    # add a BGC004 card + triage row matching the TSV locator
    with open(tb, "a") as fh:
        fh.write("2,x,BGC004,NODE_11_length_51215_cov_55.161915,NODE_11_length_51215_cov_55,region001\n")
    open(os.path.join(cards, "AS-705_BGC004_ModeB.md"), "w").write(
        "# c\n\n## §8 Comparator/KCB interpretation\n\nk.\n\n## §9 x\n")
    argv = sys.argv[:]
    sys.argv = ["x", "--from-tsv", tsv, "--strain", "AS-705", "--triage", tb, "--cards-dir", cards, "--cutoff", "0.5"]
    try:
        ingest.main()
    finally:
        sys.argv = argv
    txt = open(os.path.join(cards, "AS-705_BGC004_ModeB.md")).read()
    assert "**KNOWN**" in txt and "streptophenazine B" in txt
    assert "unavailable from the portable export" in txt, "TSV path must be honest about co-members"
    print("PASS test_from_tsv_path_states_comembers_unavailable")


if __name__ == "__main__":
    test_canon_locator_is_cov_independent()
    test_load_triage_realistic_strainless_board()
    test_end_to_end_real_triage_shape()
    test_from_tsv_path_states_comembers_unavailable()
    print("ALL PASS")
