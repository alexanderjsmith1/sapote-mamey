"""Card 6275a90d_449_pcoa_explorer_3d_view: the rotatable 3D view, point labels, the genus filter, cohort colours and the
identity code of tools/pcoa_bgc_explorer.py and its page template.

The page logic that matters for correctness (projection, identity code, labels, genus filter) sits in one DOM-free block of
the template, between the PBX3-PURE markers. These tests run that block with Node, or with osascript (JavaScript) on macOS,
and skip with a reason when neither is present. Synthetic strains only (tools/test_synthetic_ids.txt)."""
from __future__ import annotations

import csv
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "tools" / "pcoa_bgc_explorer_template.html"
spec = importlib.util.spec_from_file_location("pcoa_bgc_explorer_3d", ROOT / "tools" / "pcoa_bgc_explorer.py")
pbx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pbx)

HDR = ["id", "PC1", "PC2", "PC3", "n_represented", "source", "group", "genus", "strain", "subtype", "region_product",
       "locus_tag", "origin", "length"]
ROWS = [
    ["r1", "0.10", "0.20", "0.05", "3", "reference_held", "reference_held", "Gone", "Ref_one_genome", "KS", "T1PKS", "x1",
     "Ref_one_genome__ctg1.region001.gbk", "400"],
    ["s1", "0.00", "0.10", "-0.20", "1", "SID_held", "SID_held", "Gone", "SID_one", "KS", "T1PKS", "x2",
     "SID_one__WWAA01000001.1.region001.gbk", "400"],
    ["m1", "0.30", "0.10", "0.40", "1", "MIBiG", "MIBiG", "", "BGC0000001", "KS", "T1PKS", "abyB1", "BGC0000001.gbk", "400"],
    ["i1", "0.20", "0.30", "0.10", "1", "isolate", "group_a", "Gone", "AS-900", "KS", "T1PKS", "ctg1_1",
     "AS-900__NODE_1_length_5000_cov_9.0.region001.gbk", "16"],
    ["i2", "0.40", "0.30", "-0.10", "1", "isolate", "group_a", "Gone", "AS-901", "KS", "NRPS", "ctg2_1",
     "AS-901__NODE_2_length_4000_cov_9.0.region001.gbk", "12"],
    ["i3", "0.50", "0.50", "0.30", "1", "isolate", "group_b", "Gone", "AS-902", "KS", "terpene", "ctg5_1",
     "AS-902__NODE_5_length_3000_cov_9.0.region001.gbk", "13"],
]


def _tsv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n"); w.writerow(header); w.writerows(rows)


@pytest.fixture
def kit(tmp_path):
    _tsv(tmp_path / "kit/out_KS/PCOA_KS.tsv", HDR, ROWS)
    # i3 has no NEAREST row, so it has no identity value
    _tsv(tmp_path / "kit/out_KS/NEAREST_KS.tsv", ["id", "nearest_pident", "nearest_qcov", "nearest_strain", "nearest_source"],
         [["i1", "55.0", "90", "Ref_one_genome", "reference_held"], ["i2", "88.0", "95", "Ref_one_genome", "reference_held"]])
    (tmp_path / "kit/out_KS/RUN_KS.json").write_text(json.dumps({"pct_axes": [20.0, 10.0, 5.0], "approx_id": 70}))
    (tmp_path / "regions").mkdir()
    (tmp_path / "mibig.json").write_text(json.dumps({"entries": [
        {"accession": "BGC0000001", "compounds": ["abyssomicin C"], "taxonomy": {"name": "Producer one"}}]}))
    (tmp_path / "sid.csv").write_text("id,organism\nSID_one,Streptomyces sp. deposited one\n")
    _tsv(tmp_path / "meta.tsv", ["strain", "genus"], [["AS-900", "Gtwo"], ["AS-901", "Gone"]])
    _tsv(tmp_path / "cohorts.tsv", ["strain", "cohort"], [["AS-900", "first"], ["AS-901", "first"], ["AS-902", "second"]])
    return tmp_path


def _build(kit, out="out", *extra):
    args = ["--kit", str(kit / "kit"), "--regions", str(kit / "regions"), "--out", str(kit / out), *extra]
    assert pbx.main(args) == 0
    return kit / out


def _js(path):
    m = re.match(r'window\.__PBX&&__PBX\.put\(("[^"]+"),(.*)\);\n$', Path(path).read_text(), re.S)
    assert m
    return json.loads(m.group(2))


def _pure_block() -> str:
    t = TEMPLATE.read_text()
    m = re.search(r"/\*PBX3-PURE-BEGIN\*/(.*)/\*PBX3-PURE-END\*/", t, re.S)
    assert m, "the template lost its PBX3-PURE block"
    return m.group(1)


