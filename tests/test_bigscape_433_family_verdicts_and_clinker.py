"""BIGSCAPE_433 — family verdicts and clinker pages from a BiG-SCAPE 2 database.

A synthetic database with one query strain (two regions), one SID-layer, one TYPE-layer, one stem__region and one
MIBiG record checks: layer classification from file names; verdicts per family (private dark, private MIBiG-matched,
shared, MIBiG-and-ref) with the cross_strain flag; the placement denominator table; the clinker payload (tracks,
classes, shared orthogroups, private flag) and the HTML page; no cohort literal in the tools.
"""
import importlib.util
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


FILES = {1: "QRY-1_NODE_1_length_9000_cov_1.0.region001.gbk", 2: "QRY-1_NODE_2_length_9000_cov_1.0.region001.gbk",
         3: "QRY-2_NODE_7_length_9000_cov_1.0.region002.gbk", 4: "SID_SID9_WWAA01000001.1.region001.gbk",
         5: "TYPE_Genus_typicus_CP000001.1.region001.gbk", 6: "Genus_other__GCF_1__NZ_A01.1.region001.gbk", 7: "BGC0000001.gbk"}
# families at 0.3: 10 = {1,3} private dark cross-strain; 11 = {2,7} private MIBiG-matched; 12 = {3,4} shared; 13 = {1,6,7} MIBiG and ref; record 5 is a singleton at 0.3
FAMS = {10: [1, 3], 11: [2, 7], 12: [3, 4], 13: [1, 6, 7]}


def _db(tmp_path):
    p = tmp_path / "t.db"; con = sqlite3.connect(p)
    con.executescript("""
    create table gbk(id integer primary key, path text, organism text);
    create table bgc_record(id integer primary key, gbk_id int, record_type text, product text, nt_start int, nt_stop int);
    create table family(id integer primary key, cutoff real, newick text);
    create table bgc_record_family(record_id int, family_id int);
    create table cds(id integer primary key, gbk_id int, nt_start int, nt_stop int, orf_num int, strand int, gene_kind text, aa_seq text);
    create table hsp(cds_id int, accession text, bit_score real);""")
    for gid, f in FILES.items():
        con.execute("insert into gbk values (?,?,?)", (gid, f"/x/gbk_input/{f}", "Genus sp." if gid != 5 else "."))
        con.execute("insert into bgc_record values (?,?,?,?,?,?)", (gid, gid, "region", "T1PKS", 0, 9000))
        con.execute("insert into bgc_record values (?,?,?,?,?,?)", (gid + 100, gid, "protocluster", "T1PKS", 0, 9000))
        for k in range(3):
            cid = gid * 10 + k
            start, strand = ((2 - k) * 1000, -1) if gid == 3 else (k * 1000, 1)      # record 3 is annotated on the other strand
            con.execute("insert into cds values (?,?,?,?,?,?,?,?)", (cid, gid, start, start + 800, k, strand, "biosynthetic", "M" * 200))
            con.execute("insert into hsp values (?,?,?)", (cid, f"PF0000{k}", 50.0))
    for fid, rids in FAMS.items():
        con.execute("insert into family values (?,?,?)", (fid, 0.3, "(1:0.1,2:0.1);"))
        for rid in rids:
            con.execute("insert into bgc_record_family values (?,?)", (rid, fid))
    con.execute("insert into family values (20, 0.7, '(1:0.1,2:0.1);')")
    for rid in (1, 2, 3, 4, 5, 6, 7):
        con.execute("insert into bgc_record_family values (?,20)", (rid,))
    con.commit(); con.close()
    return p


def test_classify_layers_from_file_names():
    V = _load("bigscape_family_verdicts")
    import re
    rx = re.compile(r"^([A-Za-z]+-\d+)_"); pre = ("SID_", "TYPE_")
    assert V.classify(FILES[1], rx, pre) == ("query", "QRY-1")
    assert V.classify(FILES[4], rx, pre) == ("SID", None) and V.classify(FILES[5], rx, pre) == ("TYPE", None)
    assert V.classify(FILES[6], rx, pre) == ("REF", None) and V.classify(FILES[7], rx, pre) == ("MIBiG", None)


