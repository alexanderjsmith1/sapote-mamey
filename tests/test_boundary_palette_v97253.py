"""PC-1 (v9.7.253 Bunny Hop session 2): drift-proof the boundary-tier palette.

`mamey/boundary_palette.py` exists to be the single source of truth for BGC boundary-tier
colours, precisely so the same tier can't drift to different colours across figure modules.
Before this test that centralizer was itself untested, so nothing pinned (a) the schemes'
shape or (b) that the figure modules actually import from it rather than re-inlining literals.
"""
from pathlib import Path

from mamey import boundary_palette as bp

_CORE_TIERS = {"Interior", "Edge", "Full-contig"}
_REPO = Path(__file__).resolve().parent.parent


def test_schemes_cover_the_core_tiers():
    for scheme in (bp.BLUE_GRADIENT, bp.TRAFFIC_LIGHT):
        assert _CORE_TIERS <= set(scheme), f"scheme missing a core tier: {_CORE_TIERS - set(scheme)}"


def test_canonical_is_traffic_light():
    # The docstring names TRAFFIC_LIGHT as the recommended scheme for new figures.
    assert bp.CANONICAL is bp.TRAFFIC_LIGHT


def test_all_values_are_hex_colours():
    for scheme in (bp.BLUE_GRADIENT, bp.TRAFFIC_LIGHT):
        for tier, colour in scheme.items():
            assert isinstance(colour, str) and colour.startswith("#") and len(colour) == 7, \
                f"{tier} -> {colour!r} is not a #rrggbb hex"


def test_figure_modules_import_from_the_centralizer():
    # The whole point of the module: figure code sources its boundary colours HERE, not from
    # re-inlined literals. Assert on source text so this holds even without importing matplotlib.
    smoke = (_REPO / "mamey" / "figures_smoke.py").read_text(encoding="utf-8")
    sapote = (_REPO / "mamey" / "figures_sapote.py").read_text(encoding="utf-8")
    assert "from .boundary_palette import BLUE_GRADIENT" in smoke
    assert "from .boundary_palette import TRAFFIC_LIGHT" in sapote
