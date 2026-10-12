"""Renderer stamps: bundle renderers write their name into saved figures; the checker reads it back."""
from __future__ import annotations
import re, shutil, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from mamey.figure_stamp import savefig_metadata, stamp_file  # noqa: E402
import check_figure_provenance as cfp  # noqa: E402

# Bundle files that save figures but do not stamp them yet. This list may only shrink: a new renderer must
# stamp (savefig_metadata, stamp_file, or sapote_save_pair in R), and a converted one must leave the list.
UNSTAMPED_RENDERERS = {
    "tools/_embedding_replay.py",  # in the .450 candidate, not in .449
    "deliverable_tools/assembly_line_pdf.py",
    "deliverable_tools/bgc_gene_map.py",
    "deliverable_tools/bigscape_gene_domain_context.py",
    "deliverable_tools/render_mlsa_tree.py",
    "deliverable_tools/stacked_locus_map.py",
    "mamey/bigscape_figures.py",
    "mamey/chatgpt_commands.py",
    "mamey/cli.py",
    "mamey/cohort_class_heatmap.py",
    "mamey/cohort_figures_extended.py",
    "mamey/collection_figures.py",
    "mamey/cross_strain_threads.py",
    "mamey/figures/locus_comparison.py",
    "mamey/figures/locus_renderer_v2.py",
    "mamey/figures_extra.py",
    "mamey/figures_sapote.py",
    "mamey/figures_smoke.py",
    "mamey/interactive_figures/bee_review_prototypes.py",
    "mamey/kcb_locusmap.py",
    "mamey/locus_map.py",
    "mamey/locus_map_v8.py",
    "mamey/mamey_native_figures.py",
    "mamey/master_figure_atlas.py",
    "mamey/output_checklist.py",
    "mamey/render_brief.py",
    "tools/bee_review_main_set.py",
    "tools/bgc_figures.py",
    "tools/bgc_reference_align.py",
    "tools/blastp_coverage_wave.py",
    "tools/blastp_monitoring/plot_crawl_12h_15min.py",
    "tools/blastp_monitoring/plot_crawl_cumulative.py",
    "tools/blastp_monitoring/plot_crawl_proteins_24_96h.py",
    "tools/blastp_monitoring/plot_crawl_recent.py",
    "tools/blastp_monitoring/plot_usable_6h.py",
    "tools/build_figures.py",
    "tools/build_normalization_matrix.py",
    "tools/build_overview_figures.py",
    "tools/build_panel_figure.py",
    "tools/build_pangenome.py",
    "tools/build_size_profile.py",
    "tools/build_subset_panel.py",
    "tools/build_validation_panel.py",
    "tools/cluster_alignment.py",
    "tools/cluster_gene_compare.py",
    "tools/cluster_relate.py",
    "tools/gap_rescue_gene_table.py",
    "tools/gene_synteny_map.py",
    "tools/gene_topology.py",
    "tools/ggtree_placement.R",
    "tools/ggtree_placement_bioassay.R",
    "tools/ggtree_placement_hostcolour.R",
    "tools/ggtree_rect_heatmap.R",
    "tools/multi_reference_comparison.py",
    "tools/phylo_place.py",
    "tools/placement_figure.py",
    "tools/plot_examples.py",
    "tools/protein_pcoa_compare.py",
    "tools/protein_pcoa_render.R",
    "tools/protein_pcoa_render.py",
    "tools/render_clean_tree.py",
    "tools/render_dapr_boards.py",
    "tools/render_gcf_synteny_tree.py",
    "tools/render_placement_COLOR_STRIPS.R",
    "tools/render_screening_exploration.R",
    "tools/render_tree_COLOR_STRIPS.R",
    "tools/sapote_bioassay_figure.R",
    "tools/sapote_pub_layout.R",
    "tools/strain_slides.py",
    "tools/strain_slides_pcoa.py",
    "tools/tree_bgc_overlay.py",
    "tools/tree_overlay_figure.py",
    "tools/tree_reference_series.R",
    "tools/tree_track_render.R",
}
SAVES = re.compile(r"\.savefig\(|ggsave\(|\bpng\(|svglite\(|cairo_pdf\(|\bpdf\(")
STAMPS = ("savefig_metadata", "stamp_file", "sapote_stamp_files", "sapote_save_pair",
          "Sapote-Mamey governed figure theme", "Sapote-Mamey Figure Factory Next")

def _renderers():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if p.suffix in (".py", ".R") and p.is_file() and rel.parts[0] not in ("tests", "wheels", "examples")                 and "__pycache__" not in rel.parts:
            s = p.read_text(errors="replace")
            if SAVES.search(s):
                yield str(rel), any(k in s for k in STAMPS)

