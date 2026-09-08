"""Interactive-figure bridge for Sapote-Mamey.

This subpackage vendors Codex's self-contained widget-to-publication bridge
(`publication_bridge`) and adds `widget_data`, an emitter that builds the
widget-data aggregate FROM sealed Mamey packages. Together they let the Codex
interactive widgets + publication figures run directly on this engine's output.

`codex_heatmap_pack` is a dependency-free post-seal converter for Figure
Factory matrix sidecars. It emits vector SVG panels, portable HTML, caption and
methods text, and a checksum receipt. It is explicitly optional and does not
elevate extraction, release, biological, or publication gates.

`figure_set_registry` defines the governed 200-set Codex Figure Factory design
catalog. It includes strain-specific and cohort-specific lenses, source/gate
contracts, missingness semantics, captions, methods, and readiness states.

`publication_bridge` imports without its optional render-only dependencies
(reportlab / pypdf / pypdfium2 / Pillow); those are needed only for the
build/render path. `widget_data` never depends on them.
"""

from __future__ import annotations

# v9.7.405: `publication_bridge` and `build_widget_data` are resolved lazily (PEP 562) instead
# of at package import. Importing `widget_data` eagerly pulled in `mamey.exclusions`, whose
# OFFICIAL_DATA/ lookup emits a RuntimeWarning in any workspace that has an OFFICIAL_DATA/
# directory above the tree — and that warning landed on stderr of every optional figure tool
# (component/theme galleries) whose contract is "stderr carries one JSON diagnostic".
# Gallery and theme tools never need cohort data; nothing should pay for it at import time.
_LAZY_EXPORTS = {
    "publication_bridge": ("publication_bridge", None),
    "build_widget_data": ("widget_data", "build_widget_data"),
}


def __getattr__(name):  # PEP 562 lazy attribute resolution
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib
    module = importlib.import_module(f".{target[0]}", __name__)
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def build_codex_heatmap_pack(*args, **kwargs):
    """Lazy re-export; keeps ``python -m ...codex_heatmap_pack`` warning-free."""
    from .codex_heatmap_pack import build_codex_heatmap_pack as _build
    return _build(*args, **kwargs)


def build_codex_figure_registry(*args, **kwargs):
    """Lazy re-export for the optional 200-set registry emitter."""
    from .figure_set_registry import emit_registry as _emit
    return _emit(*args, **kwargs)


def render_codex_figure_sets(*args, **kwargs):
    """Lazy re-export for implemented registry figure-set tranches."""
    from .figure_set_renderer import render_tranche as _render
    return _render(*args, **kwargs)


def build_codex_figure_sources(*args, **kwargs):
    """Lazy re-export for the sealed-package figure source bundler."""
    from .figure_source_bundle import build_source_bundle as _build
    return _build(*args, **kwargs)


def render_codex_figure_sets_tranche_2(*args, **kwargs):
    """Lazy re-export for source-bundle-backed figure-set tranche 2."""
    from .figure_set_renderer_tranche2 import render_tranche_2 as _render
    return _render(*args, **kwargs)


def render_codex_figure_sets_tranche_3(*args, **kwargs):
    """Lazy re-export for sealed-evidence figure-set tranche 3."""
    from .figure_set_renderer_tranche3 import render_tranche_3 as _render
    return _render(*args, **kwargs)


def render_codex_figure_atlas(*args, **kwargs):
    """Lazy re-export for all implemented figure-set tranches."""
    from .figure_atlas import render_implemented_atlas as _render
    return _render(*args, **kwargs)


def render_codex_figure_sets_tranche_4(*args, **kwargs):
    """Lazy re-export for tailoring/regulator figure-set tranche 4."""
    from .figure_set_renderer_tranche4 import render_tranche_4 as _render
    return _render(*args, **kwargs)


def render_codex_figure_sets_tranche_5(*args, **kwargs):
    """Lazy re-export for the 92-set extended-evidence tranche."""
    from .figure_set_renderer_tranche5 import render_tranche_5 as _render
    return _render(*args, **kwargs)


def render_codex_figure_sets_tranche_6(*args, **kwargs):
    """Lazy re-export for ledger-gated lead-context figure sets."""
    from .figure_set_renderer_tranche6 import render_tranche_6 as _render
    return _render(*args, **kwargs)


def render_bigscape_figure_extension(*args, **kwargs):
    """Lazy re-export for the optional eight-view BiG-SCAPE extension."""
    from .bigscape_extension import render_bigscape_extension as _render
    return _render(*args, **kwargs)


__all__ = [
    "publication_bridge", "build_widget_data", "build_codex_heatmap_pack",
    "build_codex_figure_registry", "render_codex_figure_sets", "build_codex_figure_sources",
    "render_codex_figure_sets_tranche_2",
    "render_codex_figure_sets_tranche_3",
    "render_codex_figure_atlas",
    "render_codex_figure_sets_tranche_4",
    "render_codex_figure_sets_tranche_5",
    "render_codex_figure_sets_tranche_6",
    "render_bigscape_figure_extension",
]
