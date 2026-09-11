"""Governed Sapote-Mamey figure theme and export helpers.

This module controls presentation only. It does not change scan results,
scoring, biological interpretation, or release state. Callers remain
responsible for exact-locus binding and source-specific claim ceilings.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
# v9.7.410 (CLAUDE_410 savefig OOM sweep): clamp publication DPI under the Agg pixel
# ceiling before every raster write. See mamey/render_safe.py::safe_savefig_dpi.
from .render_safe import safe_savefig_dpi as _safe_dpi


CLAIM_SAFETY = (
    "Similarity is not identity; capacity is not production; "
    "missing or unbound evidence is not biological absence."
)

SVG_HASH_SALT = "sapote-mamey-governed-figure-theme-v1"

PALETTE = {
    "navy": "#0B2A3D",
    "teal": "#148C8C",
    "teal_light": "#8FD3C7",
    "gold": "#D7A33D",
    "cream": "#F7F2E7",
    "coral": "#E76F51",
    "ink": "#17252D",
    "muted": "#60747D",
    "grid": "#D8E0E3",
    "white": "#FFFFFF",
}


@dataclass(frozen=True)
class FigureProfile:
    name: str
    width_in: float
    height_in: float
    dpi: int = 300
    minimum_text_pt: float = 8.0


PROFILES = {
    "screen": FigureProfile("screen", 13.333, 7.5, 300, 10.0),
    "manuscript": FigureProfile("manuscript", 7.2, 5.0, 300, 8.0),
    "poster": FigureProfile("poster", 20.0, 12.0, 300, 13.0),
}

WORKFLOW_STYLES = {
    "OBSERVED": {"color": PALETTE["teal"], "hatch": "", "marker": "o"},
    "NO_SIGNIFICANT_EXACT_BOUND_HIT": {"color": PALETTE["grid"], "hatch": "..", "marker": "x"},
    "NOT_RETURNED": {"color": PALETTE["gold"], "hatch": "//", "marker": "^"},
    "UNBOUND": {"color": PALETTE["coral"], "hatch": "xx", "marker": "s"},
    "NOT_RUN": {"color": PALETTE["cream"], "hatch": "--", "marker": "_"},
}


def exact_locus_identity(strain: str, full_node_or_contig: str, region: str, bgc_alias: str) -> str:
    """Return the permanent four-part display identity or fail closed."""
    parts = [str(strain).strip(), str(full_node_or_contig).strip(), str(region).strip(), str(bgc_alias).strip()]
    if not all(parts):
        raise ValueError("Complete strain / full node-or-contig / region / BGC alias identity required")
    if not parts[2].lower().startswith("region"):
        raise ValueError(f"Region token must begin with 'region': {parts[2]!r}")
    return " / ".join(parts)


def normalize_workflow_state(raw: str) -> str:
    """Map detailed frozen states to display states without inventing negatives."""
    token = str(raw or "").upper()
    if token.startswith("OBSERVED_SIGNIFICANT"):
        return "OBSERVED"
    if "NO_EXACT" in token or "NO_SIGNIFICANT" in token:
        return "NO_SIGNIFICANT_EXACT_BOUND_HIT"
    if "NOT_RETURNED" in token or "UNRETURNED" in token:
        return "NOT_RETURNED"
    if "UNBOUND" in token:
        return "UNBOUND"
    if "NOT_RUN" in token or "PENDING" in token:
        return "NOT_RUN"
    return "UNBOUND"


def workflow_style(raw: str) -> dict[str, str]:
    """Return a copy of the redundant color/pattern/marker encoding."""
    return dict(WORKFLOW_STYLES[normalize_workflow_state(raw)])


def resolve_palette(variant: str | None = None) -> dict[str, str]:
    """Colour tokens for `variant`, taken from `report_theme` when it is available.

    v9.7.405 reconciliation: `mamey/report_theme.py` (the CODEX_390 governed theme) and this
    module both named a palette with the SAME token keys — navy, teal, gold, cream, muted, grid.
    PALETTE below is a frozen snapshot of one report_theme variant, so leaving both in place
    would have created two sources of truth for the same colour and let a user-selected theme
    variant silently disagree with the publication renderer. `report_theme` is the governed,
    user-selectable owner of COLOUR; this module owns PROFILE geometry, typography, the
    claim-safety footer and the paired PNG/SVG export. When report_theme is importable and a
    variant is named, its tokens win; PALETTE is the fallback for a tier that ships without it.
    report_theme stores hex WITHOUT a leading '#', so it is normalised here.
    """
    if variant:
        try:
            from .report_theme import theme_variant as _tv
        except Exception:
            _tv = None
        if _tv is not None:
            try:
                tokens = _tv(str(variant))["tokens"]["colors"]
            except Exception:
                tokens = None
            if tokens:
                resolved = dict(PALETTE)
                for key, value in tokens.items():
                    text = str(value)
                    resolved[key] = text if text.startswith("#") else "#" + text
                return resolved
    return dict(PALETTE)


def apply_theme(plt: Any, profile: str = "screen", variant: str | None = None) -> FigureProfile:
    """Apply the deterministic visual theme to a matplotlib pyplot module.

    `variant` is optional and, when given, routes colour through `resolve_palette` so a caller
    that already selected a governed report_theme variant does not get this module's snapshot
    colours instead of the ones the operator asked for.
    """
    if profile not in PROFILES:
        raise ValueError(f"Unknown figure profile: {profile!r}")
    spec = PROFILES[profile]
    palette = resolve_palette(variant)
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": max(8.0, spec.minimum_text_pt),
        "axes.titlesize": max(13.0, spec.minimum_text_pt * 1.45),
        "axes.titleweight": "bold",
        "axes.labelcolor": palette["ink"],
        "axes.edgecolor": palette["navy"],
        "axes.prop_cycle": plt.cycler(color=[palette["navy"], palette["teal"], palette["gold"], palette["coral"]]),
        "figure.facecolor": palette["cream"],
        "axes.facecolor": palette["white"],
        "grid.color": palette["grid"],
        "grid.linewidth": 0.7,
        "legend.frameon": False,
        "svg.fonttype": "none",
        "savefig.facecolor": palette["cream"],
    })
    return spec


def add_claim_safety_footer(fig: Any, *, provenance: str = "", authority: str = "Candidate Only") -> None:
    """Add a readable, non-promotional two-line footer to a figure.

    The claim ceiling and provenance deliberately occupy separate lines.  A
    single left/right line can collide at manuscript width even when each
    string is individually short enough for a screen figure.  Callers should
    reserve a bottom margin of at least 0.13 before invoking this helper.
    """
    from matplotlib.lines import Line2D

    fig.add_artist(Line2D([0.01, 0.99], [0.052, 0.052], transform=fig.transFigure,
                          color=PALETTE["grid"], linewidth=0.55))
    fig.text(0.01, 0.029, CLAIM_SAFETY, ha="left", va="bottom", fontsize=7.0,
             color=PALETTE["navy"], weight="bold")
    suffix = " | ".join(part for part in (provenance, authority) if part)
    if suffix:
        fig.text(0.01, 0.008, suffix, ha="left", va="bottom", fontsize=6.1,
                 color=PALETTE["muted"])


def save_figure_pair(fig: Any, stem: str | Path, *, profile: str = "screen") -> tuple[Path, Path]:
    """Write SVG plus 300-dpi PNG from one figure and return both paths."""
    from matplotlib import rc_context

    if profile not in PROFILES:
        raise ValueError(f"Unknown figure profile: {profile!r}")
    spec = PROFILES[profile]
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    png = stem.with_suffix(".png")
    svg = stem.with_suffix(".svg")
    fig.savefig(png, dpi=_safe_dpi(fig, spec.dpi), bbox_inches="tight",
                metadata={"Software": "Sapote-Mamey governed figure theme"})
    # Matplotlib otherwise seeds SVG element IDs from process entropy.  Scope the
    # fixed salt to this one export so callers' rcParams and PNG behavior remain
    # unchanged, including when savefig raises.
    with rc_context({"svg.hashsalt": SVG_HASH_SALT}):
        fig.savefig(svg, bbox_inches="tight",
                    metadata={"Creator": "Sapote-Mamey governed figure theme", "Date": None})
    return png, svg
