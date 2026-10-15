"""Synthetic page-default regressions: outlier labels, bounded leaders, minimum text,
reference counts, and more than thirty distinct crowded genomes.
"""
import csv, importlib.util, json, math, shutil, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("protein_pcoa_render", ROOT / "tools" / "protein_pcoa_render.py")
ppr = importlib.util.module_from_spec(spec); spec.loader.exec_module(ppr)
from tools import _min_text_check as mtc  # noqa: E402

needs_r = pytest.mark.skipif(not shutil.which("Rscript"), reason="Rscript unavailable")
GRID = [(i / 20, j / 20) for i in range(21) for j in range(21)]   # reference/MIBiG background, nearest-neighbour distance 0.05
CROWD = ["SYN-970", "SYN-971", "SYN-972", "SYN-973", "SYN-974", "SYN-975", "SYN-976", "SYN-977", "SYN-978", "SYN-979", "SYN-980", "SYN-981",
         "SYN-982", "SYN-983", "SYN-984", "SYN-985", "SYN-986", "SYN-987", "SYN-988", "SYN-989", "SYN-990", "SYN-991", "SYN-992", "SYN-993",
         "SYN-994", "SYN-995", "SYN-996", "SYN-997", "SYN-998", "SYN-999", "SYN-1000", "SYN-1001", "SYN-1002", "SYN-1003"]   # 34 genomes


def make_kit(root, cohort_pts, trimap=None, meta=True):
    """cohort_pts: [(strain, x, y, identity)]; trimap: {strain: (x, y)} moves that strain's points in the TriMap table."""
    out = root / "kit/out_KS"; out.mkdir(parents=True)
    rows = [["id", "PC1", "PC2", "PC3", "n_represented", "source", "group", "genus", "strain", "subtype", "region_product",
             "locus_tag", "origin", "length"]]
    near = [["id", "nearest_pident"]]; emb = [["id", "TRIMAP1", "TRIMAP2"]]; meta_rows = [["id", "source", "group", "genus", "strain"]]
    for n, (x, y) in enumerate(GRID):
        src = "MIBiG" if n % 5 == 0 else "reference_final"; strain = f"BGC{n:07d}" if src == "MIBiG" else f"Synthetic_ref_{n % 3}"
        rows.append([f"r{n}", x, y, 0, 2, src, "", "G", strain, "", "", "", "", 300]); emb.append([f"r{n}", x, y])
        meta_rows.append([f"r{n}", src, src, "G", strain])
    meta_rows.append(["r_extra", "SID_final", "SID_final", "G", "Synthetic_ref_sid"])   # a reference genome whose protein is a member
    for k, (strain, x, y, pid) in enumerate(cohort_pts):
        rows.append([f"i{k}", x, y, 0, 1, "isolate", "", "G", strain, "", "", f"c{k}_1", f"{strain}__N{k}.region001.gbk", 300])
        near.append([f"i{k}", pid]); meta_rows.append([f"i{k}", "isolate", "query", "G", strain])
        tx, ty = (trimap or {}).get(strain, (x, y)); emb.append([f"i{k}", tx, ty])
    for name, data in (("PCOA_KS.tsv", rows), ("NEAREST_KS.tsv", near)):
        with open(out / name, "w", newline="") as fh:
            csv.writer(fh, delimiter="\t").writerows(data)
    (out / "RUN_KS.json").write_text(json.dumps({"pct_axes": [30.0, 20.0, 10.0]}))
    if meta:
        with open(root / "kit/KS_META.tsv", "w", newline="") as fh:
            csv.writer(fh, delimiter="\t").writerows(meta_rows)
    with open(root / "trimap.tsv", "w", newline="") as fh:
        csv.writer(fh, delimiter="\t").writerows(emb)
    strains = list(dict.fromkeys(s for s, *_ in cohort_pts))
    (root / "cohorts.tsv").write_text("strain\tcohort\n" + "".join(f"{s}\tquery\n" for s in strains))
    (root / "names.tsv").write_text("strain\tdisplay\tshort\n" + "".join(
        f"{s}\tSynthetica sp{i} {s} [GCA_00000{i:04d}.1]\tS. sp{i}\n" for i, s in enumerate(strains, 1)))
    return root


def page(root, *extra):
    return ppr.main(["--kit", str(root / "kit"), "--out", str(root / "out"), "--cohort-table", str(root / "cohorts.tsv"),
                     "--panel", "query=query", "--panel-label", "query=query genome protein", "--page", "pcoa,trimap",
                     "--embedding-table", f"KS={root / 'trimap.tsv'}", "--label-names", str(root / "names.tsv"), *extra])


def labels(root):
    return list(csv.DictReader(open(root / "out/LABELS_KS_query_PAGE.tsv"), delimiter="\t"))


# FAR: an outlier with a high-identity best match; LOW: inside the background, lowest identity (the hand rule --top-strains labels it first)
BASIC = [("SYN-1004", 2.5, 2.5, 95.0), ("SYN-1005", 0.52, 0.52, 30.0), ("SYN-1006", 0.31, 0.71, 90.0)]


