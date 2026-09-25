"""v9.7.50 — the deterministic Sapote figures module is importable and exposes its contract.
End-to-end emission is verified at integration (a real `mamey run --brief standard` writes 8c/8d/8e/8f
PNG+CSV); this guards the module surface so the render_brief wiring can't silently break."""
import mamey.figures_sapote as fs


def test_render_entrypoint_exists():
    assert callable(fs.render_sapote_figures)


def test_tunable_defaults_present():
    assert fs.LEAD_AB_MIN == 70.0 and fs.LEAD_AF_MIN == 44.0 and fs.RANK_TOPN == 30


def test_boundary_weights_match_corrected_count():
    assert fs._BW == {"Interior": 1.0, "Edge": 0.5, "Full-contig": 0.25}


def test_footer_draws_no_claim_wording():
    # v9.7.442 ruling: no claim wording on figures. The footer keeps only the plot key the caller
    # passes; SCORE_NOTE / KCB_NOTE stay in the _data.csv provenance row.
    from mamey.figure_policy import FIGURE_BANNED_TEXT
    assert fs._foot() == ""
    foot = fs._foot("dashed line = lead threshold")
    assert foot == "dashed line = lead threshold"
    assert "capacity-level" not in foot and not FIGURE_BANNED_TEXT.search(foot)
