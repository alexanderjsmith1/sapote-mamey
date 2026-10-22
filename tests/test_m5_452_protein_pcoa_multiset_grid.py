"""m5_452_protein_pcoa_multiset_grid: tools/protein_pcoa_render.py --page pcoa --page-grid RxC draws several protein sets per page in an
R x C grid (row by row), each set its own ordination and axes, one shared legend, panel letters continuing across pages. The default page
mode (one set per page, layouts side by side) is unchanged (existing page tests). Synthetic data only (the page-defaults test kit)."""
import importlib.util, json, shutil, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("ppd_test", ROOT / "tests" / "test_m5_452_pcoa_page_defaults.py")
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
from tools import _min_text_check as mtc  # noqa: E402

needs_r = pytest.mark.skipif(not shutil.which("Rscript"), reason="Rscript unavailable")
SETS = ["KS", "AT", "C", "LANC", "NIS"]


def five_set_kit(root):
    """The page-defaults KS kit, copied to five sets (each set its own out_<SET> folder and META)."""
    base.make_kit(root, [("SYN-901", 0.5, 1.4, 50), ("SYN-902", 0.52, 0.5, 92), ("SYN-903", -0.4, 0.3, 60)])
    kit = root / "kit"
    for s in SETS[1:]:
        d = kit / f"out_{s}"; d.mkdir()
        for name in ("PCOA", "NEAREST"):
            (d / f"{name}_{s}.tsv").write_text((kit / "out_KS" / f"{name}_KS.tsv").read_text())
        (d / f"RUN_{s}.json").write_text((kit / "out_KS" / "RUN_KS.json").read_text())
        (kit / f"{s}_META.tsv").write_text((kit / "KS_META.tsv").read_text())
    return root


def grid(root, *extra):
    args = ["--kit", str(root / "kit"), "--out", str(root / "out"), "--cohort-table", str(root / "cohorts.tsv"),
            "--panel", "query=query", "--panel-label", "query=query genome protein", "--label-names", str(root / "names.tsv")]
    for s in SETS:
        args += ["--set", s]
    return base.ppr.main(args + list(extra))


@needs_r
def test_grid_pages_flow_sets_and_continue_letters(tmp_path):
    root = five_set_kit(tmp_path)
    assert grid(root, "--page", "pcoa", "--page-grid", "2x2") == 0
    out = root / "out"
    p1 = json.loads((out / "page_grid_query_pcoa_page1.json").read_text()); p2 = json.loads((out / "page_grid_query_pcoa_page2.json").read_text())
    assert p1["sets"] == SETS[:4] and p1["letters"] == list("abcd") and (p1["nrow"], p1["ncol"]) == (2, 2)
    assert p2["sets"] == SETS[4:] and p2["letters"] == ["e"] and (p2["nrow"], p2["ncol"]) == (1, 1)
    for k in (1, 2):
        pdf = out / f"PAGE_GRID_query_PCOA_page{k}.pdf"
        assert pdf.exists() and (out / f"PAGE_GRID_query_PCOA_page{k}_CAPTION.md").exists()
        chk = json.loads((out / f"PAGE_GRID_query_PCOA_page{k}_min_text_check.json").read_text())
        assert chk["status"] == "PASS" and chk["smallest_pt"] >= 8
    texts = {t for _, t in mtc.text_sizes(str(out / "PAGE_GRID_query_PCOA_page2.pdf"))}
    assert "e" in texts and "a" not in texts          # page 2 continues the letters
    assert len(mtc.pdf_axis_panels_grid(out / "PAGE_GRID_query_PCOA_page1.pdf", 2, 2, 4)) == 4
    for s in SETS:
        assert (out / f"GENOMES_USED_{s}.tsv").exists()
    assert "reference genomes (cluster centroids)" == p1["legend"]["ref"]   # shared legend: no per-set n (the caption gives it)


def test_grid_needs_pcoa_page(tmp_path):
    root = five_set_kit(tmp_path)
    with pytest.raises(SystemExit):
        grid(root, "--page", "pcoa,trimap", "--page-grid", "2x2")
    with pytest.raises(SystemExit):
        grid(root, "--page", "pcoa", "--page-grid", "two")


@needs_r
def test_set_kit_reads_one_set_from_its_own_kit(tmp_path):
    """--set-kit SET=PATH: a set ordinated in its own run (e.g. run-7 KSalpha) is read and bound from that kit; the render receipt
    binds its tables by path and sha256."""
    root = five_set_kit(tmp_path)
    other = root / "other_kit"; other.mkdir()
    (root / "kit" / "out_NIS").rename(other / "out_NIS"); (root / "kit" / "NIS_META.tsv").rename(other / "NIS_META.tsv")
    assert grid(root, "--page", "pcoa", "--page-grid", "2x2", "--set-kit", f"NIS={other}") == 0
    rec = json.loads((root / "out" / "render_receipt.json").read_text())
    bound = {Path(b["path"]).resolve() for b in rec["inputs"] if b.get("sha256")}
    assert (other / "out_NIS" / "PCOA_NIS.tsv").resolve() in bound and (other / "NIS_META.tsv").resolve() in bound
    assert json.loads((root / "out" / "page_grid_query_pcoa_page2.json").read_text())["sets"] == ["NIS"]


def test_set_kit_must_name_a_drawn_set(tmp_path, caplog):
    root = five_set_kit(tmp_path)
    assert grid(root, "--page", "pcoa", "--page-grid", "2x2", "--set-kit", f"T2KS={root / 'kit'}") == 2
    assert "--set-kit names sets not drawn" in caplog.text


def test_grid_axis_text_follows_the_admitted_definition():
    """Audit F23: a grid caption words axis percentages by their admitted definition state, as single pages do; supplied
    values are never called variance explained, and are shown unclipped."""
    from tools import protein_pcoa_page_docs as docs
    supplied = docs._grid_axis_text({"pct_axes": [140.0, -20.0], "axis_metadata": {"pct_axes": [140.0, -20.0],
                                                                                    "definition": {"state": "SUPPLIED_UNVERIFIED"}}})
    assert "variance explained" not in supplied and "unverified" in supplied and "140.0%" in supplied and "-20.0%" in supplied
    native = docs._grid_axis_text({"pct_axes": [40.0, 20.0], "axis_metadata": {"pct_axes": [40.0, 20.0],
                                                                               "definition": {"state": "NATIVE_COORDINATE_SOURCE_BOUND"}}})
    assert "eigenvalue/signed-trace" in native and "not conventional variance explained" in native
    assert "unverified" in docs._grid_axis_text({"pct_axes": [40.0, 20.0]})   # no metadata at all: unverified
