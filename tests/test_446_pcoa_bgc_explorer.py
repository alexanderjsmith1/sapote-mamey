"""tools/pcoa_bgc_explorer.py: BGC numbers only from a package built from the same antiSMASH result, BLASTp rows bound by
strain + locus + protein length (never by BGC number), dropped origins gone, delivered outputs never overwritten.
Synthetic strains only (tools/test_synthetic_ids.txt)."""
import csv
import importlib.util
import json
import re
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pcoa_bgc_explorer", ROOT / "tools" / "pcoa_bgc_explorer.py")
pbx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pbx)

PROT = {"ctg1_1": "MKVLAAGGTTRRSSAA", "ctg1_2": "MSTNPKLLLVVAA", "ctg2_1": "MAAAKKRRLLSS", "ctg5_1": "MPPQQRRSSTTVV"}


def gbk(record, start, end, product, cds):
    feats = [f"     region          1..900\n                     /contig_edge=\"False\"\n                     /product=\"{product}\""]
    for i, locus in enumerate(cds):
        feats.append(f"     CDS             {1 + i * 300}..{300 + i * 300}\n                     /gene_kind=\"biosynthetic\"\n"
                     f"                     /gene_functions=\"biosynthetic (rule-based-clusters) T1PKS: PKS_KS\"\n"
                     f"                     /locus_tag=\"{locus}\"\n                     /translation=\"{PROT[locus]}\"")
    seq = "a" * 900
    origin = "\n".join(f"{i + 1:>9} {seq[i:i + 60]}" for i in range(0, 900, 60))
    return (f"LOCUS       {record}  900 bp    DNA     linear   UNK 01-JAN-1980\nDEFINITION  test.\n"
            f"COMMENT     ##antiSMASH-Data-START##\n            Orig. start  :: {start}\n            Orig. end    :: {end}\n"
            f"            ##antiSMASH-Data-END##\nFEATURES             Location/Qualifiers\n" + "\n".join(feats)
            + f"\nORIGIN\n{origin}\n//\n")


def write_tsv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n"); w.writerow(header); w.writerows(rows)


def crosswalk(path, strain, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["strain", "bgc_id", "source_gbk", "start", "end"])
        for r in rows:
            w.writerow([strain, *r])


