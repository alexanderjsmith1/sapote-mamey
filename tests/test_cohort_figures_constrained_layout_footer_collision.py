"""mamey/cohort_figures.py's `_save_pair` never reserved bottom margin for the mandatory
claim-safety footer on any of its 15 `constrained_layout=True` figures.

Found by running the real pipeline (BC2-408): a genuine 2-strain `mamey cohort-figures` run
(AS-705 + AS-747, this cycle's own real deliverable strains -- the one cross-strain surface never
exercised earlier this cycle) followed by opening the rendered PNGs (figure-inspection-before-
send). F03 (`product_class_heatmap`)'s x-axis strain labels ("Streptomyces sp. / strain AS-705",
"strain AS-747") rendered directly through the mandatory claim-safety sentence.

Root cause: `add_claim_safety_footer()` (mamey/figure_theme.py) places the footer at a FIXED
figure-fraction position via plain `fig.text()` calls, and its own docstring requires the caller
reserve >= 0.13 bottom margin first. For a NORMAL figure, `fig.subplots_adjust(bottom=...)` (the
fix already used once this cycle for mamey/domain_figures.py's own footer collision) does that.
But `constrained_layout=True` (used by 15 of this file's figure functions) actively repositions
the axes on every draw -- including the draw triggered by the later `savefig(...,
bbox_inches="tight")` call -- and matplotlib makes `subplots_adjust()` a silent no-op once
constrained_layout is active (its own UserWarning: "not calling subplots_adjust"). So the
one-line domain_figures.py fix does not apply here; the fix instead reserves the margin through
the layout engine's own `rect` API, which constrained_layout genuinely honors.
"""
from __future__ import annotations

import csv
import json
import os

import pytest

mpl = pytest.importorskip("matplotlib")
from mamey import cohort_figures as cf


def test_save_pair_reserves_bottom_margin_on_constrained_layout_figure():
    """Direct test of `_save_pair`'s own fix: a constrained-layout figure passed through it
    must come out with the footer's documented >= 0.13 bottom margin reserved."""
    import matplotlib.pyplot as plt
    import tempfile

    fig, ax = plt.subplots(figsize=(6, 8), constrained_layout=True)
    ax.plot([1, 2, 3])
    with tempfile.TemporaryDirectory() as d:
        cf._save_pair(fig, os.path.join(d, "test_fig.png"))
        engine = fig.get_layout_engine()
        assert engine is not None, "figure should still be using constrained_layout"
        rect = engine.get().get("rect")
        assert rect is not None and rect[1] >= 0.13, (
            f"constrained-layout figure's reserved bottom margin was {rect!r} -- below "
            f"add_claim_safety_footer()'s own documented minimum of 0.13, the exact condition "
            f"that let F03's x-axis labels render through the claim-safety sentence"
        )
    plt.close(fig)


def test_save_pair_is_a_noop_on_non_constrained_layout_figure():
    """Regression guard: a figure that never opted into constrained_layout has no layout engine
    to reserve space on -- `_save_pair` must not raise or otherwise misbehave for it."""
    import matplotlib.pyplot as plt
    import tempfile

    fig, ax = plt.subplots(figsize=(6, 4))  # constrained_layout NOT set (this file's other 10 figures)
    ax.plot([1, 2, 3])
    assert fig.get_layout_engine() is None
    with tempfile.TemporaryDirectory() as d:
        cf._save_pair(fig, os.path.join(d, "test_fig2.png"))  # must not raise
    plt.close(fig)