@pytest.fixture(scope="module")
def basic(tmp_path_factory):
    root = make_kit(tmp_path_factory.mktemp("basic"), BASIC, trimap={"SYN-1004": (0.5, 0.5), "SYN-1005": (-1.5, 2.0)})
    assert page(root) == 0
    return root


@needs_r
def test_p1_outliers_are_labelled_per_panel_not_lowest_identity(basic):
    drawn = {(r["layout"], r["strain"]) for r in labels(basic) if r["drawn"] == "yes"}
    listed = {(r["layout"], r["strain"]) for r in labels(basic)}
    assert ("pcoa", "SYN-1004") in drawn and ("pcoa", "SYN-1005") not in listed      # PCoA: the far point, not the lowest identity
    assert ("trimap", "SYN-1005") in drawn and ("trimap", "SYN-1004") not in listed  # TriMap: its own outlier (per panel)
    rec = json.loads((basic / "out/page_KS_query.json").read_text())
    assert "plot_pcoa.py lines 105-116" in rec["label_rule"] and rec["labels"]["pcoa"]["labelled"] == rec["labels"]["pcoa"]["outlier_groups"]


@needs_r
def test_p1_top_strains_is_refused_in_page_mode(tmp_path):
    root = make_kit(tmp_path, BASIC)
    assert page(root, "--top-strains", "3") == 2 and not (root / "out/PAGE_KS_query_PCOA_TRIMAP.pdf").exists()


@needs_r
def test_p1b_page_defaults_tiers_floor_and_italic_names(basic):
    rec = json.loads((basic / "out/page_KS_query.json").read_text())
    assert rec["mid_below"] == 85.0 and rec["min_text"]["min_text_pt"] == 8.0 and "iso_mid" in rec["legend"]
    chk = json.loads((basic / "out/PAGE_KS_query_PCOA_TRIMAP_min_text_check.json").read_text())
    assert chk["status"] == "PASS" and chk["smallest_pt"] >= 7.95
    faces = []
    from pypdf import PdfReader
    PdfReader(str(basic / "out/PAGE_KS_query_PCOA_TRIMAP.pdf")).pages[0].extract_text(
        visitor_text=lambda t, cm, tm, font, fs: faces.append((t.strip(), str(font.get("/BaseFont")) if font else "")))
    assert any(t.startswith("S. sp") and "Italic" in f for t, f in faces)


@needs_r
def test_p3_every_drawn_leader_is_within_the_limit(basic):
    segs = mtc.pdf_stroke_segments(basic / "out/PAGE_KS_query_PCOA_TRIMAP.pdf", ppr.LEADER_RGB)
    assert segs and all(math.hypot(x1 - x0, y1 - y0) / 72 <= ppr.LEADER_MAX_IN + 0.005 for x0, y0, x1, y1 in segs)
    assert ppr.LEADER_MAX_IN == 0.35
    assert mtc.page_label_faults(basic / "out/PAGE_KS_query_PCOA_TRIMAP.pdf", 2, ppr.LEADER_MAX_IN, ppr.LEADER_RGB) == {0: [], 1: []}


def test_p3_pdf_read_back_flags_a_long_leader(tmp_path):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(7.2, 4)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 7.2); ax.set_ylim(0, 4); ax.axis("off")
    ax.plot([0.5, 1.0], [1, 1], color="#555555", lw=.5)   # 0.5 in, left column
    ax.plot([5.0, 5.2], [1, 1], color="#555555", lw=.5)   # 0.2 in, right column
    fig.savefig(tmp_path / "l.pdf"); plt.close(fig)
    f = mtc.page_label_faults(tmp_path / "l.pdf", 2, 0.35, ppr.LEADER_RGB)
    assert f[0] and "leader 0.50 in" in f[0][0] and not f[1]


@needs_r
def test_p4_legend_states_reference_genome_n_from_meta(basic):
    rec = json.loads((basic / "out/page_KS_query.json").read_text())
    assert rec["n_reference_genomes"] == 4   # 3 reference strains + 1 SID; MIBiG and query genomes are not counted
    assert rec["legend"]["ref"] == "reference genomes, n = 4 (cluster centroids)"


@needs_r
def test_p4_page_refuses_without_meta(tmp_path, caplog):
    root = make_kit(tmp_path, BASIC, meta=False)
    assert page(root) == 2 and "KS_META.tsv (the legend states the reference genome count)" in caplog.text


@needs_r
def test_p6_panel_title_without_set_names(basic):
    svg = (basic / "out/PAGE_KS_query_PCOA_TRIMAP.svg").read_text()
    assert "PKS ketosynthase (KS) domains" in ppr.svg_visible_text(svg)