@pytest.fixture
def kit(tmp_path):
    reg = tmp_path / "regions/g"
    reg.mkdir(parents=True)
    (reg / "AS-900__NODE_1_length_5000_cov_9.0.region001.gbk").write_text(gbk("NODE_1", 100, 1000, "T1PKS", ["ctg1_1", "ctg1_2"]))
    (reg / "AS-900__NODE_2_length_4000_cov_9.0.region001.gbk").write_text(gbk("NODE_2", 0, 900, "NRPS", ["ctg2_1"]))
    (reg / "AS-901__NODE_5_length_3000_cov_9.0.region001.gbk").write_text(gbk("NODE_5", 50, 950, "terpene", ["ctg5_1"]))
    hdr = ["id", "PC1", "PC2", "PC3", "n_represented", "source", "group", "genus", "strain", "subtype", "region_product",
           "locus_tag", "origin", "length"]
    write_tsv(tmp_path / "kit/out_KS/PCOA_KS.tsv", hdr, [
        ["r1", "0.1", "0.2", "0", "3", "reference_held", "reference_held", "G", "Ref_one", "KS", "T1PKS", "x1", "Ref__a.gbk", "400"],
        ["s1", "0.0", "0.1", "0", "1", "SID_held", "SID_held", "G", "SID_one", "KS", "T1PKS", "x2", "SID__a.gbk", "400"],
        ["m1", "0.3", "0.1", "0", "1", "MIBiG", "MIBiG", "G", "BGC0000001", "KS", "T1PKS", "x3", "BGC0000001.gbk", "400"],
        ["i1", "0.2", "0.3", "0", "1", "isolate", "group_a", "G", "AS-900", "KS", "T1PKS", "ctg1_1",
         "AS-900__NODE_1_length_5000_cov_9.0.region001.gbk", "16"],
        ["i2", "0.4", "0.3", "0", "1", "isolate", "group_a", "G", "AS-900", "KS", "NRPS", "ctg2_1",
         "AS-900__NODE_2_length_4000_cov_9.0.region001.gbk", "12"],
        ["i3", "0.5", "0.5", "0", "1", "isolate", "group_a", "G", "AS-901", "KS", "terpene", "ctg5_1",
         "AS-901__NODE_5_length_3000_cov_9.0.region001.gbk", "13"]])
    write_tsv(tmp_path / "kit/out_KS/NEAREST_KS.tsv", ["id", "nearest_pident", "nearest_qcov", "nearest_strain", "nearest_source"],
              [["i1", "55.0", "90", "Ref_one", "reference_held"], ["i3", "88.0", "95", "Ref_one", "reference_held"]])
    (tmp_path / "kit/out_KS/RUN_KS.json").write_text(json.dumps({"pct_axes": [20.0, 10.0, 5.0], "approx_id": 70}))
    (tmp_path / "drop.txt").write_text("AS-900__NODE_2_length_4000_cov_9.0.region001.gbk\n")
    # AS-900: one package from the same result; AS-901: only a package of another run (an extra region)
    crosswalk(tmp_path / "pk/a/AS-900_2b_bgc_crosswalk.csv", "AS-900",
              [["BGC001", "NODE_1_length_5000_cov_9.0.region001.gbk", "100", "1000"],
               ["BGC002", "NODE_2_length_4000_cov_9.0.region001.gbk", "0", "900"]])
    crosswalk(tmp_path / "pk/b/AS-901_2b_bgc_crosswalk.csv", "AS-901",
              [["BGC001", "NODE_5_length_3000_cov_9.0.region001.gbk", "50", "950"],
               ["BGC002", "NODE_9_length_3000_cov_9.0.region001.gbk", "0", "900"]])
    db = sqlite3.connect(tmp_path / "snap.sqlite")
    db.execute("CREATE TABLE hits (strain TEXT, bgc_id TEXT, gene TEXT, aa_length INTEGER, channel TEXT, pct_identity REAL, "
               "query_coverage REAL, subject_organism TEXT, subject_def TEXT, evalue REAL, bitscore REAL, provenance_suspect INTEGER)")
    db.executemany("INSERT INTO hits VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", [
        ("AS-900", "BGC077", "ctg1_1", 16, "ncbi_nr", 91.0, 99.0, "Org a", "KS protein [Org a]", 1e-50, 300.0, 0),   # bound
        ("AS-900", "BGC001", "ctg1_2", 99, "ncbi_nr", 80.0, 99.0, "Org b", "wrong length", 1e-40, 200.0, 0),       # length differs
        ("AS-901", "BGC001", "ctg5_1", 13, "local_swissprot", 70.0, 90.0, "Org c", "suspect", 1e-30, 150.0, 1),    # suspect
        ("AS-123", "BGC001", "ctg1_1", 16, "ncbi_nr", 99.0, 99.0, "Org d", "other strain", 1e-60, 400.0, 0)])      # not ours
    db.commit(); db.close()
    return tmp_path


def run(kit, *extra):
    args = ["--kit", str(kit / "kit"), "--regions", str(kit / "regions"), "--out", str(kit / "out"),
            "--packages", str(kit / "pk"), "--drop-origins", str(kit / "drop.txt"), "--blastp-snapshot", str(kit / "snap.sqlite"),
            *extra]
    return pbx.main(args)


def js(path):
    text = Path(path).read_text()
    m = re.match(r'window\.__PBX&&__PBX\.put\(("[^"]+"),(.*)\);\n$', text, re.S)
    assert m, text[:80]
    return json.loads(m.group(2))


def test_aliases_need_a_package_from_the_same_result(kit):
    assert run(kit) == 0
    a900 = js(kit / "out/data/regions/AS-900.js")
    reg = a900["AS-900__NODE_1_length_5000_cov_9.0.region001.gbk"]
    assert reg["alias"] == "BGC001" and reg["alias_hold"] is None
    a901 = js(kit / "out/data/regions/AS-901.js")
    reg = a901["AS-901__NODE_5_length_3000_cov_9.0.region001.gbk"]
    assert reg["alias"] is None and "no package crosswalk" in reg["alias_hold"]


def test_dropped_origins_are_gone(kit):
    run(kit)
    data = js(kit / "out/data/sets/KS.js")
    assert data["dropped"] == 1
    assert not any(p[3] == "i" and p[10].startswith("AS-900__NODE_2") for p in data["pts"])
    assert "AS-900__NODE_2_length_4000_cov_9.0.region001.gbk" not in js(kit / "out/data/regions/AS-900.js")


