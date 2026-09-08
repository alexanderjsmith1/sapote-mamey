"""Portable theme-gallery prototype for post-seal Sapote-Mamey figures.

This module does not read packages, calculate scores, or make biological
claims.  It lets a user compare presentation themes using only generic sample
marks before choosing a visual direction for a real post-seal figure.
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
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .optional_output import OutputRefusal, logical_artifact_locator, write_output_bundle


SCHEMA_VERSION = "sapote_mamey.figure_theme_gallery.v1"
PROTOTYPE_STATUS = "VISUAL_PROTOTYPE_NOT_RUNTIME_WIRED"
SCOPE_NOTE = (
    "Generic demonstration marks only. The gallery does not represent a strain, BGC, product, "
    "activity, production, identity, novelty, or ecological function."
)


@dataclass(frozen=True)
class Theme:
    """One self-contained visual profile for user evaluation."""

    theme_id: str
    name: str
    description: str
    paper: str
    ink: str
    muted: str
    card: str
    line: str
    primary: str
    secondary: str
    accent: str
    caution: str

    def css_vars(self) -> dict[str, str]:
        return {
            "paper": self.paper,
            "ink": self.ink,
            "muted": self.muted,
            "card": self.card,
            "line": self.line,
            "primary": self.primary,
            "secondary": self.secondary,
            "accent": self.accent,
            "caution": self.caution,
        }


THEMES: tuple[Theme, ...] = (
    Theme("evidence-navy", "Evidence Navy", "Calm navy, teal, gold, and cream for evidence-led summaries.",
          "#F7F4EC", "#10263E", "#506270", "#FFFFFF", "#D7DEE2", "#0D7891", "#3CB9B2", "#E7AF38", "#C86447"),
    Theme("scientific-cream", "Scientific Cream", "Warm paper with measured blue and terracotta accents for reports.",
          "#FBF6E8", "#24303A", "#69757D", "#FFFDF8", "#DED6C5", "#2E6EA5", "#6C9A8B", "#D58B43", "#B95245"),
    Theme("signal-dark", "Signal Dark", "High-legibility dark interface for focused on-screen exploration.",
          "#101820", "#F4F8F8", "#AAB8BC", "#18242D", "#354A53", "#55C7D8", "#85D6A6", "#F6C85F", "#FF907B"),
    Theme("high-contrast", "High Contrast", "Black, white, cobalt, and yellow for projection and accessibility checks.",
          "#FFFFFF", "#0A0A0A", "#424242", "#FFFFFF", "#171717", "#0047BB", "#007A66", "#F5C400", "#CC2D2D"),
    Theme("field-notebook", "Field Notebook", "Muted natural tones for ecological and sampling-context views.",
          "#F4F0E3", "#29352C", "#647064", "#FFFDF6", "#D7D0BC", "#39705A", "#5C8CB2", "#C9963F", "#B65C4B"),
    Theme("quiet-slate", "Quiet Slate", "Neutral slate with restrained coral and blue for dense tables and matrices.",
          "#F4F6F8", "#25313C", "#62707C", "#FFFFFF", "#D7DEE5", "#517AA3", "#6A9A9B", "#D89C5B", "#C85E6A"),
)


def theme_profiles() -> tuple[Theme, ...]:
    """Return the ordered, user-selectable profiles without mutable globals."""
    return THEMES


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _sample_svg(theme: Theme, *, width: int = 480, height: int = 260) -> str:
    """Return one accessible, data-free sample figure for a profile."""
    x0, y0, chart_w, chart_h = 42, 92, 250, 112
    bars = (46, 78, 58, 94, 68, 38)
    cells = ((0, 0, "Observed"), (1, 0, "Gap"), (2, 0, "Observed"), (0, 1, "Gated"), (1, 1, "Observed"), (2, 1, "Gap"))
    cell_fill = {"Observed": theme.secondary, "Gap": theme.paper, "Gated": theme.accent}
    pattern = '<path d="M-4,4 l8,-8 M0,12 l12,-12 M8,16 l8,-8" stroke="{line}" stroke-width="1.2" opacity=".9"/>'
    matrix = []
    for col, row, state in cells:
        x, y = 332 + col * 35, 102 + row * 37
        content = pattern.format(line=theme.muted) if state == "Gap" else ""
        matrix.append(
            f'<g><rect x="{x}" y="{y}" width="29" height="31" rx="3" fill="{cell_fill[state]}" stroke="{theme.line}"/>{content}'
            f'<title>{state} sample channel state</title></g>'
        )
    bar_marks = []
    for idx, value in enumerate(bars):
        x = x0 + 10 + idx * 38
        fill = theme.primary if idx != 3 else theme.accent
        bar_marks.append(f'<rect x="{x}" y="{y0 + chart_h - value}" width="23" height="{value}" rx="3" fill="{fill}"><title>Generic sample mark {idx + 1}</title></rect>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="{theme.theme_id}-title {theme.theme_id}-desc">
<title id="{theme.theme_id}-title">{_esc(theme.name)} Sample Figure</title>
<desc id="{theme.theme_id}-desc">Generic evidence matrix, sample bar marks, and labelled availability states. {_esc(SCOPE_NOTE)}</desc>
<rect width="100%" height="100%" rx="12" fill="{theme.paper}"/>
<text x="24" y="32" font-family="Arial, sans-serif" font-size="17" font-weight="700" fill="{theme.ink}">{_esc(theme.name)}</text>
<text x="24" y="52" font-family="Arial, sans-serif" font-size="10" fill="{theme.muted}">Deterministic Extraction · Evidence-Aware Presentation</text>
<line x1="{x0}" y1="{y0 + chart_h}" x2="{x0 + chart_w}" y2="{y0 + chart_h}" stroke="{theme.line}"/>
<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0 + chart_h}" stroke="{theme.line}"/>
{''.join(bar_marks)}
<text x="{x0}" y="224" font-family="Arial, sans-serif" font-size="9" fill="{theme.muted}">Generic Evidence Marks</text>
<text x="332" y="87" font-family="Arial, sans-serif" font-size="10" font-weight="700" fill="{theme.ink}">Channel States</text>
{''.join(matrix)}
<rect x="332" y="187" width="10" height="10" fill="{theme.secondary}"/><text x="347" y="196" font-family="Arial, sans-serif" font-size="8.5" fill="{theme.muted}">Observed</text>
<rect x="398" y="187" width="10" height="10" fill="{theme.paper}" stroke="{theme.line}"/><text x="413" y="196" font-family="Arial, sans-serif" font-size="8.5" fill="{theme.muted}">Gap</text>
<text x="24" y="246" font-family="Arial, sans-serif" font-size="7.7" fill="{theme.muted}">Sample only · no biological interpretation</text>
</svg>'''


def render_theme_overview_svg() -> str:
    """Render all profiles into one vector comparison plate."""
    card_w, card_h, gap, cols = 510, 292, 24, 2
    rows = (len(THEMES) + cols - 1) // cols
    width, height = cols * card_w + (cols + 1) * gap, rows * card_h + (rows + 1) * gap + 66
    cards = []
    for index, theme in enumerate(THEMES):
        x = gap + (index % cols) * (card_w + gap)
        y = 66 + gap + (index // cols) * (card_h + gap)
        cards.append(f'<g transform="translate({x},{y})">{_sample_svg(theme)}</g>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="overview-title overview-desc">
<title id="overview-title">Sapote-Mamey Figure Theme Gallery</title>
<desc id="overview-desc">Six portable figure themes rendered with identical generic sample marks for visual comparison. {_esc(SCOPE_NOTE)}</desc>
<rect width="100%" height="100%" fill="#E9EEF1"/>
<text x="24" y="32" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#17212B">Sapote-Mamey Figure Theme Gallery</text>
<text x="24" y="52" font-family="Arial, sans-serif" font-size="12" fill="#53616B">Six Visual Directions · Generic Sample Data · No Runtime Integration</text>
{''.join(cards)}</svg>'''


def render_theme_gallery_html() -> str:
    """Render a self-contained chooser that works over file:// with no network."""
    default = THEMES[0]
    choices = ''.join(f'<option value="{_esc(t.theme_id)}">{_esc(t.name)}</option>' for t in THEMES)
    cards = ''.join(
        f'<article class="card" data-theme="{_esc(theme.theme_id)}"><h2>{_esc(theme.name)}</h2>'
        f'<p>{_esc(theme.description)}</p><div class="preview">{_sample_svg(theme, width=420, height=228)}</div>'
        f'<button type="button" data-select="{_esc(theme.theme_id)}">Preview This Theme</button></article>'
        for theme in THEMES
    )
    payload = {theme.theme_id: {"name": theme.name, "description": theme.description, "vars": theme.css_vars()} for theme in THEMES}
    # ``script`` is a raw-text HTML element: escaping JSON quotes would leave
    # literal ``&quot;`` text that JavaScript cannot parse.  Escape only the
    # closing-tag sequence so a future description cannot terminate the block.
    payload_text = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sapote-Mamey Figure Theme Gallery</title><style>