def run_js(expr: str, data: dict | None = None):
    """Evaluate `expr` (an expression giving a JSON string) after the template's pure block, with `D` bound to `data`."""
    code = _pure_block() + f"\nvar D = {json.dumps(data or {})};\n"
    node = shutil.which("node")
    if node:
        res = subprocess.run([node, "-e", code + f"process.stdout.write({expr});"], capture_output=True, text=True, timeout=60)
    elif sys.platform == "darwin" and shutil.which("osascript"):
        res = subprocess.run(["osascript", "-l", "JavaScript", "-e", code + expr], capture_output=True, text=True, timeout=60)
    else:
        pytest.skip("no JavaScript runtime (node, or osascript on macOS) to run the page logic")
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout.strip())


# ---------------------------------------------------------------- the 3D view
def test_3d_view_keeps_the_point_count_and_order(kit):
    out = _build(kit)
    d = _js(out / "data/sets/KS.js")
    assert [p[:3] for p in d["pts"]] == [[float(r[1]), float(r[2]), float(r[3])] for r in ROWS]
    got = run_js("JSON.stringify(D.pts.map(p => PBX3.project(p, PBX3.turn(PBX3.I(), 0.7, -0.4), PBX3.center(D.pts))))", d)
    assert len(got) == len(d["pts"])                       # one projected point per data point, same index
    c = [sum(p[k] for p in d["pts"]) / len(d["pts"]) for k in range(3)]
    for p, q in zip(d["pts"], got):                         # rotation keeps each point's distance from the centre
        assert abs(sum((p[k] - c[k]) ** 2 for k in range(3)) - sum(v * v for v in q)) < 1e-9