def test_blastp_binds_by_locus_and_length_never_by_bgc_number(kit):
    run(kit)
    genes = {c[3]: c for reg in js(kit / "out/data/regions/AS-900.js").values() for c in reg["cds"]}
    assert genes["ctg1_1"][9]["nr"][0] == 91.0          # bound although the store calls it BGC077
    assert genes["ctg1_2"][9] == {}                      # length 99 against a 13 aa gene: not bound
    a901 = {c[3]: c for reg in js(kit / "out/data/regions/AS-901.js").values() for c in reg["cds"]}
    assert a901["ctg5_1"][9] == {}                       # provenance suspect: not bound
    receipt = json.loads((kit / "out/build_receipt.json").read_text())["summary"]["blastp_rows"]
    assert receipt["aa_length_mismatch"] == 1 and receipt["provenance_suspect"] == 1 and receipt["noncurrent_locus"] == 1


def test_two_disagreeing_packages_hold_the_strain(kit):
    crosswalk(kit / "pk/c/AS-900_2b_bgc_crosswalk.csv", "AS-900",
              [["BGC005", "NODE_1_length_5000_cov_9.0.region001.gbk", "100", "1000"],
               ["BGC006", "NODE_2_length_4000_cov_9.0.region001.gbk", "0", "900"]])
    run(kit)
    reg = js(kit / "out/data/regions/AS-900.js")["AS-900__NODE_1_length_5000_cov_9.0.region001.gbk"]
    assert reg["alias"] is None and "disagree" in reg["alias_hold"]


def test_refuses_to_overwrite_a_delivered_folder(kit):
    (kit / "out").mkdir()
    (kit / "out/index.html").write_text("delivered")
    assert run(kit) == 2
    assert (kit / "out/index.html").read_text() == "delivered"


def test_page_is_offline_and_names_no_strain(kit):
    run(kit)
    page = (kit / "out/index.html").read_text()
    assert "fetch(" not in page and not re.search(r"<script[^>]+src=\"https?:", page) and "fonts.googleapis" not in page
    for f in (ROOT / "tools/pcoa_bgc_explorer.py", ROOT / "tools/pcoa_bgc_explorer_template.html"):
        assert not re.search(r"\bA[JS]S?-\d", f.read_text()), f


def test_resistance_table(kit):
    write_tsv(kit / "kit/out_RES01/PCOA_RES01.tsv", ["id", "PC1", "PC2", "PC3", "n_represented", "source", "group", "genus",
                                                     "strain", "subtype", "region_product", "locus_tag", "origin", "length"],
              [["q1", "0", "0", "0", "1", "isolate", "group_a", "G", "AS-900", "efflux", "T1PKS", "ctg1_2",
                "AS-900__NODE_1_length_5000_cov_9.0.region001.gbk", "13"]])
    assert run(kit, "--resistance-prefix", "RES", "--group", "RES=Resistance families") == 0
    rows = list(csv.DictReader(open(kit / "out/resistance_genes_in_bgcs.tsv"), delimiter="\t"))
    assert len(rows) == 1 and rows[0]["identity"] == "AS-900 / NODE_1_length_5000_cov_9.0 / region001 / BGC001"
    index = js(kit / "out/data/index.js")
    assert {s["set"]: s["group"] for s in index["sets"]} == {"KS": "Protein classes", "RES01": "Resistance families"}


def test_outliers_are_scored_and_ranked(kit):
    assert run(kit) == 0
    rows = list(csv.DictReader(open(kit / "out/outliers.tsv"), delimiter="\t"))
    by = {r["strain"]: r for r in rows}
    assert "distant in sequence" in by["AS-900"]["tier"]          # best match 55% < 70
    assert "far" not in by["AS-900"]["tier"]
    assert "sequence" not in by["AS-901"]["tier"]                 # 88%: no sequence call
    assert rows[0]["strain"] == "AS-900" and rows[0]["rank"] == "1"
    assert by["AS-900"]["identity"].startswith("AS-900 / NODE_1_length_5000_cov_9.0 / region001 / BGC001")
    index = js(kit / "out/data/index.js")
    assert [o[2] for o in index["outliers"]][0] == "AS-900"
    assert js(kit / "out/data/sets/KS.js")["isolation"]
    assert by["AS-900"]["contig_length"] == "5000" and by["AS-900"]["contig_flag"] == ""


def test_no_study_vocabulary_in_the_tool():
    for f in ("tools/pcoa_bgc_explorer.py", "tools/pcoa_bgc_explorer_template.html"):
        t = (ROOT / f).read_text().lower()
        assert not re.search(r"\b(bees?|wasps?|moss|mosses|attines?|hymenoptera)\b", t), f