def test_verdicts_cross_strain_and_placement(tmp_path):
    V = _load("bigscape_family_verdicts")
    out = tmp_path / "v.tsv"
    assert V.main([str(_db(tmp_path)), str(out), "--cutoff", "0.3"]) == 0
    rows = {int(r.split("\t")[0]): r.split("\t") for r in out.read_text().splitlines()[1:]}
    hdr = out.read_text().splitlines()[0].split("\t"); V_ = hdr.index("verdict"); X = hdr.index("cross_strain"); L = hdr.index("layer_counts")
    assert rows[10][V_] == "QUERY_PRIVATE_REFERENCE_DARK" and rows[10][X] == "yes"
    assert rows[11][V_] == "QUERY_PRIVATE_MIBIG_MATCHED" and rows[11][X].startswith("no")
    assert rows[12][V_] == "QUERY_SHARED_REFERENCE" and rows[12][L] == "SID=1"
    assert rows[13][V_] == "QUERY_MIBIG_AND_REF" and rows[13][L] == "MIBiG=1;REF=1"
    plc = [r.split("\t") for r in (tmp_path / "v.tsv.placement.tsv").read_text().splitlines()[1:]]
    assert plc[0][:4] == ["0.3", "7", "6", "1"] and plc[1][:4] == ["0.7", "7", "7", "0"]   # region denominator, never protoclusters


def test_clinker_payload_and_page(tmp_path):
    C = _load("bigscape_clinker_html")
    db = _db(tmp_path); out = tmp_path / "figs"
    assert C.main(["--db", str(db), "--out", str(out), "--family", "10", "12"]) == 0
    html = (out / "GCF10_c0.3_clinker.html").read_text()
    assert '"private":true' in html and '"cls":"query"' in html and "query-private" in html
    html12 = (out / "GCF12_c0.3_clinker.html").read_text()
    assert '"private":false' in html12 and '"cls":"SID"' in html12
    import json
    payload = json.loads(html.split("const DATA=", 1)[1].split(";const NS", 1)[0])
    flipped = {tr["strain"]: tr.get("flipped", False) for tr in payload["tracks"]}
    assert flipped == {"QRY-1": False, "QRY-2": True}                # the reversed track is shown reverse-complemented
    q2 = next(tr for tr in payload["tracks"] if tr["strain"] == "QRY-2")
    assert [g["og"] for g in q2["genes"]] == ["PF00000", "PF00001", "PF00002"] and all(g["strand"] == 1 for g in q2["genes"])
    idx = (out / "CLINKER_INDEX.tsv").read_text().splitlines()
    assert len(idx) == 3 and "\tquery=2\t" in idx[1] and "3\t" in idx[1]        # 3 shared orthogroups


def test_tools_have_no_cohort_literal():
    for name in ("bigscape_family_verdicts.py", "bigscape_family_figures.py", "bigscape_clinker_html.py", "bigscape_launch.sh"):
        assert "AS-" not in (ROOT / "tools" / name).read_text(), name


def test_bigscape_tsv_exports_neutralise_formula_leading_product(tmp_path):
    db = _db(tmp_path)
    payload = '=HYPERLINK("https://example.invalid", "x")'
    con = sqlite3.connect(db)
    con.execute("update bgc_record set product=? where id=1", (payload,))
    con.commit(); con.close()

    verdict = _load("bigscape_family_verdicts")
    verdict_out = tmp_path / "verdict.tsv"
    assert verdict.main([str(db), str(verdict_out), "--cutoff", "0.3"]) == 0
    with verdict_out.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    assert any(row["query_products"].startswith("'" + payload) for row in rows)

    clinker = _load("bigscape_clinker_html")
    out = tmp_path / "clinker"
    assert clinker.main(["--db", str(db), "--out", str(out), "--focus", "QRY-1"]) == 0
    with (out / "strain_focus" / "QRY-1" / "CLINKER_INDEX.tsv").open(newline="", encoding="utf-8") as fh:
        index = list(csv.DictReader(fh, delimiter="\t"))
    assert any(row["strain_product"].startswith("'" + payload) for row in index)

    figures = _load("bigscape_family_figures")
    figures_out = tmp_path / "figures.tsv"
    figures.write_tsv(figures_out, [{"product": payload}], ["product"])
    with figures_out.open(newline="", encoding="utf-8") as fh:
        assert next(csv.DictReader(fh, delimiter="\t"))["product"] == "'" + payload
