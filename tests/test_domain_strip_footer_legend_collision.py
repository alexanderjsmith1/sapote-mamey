"""mamey/domain_figures.py: the domain-strip figure's role legend visually collided with the
mandatory claim-safety footer.

Found by running the real pipeline (BC2-408): `mamey domain-level --emit-figures` against this
cycle's own real AS-705 package, then visually inspecting the rendered PNGs (figure-inspection-
before-send). `AS705_BGC031_domain_strip.png`'s legend swatches/labels ("PKS domain", "PKS
ketosynthase", ...) rendered directly on top of the bold claim-safety sentence every figure in this
project must carry legibly: "Similarity is not identity; capacity is not production; missing or
unbound evidence is not biological absence."

Root cause: `mamey.figure_theme.add_claim_safety_footer()`'s own docstring states its contract
plainly: "Callers should reserve a bottom margin of at least 0.13 before invoking this helper."
`_render_domain_strips()` never reserved any bottom margin, and its role legend sits at
axes-fraction y=-0.05 (just below the axes) -- on a strip plot whose axes occupy nearly the full
figure height, that lands almost exactly where the footer text is placed (figure-fraction
y=0.052/0.029/0.008), so the two collide. The sibling `_render_core_burden()` figure was unaffected
because its own legend is anchored ABOVE the axes, not below.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")

from mamey import domain_figures as dfig


def _rows():
    return [
        {"Strain": "AS-TEST", "BGC_ID": "BGC001", "Assembly_Locator": "NODE_1_length_5000 region001",
         "locus_tag": "ctg1_0", "cds_start": "100", "cds_end": "400", "strand": "1",
         "domain_name": "PKS_KS", "domain_role_category": "PKS ketosynthase"},
        {"Strain": "AS-TEST", "BGC_ID": "BGC001", "Assembly_Locator": "NODE_1_length_5000 region001",
         "locus_tag": "ctg1_1", "cds_start": "600", "cds_end": "900", "strand": "1",
         "domain_name": "PKS_AT", "domain_role_category": "PKS acyltransferase/loading"},
    ]


def _complexity():
    return [{"BGC_ID": "BGC001", "Biosynthetic_core_domain_count": "2"}]


def test_domain_strip_reserves_the_documented_footer_margin(tmp_path, monkeypatch):
    """add_claim_safety_footer()'s own contract: callers must reserve >= 0.13 of bottom margin.
    Assert the figure this function builds actually does, before it's saved and closed."""
    import matplotlib.pyplot as plt

    captured = {}

    def _fake_save_pair(fig, png, *, source, rows):
        # capture the figure's own reserved bottom margin before the real code would close it
        captured["bottom"] = fig.subplotpars.bottom
        plt.close(fig)

    monkeypatch.setattr(dfig, "_save_pair", _fake_save_pair)

    specs = dfig._load_specs()
    result = {"figures": [], "manifest_rows": [], "warnings": []}
    dfig._render_domain_strips(_rows(), _complexity(), tmp_path, specs, plt, result, top_n=1)

    assert "bottom" in captured, "the figure was never saved -- _render_domain_strips did not run"
    assert captured["bottom"] >= 0.13, (
        f"bottom margin reserved was {captured['bottom']!r}, below add_claim_safety_footer()'s own "
        f"documented minimum of 0.13 -- the mandatory claim-safety text and the role legend will "
        f"visually collide, exactly as observed on the real AS-705/BGC031 render"
    )