def test_dropped_region_files_do_not_block_a_package_built_without_them(kit):
    # the package of AS-900 lists only NODE_1; NODE_2 is on the drop list, so the package still binds
    crosswalk(kit / "pk/a/AS-900_2b_bgc_crosswalk.csv", "AS-900", [["BGC001", "NODE_1_length_5000_cov_9.0.region001.gbk", "100", "1000"]])
    run(kit)
    reg = js(kit / "out/data/regions/AS-900.js")["AS-900__NODE_1_length_5000_cov_9.0.region001.gbk"]
    assert reg["alias"] == "BGC001"


# ---- Task 198 review: F2 repeated locus tags, F3 strain field, F4 identical sequences ----------------------------------
def _extra_region(kit, node, locus, protein, pc_id):
    """Add one AS-900 region file with a single CDS carrying `protein`, plus a PCoA point that uses it."""
    fn = f"AS-900__{node}_length_3000_cov_9.0.region001.gbk"
    text = gbk(node, 0, 900, "T1PKS", ["ctg1_1"]).replace('/locus_tag="ctg1_1"', f'/locus_tag="{locus}"')
    text = text.replace(f'/translation="{PROT["ctg1_1"]}"', f'/translation="{protein}"')
    (kit / "regions/g" / fn).write_text(text)
    pc = kit / "kit/out_KS/PCOA_KS.tsv"
    with open(pc, "a", newline="") as fh:
        csv.writer(fh, delimiter="\t", lineterminator="\n").writerow(
            [pc_id, "0.6", "0.6", "0", "1", "isolate", "group_a", "G", "AS-900", "KS", "T1PKS", locus, fn, str(len(protein))])
    return fn


def test_crosswalk_rows_naming_another_strain_are_held(kit):
    crosswalk(kit / "pk/a/AS-900_2b_bgc_crosswalk.csv", "AS-123",          # right file name, wrong strain in every row
              [["BGC001", "NODE_1_length_5000_cov_9.0.region001.gbk", "100", "1000"],
               ["BGC002", "NODE_2_length_4000_cov_9.0.region001.gbk", "0", "900"]])
    assert run(kit) == 0
    reg = js(kit / "out/data/regions/AS-900.js")["AS-900__NODE_1_length_5000_cov_9.0.region001.gbk"]
    assert reg["alias"] is None and "different strain" in reg["alias_hold"]


def test_a_locus_tag_naming_two_proteins_gets_no_blastp_hit(kit):
    _extra_region(kit, "NODE_3", "ctg1_1", "MKVLAAGGTTRR", "i4")            # same tag, 12 aa, different protein
    assert run(kit) == 0
    regs = js(kit / "out/data/regions/AS-900.js")
    hits = [c[9] for reg in regs.values() for c in reg["cds"] if c[3] == "ctg1_1"]
    assert len(hits) == 2 and all(h == {} for h in hits)
    assert "AS-900\tctg1_1" in (kit / "out/BLASTP_LOCUS_HOLDS.tsv").read_text()
    receipt = json.loads((kit / "out/build_receipt.json").read_text())["summary"]["blastp_rows"]
    assert receipt["locus_tag_conflict_held"] == 1


def test_an_exact_sequence_row_reaches_every_gene_with_that_sequence(kit):
    import hashlib
    _extra_region(kit, "NODE_3", "ctg3_1", PROT["ctg1_1"], "i4")            # a second gene, identical protein
    db = sqlite3.connect(kit / "snap.sqlite")
    db.execute("CREATE TABLE clusterednr_exact_locus_admission (query_sequence_sha256 TEXT, channel TEXT, pct_identity REAL, "
               "query_coverage_pct_derived REAL, subject_organism TEXT, subject_definition TEXT, evalue REAL, bitscore REAL)")
    db.execute("INSERT INTO clusterednr_exact_locus_admission VALUES (?,?,?,?,?,?,?,?)",
               (hashlib.sha256(PROT["ctg1_1"].encode()).hexdigest(), "ncbi_nr", 97.0, 100.0, "Org e", "exact", 1e-80, 900.0))
    db.commit(); db.close()
    assert run(kit) == 0
    genes = {c[3]: c for reg in js(kit / "out/data/regions/AS-900.js").values() for c in reg["cds"]}
    assert genes["ctg1_1"][9]["nr"][0] == 97.0 and genes["ctg3_1"][9]["nr"][0] == 97.0
    receipt = json.loads((kit / "out/build_receipt.json").read_text())["summary"]["blastp_rows"]
    assert receipt["exact_sequence"] == 2
