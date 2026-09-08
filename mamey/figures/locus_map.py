"""Locus map SVG renderer — lightweight, no matplotlib dependency (v9.7.145).

SIBLING (not a duplicate): `mamey/locus_map.py` is the matplotlib PNG renderer used by the main
figure pipeline; it reads the chemotype-role palette from data/locus_role_palette.json. This SVG
module is stdlib-only for environments without matplotlib and carries its own fixed generic-role
palette below (coarser roles: biosynthetic / transport / te / er / …). The palette divergence is
intentional given the different role granularity; see PC-10 in the v9.7.253 audit.


Generates a BGC locus map as an SVG string from a parsed GBK region file.
Pure Python + stdlib only.

Usage::

    svg_text = render_locus_map_svg(gbk_path="path/to/region001.gbk")
    Path("BGC028_locus_map.svg").write_text(svg_text, encoding="utf-8")

CLI::

    python -m mamey.figures.locus_map --gbk region001.gbk --out ./figures/
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

import re
import xml.etree.ElementTree as ET
import xml.sax.saxutils as _saxutils
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── Colour palette ────────────────────────────────────────────────────────────
COLORS = {
    "biosynthetic":             "#2E75B6",   # PKS/NRPS core — blue
    "biosynthetic-additional":  "#5BA3D4",   # tailoring — light blue
    "transport":                "#538135",   # ABC/transport — green
    "te":                       "#1F4E79",   # TE domain override — dark navy
    "er":                       "#CC0000",   # ER domain override — red
    "docking":                  "#7030A0",   # docking domain — purple
    "p450":                     "#C55A11",   # P450 — orange
    "regulatory":               "#833C00",   # regulatory — brown
    "other":                    "#A6A6A6",   # unknown — grey
}

LEGEND_ITEMS = [
    ("PKS/NRPS core",    COLORS["biosynthetic"]),
    ("Tailoring",        COLORS["biosynthetic-additional"]),
    ("Transport/ABC",    COLORS["transport"]),
    ("TE release",       COLORS["te"]),
    ("ER (reducing) ★",  COLORS["er"]),
    ("Docking domain",   COLORS["docking"]),
    ("P450",             COLORS["p450"]),
    ("Regulatory",       COLORS["regulatory"]),
    ("Unknown",          COLORS["other"]),
]


# ── Data structures ───────────────────────────────────────────────────────────
@dataclass
class CDS:
    locus: str
    strand: str           # "+" or "-"
    start: int
    end: int
    kind: str             # gene_kind from antiSMASH annotation
    label: str = ""
    asdomain: list[str] = field(default_factory=list)
    er_present: bool = False
    te_present: bool = False
    dock_n: bool = False
    dock_c: bool = False
    p450: bool = False

    @property
    def length_bp(self) -> int:
        return self.end - self.start

    def color(self) -> str:
        if self.p450:
            return COLORS["p450"]
        if self.te_present:
            return COLORS["te"]
        return COLORS.get(self.kind, COLORS["other"])


# ── GBK parser (minimal, antiSMASH region GBK only) ──────────────────────────
def _parse_gbk_cds(text: str) -> list[CDS]:
    """Extract CDS features from an antiSMASH region GBK string."""
    genes: list[CDS] = []
    blocks = re.split(r"(?=     CDS             )", text)
    for block in blocks[1:]:
        if not block.strip().startswith("CDS"):
            continue
        coord = re.search(r"CDS\s+(complement\()?(\d+)\.\.(\d+)", block)
        if not coord:
            continue
        strand = "-" if coord.group(1) else "+"
        start = int(coord.group(2))
        end = int(coord.group(3))
        locus_m = re.search(r'/locus_tag="([^"]+)"', block)
        kind_m = re.search(r'/gene_kind="([^"]+)"', block)
        asd = re.findall(r'/aSDomain="([^"]+)"', block)
        nrps_domains = re.findall(
            r'Domain:\s+(PKS_ER|Thioesterase|PKS_Docking_Nterm|PKS_Docking_Cterm'
            r'|p450|PKS_AT|PKS_DH|PKS_KR|ACP)[^(]*\(',
            block,
        )
        locus = locus_m.group(1) if locus_m else "?"
        kind = kind_m.group(1) if kind_m else "other"
        er = any("PKS_ER" in d or "ER" in d for d in nrps_domains)
        te = any("Thioesterase" in d for d in nrps_domains)
        dn = any("Docking_Nterm" in d for d in asd + nrps_domains)
        dc = any("Docking_Cterm" in d for d in asd + nrps_domains)
        p450 = "p450" in asd or any("p450" in d.lower() for d in nrps_domains)
        genes.append(CDS(
            locus=locus, strand=strand, start=start, end=end,
            kind=kind, asdomain=asd[:4],
            er_present=er, te_present=te,
            dock_n=dn, dock_c=dc, p450=p450,
        ))
    return genes


# ── SVG helpers ───────────────────────────────────────────────────────────────
def _arrow_points(x1: float, x2: float, y: float, h: float, strand: str) -> str:
    """Generate polygon points for a directional gene arrow."""
    tip = min(8.0, abs(x2 - x1) * 0.25)
    mid = y + h / 2
    if strand == "+":
        body = x2 - tip
        pts = [(x1,y),(body,y),(x2,mid),(body,y+h),(x1,y+h)]
    else:
        body = x1 + tip
        pts = [(x2,y),(body,y),(x1,mid),(body,y+h),(x2,y+h)]
    return " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)


def _zigzag(x: float, y: float, h: float, side: str) -> str:
    """SVG polyline points for a truncation zigzag marker."""
    if side == "left":
        pts = [(x+8,y),(x,y+h/3),(x+8,y+2*h/3),(x,y+h)]
    else:
        pts = [(x-8,y),(x,y+h/3),(x-8,y+2*h/3),(x,y+h)]
    return " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)


# ── Main renderer ─────────────────────────────────────────────────────────────
def render_locus_map_svg(
    gbk_path: Optional[str | Path] = None,
    gbk_text: Optional[str] = None,
    width_px: int = 800,
    title: str = "",
    truncated: str = "both",
) -> str:
    """Render a BGC locus map as an SVG string.

    Args:
        gbk_path:  Path to antiSMASH region GBK file.
        gbk_text:  GBK text (alternative to gbk_path).
        width_px:  Output SVG width in pixels.
        title:     Title string shown above the map.
        truncated: Which ends are truncated — "left", "right", "both", or "none".

    Returns:
        SVG string (valid XML).
    """
    if not isinstance(width_px, int) or width_px < 200 or width_px > 10000:
        raise ValueError(f"width_px must be an integer between 200 and 10000, got {width_px!r}")
    if gbk_text is None:
        if gbk_path is None:
            raise ValueError("Provide gbk_path or gbk_text")
        gbk_text = Path(gbk_path).read_text(encoding="utf-8", errors="replace")

    locus_m = re.search(r"LOCUS\s+\S+\s+(\d+)\s+bp", gbk_text)
    contig_len = int(locus_m.group(1)) if locus_m else 1
    genes = _parse_gbk_cds(gbk_text)

    # Layout constants
    MARGIN    = 55
    DRAW_W    = width_px - 2 * MARGIN
    TITLE_H   = 28
    GENE_Y    = TITLE_H + 10
    GENE_H    = 22
    DOM_Y     = GENE_Y + GENE_H + 3
    DOM_H     = 7
    SCALE_Y   = DOM_Y + DOM_H + 14
    LEG_Y     = SCALE_Y + 20
    LEG_COLS  = 3
    LEG_ROW_H = 16
    LEG_ROWS  = (len(LEGEND_ITEMS) + LEG_COLS - 1) // LEG_COLS
    SVG_H     = LEG_Y + LEG_ROWS * LEG_ROW_H + 12

    def sx(bp: int) -> float:
        return MARGIN + (bp / contig_len) * DRAW_W

    svg_parts: list[str] = [
        f'<svg width="{width_px}" height="{SVG_H}" '
        f'xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{width_px}" height="{SVG_H}" fill="white"/>',
    ]

    # Title
    if title:
        svg_parts.append(
            f'<text x="{width_px//2}" y="18" text-anchor="middle" '
            f'font-family="Arial" font-size="10" font-weight="bold" '
            f'fill="#1F4E79">{_saxutils.escape(str(title))}</text>'
        )

    # Backbone
    svg_parts.append(
        f'<line x1="{MARGIN}" y1="{GENE_Y + GENE_H/2:.1f}" '
        f'x2="{width_px - MARGIN}" y2="{GENE_Y + GENE_H/2:.1f}" '
        f'stroke="#CCCCCC" stroke-width="1"/>'
    )

    # Truncation markers
    for side in (["left"] if truncated == "left"
                 else ["right"] if truncated == "right"
                 else ["left", "right"] if truncated == "both"
                 else []):
        xpos = MARGIN if side == "left" else width_px - MARGIN
        pts = _zigzag(xpos, GENE_Y - 4, GENE_H + 8, side)
        svg_parts.append(
            f'<polyline points="{pts}" fill="none" '
            f'stroke="#CC0000" stroke-width="1.8"/>'
        )
        lbl = "◀ truncated" if side == "left" else "truncated ▶"
        ha = "start" if side == "left" else "end"
        lx = xpos + (12 if side == "left" else -12)
        svg_parts.append(
            f'<text x="{lx:.1f}" y="{GENE_Y - 6}" text-anchor="{ha}" '
            f'font-family="Arial" font-size="7" fill="#CC0000" '
            f'font-style="italic">{_saxutils.escape(str(lbl))}</text>'
        )

    # Gene arrows
    for g in genes:
        x1, x2 = sx(g.start), sx(g.end)
        pts = _arrow_points(x1, x2, GENE_Y, GENE_H, g.strand)
        svg_parts.append(
            f'<polygon points="{pts}" fill="{g.color()}" '
            f'stroke="white" stroke-width="0.4"/>'
        )
        # Label inside arrow if wide enough
        if abs(x2 - x1) > 35 and g.locus:
            lx = (x1 + x2) / 2
            svg_parts.append(
                f'<text x="{lx:.1f}" y="{GENE_Y + GENE_H/2 + 3:.1f}" '
                f'text-anchor="middle" font-family="Arial" font-size="6.5" '
                f'fill="white" font-weight="bold" clip-path="none">'
                f'{_saxutils.escape(str(g.locus))}</text>'
            )

        # Domain bars below gene
        if g.er_present:
            # Approximate ER position: 60–75% into the gene
            er_s = sx(int(g.start + g.length_bp * 0.60))
            er_e = sx(int(g.start + g.length_bp * 0.75))
            svg_parts.append(
                f'<rect x="{er_s:.1f}" y="{DOM_Y}" '
                f'width="{max(2, er_e-er_s):.1f}" height="{DOM_H}" '
                f'fill="{COLORS["er"]}" rx="1"/>'
            )
        if g.dock_n:
            d_e = sx(min(g.start + 100, g.end))
            svg_parts.append(
                f'<rect x="{sx(g.start):.1f}" y="{DOM_Y}" '
                f'width="{max(2, d_e - sx(g.start)):.1f}" height="{DOM_H}" '
                f'fill="{COLORS["docking"]}" rx="1"/>'
            )
        if g.dock_c:
            d_s = sx(max(g.end - 200, g.start))
            svg_parts.append(
                f'<rect x="{d_s:.1f}" y="{DOM_Y}" '
                f'width="{max(2, sx(g.end) - d_s):.1f}" height="{DOM_H}" '
                f'fill="{COLORS["docking"]}" rx="1"/>'
            )
        if g.te_present:
            te_s = sx(int(g.start + g.length_bp * 0.85))
            te_e = sx(g.end)
            svg_parts.append(
                f'<rect x="{te_s:.1f}" y="{DOM_Y}" '
                f'width="{max(2, te_e - te_s):.1f}" height="{DOM_H}" '
                f'fill="{COLORS["te"]}" rx="1"/>'
            )

    # Scale bar — 5 kb
    bar_w = (5000 / contig_len) * DRAW_W
    bar_x = width_px - MARGIN - bar_w - 5
    svg_parts += [
        f'<line x1="{bar_x:.1f}" y1="{SCALE_Y}" x2="{bar_x+bar_w:.1f}" y2="{SCALE_Y}" '
        f'stroke="#444" stroke-width="1.5"/>',
        f'<line x1="{bar_x:.1f}" y1="{SCALE_Y-3}" x2="{bar_x:.1f}" y2="{SCALE_Y+3}" '
        f'stroke="#444" stroke-width="1.5"/>',
        f'<line x1="{bar_x+bar_w:.1f}" y1="{SCALE_Y-3}" x2="{bar_x+bar_w:.1f}" y2="{SCALE_Y+3}" '
        f'stroke="#444" stroke-width="1.5"/>',
        f'<text x="{bar_x + bar_w/2:.1f}" y="{SCALE_Y+12}" text-anchor="middle" '
        f'font-family="Arial" font-size="8" fill="#444">5 kb</text>',
    ]

    # Legend
    col_w = (width_px - 2 * MARGIN) // LEG_COLS
    for i, (label, color) in enumerate(LEGEND_ITEMS):
        row, col = divmod(i, LEG_COLS)
        lx = MARGIN + col * col_w
        ly = LEG_Y + row * LEG_ROW_H
        svg_parts += [
            f'<rect x="{lx}" y="{ly+1}" width="11" height="9" fill="{color}" rx="1"/>',
            f'<text x="{lx+14}" y="{ly+9}" font-family="Arial" '
            f'font-size="8" fill="#444">{_saxutils.escape(str(label))}</text>',
        ]

    svg_parts.append("</svg>")
    svg_text = "\n".join(svg_parts)

    # Validate it's parseable XML before returning
    ET.fromstring(svg_text)
    return svg_text


# ── CLI entry point ───────────────────────────────────────────────────────────
def _main() -> None:
    import argparse, sys
    parser = argparse.ArgumentParser(
        description="Render a BGC locus map SVG from an antiSMASH region GBK file."
    )
    parser.add_argument("--gbk", required=True, help="Path to region GBK file")
    parser.add_argument("--out", default=".", help="Output directory")
    parser.add_argument("--width", type=int, default=800, help="SVG width in pixels")
    parser.add_argument("--truncated", default="both",
                        choices=["left","right","both","none"],
                        help="Which ends are truncated")
    parser.add_argument("--title", default="", help="Map title")
    args = parser.parse_args()

    gbk = Path(args.gbk)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    svg = render_locus_map_svg(
        gbk_path=gbk,
        width_px=args.width,
        title=args.title or gbk.stem,
        truncated=args.truncated,
    )
    out_path = out / f"{gbk.stem}_locus_map.svg"
    out_path.write_text(svg, encoding="utf-8")
    emit(f"Written: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    _main()
