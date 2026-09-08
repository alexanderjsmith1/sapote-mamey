"""Static, data-free SVG component gallery for Sapote-Mamey reports.

The gallery demonstrates reusable figure compositions without reading a run
package or interpreting biological evidence.  It builds on the separately
proposed theme gallery and emits plain SVG plus a compact JSON contract that a
later document or widget renderer can consume.
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from ..console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from mamey.console import emit

import argparse
import html
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from .optional_output import OutputRefusal, logical_artifact_locator, write_output_bundle
from .theme_gallery import PROTOTYPE_STATUS, SCOPE_NOTE, Theme, theme_profiles


SCHEMA_VERSION = "sapote_mamey.figure_component_gallery.v1"
COMPONENT_STATUS = "STATIC_COMPONENT_PROTOTYPE_NOT_RUNTIME_WIRED"
DEFAULT_THEME_ID = "evidence-navy"


@dataclass(frozen=True)
class ComponentSpec:
    """One reusable, claim-bounded figure composition."""

    component_id: str
    name: str
    purpose: str
    required_fields: tuple[str, ...]
    caption_pattern: str
    claim_ceiling: str
    alt_text: str


COMPONENTS: tuple[ComponentSpec, ...] = (
    ComponentSpec(
        "three-channel-evidence",
        "Three-Channel Evidence Matrix",
        "Keep nr, ClusteredNR, and local Swiss-Prot observations visibly separate for each governed gene.",
        ("gene_id", "protein_sha256", "nr_state", "clusterednr_state", "local_swissprot_state"),
        "Per-gene evidence availability across three separately governed similarity channels; gaps are workflow states.",
        "Similarity may support enzyme-family capacity only; it does not establish identity, production, or activity.",
        "A matrix with three named evidence channels and patterned cells for unavailable workflow states.",
    ),
    ComponentSpec(
        "gene-role-reaction-ledger",
        "Gene-Role and Reaction Ledger",
        "Show committed chemistry, complementary maturation, control functions, and inconclusive assignments as distinct lanes.",
        ("gene_id", "protein_sha256", "role_lane", "reaction_or_function", "evidence_state", "alternatives"),
        "Source-bound gene roles arranged by biosynthetic function; arrows indicate a proposed reading order, not proven flux.",
        "Proposed order and precursor flow remain hypotheses until the relevant biochemical evidence is available.",
        "Four role lanes with generic gene tokens and a dashed proposed reaction path.",
    ),
    ComponentSpec(
        "locus-architecture",
        "Locus Architecture Strip",
        "Display region boundaries, gene direction, role class, and interval uncertainty without implying physical linkage outside the region.",
        ("full_node_or_contig", "region", "gene_id", "start", "end", "strand", "role_lane"),
        "Exact region architecture with direction and role-class encoding; boundary observations are shown explicitly.",
        "Proximity within a displayed region is not pathway identity, co-regulation, production, or off-region linkage.",
        "A bounded region strip containing directional gene arrows grouped by generic role colors.",
    ),
    ComponentSpec(
        "comparison-availability",
        "Comparison Availability Board",
        "Disposition frozen comparator streams before drawing any cohort or type-level conclusion.",
        ("stream", "state", "source_locator", "source_sha256", "binding_status"),
        "Availability and binding state for local comparison streams; unavailable or unbound sources remain typed holds.",
        "Availability, similarity, or co-occurrence does not establish pathway identity, novelty, production, or activity.",
        "Five comparator streams with observed, pending, unavailable, and unbound states shown separately.",
    ),
    ComponentSpec(
        "evidence-stage-ladder",
        "Evidence-Stage Ladder",
        "Display distinct evidence objects and their source-object requirements without ranking them as permissions or proof.",
        ("evidence_stage", "source_object_type", "source_locator", "source_sha256", "observation_state"),
        "Distinct sequence, culture, structure, assay, and host-study evidence objects shown with their independent source requirements.",
        "The stages identify different source-object categories; they do not form an authorization or inference hierarchy.",
        "Five separately sourced evidence stages arranged as a connected sequence of neutral panels.",
    ),
)


def component_specs() -> tuple[ComponentSpec, ...]:
    """Return the ordered component registry."""
    return COMPONENTS


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _theme(theme_id: str) -> Theme:
    for theme in theme_profiles():
        if theme.theme_id == theme_id:
            return theme
    choices = ", ".join(theme.theme_id for theme in theme_profiles())
    raise ValueError(f"Unknown theme_id {theme_id!r}; expected one of: {choices}")


def _text(x: int, y: int, value: str, theme: Theme, *, size: int = 12, weight: int = 400,
          color: str | None = None, anchor: str = "start") -> str:
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
        f'font-family="Arial, Helvetica, sans-serif" font-size="{size}" '
        f'font-weight="{weight}" fill="{color or theme.ink}">{_esc(value)}</text>'
    )


def _panel_frame(theme: Theme, title: str, subtitle: str, body: str, *, width: int = 660,
                 height: int = 300) -> str:
    return (
        f'<rect width="{width}" height="{height}" rx="14" fill="{theme.card}" stroke="{theme.line}"/>'
        + _text(22, 31, title, theme, size=17, weight=700)
        + _text(22, 51, subtitle, theme, size=10, color=theme.muted)
        + body
    )


def _evidence_matrix(theme: Theme) -> str:
    cols = ("nr", "ClusteredNR", "Local Swiss-Prot")
    rows = ("gene_A", "gene_B", "gene_C", "gene_D")
    states = (
        ("Observed", "Unreturned", "Observed"),
        ("Observed", "Observed", "Unbound"),
        ("Unreturned", "Unreturned", "Observed"),
        ("Observed", "Unbound", "Unreturned"),
    )
    fills = {"Observed": theme.secondary, "Unreturned": theme.paper, "Unbound": theme.caution}
    body = [_text(148 + index * 132, 82, name, theme, size=9, weight=700, anchor="middle") for index, name in enumerate(cols)]
    for row_idx, row in enumerate(rows):
        y = 102 + row_idx * 36
        body.append(_text(24, y + 20, row, theme, size=10, weight=700))
        for col_idx, state in enumerate(states[row_idx]):
            x = 82 + col_idx * 132
            pattern = ''
            if state == "Unreturned":
                pattern = f'<path d="M{x+4},{y+26} L{x+34},{y+4} M{x+34},{y+26} L{x+64},{y+4} M{x+64},{y+26} L{x+94},{y+4}" stroke="{theme.muted}" stroke-width="1" opacity=".65"/>'
            body.append(f'<g><rect x="{x}" y="{y}" width="116" height="28" rx="4" fill="{fills[state]}" stroke="{theme.line}"/>{pattern}' + _text(x + 58, y + 19, state, theme, size=8, weight=700, anchor="middle") + f'<title>{_esc(row)} · {_esc(cols[col_idx])} · {_esc(state)}</title></g>')
    body.append(_text(24, 270, "Workflow states are not biological negatives", theme, size=9, weight=700, color=theme.caution))
    return _panel_frame(theme, "Three-Channel Evidence Matrix", "Channels Stay Separate · Protein SHA Binding Required", ''.join(body))


def _reaction_ledger(theme: Theme) -> str:
    lanes = (
        ("Committed Chemistry", theme.primary, ("gene_A", "gene_B")),
        ("Maturation and Tailoring", theme.secondary, ("gene_C", "gene_D", "gene_E")),
        ("Transport · Regulation · Resistance", theme.accent, ("gene_F", "gene_G")),
        ("Inactive or Inconclusive", theme.muted, ("gene_H",)),
    )
    body: list[str] = []
    for index, (label, color, genes) in enumerate(lanes):
        y = 78 + index * 48
        body.append(_text(22, y + 17, label, theme, size=9, weight=700))
        body.append(f'<line x1="205" y1="{y+14}" x2="620" y2="{y+14}" stroke="{theme.line}"/>')
        for gene_idx, gene in enumerate(genes):
            x = 220 + gene_idx * 115
            body.append(f'<rect x="{x}" y="{y}" width="92" height="28" rx="5" fill="{color}" opacity=".92"/>' + _text(x + 46, y + 19, gene, theme, size=9, weight=700, anchor="middle", color=theme.paper if color != theme.accent else theme.ink))
    body.append(f'<path d="M220,246 C300,275 430,275 565,246" fill="none" stroke="{theme.primary}" stroke-width="2" stroke-dasharray="6 5" marker-end="url(#arrow-{theme.theme_id})"/>')
    body.append(_text(392, 284, "Proposed Reading Order · Alternatives Retained", theme, size=9, weight=700, anchor="middle"))
    return _panel_frame(theme, "Gene-Role and Reaction Ledger", "Gene-Level Roles Before Narrative Prose", ''.join(body))


def _locus_strip(theme: Theme) -> str:
    roles = (theme.primary, theme.primary, theme.secondary, theme.secondary, theme.accent, theme.muted, theme.secondary, theme.primary)
    body = [f'<rect x="28" y="92" width="604" height="112" rx="7" fill="{theme.paper}" stroke="{theme.line}"/>',
            _text(36, 83, "Exact Region Boundary", theme, size=9, weight=700),
            f'<line x1="50" y1="150" x2="610" y2="150" stroke="{theme.line}" stroke-width="2"/>']
    for index, color in enumerate(roles):
        x = 55 + index * 66
        direction = 1 if index not in (4, 5) else -1
        if direction == 1:
            points = f"{x},132 {x+49},132 {x+61},150 {x+49},168 {x},168"
        else:
            points = f"{x+61},132 {x+12},132 {x},150 {x+12},168 {x+61},168"
        body.append(f'<polygon points="{points}" fill="{color}" stroke="{theme.card}" stroke-width="2"><title>gene_{index+1} · generic role class</title></polygon>')
    body.extend((_text(52, 222, "Boundary-Proximal", theme, size=9, color=theme.muted),
                 _text(608, 222, "Boundary-Proximal", theme, size=9, color=theme.muted, anchor="end"),
                 _text(330, 258, "Direction and proximity are observations; linkage claims require additional evidence", theme, size=9, weight=700, anchor="middle", color=theme.caution)))
    return _panel_frame(theme, "Locus Architecture Strip", "Full Node or Contig · Region · Governed Gene Roster", ''.join(body))


def _comparison_board(theme: Theme) -> str:
    streams = (("MIBiG", "Observed"), ("ClusterBlast", "Observed"), ("BiG-SCAPE", "Pending"), ("RG-GMCI", "Unbound"), ("Assembly Link", "Unavailable"))
    body: list[str] = []
    for index, (stream, state) in enumerate(streams):
        y = 76 + index * 39
        body.append(_text(28, y + 20, stream, theme, size=10, weight=700))
        color = {"Observed": theme.secondary, "Pending": theme.accent, "Unbound": theme.caution, "Unavailable": theme.muted}[state]
        body.append(f'<rect x="192" y="{y}" width="122" height="28" rx="5" fill="{color}"/>' + _text(253, y + 19, state, theme, size=9, weight=700, anchor="middle", color=theme.paper if state in ("Observed", "Unbound") else theme.ink))
        body.append(f'<line x1="332" y1="{y+14}" x2="614" y2="{y+14}" stroke="{theme.line}" stroke-width="5" stroke-linecap="round"/>')
    body.append(_text(28, 284, "Disposition Every Stream Before Drawing a Comparison Conclusion", theme, size=9, weight=700, color=theme.caution))
    return _panel_frame(theme, "Comparison Availability Board", "Source State First · Comparison Meaning Second", ''.join(body))


def _evidence_stage_ladder(theme: Theme) -> str:
    stages = (
        ("Sequence · Domain", "GBK · Protein SHA"),
        ("Culture Production", "Culture Record · Feature"),
        ("Purified Structure", "Purification · Structure"),
        ("Target Assay", "Raw Rows · Denominator"),
        ("Host Outcome", "Study Record · Endpoint"),
    )
    colors = (theme.primary, theme.secondary, theme.accent, theme.primary, theme.secondary)
    body: list[str] = []
    for index, ((label, source), color) in enumerate(zip(stages, colors)):
        x = 22 + index * 126
        body.append(f'<rect x="{x}" y="102" width="112" height="82" rx="8" fill="{color}" opacity=".92"/>')
        body.append(_text(x + 56, 128, label, theme, size=8, weight=700, anchor="middle", color=theme.paper if index in (0, 3) else theme.ink))
        body.append(_text(x + 56, 157, source, theme, size=7, weight=700, anchor="middle", color=theme.paper if index in (0, 3) else theme.ink))
        if index < len(stages) - 1:
            body.append(f'<line x1="{x+112}" y1="143" x2="{x+124}" y2="143" stroke="{theme.line}" stroke-width="2"/>')
    body.append(_text(330, 224, "Separate Source Objects · Explicit Locators · Independent Provenance", theme, size=9, weight=700, anchor="middle"))
    return _panel_frame(theme, "Evidence-Stage Ladder", "Sequence · Culture · Structure · Assay · Host Study", ''.join(body))


def render_component_gallery_svg(theme_id: str = DEFAULT_THEME_ID) -> str:
    """Render five reusable compositions on one accessible SVG plate."""
    theme = _theme(theme_id)
    renderers = (_evidence_matrix, _reaction_ledger, _locus_strip, _comparison_board, _evidence_stage_ladder)
    panel_w, panel_h, gap, cols = 660, 300, 24, 2
    rows = (len(renderers) + cols - 1) // cols
    width = cols * panel_w + (cols + 1) * gap
    height = 92 + rows * panel_h + (rows + 1) * gap
    panels = []
    for index, renderer in enumerate(renderers):
        x = gap + (index % cols) * (panel_w + gap)
        y = 92 + gap + (index // cols) * (panel_h + gap)
        panels.append(f'<g transform="translate({x},{y})">{renderer(theme)}</g>')
    definitions = f'''<defs><marker id="arrow-{theme.theme_id}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{theme.primary}"/></marker></defs>'''
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="component-title component-desc">
<title id="component-title">Sapote-Mamey Figure Component Gallery</title>
<desc id="component-desc">Five generic figure compositions rendered in the {_esc(theme.name)} theme.</desc>
{definitions}<rect width="100%" height="100%" fill="{theme.paper}"/>
{_text(24, 36, "Sapote-Mamey Figure Component Gallery", theme, size=25, weight=700)}
{_text(24, 60, f"{theme.name} · Deterministic Extraction · Evidence-Aware Presentation", theme, size=12, color=theme.muted)}
{''.join(panels)}</svg>'''


def component_manifest(theme_id: str = DEFAULT_THEME_ID) -> dict[str, object]:
    """Return the compact rendering and caption contract."""
    theme = _theme(theme_id)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": COMPONENT_STATUS,
        "prototype_dependency": PROTOTYPE_STATUS,
        "theme_id": theme.theme_id,
        "theme_name": theme.name,
        "scope_note": SCOPE_NOTE,
        "component_count": len(COMPONENTS),
        "components": [asdict(spec) for spec in COMPONENTS],
    }


def write_component_gallery(output_dir: str | Path, theme_id: str = DEFAULT_THEME_ID) -> dict[str, object]:
    """Write the static SVG plate and machine-readable component manifest."""
    root = write_output_bundle(output_dir, {
        "sapote_mamey_figure_component_gallery.svg": render_component_gallery_svg(theme_id).encode("utf-8"),
        "sapote_mamey_figure_component_manifest.json": (json.dumps(component_manifest(theme_id), indent=2) + "\n").encode("utf-8"),
    })
    return {
        "status": "PASS",
        "schema_version": SCHEMA_VERSION,
        "theme_id": theme_id,
        "component_count": len(COMPONENTS),
        "output_root": root.name,
        "svg": logical_artifact_locator(root, "sapote_mamey_figure_component_gallery.svg"),
        "manifest": logical_artifact_locator(root, "sapote_mamey_figure_component_manifest.json"),
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write static Sapote-Mamey figure component previews.")
    parser.add_argument("--out", required=True, help="Output directory for the SVG and JSON component manifest")
    parser.add_argument("--theme", default=DEFAULT_THEME_ID, choices=[theme.theme_id for theme in theme_profiles()])
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        receipt = write_component_gallery(args.out, args.theme)
    except OutputRefusal as exc:
        emit(json.dumps({"status": "REFUSED", "error_code": "OUTPUT_REFUSED", "message": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    emit(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