def test_every_renderer_stamps_or_is_listed():
    found = dict(_renderers())
    new = sorted(r for r, ok in found.items() if not ok and r not in UNSTAMPED_RENDERERS)
    assert not new, f"new renderers save figures without a stamp: {new}"
    done = sorted(r for r in UNSTAMPED_RENDERERS if found.get(r))
    assert not done, f"these now stamp; remove them from UNSTAMPED_RENDERERS: {done}"
    # a listed file may be absent from an older or newer cut; one that exists but no longer saves must leave the list
    gone = sorted(r for r in UNSTAMPED_RENDERERS if r not in found and (ROOT / r).exists())
    assert not gone, f"listed renderers no longer save figures: {gone}"

@pytest.fixture
def fig():
    mpl = pytest.importorskip("matplotlib"); mpl.use("Agg")
    import matplotlib.pyplot as plt
    f, ax = plt.subplots(figsize=(2, 1)); ax.plot([0, 1], [0, 1])
    yield f
    plt.close(f)

@pytest.mark.parametrize("ext", [".png", ".pdf", ".svg"])
def test_savefig_metadata_passes_and_plain_does_not(tmp_path, fig, ext):
    good, plain = tmp_path / f"good{ext}", tmp_path / f"plain{ext}"
    fig.savefig(good, metadata=savefig_metadata(good, "unit_test"))
    fig.savefig(plain)
    assert cfp.stamp(good)[0] == "PASS"
    assert cfp.stamp(plain)[0] == "PLAIN_MPL"

@pytest.mark.parametrize("ext", [".png", ".pdf", ".svg"])
def test_stamp_file_after_saving(tmp_path, fig, ext):
    p = tmp_path / f"late{ext}"
    fig.savefig(p)
    before = p.read_bytes()
    stamp_file(p, "unit_test")
    assert cfp.stamp(p)[0] == "PASS"
    if ext == ".pdf":
        assert p.read_bytes().startswith(before) and p.read_bytes().rstrip().endswith(b"%%EOF")
    if ext == ".png":
        Image = pytest.importorskip("PIL.Image")
        g = tmp_path / "ref.png"; g.write_bytes(before)
        with Image.open(p) as a, Image.open(g) as b:
            assert a.tobytes() == b.tobytes()

def test_png_stamp_replaces_matplotlib_software_once(tmp_path, fig):
    p = tmp_path / "x.png"; fig.savefig(p)
    stamp_file(p, "one"); stamp_file(p, "two")
    meta = cfp.png_text(p)
    assert meta["Software"] == "Sapote-Mamey two" and p.read_bytes().count(b"Software\x00") == 1

def test_caption_copy_follows_its_plot(tmp_path, fig):
    plot = tmp_path / "F1_plot_only.png"; fig.savefig(plot, metadata=savefig_metadata(plot, "unit_test"))
    fig.savefig(tmp_path / "F1_with_caption.png")  # an unstamped caption copy
    v = {r["path"]: r["verdict"] for r in cfp.check(tmp_path)}
    assert v["F1_with_caption.png"] == "PLAIN_MPL"  # a matplotlib stamp is not inherited
    (tmp_path / "F1_with_caption.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    v = {r["path"]: r["verdict"] for r in cfp.check(tmp_path)}
    assert v["F1_with_caption.png"] == "PASS_DERIVED"

def test_caption_band_stamps_its_outputs(tmp_path, fig):
    pytest.importorskip("PIL")
    import caption_band
    plot = tmp_path / "F2_plot_only.png"; fig.savefig(plot, dpi=300, metadata=savefig_metadata(plot, "unit_test"))
    cap = tmp_path / "cap.md"; cap.write_text("**Figure 2.** Test caption.\n")
    caption_band.add_band(plot, cap, tmp_path)
    for n in ("F2_with_caption.png", "F2_with_caption.pdf"):
        assert cfp.stamp(tmp_path / n)[0] == "PASS", n

def test_strict_exit_code(tmp_path, fig):
    fig.savefig(tmp_path / "a.png")
    assert cfp.main([str(tmp_path), "--tsv", str(tmp_path / "o.tsv")]) == 0
    assert cfp.main([str(tmp_path), "--strict", "--tsv", str(tmp_path / "o.tsv")]) == 1

def test_r_save_pair_stamps(tmp_path):
    rs = shutil.which("Rscript")
    if not rs:
        pytest.skip("Rscript not installed")
    code = (f'suppressMessages({{library(ggplot2)}}); source("{ROOT}/tools/sapote_figure_theme.R"); '
            f'p <- ggplot(data.frame(x=1:3,y=1:3), aes(x,y)) + geom_point(); '
            f'sapote_save_pair(p, "{tmp_path}/r_fig", "SINGLE_COLUMN", 2)')
    r = subprocess.run([rs, "-e", code], capture_output=True, text=True)
    if r.returncode and ("there is no package" in r.stderr or "svglite" in r.stderr):
        pytest.skip("ggplot2/svglite not installed")
    assert r.returncode == 0, r.stderr
    assert "FIGURE_STAMP" not in r.stderr, r.stderr
    for ext in (".png", ".svg"):
        assert cfp.stamp(tmp_path / f"r_fig{ext}")[0] == "PASS", ext
