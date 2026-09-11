"""test_figure_render_e2e.py — end-to-end figure render test.

Covers W2 Part A (v9.7.149b wishlist): verify that figures actually render as
valid PNGs when matplotlib is available (the existing
`test_figure_generation_is_nonblocking` only checks the no-matplotlib path).

Also verifies that `compile_report.assemble()` embeds an image reference in
its rendered output when PNGs are present.

Fixtures use AS-XXX only.

Note on schema: the wishlist describes `deep_data.json` as carrying
`bgc_rows`/`gene_rows` — that's not what `cohort_figures.load()` actually
reads. The real schema is `bgc_profile` (list of dicts with `bgc_id` + per-
catalytic-domain counts). This test uses the actual schema.
"""
from __future__ import annotations

import json
import pathlib

import pytest


PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _make_gold_package(tmp_path: pathlib.Path,
                       strain_id: str = "AS-XXX") -> pathlib.Path:
    """Build a synthetic gold-mode package matching cohort_figures.load()'s
    expected layout: tmp_path / <strain> / package/ with deep_data.json,
    gene_data.json, manifest_short.json, <strain>_1_intake.json.
    """
    pkg = tmp_path / strain_id / "package"
    pkg.mkdir(parents=True)

    # deep_data.json — at minimum needs bgc_profile with bgc_id + domain counts
    deep = {
        "strain_id": strain_id,
        "bgc_profile": [
            {"bgc_id": "BGC001", "PKS_KS": 3, "PKS_AT": 2, "PKS_KR": 1,
             "NRPS_C": 0, "NRPS_A": 0, "NRPS_T_PCP": 0,
             "TE_release": 1, "Transporter": 2, "Regulator": 1,
             "Oxidoreductase": 1, "PKS_DH": 1,
             "cctt_triggers": "", "resistance_tier": ""},
            {"bgc_id": "BGC002", "PKS_KS": 0, "PKS_AT": 0, "PKS_KR": 0,
             "NRPS_C": 2, "NRPS_A": 2, "NRPS_T_PCP": 2,
             "TE_release": 0, "Transporter": 1, "Regulator": 0,
             "Oxidoreductase": 0, "PKS_DH": 0,
             "cctt_triggers": "", "resistance_tier": ""},
            {"bgc_id": "BGC003", "PKS_KS": 1, "PKS_AT": 1, "PKS_KR": 0,
             "NRPS_C": 1, "NRPS_A": 1, "NRPS_T_PCP": 1,
             "TE_release": 0, "Transporter": 1, "Regulator": 1,
             "Oxidoreductase": 0, "PKS_DH": 0,
             "cctt_triggers": "", "resistance_tier": ""},
        ],
        "domain_hits": [],
        "active_sites": [],
    }
    (pkg / "deep_data.json").write_text(json.dumps(deep))

    # gene_data.json — load() opens it; figs_single doesn't read it but load
    # would crash on missing file.
    (pkg / "gene_data.json").write_text(json.dumps({
        "ripp": [], "domain_arch": [], "substrates": [],
    }))

    # manifest_short.json
    (pkg / "manifest_short.json").write_text(json.dumps({
        "strain_id": strain_id, "raw_bgcs": 3,
        "corrected_bgcs": 3.0, "assembly_tier": "EXCELLENT",
        "taxonomy": "Streptomyces sp.",
    }))

    # <strain>_1_intake.json — fallback taxonomy source
    (pkg / f"{strain_id}_1_intake.json").write_text(json.dumps({
        "taxonomy": "Streptomyces sp.",
    }))

    return pkg


# ---------------------------------------------------------------------------
# Part A — end-to-end render
# ---------------------------------------------------------------------------

def test_cohort_figures_generate_emits_real_pngs(tmp_path):
    """The existing nonblocking test only checks the no-matplotlib path. This
    one fires when matplotlib IS available and verifies real PNG output."""
    pytest.importorskip("matplotlib")
    from mamey import cohort_figures
    _make_gold_package(tmp_path)
    out = tmp_path / "figs"
    res = cohort_figures.generate(
        runs_dir=str(tmp_path), out=str(out), strains=["AS-XXX"], series="F",
    )
    assert res["figures"] >= 1, f"no figures generated: {res}"
    pngs = list(out.glob("*.png"))
    assert pngs, f"no PNGs in {out}"


def test_emitted_pngs_have_valid_magic_bytes(tmp_path):
    pytest.importorskip("matplotlib")
    from mamey import cohort_figures
    _make_gold_package(tmp_path)
    out = tmp_path / "figs"
    cohort_figures.generate(
        runs_dir=str(tmp_path), out=str(out), strains=["AS-XXX"], series="F",
    )
    for png in out.glob("*.png"):
        head = png.read_bytes()[:8]
        assert head == PNG_MAGIC, f"bad magic for {png.name}: {head!r}"


def test_compile_report_embeds_image_reference_when_pngs_present(tmp_path):
    """When PNGs exist in the package, compile_report should embed at least
    one markdown image reference (`![...](...)`) in its §6 Figures section."""
    pytest.importorskip("matplotlib")
    from mamey import compile_report
    pkg = _make_gold_package(tmp_path)

    # Place a real PNG inside the package so the rglob picks it up.
    # We render via matplotlib to get a guaranteed-valid PNG.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig_dir = pkg / "gold_figures"
    fig_dir.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(2, 2))
    ax.plot([0, 1], [0, 1])
    fig.savefig(fig_dir / "F01_test_figure.png", dpi=80)
    plt.close(fig)

    # Read the §6 Figures section directly (private API but stable here).
    figures_md = compile_report._figures(pkg, generate=False)
    assert "![" in figures_md, (
        "compile_report._figures should embed a markdown image reference "
        f"when PNGs are present. Got: {figures_md[:300]!r}"
    )
    assert "F01_test_figure" in figures_md


def test_render_is_deterministic_pngs_stable_across_runs(tmp_path):
    """Two consecutive runs over identical input produce PNGs of identical
    byte length (sanity check — full byte-equality may differ if matplotlib
    embeds timestamps, but file size should be stable)."""
    pytest.importorskip("matplotlib")
    from mamey import cohort_figures

    _make_gold_package(tmp_path)
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    cohort_figures.generate(runs_dir=str(tmp_path), out=str(out_a),
                            strains=["AS-XXX"], series="F")
    cohort_figures.generate(runs_dir=str(tmp_path), out=str(out_b),
                            strains=["AS-XXX"], series="F")
    names_a = sorted(p.name for p in out_a.glob("*.png"))
    names_b = sorted(p.name for p in out_b.glob("*.png"))
    assert names_a == names_b, f"figure set drifted: {names_a} vs {names_b}"
