"""v9.7.90 locus maps: gene-arrow figure render, palette classification, anti-overlap guard."""
from __future__ import annotations
import csv, os
import pytest

pytest.importorskip("matplotlib")
from mamey.locus_map import (classify, render_locus_map, cds_rows_from_table,
                             _load_palette, FOOTER)


def _fixture_rows():
    """A small CDS table spanning core (PKS/NRPS/Ppd) + accessory + hypothetical genes."""
    raw = [
        {"locus_tag": "g1", "start": 100, "end": 1300, "strand": 1, "aa_length": 400,
         "gene_functions": "biosynthetic (rule-based-clusters) T1PKS: PKS_KS"},
        {"locus_tag": "g2", "start": 1400, "end": 2200, "strand": 1, "aa_length": 260,
         "gene_functions": "biosynthetic-additional TPP_enzyme"},
        {"locus_tag": "g3", "start": 2300, "end": 3100, "strand": -1, "aa_length": 260,
         "gene_functions": "biosynthetic-additional (smcogs) Aminotran_1_2"},
        {"locus_tag": "g4", "start": 3200, "end": 3800, "strand": 1, "aa_length": 200,
         "gene_functions": "transport (smcogs) ABC transporter"},
        {"locus_tag": "g5", "start": 3900, "end": 4500, "strand": 1, "aa_length": 200,
         "gene_functions": ""},  # hypothetical -> other
    ]
    return cds_rows_from_table(raw)


# --- palette / classification ---

def test_palette_loads():
    rules, default, short = _load_palette()
    assert len(rules) >= 10
    assert default[0] == "other / hypothetical"


def test_classify_core_and_default():
    assert classify("PKS_KS domain")[0] == "PKS module"
    assert classify("TPP_enzyme")[0].startswith("Ppd")
    assert classify("PEP_mutase")[2] is True  # is_core
    assert classify("nothing recognizable here")[0] == "other / hypothetical"


def test_unknown_never_crashes():
    # any blob returns a 3-tuple, never raises
    for blob in ["", "???", "12345", "DUF9999"]:
        role, color, core = classify(blob)
        assert isinstance(role, str) and color.startswith("#")


# --- render single + paired ---

def test_render_single_map(tmp_path):
    rows = _fixture_rows()
    png = tmp_path / "BGC001_NODE_1_locus.png"
    csvp = tmp_path / "BGC001_NODE_1_locus_data.csv"
    render_locus_map([("BGC001 · NODE_1 · region001 — T1PKS · Interior", rows)],
                     png, csvp, suptitle="STRAINX — BGC001 locus (top antibacterial lead)",
                     claim_prefix="PUBLIC")
    assert png.exists() and png.stat().st_size > 0
    assert csvp.exists()
    # >=1 core gene colored (PKS/Ppd/AT are core)
    with open(csvp) as fh:
        data = list(csv.DictReader(fh))
    core_roles = {"PKS module", "Ppd — phosphonopyruvate decarboxylase (step 2)", "aminotransferase"}
    assert any(r["role"] in core_roles for r in data)
    # data CSV carries the panel title (node/contig anchor)
    assert any("NODE_1" in r["panel"] for r in data)


def test_render_paired_map(tmp_path):
    rows = _fixture_rows()
    png = tmp_path / "BGC001__BGC002_pair_locus.png"
    csvp = tmp_path / "BGC001__BGC002_pair_locus_data.csv"
    render_locus_map([("BGC001 · NODE_1 · region001 — phosphonate · Edge", rows),
                      ("BGC002 · NODE_2 · region001 — phosphonate · Interior", rows)],
                     png, csvp, suptitle="STRAINX — RG-GMCI HIGH pair BGC001 ↔ BGC002",
                     claim_prefix="PRIVATE")
    assert png.exists() and png.stat().st_size > 0
    with open(csvp) as fh:
        panels = {r["panel"].split(" ")[0] for r in csv.DictReader(fh)}
    assert "BGC001" in panels and "BGC002" in panels