:root{{--paper:{default.paper};--ink:{default.ink};--muted:{default.muted};--card:{default.card};--line:{default.line};--primary:{default.primary};--secondary:{default.secondary};--accent:{default.accent};--caution:{default.caution}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}}header,main{{max-width:1160px;margin:auto;padding:24px}}header{{border-bottom:1px solid var(--line)}}h1{{margin:0;font-size:clamp(1.8rem,4vw,2.8rem)}}h2{{margin:.2rem 0;font-size:1.08rem}}.eyebrow{{font-size:.78rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--primary)}}.muted{{color:var(--muted)}}.toolbar{{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:20px 0}}select,button{{font:inherit;border:1px solid var(--line);border-radius:7px;padding:9px 12px;background:var(--card);color:var(--ink)}}button{{cursor:pointer;font-weight:650}}button:focus,select:focus{{outline:3px solid var(--accent);outline-offset:2px}}.active{{border:2px solid var(--primary);box-shadow:0 0 0 3px color-mix(in srgb,var(--primary) 18%,transparent)}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:18px}}.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;transition:transform .15s ease,border-color .15s ease}}.card:hover{{transform:translateY(-2px)}}.preview{{overflow:auto;border-radius:8px;margin:12px 0;border:1px solid var(--line)}}.preview svg{{display:block;width:100%;height:auto}}.notice{{margin-top:20px;padding:14px 16px;background:color-mix(in srgb,var(--accent) 16%,var(--paper));border-left:4px solid var(--accent);border-radius:6px}}@media(max-width:600px){{header,main{{padding:18px}}}}
</style></head><body><header><div class="eyebrow">{PROTOTYPE_STATUS.replace('_', ' ')}</div><h1>Sapote-Mamey Figure Theme Gallery</h1><p class="muted">Deterministic Extraction · Evidence-Aware Presentation · Choose a visual direction before rendering real post-seal outputs.</p></header><main>
<section class="toolbar" aria-label="Theme controls"><label for="themeSelect">Active Theme</label><select id="themeSelect">{choices}</select><span id="selection" class="muted" aria-live="polite"></span></section>
<section class="grid" aria-label="Theme previews">{cards}</section><section class="notice"><strong>Scope.</strong> {_esc(SCOPE_NOTE)}</section></main>
<script id="theme-data" type="application/json">{payload_text}</script><script>
const data=JSON.parse(document.getElementById('theme-data').textContent);const select=document.getElementById('themeSelect');const label=document.getElementById('selection');const cards=[...document.querySelectorAll('[data-theme]')];
function apply(id){{const theme=data[id];if(!theme)return;for(const [key,value] of Object.entries(theme.vars))document.documentElement.style.setProperty('--'+key,value);select.value=id;label.textContent='Previewing '+theme.name;cards.forEach(card=>card.classList.toggle('active',card.dataset.theme===id));}}
select.addEventListener('change',event=>apply(event.target.value));cards.forEach(card=>card.querySelector('button').addEventListener('click',()=>apply(card.dataset.theme)));apply(select.value);
</script></body></html>'''


def write_theme_gallery(output_dir: str | Path) -> dict[str, str | int]:
    """Write local, network-free HTML and SVG previews to ``output_dir``."""
    root = write_output_bundle(output_dir, {
        "sapote_mamey_figure_theme_gallery.html": render_theme_gallery_html().encode("utf-8"),
        "sapote_mamey_figure_theme_overview.svg": render_theme_overview_svg().encode("utf-8"),
    })
    return {
        "status": "PASS",
        "schema_version": SCHEMA_VERSION,
        "theme_count": len(THEMES),
        "output_root": root.name,
        "html": logical_artifact_locator(root, "sapote_mamey_figure_theme_gallery.html"),
        "svg": logical_artifact_locator(root, "sapote_mamey_figure_theme_overview.svg"),
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write portable Sapote-Mamey figure theme previews.")
    parser.add_argument("--out", required=True, help="Output directory for the self-contained HTML and SVG previews")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        receipt = write_theme_gallery(args.out)
    except OutputRefusal as exc:
        emit(json.dumps({"status": "REFUSED", "error_code": "OUTPUT_REFUSED", "message": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    emit(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