def _make_pkg(root, sid, tier, release, taxonomy, products, n_bgc=4):
    """Same synthetic gold package as
    tests/test_cohort_figures_product_class_case_insensitive_bc2_399.py::_make_pkg."""
    pkg = os.path.join(root, sid, "package")
    os.makedirs(pkg, exist_ok=True)
    bgc_profile, domain_hits, active_sites, substrates, domain_arch = [], [], [], [], []
    triggers = ["T43-HAL_halogenase", "T43-LAN_lanthipeptide", "T43-THA_thioamide"]
    tiers = ["NULL_NO_SOURCE_DERIVED_RESISTANCE", "T3_TRANSPORTER_ONLY_ROUTING",
             "T2_RESISTANCE_LIKE_SOURCE_DERIVED", "T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED"]
    for i in range(n_bgc):
        bid = f"BGC{i+1:03d}"
        bgc_profile.append({
            "sid": sid, "bgc_id": bid, "resistance_tier": tiers[i % len(tiers)],
            "cctt_triggers": triggers[i % len(triggers)],
            "PKS_KS": i % 3, "PKS_AT": i % 2, "PKS_KR": (i + 1) % 2, "PKS_DH": i % 2,
            "NRPS_C": i % 2, "NRPS_A": (i + 1) % 3, "NRPS_T_PCP": i % 2,
            "TE_release": i % 2, "Transporter": i % 2, "Regulator": (i + 1) % 2,
            "Oxidoreductase": i % 2,
        })
        domain_arch.append({"bgc_id": bid, "architecture": repr({"domain_counts": {
            "PKS_KS": i % 3, "PKS_AT": i % 2, "PKS_KR": (i + 1) % 2, "PKS_DH": i % 2,
            "NRPS_C": i % 2, "NRPS_A": (i + 1) % 3, "NRPS_T_PCP": i % 2, "TE_release": i % 2}})})
        active_sites.append({"domain_id": f"ctg{i+1}_1_PKS_KS", "locus": f"ctg{i+1}_1",
                             "active_site_calls": "His: True, Cys: False"})
        substrates.append({"domain_id": f"ctg{i+1}_1_AMP-binding", "substrate": ["ala", "val", "ser"][i % 3]})
        substrates.append({"domain_id": f"ctg{i+1}_2_PKS_AT", "substrate": ["mal", "mmal"][i % 2]})
    for p in ["PKS_KS", "AMP-binding", "Condensation", "Trp_halogenase", "Glyco_hydro_18",
              "ABC_tran", "MFS_1", "TetR_N", "GntR", "IucA_IucC", "FhuF", "LANC_like"]:
        for _ in range(3):
            domain_hits.append({"pfam": p, "tier1": p in ("PKS_KS", "AMP-binding", "Condensation")})
    json.dump({"bgc_profile": bgc_profile, "domain_hits": domain_hits, "active_sites": active_sites},
              open(os.path.join(pkg, "deep_data.json"), "w"))
    json.dump({"substrates": substrates, "domain_arch": domain_arch, "ripp": [{"family": "lanthipeptides"}]},
              open(os.path.join(pkg, "gene_data.json"), "w"))
    json.dump({"assembly_tier": tier, "raw_bgcs": n_bgc, "corrected_bgcs": n_bgc,
               "release": release, "taxonomy": taxonomy},
              open(os.path.join(pkg, "manifest_short.json"), "w"))
    with open(os.path.join(pkg, f"{sid}_2_inventory.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["BGC_ID", "Products"])
        for i in range(n_bgc):
            w.writerow([f"BGC{i+1:03d}", products[i % len(products)]])
    return pkg


def test_real_two_strain_cohort_run_renders_without_raising(tmp_path):
    """End-to-end smoke check, mirroring the real repro: a genuine 2-strain cohort run through
    `cf.generate()` must complete and produce the F03 heatmap (the figure the real collision was
    found on) without error, on the fixed `_save_pair`."""
    runs = tmp_path / "runs"
    _make_pkg(str(runs), "SID9101", "GOOD", "PUBLIC", "Streptomyces sp.",
              products=["NRPS", "T1PKS", "terpene"], n_bgc=5)
    _make_pkg(str(runs), "SID9102", "GOOD", "PUBLIC", "Streptomyces sp.",
              products=["PKS", "T1PKS", "saccharide"], n_bgc=6)
    out = tmp_path / "figs"
    res = cf.generate(runs_dir=str(runs), out=str(out))
    assert res["figures"] >= 1, res
    import glob
    assert glob.glob(str(out / "*product_class_heatmap.png")), "F03 was not produced"