def test_footer_is_claim_safe(tmp_path):
    rows = _fixture_rows()
    png = tmp_path / "m.png"; csvp = tmp_path / "m.csv"
    render_locus_map([("t", rows)], png, csvp, suptitle="s", claim_prefix="PUBLIC")
    # the claim-safe doctrine strings are in the footer constant
    assert "not a product claim" in FOOTER
    assert "KCB = similarity, not identity" in FOOTER


def test_anti_overlap_footer_below_legend(tmp_path):
    """Pin the gray-text fix: the footer artist's y must sit below the legend band y0."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mamey import locus_map
    rows = _fixture_rows()
    # intercept the figure to inspect artist positions
    orig_savefig = plt.Figure.savefig
    captured = {}

    def _spy(self, *a, **k):
        # legend is the last fig.legend; footer is a fig.text at y=0.012
        captured["texts"] = [(t.get_position()[1], t.get_text()) for t in self.texts]
        captured["legends"] = [lg.get_bbox_to_anchor().y0 if hasattr(lg.get_bbox_to_anchor(), "y0")
                               else lg.get_bbox_to_anchor()._bbox.y0 for lg in self.legends]
        return orig_savefig(self, *a, **k)

    plt.Figure.savefig = _spy
    try:
        png = tmp_path / "m.png"; csvp = tmp_path / "m.csv"
        locus_map.render_locus_map([("t", rows)], png, csvp, suptitle="s", claim_prefix="PUBLIC")
    finally:
        plt.Figure.savefig = orig_savefig
    # footer text y (0.012) is below the legend anchor y (0.055)
    footer_ys = [y for y, txt in captured.get("texts", []) if "product claim" in txt]
    assert footer_ys, "footer text not found"
    assert min(footer_ys) < 0.055, "footer must be below the legend band (anti-overlap regressed)"


def test_post_seal_rehydrate_from_sec_met(tmp_path):
    """Post-seal path: rows from sec_met_domains still classify (gene_context shape)."""
    raw = [{"locus_tag": "g1", "start": 0, "end": 1000, "strand": 1,
            "sec_met_domains": ["PKS_KS", "PKS_AT"], "aa_length": 300},
           {"locus_tag": "g2", "start": 1100, "end": 1500, "strand": -1,
            "sec_met_domains": [], "aa_length": 130}]
    rows = cds_rows_from_table(raw)
    assert rows[0]["role"] == "PKS module"
    assert rows[1]["role"] == "other / hypothetical"


# --- in-run integration (standard run produces maps for leads) ---

REF = next((p for p in ["/mnt/user-data/uploads/BGC0000093.zip"] if os.path.exists(p)), None)


@pytest.mark.skipif(REF is None, reason="no public reference present")
def test_in_run_produces_locus_maps(tmp_path):
    """A standard run writes locus maps into the package's locus_maps/ dir."""
    import subprocess, glob
    out = str(tmp_path / "run")
    env = dict(os.environ, PYTHONPATH=".")
    subprocess.run(
        ["python3", "-m", "mamey", "run", "--strain", "LMSMOKE", "--display", "ref",
         "--input-zip", REF, "--taxonomy", "Streptomyces", "--source", "test",
         "--outdir", out, "--mode", "standard", "--release", "PUBLIC",
         "--json-evidence", "bounded", "--brief", "none"],
        check=True, capture_output=True, timeout=300, env=env)
    pkg = glob.glob(os.path.join(out, "**", "package"), recursive=True)[0]
    lm = os.path.join(pkg, "locus_maps")
    assert os.path.isdir(lm), "locus_maps/ dir not created"
    maps = glob.glob(os.path.join(lm, "*_locus.png"))
    assert len(maps) >= 1, "no locus maps rendered in-run"
    # manifest catalogs them
    assert os.path.exists(os.path.join(lm, "locus_map_manifest.csv"))
    # each map has a companion data CSV
    for m in maps:
        assert os.path.exists(m.replace("_locus.png", "_locus_data.csv"))