def test_projection_reduces_to_the_flat_view():
    flat = run_js("JSON.stringify([[0.2,0.3,0],[-0.5,0.1,0],[0.4,-0.6,0]].map(p => PBX3.project(p, PBX3.I(), [0,0,0])))")
    assert flat == [[0.2, 0.3, 0], [-0.5, 0.1, 0], [0.4, -0.6, 0]]
    # with no rotation the screen axes are PCoA 1 and 2 whatever PCoA 3 is (the "Flat" button)
    snap = run_js("JSON.stringify(PBX3.project([0.2,0.3,0.9], PBX3.I(), [0,0,0]).slice(0,2))")
    assert snap == [0.2, 0.3]
    # a quarter turn about the vertical brings PCoA 3 onto the horizontal screen axis
    turned = run_js("JSON.stringify(PBX3.project([0,0,1], PBX3.rotY(Math.PI/2), [0,0,0]).map(v => +v.toFixed(9)))")
    assert turned == [1, 0, 0]
    assert run_js("JSON.stringify(PBX3.turn(PBX3.I(), 0, 0))") == [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


# ---------------------------------------------------------------- labels
def test_mibig_label_carries_its_accession_compound_and_producer(kit):
    out = _build(kit, "out", "--mibig-names", str(kit / "mibig.json"))
    d = _js(out / "data/sets/KS.js")
    assert d["mibig"] == {"BGC0000001": ["abyssomicin C", "Producer one"]}
    lab = run_js("JSON.stringify(PBX3.label(D.pts.find(p => p[3] === 'm'), D))", d)
    assert lab[0] == "MIBiG cluster BGC0000001" and "abyssomicin C" in lab and "producer: Producer one" in lab
    assert "gene abyB1" in lab


def test_sid_label_uses_the_deposited_organism_and_the_kit_genus_only_otherwise(kit):
    with_meta = _js(_build(kit, "a", "--sid-metadata", str(kit / "sid.csv")) / "data/sets/KS.js")
    without = _js(_build(kit, "b") / "data/sets/KS.js")
    expr = "JSON.stringify(PBX3.label(D.pts.find(p => p[3] === 's'), D))"
    lab = run_js(expr, with_meta)
    assert lab[1] == "Streptomyces sp. deposited one" and any(x.startswith("contig WWAA01000001.1") for x in lab)
    lab = run_js(expr, without)
    assert lab[1].startswith("Gone (genus from the PCoA table")


def test_sid_organism_matches_a_display_name_by_its_sid_token(kit):
    rows = [r[:] for r in ROWS]
    rows[1][8] = "Genus sp. SID_one"                         # a kit that carries a display name, not the id
    rows[1][12] = "Genus sp. SID_one__WWAA01000001.1.region001.gbk"
    (kit / "sid.csv").write_text("id,organism\nSID7,Streptomyces sp. deposited seven\n")
    rows[1][8] = "Genus sp. SID7"; rows[1][12] = "Genus sp. SID7__WWAA01000001.1.region001.gbk"
    _tsv(kit / "kit/out_KS/PCOA_KS.tsv", HDR, rows)
    out = _build(kit, "out", "--sid-metadata", str(kit / "sid.csv"))
    assert _js(out / "data/sets/KS.js")["sid_org"] == {"Genus sp. SID7": "Streptomyces sp. deposited seven"}
    receipt = json.loads((out / "build_receipt.json").read_text())["summary"]
    assert receipt["sid_strains"] == 1 and receipt["sid_strains_with_organism"] == 1


def test_several_sid_metadata_files_first_wins_and_clashes_are_listed(kit):
    (kit / "sid_more.csv").write_text("id,display,organism,source\nSID_one,x,Streptomyces sp. other one,record\n"
                                       "SID_two,y,Streptomyces sp. two,record\n")
    out = _build(kit, "out", "--sid-metadata", str(kit / "sid.csv"), "--sid-metadata", str(kit / "sid_more.csv"))
    assert _js(out / "data/sets/KS.js")["sid_org"] == {"SID_one": "Streptomyces sp. deposited one"}   # the first file wins
    rows = list(csv.DictReader(open(out / "SID_METADATA_DISAGREEMENTS.tsv"), delimiter="\t"))
    assert rows == [{"id": "SID_one", "organism_kept": "Streptomyces sp. deposited one", "kept_from": "sid.csv",
                     "organism_other": "Streptomyces sp. other one", "other_file": "sid_more.csv"}]
    assert json.loads((out / "build_receipt.json").read_text())["summary"]["sid_metadata_disagreements"] == 1


def test_reference_label_names_the_genome_and_gene(kit):
    d = _js(_build(kit) / "data/sets/KS.js")
    assert run_js("JSON.stringify(PBX3.label(D.pts.find(p => p[3] === 'r'), D))", d) == [
        "Reference genome", "Ref one genome", "gene x1"]


# ---------------------------------------------------------------- identity code and genus filter
def test_points_without_an_identity_value_never_get_the_identity_code(kit):
    d = _js(_build(kit) / "data/sets/KS.js")
    marks = run_js("JSON.stringify(D.pts.map(p => [p[3], PBX3.marker(p)]))", d)
    for code, m in marks:
        if code != "i":
            assert m == "noid"                              # SID, reference and MIBiG points
    iso = [m for c, m in marks if c == "i"]
    assert iso == ["filled", "open", "noid"]                # 55%, 88%, no NEAREST row
    t = TEMPLATE.read_text()
    assert "no identity value" in t                         # the key names the symbol


def test_genus_filter_never_drops_mibig_points(kit):
    d = _js(_build(kit) / "data/sets/KS.js")
    kept = run_js("JSON.stringify(D.pts.filter(p => PBX3.keep(p, 'No_such_genus', D.strings)).map(p => p[3]))", d)
    assert kept == ["m"]
    kept = run_js("JSON.stringify(D.pts.filter(p => PBX3.keep(p, 'Gone', D.strings)).map(p => p[3]))", d)
    assert kept == ["r", "s", "m", "i", "i", "i"]


# ---------------------------------------------------------------- genus source, cohorts, subgroups
def test_cohort_genus_comes_from_the_strain_metadata_and_disagreements_are_listed(kit):
    out = _build(kit, "out", "--strain-metadata", str(kit / "meta.tsv"))
    d = _js(out / "data/sets/KS.js")
    S = d["strings"]
    by_strain = {S[p[5]]: S[p[4]] for p in d["pts"] if p[3] == "i"}
    assert by_strain == {"AS-900": "Gtwo", "AS-901": "Gone", "AS-902": "Gone"}   # no metadata row: the kit genus stays
    rows = list(csv.DictReader(open(out / "GENUS_DISAGREEMENTS.tsv"), delimiter="\t"))
    assert rows == [{"strain": "AS-900", "kit_genus": "Gone", "metadata_genus": "Gtwo", "sets": "KS"}]
    receipt = json.loads((out / "build_receipt.json").read_text())["summary"]
    assert receipt["genus_disagreements"] == 1
    assert _js(out / "data/index.js")["genus_source"] == "strain metadata"


def test_cohorts_and_subgroups_reach_the_page(kit):
    out = _build(kit, "out", "--cohort-table", str(kit / "cohorts.tsv"), "--subgroup", "AS-901=sub_b")
    idx = _js(out / "data/index.js")
    assert idx["cohorts"] == ["first", "second"] and idx["subgroup_of"] == {"AS-901": "sub_b"}
    t = TEMPLATE.read_text()
    assert len(set(re.findall(r'"(--c\d)"', t))) >= 6      # six distinct cohort colour slots
    assert re.search(r"--sid:\s*#[0-9a-f]{6}", t) and not re.search(r"--sid:\s*var\(--ref\)", t)


# ---------------------------------------------------------------- offline page, no identifiers
def test_page_loads_nothing_from_the_network():
    t = TEMPLATE.read_text()
    assert not re.search(r"""<(script|link|img|iframe)[^>]+(src|href)\s*=\s*["']?https?:""", t, re.I)
    assert "@import" not in t and "fetch(" not in t and "XMLHttpRequest" not in t
    assert not re.search(r"cdn|unpkg|jsdelivr|plotly", t, re.I)
    # the one "http" is the MIBiG repository link a user may click in the gene panel; nothing is loaded from it
    others = [m.start() for m in re.finditer(r"https?:", t)
              if not t.startswith("https://mibig.secondarymetabolites.org/repository/", m.start())]
    assert others == []


def test_no_cohort_identifiers_in_the_page_or_the_tool():
    for f in (TEMPLATE, ROOT / "tools" / "pcoa_bgc_explorer.py"):
        assert not re.search(r"\bA[JS]S?-\d", f.read_text()), f