def test_p2_placement_skips_a_boxed_in_target_and_keeps_free_ones():
    import numpy as np
    ring = [(200 + r * math.cos(t), 200 + r * math.sin(t), 1.0) for r in range(4, 44, 2) for t in np.linspace(0, 2 * math.pi, 90, endpoint=False)]
    obst = np.array([(50, 50, 2.0), (200, 200, 2.0)] + ring)
    res = ppr.place_labels_pt([(50, 50, 2.0), (200, 200, 2.0)], ["S. far", "S. inside"], obst, (0, 400, 0, 400), [],
                              font_size=8, italic=True, max_leader_pt=ppr.LEADER_MAX_IN * 72)
    assert res[0] is not None and res[0]["leader_pt"] <= ppr.LEADER_MAX_IN * 72 and res[1] is None


def test_p2_placement_rejects_crossing_leaders():
    import itertools, random
    import numpy as np
    a, b = (0, 0, 10, 10), (0, 10, 10, 0)
    assert ppr._segments_cross(a, b) and not ppr._segments_cross(a, (20, 20, 30, 30))
    rnd = random.Random(12)   # a crowded layout where, without the check, the nearest free spots give crossing leaders
    tg = [(100 + rnd.uniform(-12, 12), 100 + rnd.uniform(-12, 12), 2.0) for _ in range(4)]
    ob = [(100 + rnd.uniform(-30, 30), 100 + rnd.uniform(-30, 30), 2.0) for _ in range(25)] + tg
    res = ppr.place_labels_pt(tg, ["1", "2", "3", "4"], np.array(ob), (0, 200, 0, 200), [], font_size=8, italic=False,
                              max_leader_pt=ppr.LEADER_MAX_IN * 72)
    segs = [r["seg"] for r in res if r]
    assert len(segs) >= 2 and not any(ppr._segments_cross(x, y) for x, y in itertools.combinations(segs, 2))


@pytest.fixture(scope="module")
def crowd(tmp_path_factory):
    pts = [(s, 2.0 + 0.012 * (k % 6), 0.5 + 0.012 * (k // 6), 92.0) for k, s in enumerate(CROWD)]   # 34 genomes packed together
    root = make_kit(tmp_path_factory.mktemp("crowd"), pts + BASIC)
    assert page(root) == 0
    return root


@needs_r
def test_p1c_page_labels_are_names_never_numbers(crowd):
    """FIGURE_HOUSE_RULES rule 6: a page never carries number labels, even with more than --number-above outliers (34 genomes here)."""
    rec = json.loads((crowd / "out/page_KS_query.json").read_text())
    assert all(v["outlier_groups"] > 30 for v in rec["labels"].values())
    drawn = [r for r in labels(crowd) if r["drawn"] == "yes"]
    assert drawn and not any(r["label_text"].split(" x")[0].strip().isdigit() for r in drawn)
    assert all(r["label_text"].startswith("S. sp") for r in drawn)
    assert not any(v["numbered"] for v in rec["labels"].values())


@needs_r
def test_p2_crowded_outliers_are_listed_when_not_drawn(crowd):
    rec = json.loads((crowd / "out/page_KS_query.json").read_text())["labels"]["pcoa"]
    rows = [r for r in labels(crowd) if r["layout"] == "pcoa"]
    assert rec["labelled"] < rec["outlier_groups"]
    assert any(r["drawn"] == "no: no free spot within 0.35 in" for r in rows)
    assert len({r["outlier_rank"] for r in rows}) == rec["outlier_groups"]
    assert mtc.page_label_faults(crowd / "out/PAGE_KS_query_PCOA_TRIMAP.pdf", 2, ppr.LEADER_MAX_IN, ppr.LEADER_RGB) == {0: [], 1: []}


@needs_r
def test_p5_documents_written_from_receipts_and_checked(basic):
    out = basic / "out"; rec = json.loads((out / "page_KS_query.json").read_text())
    cap = (out / "PAGE_KS_query_PCOA_TRIMAP_CAPTION.md").read_text()
    assert f"{rec['n_cohort_points']:,} query genome proteins from 3 genomes" in cap
    assert f"{rec['labels']['pcoa']['labelled']} of {rec['labels']['pcoa']['outlier_groups']} in **a**" in cap
    assert "reference cluster centroids representing" in cap and f"from {rec['n_reference_genomes']:,} reference genomes" in cap
    assert "*Synthetica sp1*" in cap   # house rule 6 name, genus and species italic
    qc = json.loads((out / "QC_SUMMARY.json").read_text())
    assert qc["caption_guard"] == {} and qc["figure_render_qc_exit"] == 0 and "errors 0," in qc["figure_render_qc"]
    gen = list(csv.DictReader(open(out / "GENOMES_USED_KS.tsv"), delimiter="\t"))
    assert sum(r["role"] == "cohort" for r in gen) == 3 and sum(r["role"].startswith("reference") for r in gen) == 4
    assert (out / "METHODS_PAGE_KS_query_PCOA_TRIMAP.md").read_text().startswith("# METHODS: PAGE_KS_query_PCOA_TRIMAP")


@needs_r
def test_p5_banned_caption_wording_refuses_the_page(tmp_path, caplog):
    root = make_kit(tmp_path, BASIC)
    assert page(root, "--caption-note", "These genomes are not production references.") == 2
    assert "page documents failed the bundle checks" in caplog.text
