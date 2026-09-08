"""master_figure_atlas.py — boss-ready figure atlas from a Sapote–Mamey master workbook.

v9.7.73 developer patch: cohort-Master-Figure-Atlas-1

This module renders a boss-ready, cross-strain figure bundle from the manual
recovery / parallel-chat master workbook sheets:

    Strain_Summary
    Special_Buckets
    Top_Antibacterial
    Top_Antifungal

The figures are deliberately dashboard/card based. They avoid raw wide tables in
PNG/PDF-facing outputs and write full-detail CSV sidecars for every rendered
figure. The workbook reader is stdlib-only so the figure path does not add a new
runtime dependency to Sapote–Mamey.

Claim-safety:
- AB/AF scores are deterministic priority scores, not activity measurements.
- KCB context is similarity / anchor text, not product identity.
- Assembly-tier warnings are visible on dashboard/coworker-facing figures.
"""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import datetime as _dt
import json
import math
import os
import re
import textwrap
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
# v9.7.410 (CLAUDE_410 savefig OOM sweep): clamp publication DPI under the Agg pixel
# ceiling before every raster write. See mamey/render_safe.py::safe_savefig_dpi.
from .render_safe import safe_savefig_dpi as _safe_dpi

# W2-H3/v9.7.352: figure deps are optional ([all] extra). Guard the import so this module — which
# cli.py imports — stays importable on a core-only install instead of crashing with ImportError.
try:
    import matplotlib
    matplotlib.use("Agg")
    matplotlib.rcParams["svg.fonttype"] = "none"
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    _HAVE_MPL = True
except ImportError:  # degrade gracefully; render entrypoints check _HAVE_MPL before drawing
    _HAVE_MPL = False

_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

PALETTE = {
    "navy": "#0b2447",
    "blue": "#1f5f8b",
    "teal": "#0f766e",
    "green": "#2b7a4b",
    "amber": "#c97706",
    "orange": "#ea580c",
    "purple": "#5b3c99",
    "red": "#b91c1c",
    "gray": "#6b7280",
    "light": "#f8fafc",
    "line": "#cbd5e1",
    "ink": "#0f172a",
}

ASSEMBLY_COLORS = {
    "GOOD": "#2b7a4b",
    "MODERATE": "#1f5f8b",
    "POOR": "#c97706",
    "VERY_POOR": "#b91c1c",
    "UNKNOWN": "#6b7280",
    "": "#6b7280",
}

# COH-04: the canonical assembly tiers, in display order. The dual-priority atlas iterates the
# tiers ACTUALLY PRESENT in the data (with an UNKNOWN bucket) rather than this fixed list, so a
# strain whose assembly_tier is blank/UNKNOWN still gets a scatter marker instead of silently
# vanishing from the plot while still feeding the medians/labels/CSV. Mirrors the
# `assembly_tier or "unknown"` bucketing in cross_strain_figures.py.
_ASSEMBLY_TIER_ORDER = ["GOOD", "MODERATE", "POOR", "VERY_POOR"]

FIGURE_NOTE = (
    "Deterministic priority/capacity summary; not wet-lab activity. "
    "KCB text is similarity/anchor context, not product identity."
)

FIGURE_ID_DATE = "20260618"
FIGURE_ID_REVISION = "r1"

FIGURE_ID_REGISTRY = {
    "fig_master_dashboard": {
        "visible_id": "CSA18-00",
        "long_id": "CSA18_MASTER_DASH00_20260618_r1",
        "purpose": "cohort master dashboard",
        "slug": "master_dashboard",
        "caption": "Boss-facing dashboard summarizing the cohort cross-strain master workbook.",
    },
    "fig_dual_priority_atlas": {
        "visible_id": "CSA18-01",
        "long_id": "CSA18_PRIORITY_DUALTRACK01_20260618_r1",
        "purpose": "Cross-strain top antibacterial vs top antifungal priority atlas",
        "slug": "cross_strain_dual_priority_node_first",
        "caption": "Each point is one strain, positioned by top antibacterial and antifungal deterministic priority scores; labels use strain ID plus node-first AB/AF locators.",
    },
    "fig_bgc_assembly_landscape": {
        "visible_id": "CSA18-03",
        "long_id": "CSA18_BGC_RAWCORR03_20260618_r1",
        "purpose": "Raw versus corrected BGC burden and assembly fragmentation",
        "slug": "bgc_boundary_landscape_by_strain",
        "caption": "Raw and corrected BGC burden by strain with assembly-tier context.",
    },
    "fig_special_bucket_heatmap": {
        "visible_id": "CSA18-04",
        "long_id": "CSA18_SPECIALBUCKETS04_20260618_r1",
        "purpose": "Special-review bucket heatmap",
        "slug": "special_bucket_burden_by_strain",
        "caption": "Special-review bucket burden by strain, including nucleoside priority rows, polyene/PTM flags, other-token rows, and RG-GMCI high pairs.",
    },
    "fig_top_lead_boards": {
        "visible_id": "CSA18-07",
        "long_id": "CSA18_TOPLEADS07_20260618_r1",
        "purpose": "Top antibacterial and antifungal lead board",
        "slug": "top_lead_board_node_first",
        "caption": "One best antibacterial and antifungal deterministic lead per strain, displayed with node-first locators.",
    },
    "fig_strain_card_atlas": {
        "visible_id": "CSA18-08",
        "long_id": "CSA18_STRAINCARD08_20260618_r1",
        "purpose": "Strain card atlas",
        "slug": "strain_card_atlas",
        "caption": "Compact boss-facing card summary for each completed strain in the master workbook.",
    },
}

CLAIM_CEILING = (
    "Deterministic Sapote-Mamey priority/capacity figure. The figure may prioritize "
    "or summarize evidence, but it does not establish wet-lab activity, causality, "
    "contig joining, production, or confirmed product identity."
)


@dataclass
class MasterFigureInput:
    strain_summary: list[dict[str, Any]]
    special_buckets: list[dict[str, Any]]
    top_antibacterial: list[dict[str, Any]]
    top_antifungal: list[dict[str, Any]]
    source_file: str = ""


# ── stdlib XLSX reader ────────────────────────────────────────────────────────

def _col_index(cell_ref: str) -> int:
    m = re.match(r"([A-Z]+)", cell_ref or "")
    if not m:
        return 0
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    out: list[str] = []
    for si in root.findall("a:si", _NS):
        texts = [t.text or "" for t in si.findall(".//a:t", _NS)]
        out.append("".join(texts))
    return out


def _sheet_paths(zf: zipfile.ZipFile) -> dict[str, str]:
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rid_to_target = {}
    for rel in rels.findall("rel:Relationship", _NS):
        rid = rel.attrib.get("Id")
        target = rel.attrib.get("Target", "")
        if rid:
            target = target.lstrip("/")
            if not target.startswith("xl/"):
                target = "xl/" + target
            rid_to_target[rid] = target
    paths = {}
    for sh in wb.findall(".//a:sheet", _NS):
        name = sh.attrib.get("name", "")
        rid = sh.attrib.get(f"{{{_NS['r']}}}id")
        if name and rid in rid_to_target:
            paths[name] = rid_to_target[rid]
    return paths


def _cell_value(cell: ET.Element, shared: list[str]) -> Any:
    ctype = cell.attrib.get("t", "")
    if ctype == "inlineStr":
        texts = [t.text or "" for t in cell.findall(".//a:t", _NS)]
        return "".join(texts)
    v = cell.find("a:v", _NS)
    if v is None or v.text is None:
        return None
    raw = v.text
    if ctype == "s":
        try:
            return shared[int(raw)]
        except Exception:
            return raw
    if ctype == "b":
        return raw == "1"
    # Best-effort numeric conversion for normal cells.
    try:
        f = float(raw)
        return int(f) if f.is_integer() else f
    except Exception:
        return raw


def read_xlsx_table(workbook_path: str | os.PathLike[str], sheet_name: str) -> list[dict[str, Any]]:
    """Return a sheet as a list of dictionaries keyed by the first row.

    This intentionally does not evaluate formulas. It reads cached cell values
    from the XLSX XML, which is sufficient for the manual-recovery master rows.
    """
    workbook_path = str(workbook_path)
    with zipfile.ZipFile(workbook_path) as zf:
        shared = _shared_strings(zf)
        paths = _sheet_paths(zf)
        if sheet_name not in paths:
            return []
        root = ET.fromstring(zf.read(paths[sheet_name]))
        rows: list[list[Any]] = []
        for row_el in root.findall(".//a:sheetData/a:row", _NS):
            vals: dict[int, Any] = {}
            for cell in row_el.findall("a:c", _NS):
                idx = _col_index(cell.attrib.get("r", ""))
                vals[idx] = _cell_value(cell, shared)
            if vals:
                width = max(vals) + 1
                rows.append([vals.get(i) for i in range(width)])
        if not rows:
            return []
        header = [str(h).strip() if h is not None else "" for h in rows[0]]
        records: list[dict[str, Any]] = []
        for row in rows[1:]:
            if not any(v not in (None, "") for v in row):
                continue
            rec = {header[i]: row[i] if i < len(row) else None for i in range(len(header)) if header[i]}
            records.append(rec)
        return records


def load_master_figure_input(workbook_path: str | os.PathLike[str]) -> MasterFigureInput:
    return MasterFigureInput(
        strain_summary=read_xlsx_table(workbook_path, "Strain_Summary"),
        special_buckets=read_xlsx_table(workbook_path, "Special_Buckets"),
        top_antibacterial=read_xlsx_table(workbook_path, "Top_Antibacterial"),
        top_antifungal=read_xlsx_table(workbook_path, "Top_Antifungal"),
        source_file=os.path.basename(str(workbook_path)),
    )


# ── safety helpers ────────────────────────────────────────────────────────────

def _num(v: Any, default: float = 0.0) -> float:
    try:
        if v in (None, ""):
            return default
        return float(v)
    except Exception:
        return default


def _int(v: Any, default: int = 0) -> int:
    return int(round(_num(v, default)))


def _text(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _wrap(s: Any, width: int = 32, max_lines: int = 2) -> str:
    """Layout-safe label: wrap before truncating; never break mid-word."""
    txt = re.sub(r"\s+", " ", _text(s))
    if not txt:
        return ""
    lines = textwrap.wrap(txt, width=width, break_long_words=False, break_on_hyphens=False)
    if not lines:
        return txt[:width]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".,;: ") + "…"
    return "\n".join(lines)


def _short(s: Any, n: int = 44) -> str:
    txt = re.sub(r"\s+", " ", _text(s))
    if len(txt) <= n:
        return txt
    cut = txt[: max(1, n - 1)].rsplit(" ", 1)[0].rstrip(".,;:;|")
    return (cut or txt[: n - 1]) + "…"


def _product_anchor(kcb: Any) -> str:
    s = _text(kcb)
    if "|" in s:
        parts = [p.strip() for p in s.split("|")]
        if len(parts) >= 2:
            return _short(parts[1], 42)
    if "Type:" in s:
        return _short(s.split("Type:", 1)[1], 42)
    return _short(s, 42)


def _index_by_strain(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out = {}
    for r in rows:
        sid = _text(r.get("strain_id") or r.get("strain"))
        if sid and sid not in out:
            out[sid] = r
    return out


def _rank1(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        sid = _text(r.get("strain_id"))
        rank = _int(r.get("rank"), 9999)
        if sid and rank == 1 and sid not in out:
            out[sid] = r
    return out


def _write_csv(path: Path, header: list[str], rows: list[list[Any]], provenance: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # v9.7.374 fix: was a bare open(path, "w") -- an interrupted write (kill, disk full) left a
    # truncated/corrupt figure-sidecar CSV sitting next to an otherwise-complete figure. Matches
    # the established tmp-sibling + rename pattern used throughout this codebase for exactly this
    # failure mode (mamey/packaging.py::_atomic_write_text, mamey/workbook.py's atomic wb.save()).
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = _SafeWriter(f)
        w.writerow(["# provenance", provenance])
        w.writerow(header)
        w.writerows(rows)
    tmp.replace(path)


def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Crash-safe text write: write to a sibling .tmp then rename into place, so an interrupted
    render never leaves a truncated/corrupt figure_manifest.json or remake guide (v9.7.374 fix;
    mirrors mamey/packaging.py::_atomic_write_text)."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding=encoding)
    tmp.replace(path)


def _median(values: list[float]) -> float:
    vals = sorted(v for v in values if math.isfinite(v))
    if not vals:
        return 0.0
    mid = len(vals) // 2
    if len(vals) % 2:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / 2.0


def _fmt1(value: float) -> str:
    # Human-facing reporting uses conventional half-up rounding, not Python's
    # bankers rounding, so 86.25 displays as 86.3.
    return f"{math.floor(value * 10 + 0.5) / 10:.1f}"


def _node_only(locator: Any) -> str:
    txt = _text(locator)
    m = re.search(r"(NODE_[0-9A-Za-z_.-]+)", txt)
    return m.group(1) if m else _short(txt, 24)


def _fig_meta(figure_key: str) -> dict[str, str]:
    if figure_key not in FIGURE_ID_REGISTRY:
        raise KeyError(f"unknown figure key: {figure_key}")
    return FIGURE_ID_REGISTRY[figure_key]


def _fig_path(out_dir: Path, figure_key: str) -> Path:
    meta = _fig_meta(figure_key)
    return out_dir / f"{meta['visible_id']}_{meta['slug']}.png"


def _write_sidecar(out_dir: Path, entry: dict[str, Any], *, caption: str, data_source: str, claim_ceiling: str) -> str:
    path = out_dir / f"{entry['visible_id']}.md"
    title = entry.get("purpose") or entry.get("figure_id") or entry.get("visible_id")
    content = f"""# {entry['visible_id']} — {title}

## Long ID

{entry['long_id']}

## Figure files

- PNG: {Path(entry['png']).name}
- SVG: {Path(entry['svg']).name}
- PDF: {Path(entry['pdf']).name}

## Caption

{caption}

## Data source

{data_source or 'Sapote-Mamey master workbook'}

## Source CSV

{Path(entry['source_csv']).name}

## Regeneration notes

Run `python tools/build_master_figures.py --workbook <MASTER.xlsx> --out-dir <FIGURE_DIR>`.

## Claim ceiling

{claim_ceiling}

## Revision history

- r1: initial stable Figure/Card ID contract rendering.
"""
    # v9.7.374 fix: was a bare path.write_text() -- see _write_csv above for the failure mode.
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)
    return str(path)


def _register_figure(out_dir: Path, figure_key: str, png: Path, source_csv: Path, *, data_source: str = "") -> dict[str, Any]:
    meta = _fig_meta(figure_key)
    entry = {
        "figure_id": figure_key,
        "visible_id": meta["visible_id"],
        "long_id": meta["long_id"],
        "purpose": meta["purpose"],
        "png": str(png),
        "svg": str(png.with_suffix(".svg")),
        "pdf": str(png.with_suffix(".pdf")),
        "source_csv": str(source_csv),
        "caption": meta["caption"],
        "claim_ceiling": CLAIM_CEILING,
    }
    entry["sidecar_md"] = _write_sidecar(
        out_dir, entry, caption=meta["caption"], data_source=data_source, claim_ceiling=CLAIM_CEILING
    )
    return entry


def _write_figure_index(path: Path, figures: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # v9.7.374 fix: was a bare open(path, "w") -- see _write_csv above for the failure mode. This
    # file (FIGURE_INDEX.csv) is the cross-figure index a boss/coworker opens first.
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = _SafeWriter(f)
        w.writerow([
            "visible_id", "long_id", "figure_id", "purpose", "png", "svg", "pdf",
            "source_csv", "sidecar_md", "caption", "claim_ceiling",
        ])
        for fig in figures:
            w.writerow([
                fig.get("visible_id"), fig.get("long_id"), fig.get("figure_id"), fig.get("purpose"),
                Path(fig.get("png", "")).name, Path(fig.get("svg", "")).name,
                Path(fig.get("pdf", "")).name, Path(fig.get("source_csv", "")).name,
                Path(fig.get("sidecar_md", "")).name, fig.get("caption"), fig.get("claim_ceiling"),
            ])
    tmp.replace(path)


def _save(fig, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=_safe_dpi(fig, 220), bbox_inches="tight", facecolor="white")
    fig.savefig(path.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path)


def _footer(fig, source_file: str) -> None:
    fig.text(0.015, 0.025, f"Source: {source_file or 'Sapote–Mamey master workbook'} · {FIGURE_NOTE}",
             fontsize=7, color=PALETTE["gray"], va="bottom")


def _card(ax, x: float, y: float, w: float, h: float, title: str, body: str,
          accent: str = "blue", title_size: int = 10, body_size: int = 8.5) -> None:
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.018",
                                linewidth=1.0, edgecolor=PALETTE["line"], facecolor="white"))
    ax.add_patch(FancyBboxPatch((x, y + h - 0.055), w, 0.055, boxstyle="round,pad=0.012,rounding_size=0.018",
                                linewidth=0, facecolor=PALETTE.get(accent, PALETTE["blue"])))
    ax.text(x + 0.02, y + h - 0.029, title, fontsize=title_size, color="white",
            fontweight="bold", va="center")
    ax.text(x + 0.02, y + h - 0.08, body, fontsize=body_size, color=PALETTE["ink"], va="top")


# ── figure renderers ──────────────────────────────────────────────────────────

def _fig_master_dashboard(data: MasterFigureInput, out_dir: Path) -> dict[str, Any]:
    rows = data.strain_summary
    n = len(rows)
    raw_total = sum(_num(r.get("raw_bgcs")) for r in rows)
    corrected_total = sum(_num(r.get("corrected_bgcs")) for r in rows)
    very_poor = sum(1 for r in rows if _text(r.get("assembly_tier")).upper() == "VERY_POOR")
    poor = sum(1 for r in rows if _text(r.get("assembly_tier")).upper() == "POOR")
    moderate = sum(1 for r in rows if _text(r.get("assembly_tier")).upper() == "MODERATE")
    rgg_high = sum(_num(r.get("rggmci_high_pairs")) for r in rows)

    fig, ax = plt.subplots(figsize=(16, 9))
    ax.axis("off")
    ax.text(0.02, 0.955, "cohort master figure dashboard", fontsize=27, color=PALETTE["navy"], fontweight="bold")
    ax.text(0.02, 0.915, "Cross-strain Sapote–Mamey summary from the parallel-chat master workbook", fontsize=13, color=PALETTE["gray"])

    metrics = [
        ("Completed strains", f"{n}"),
        ("Raw BGCs", f"{raw_total:.0f}"),
        ("Corrected BGCs", f"{corrected_total:.1f}"),
        ("RG-GMCI high pairs", f"{rgg_high:.0f}"),
        ("Assembly warnings", f"{poor + very_poor} POOR/VERY_POOR"),
    ]
    x0, y0, w, h, gap = 0.02, 0.80, 0.18, 0.09, 0.015
    for i, (label, val) in enumerate(metrics):
        _card(ax, x0 + i * (w + gap), y0, w, h, label, val, ["teal", "green", "blue", "purple", "red"][i], 9, 15)

    # Derive poor-assembly warning from actual data (not hardcoded strain names)
    poor_strains = [_text(r.get("strain_id")) for r in rows
                    if _text(r.get("assembly_tier")).upper() in ("POOR", "VERY_POOR")]
    if poor_strains:
        _names = ", ".join(poor_strains[:4]) + ("\u2026" if len(poor_strains) > 4 else "")
        warning = f"Assembly caution: {_names} ({len(poor_strains)} strain(s) POOR/VERY_POOR) \u2014 fragment-aware interpretation required."
        ax.add_patch(FancyBboxPatch((0.02, 0.735), 0.96, 0.045, boxstyle="round,pad=0.01,rounding_size=0.015",
                                    linewidth=1, edgecolor=PALETTE["red"], facecolor="#fff1f2"))
        ax.text(0.035, 0.758, warning, fontsize=10.5, color=PALETTE["red"], fontweight="bold", va="center")

    # Strain tiles, 5 x 2 grid.
    sx, sy = 0.02, 0.475
    tw, th = 0.18, 0.20
    for i, r in enumerate(rows[:10]):
        col, row = i % 5, i // 5
        x = sx + col * (tw + gap)
        y = sy - row * (th + 0.045)
        tier = _text(r.get("assembly_tier")).upper()
        accent = "red" if tier == "VERY_POOR" else "amber" if tier == "POOR" else "blue" if tier == "MODERATE" else "green"
        sid = _text(r.get("strain_id"))
        display = _wrap(r.get("display_name"), 28, 2)
        body = (
            f"{display}\n"
            f"BGCs raw/corr: {_num(r.get('raw_bgcs')):.0f} / {_num(r.get('corrected_bgcs')):.1f}\n"
            f"Interior: {_num(r.get('interior_pct')):.1f}% · N50: {_num(r.get('n50')):,.0f}\n"
            f"Top AB: {_short(r.get('top_antibacterial_products'), 36)}\n"
            f"Top AF: {_short(r.get('top_antifungal_products'), 36)}"
        )
        _card(ax, x, y, tw, th, f"{sid} · {tier or 'UNKNOWN'}", body, accent, 8.4, 6.7)

    _footer(fig, data.source_file)
    png = _fig_path(out_dir, "fig_master_dashboard")
    csv_rows = [[r.get("strain_id"), r.get("display_name"), r.get("assembly_tier"), r.get("raw_bgcs"),
                 r.get("corrected_bgcs"), r.get("top_antibacterial_products"), r.get("top_antifungal_products")]
                for r in rows]
    _write_csv(out_dir / f"{_fig_meta('fig_master_dashboard')['visible_id']}_master_dashboard_data.csv",
               ["strain_id", "display_name", "assembly_tier", "raw_bgcs", "corrected_bgcs", "top_antibacterial_products", "top_antifungal_products"],
               csv_rows, "Sapote–Mamey master dashboard figure data")
    _save(fig, png)
    return _register_figure(out_dir, "fig_master_dashboard", png, png.with_name(png.stem + "_data.csv"), data_source=data.source_file)


def _fig_bgc_assembly_landscape(data: MasterFigureInput, out_dir: Path) -> dict[str, Any]:
    rows = sorted(data.strain_summary, key=lambda r: _num(r.get("corrected_bgcs")))
    labels = [_text(r.get("strain_id")) for r in rows]
    raw = [_num(r.get("raw_bgcs")) for r in rows]
    corr = [_num(r.get("corrected_bgcs")) for r in rows]
    interior = [_num(r.get("interior_pct")) for r in rows]

    fig, ax = plt.subplots(figsize=(13.5, 8.0))
    y = list(range(len(rows)))
    ax.barh(y, raw, height=0.72, label="raw BGCs", alpha=0.30, color=PALETTE["gray"])
    colors = [ASSEMBLY_COLORS.get(_text(r.get("assembly_tier")).upper(), PALETTE["blue"]) for r in rows]
    ax.barh(y, corr, height=0.43, label="corrected BGCs", color=colors)
    for yi, r, c, pct in zip(y, rows, corr, interior):
        ax.text(max(raw) + 2, yi, f"{_text(r.get('assembly_tier'))} · interior {pct:.1f}%", va="center", fontsize=8, color=PALETTE["ink"])
        ax.text(c + 0.6, yi, f"{c:.1f}", va="center", fontsize=7.5, color=PALETTE["ink"])
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("BGC count: raw background bar, corrected foreground bar")
    ax.set_title("BGC burden and assembly fragmentation by strain", fontsize=18, color=PALETTE["navy"], fontweight="bold")
    ax.legend(loc="lower right", fontsize=9)
    ax.set_xlim(0, max(raw) + 28)
    ax.grid(axis="x", alpha=0.25)
    fig.text(0.015, 0.945, "Figure: raw vs corrected BGC burden, with assembly tier warnings", fontsize=11, color=PALETTE["gray"])
    _footer(fig, data.source_file)
    png = _fig_path(out_dir, "fig_bgc_assembly_landscape")
    _write_csv(out_dir / f"{_fig_meta('fig_bgc_assembly_landscape')['visible_id']}_bgc_boundary_landscape_by_strain_data.csv",
               ["strain_id", "raw_bgcs", "corrected_bgcs", "interior_pct", "assembly_tier"],
               [[r.get("strain_id"), r.get("raw_bgcs"), r.get("corrected_bgcs"), r.get("interior_pct"), r.get("assembly_tier")] for r in rows],
               "Sapote–Mamey raw/corrected BGC burden figure data")
    _save(fig, png)
    return _register_figure(out_dir, "fig_bgc_assembly_landscape", png, png.with_name(png.stem + "_data.csv"), data_source=data.source_file)


# Per-strain label-offset overrides for the dual-priority atlas, keyed by REAL strain ID.
# Empty by default: with no override, every strain uses the deterministic generic fallback in
# _fig_dual_priority_atlas (score+1.0, score+1.0+i%3). Supplying an entry pins that strain's
# label to a hand-placed (x, y, ha) so labels don't overlap on a crowded cohort master.
#
# FIXED v9.7.308 (audit path 2). This replaces a 10-entry dict literal whose keys were all the
# placeholder "AS-XXX": Python keeps only the last duplicate key, so 9 of the 10 hand-tuned
# offsets were dead and none ever fired (real strain IDs are never literally "AS-XXX"). Behavior
# is unchanged by this fix — the atlas already rendered every label with the generic fallback —
# but the dead/misleading dict is gone and the override path is now collision-proof. Duplicate
# or placeholder keys are blocked by test_label_position_overrides_have_distinct_real_keys and
# by tools/repo_health.py.
#
# The 10 (x, y, ha) tuples authored for the original 10-strain master are preserved below so the
# editorial work is not lost. Assigning each to the real strain it was nudged for requires an
# actual rendered atlas (a visual call, not a code guess); until then they stay as reference.
_AUTHORED_LABEL_OFFSETS_PENDING_MAPPING: list[tuple[float, float, str]] = [
    (78.2, 100.2, "left"),
    (91.8, 75.7, "right"),
    (101.2, 65.9, "left"),
    (101.2, 58.4, "left"),
    (101.2, 43.2, "left"),
    (88.4, 49.2, "left"),
    (88.2, 39.3, "left"),
    (80.0, 40.5, "right"),
    (73.1, 52.8, "left"),
    (54.2, 50.3, "left"),
]
LABEL_POSITION_OVERRIDES: dict[str, tuple[float, float, str]] = {}


def _fig_dual_priority_atlas(data: MasterFigureInput, out_dir: Path) -> dict[str, Any]:
    rows = data.strain_summary
    ab1 = _rank1(data.top_antibacterial)
    af1 = _rank1(data.top_antifungal)
    plot_rows = []
    for r in rows:
        sid = _text(r.get("strain_id"))
        ab_row = ab1.get(sid) or {}
        af_row = af1.get(sid) or {}
        ab_locator = _text(r.get("top_antibacterial_locator") or ab_row.get("assembly_locator"))
        af_locator = _text(r.get("top_antifungal_locator") or af_row.get("assembly_locator"))
        ab_node = _node_only(ab_locator)
        af_node = _node_only(af_locator)
        plot_rows.append({
            "strain_id": sid,
            # COH-04: normalize to an explicit UNKNOWN bucket so blank-tier strains are not dropped
            # from the scatter (they were still feeding medians/labels/CSV) — see tier loop below.
            "assembly_tier": (_text(r.get("assembly_tier")).upper() or "UNKNOWN"),
            "top_ab_score": _num(r.get("top_antibacterial_score") or ab_row.get("antibacterial_score")),
            "top_af_score": _num(r.get("top_antifungal_score") or af_row.get("antifungal_score")),
            "top_ab_product": _text(r.get("top_antibacterial_products") or ab_row.get("products")),
            "top_af_product": _text(r.get("top_antifungal_products") or af_row.get("products")),
            "top_ab_locator": ab_locator,
            "top_af_locator": af_locator,
            "ab_node": ab_node,
            "af_node": af_node,
            "visible_label": f"{sid}\nAB {ab_node} · AF {af_node}",
        })
    xs = [r["top_ab_score"] for r in plot_rows]
    ys = [r["top_af_score"] for r in plot_rows]
    x_med = _median(xs)
    y_med = _median(ys)

    fig = plt.figure(figsize=(17.2, 9.6))
    ax = fig.add_axes([0.07, 0.15, 0.70, 0.74])
    panel_ax = fig.add_axes([0.80, 0.16, 0.18, 0.71])
    panel_ax.axis("off")

    # COH-04: iterate the tiers actually present (canonical order first, any extras — incl. the
    # UNKNOWN bucket — appended) so no strain is silently omitted from the scatter while still
    # counting toward medians/labels/CSV. plot_rows["assembly_tier"] is already normalized upper.
    present_tiers = {r["assembly_tier"] for r in plot_rows}
    tier_iter = [t for t in _ASSEMBLY_TIER_ORDER if t in present_tiers] \
        + sorted(present_tiers - set(_ASSEMBLY_TIER_ORDER))
    for tier in tier_iter:
        sub = [r for r in plot_rows if r["assembly_tier"] == tier]
        if sub:
            ax.scatter([r["top_ab_score"] for r in sub], [r["top_af_score"] for r in sub],
                       s=115, label=tier, color=ASSEMBLY_COLORS.get(tier, PALETTE["blue"]),
                       edgecolor="white", linewidth=1.1, zorder=3)
        else:
            ax.scatter([], [], s=115, label=tier, color=ASSEMBLY_COLORS.get(tier, PALETTE["gray"]))

    ax.axvline(x_med, linestyle="--", linewidth=1.4, color=PALETTE["gray"], alpha=0.65, zorder=1)
    ax.axhline(y_med, linestyle="--", linewidth=1.4, color=PALETTE["gray"], alpha=0.65, zorder=1)
    if xs and ys:
        ax.text(x_med + 0.6, max(ys) + 6.2, f"AB median = {_fmt1(x_med)}", fontsize=10, ha="left", va="top", color=PALETTE["ink"])
        ax.text(max(xs) + 11.0, y_med + 0.6, f"AF median = {_fmt1(y_med)}", fontsize=10, ha="right", va="bottom", color=PALETTE["ink"])

    # Per-strain label offsets come from LABEL_POSITION_OVERRIDES (module constant, keyed by
    # real strain ID, empty by default). Any strain without an override — i.e. all of them until
    # an editorial mapping is supplied — uses the deterministic generic fallback below. Visible
    # labels intentionally exclude BGC IDs. See the note above LABEL_POSITION_OVERRIDES for the
    # history (this replaced a duplicate-key "AS-XXX" dict that never actually routed).
    label_positions = LABEL_POSITION_OVERRIDES
    for i, r in enumerate(plot_rows):
        tx, ty, ha = label_positions.get(r["strain_id"], (r["top_ab_score"] + 1.0, r["top_af_score"] + 1.0 + (i % 3), "left"))
        ax.annotate(
            r["visible_label"],
            xy=(r["top_ab_score"], r["top_af_score"]),
            xytext=(tx, ty),
            textcoords="data",
            fontsize=8.6,
            fontweight="bold",
            ha=ha,
            va="center",
            arrowprops=dict(arrowstyle="-", lw=0.9, shrinkA=0, shrinkB=5, color=PALETTE["ink"]),
            bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.84),
            zorder=4,
        )

    if xs and ys:
        ax.set_xlim(max(0, min(xs) - 3), max(xs) + 12)
        ax.set_ylim(max(0, min(ys) - 5), max(ys) + 7)
    ax.grid(True, alpha=0.23)
    ax.set_title("Cross-strain dual-track priority atlas", fontsize=21, fontweight="bold", color=PALETTE["navy"], pad=14)
    ax.set_xlabel("Top antibacterial priority score per strain", fontsize=12, fontweight="bold")
    ax.set_ylabel("Top antifungal priority score per strain", fontsize=12, fontweight="bold")
    ax.text(0.02, 0.98, "Antifungal-first", transform=ax.transAxes, fontsize=10, fontweight="bold", va="top", color=PALETTE["purple"])
    ax.text(0.98, 0.98, "Dual strength", transform=ax.transAxes, fontsize=10, fontweight="bold", ha="right", va="top", color=PALETTE["purple"])
    ax.text(0.02, 0.02, "Lower priority", transform=ax.transAxes, fontsize=10, fontweight="bold", va="bottom", color=PALETTE["purple"])
    ax.text(0.98, 0.02, "Antibacterial-first", transform=ax.transAxes, fontsize=10, fontweight="bold", ha="right", va="bottom", color=PALETTE["purple"])

    panel_ax.text(0.0, 0.98, "Priority readout", fontsize=17, fontweight="bold", va="top", color=PALETTE["navy"])
    highest_af = max(plot_rows, key=lambda r: r["top_af_score"], default=None)
    dual = sorted([r for r in plot_rows if r["top_ab_score"] >= x_med and r["top_af_score"] >= y_med], key=lambda r: r["top_ab_score"] + r["top_af_score"], reverse=True)[:3]
    antibacterial_first = sorted([r for r in plot_rows if r["top_af_score"] < y_med], key=lambda r: r["top_ab_score"], reverse=True)[:4]
    balanced = min(plot_rows, key=lambda r: abs(r["top_ab_score"] - x_med) + abs(r["top_af_score"] - y_med), default=None)
    readout = [
        ("Highest antifungal outlier", highest_af["strain_id"] if highest_af else "n/a", f"AB {highest_af['ab_node']} · AF {highest_af['af_node']}" if highest_af else ""),
        ("Strong dual-strength strains", ", ".join(r["strain_id"] for r in dual) or "n/a", ""),
        ("Antibacterial-first group", _wrap(", ".join(r["strain_id"] for r in antibacterial_first) or "n/a", 22, 2), ""),
        ("Median-near balance point", balanced["strain_id"] if balanced else "n/a", ""),
    ]
    y = 0.85
    for title, line1, line2 in readout:
        panel_ax.text(0.0, y, title, fontsize=10.5, fontweight="bold", va="top", color=PALETTE["ink"])
        panel_ax.text(0.0, y - 0.055, line1, fontsize=11.5, va="top", color=PALETTE["ink"])
        if line2:
            panel_ax.text(0.0, y - 0.105, line2, fontsize=9.5, va="top", color=PALETTE["gray"])
        panel_ax.plot([0, 1], [y - 0.145, y - 0.145], lw=0.8, alpha=0.35, color=PALETTE["line"])
        y -= 0.20

    panel_ax.text(0.0, 0.15, "Assembly tier", fontsize=10.5, fontweight="bold", va="top", color=PALETTE["ink"])
    panel_ax.text(0.0, 0.10, "GOOD · MODERATE · POOR · VERY_POOR", fontsize=8.7, va="top", color=PALETTE["gray"])
    panel_ax.text(0.0, 0.01, "Label contract: strain ID + AB node + AF node.\nBGC IDs remain in source data.", fontsize=8.4, va="bottom", color=PALETTE["gray"])

    meta = _fig_meta("fig_dual_priority_atlas")
    fig.text(0.93, 0.935, f"Card ID: {meta['visible_id']}", fontsize=12, fontweight="bold", ha="center", va="center",
             bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=PALETTE["line"]))
    _footer(fig, data.source_file)
    png = _fig_path(out_dir, "fig_dual_priority_atlas")
    source_csv = out_dir / f"{meta['visible_id']}_cross_strain_dual_priority_node_first_data.csv"
    _write_csv(source_csv,
               ["strain_id", "assembly_tier", "top_ab_score", "top_af_score", "ab_node", "af_node", "visible_label", "top_ab_locator", "top_af_locator", "top_ab_product", "top_af_product"],
               [[r[k] for k in ["strain_id", "assembly_tier", "top_ab_score", "top_af_score", "ab_node", "af_node", "visible_label", "top_ab_locator", "top_af_locator", "top_ab_product", "top_af_product"]] for r in plot_rows],
               "Sapote-Mamey cross-strain top AB/AF priority figure data; visible labels are node-first and exclude BGC IDs")
    _save(fig, png)
    return _register_figure(out_dir, "fig_dual_priority_atlas", png, source_csv, data_source=data.source_file)


def _fig_special_bucket_heatmap(data: MasterFigureInput, out_dir: Path) -> dict[str, Any]:
    rows = data.special_buckets or []
    metrics = ["nucleoside_priority_rows", "polyene_ptm_flag_rows", "other_token_rows", "rggmci_high_pairs"]
    labels = ["Nucleoside priority", "Polyene/PTM flags", "Other-token rows", "RG-GMCI high pairs"]
    strain_ids = [_text(r.get("strain_id")) for r in rows]
    matrix = [[_num(r.get(m)) for m in metrics] for r in rows]
    # Scale each column independently for visibility, sidecar preserves exact values.
    scaled = []
    for row in matrix:
        scaled.append([])
    colmax = [max([row[j] for row in matrix] or [1]) or 1 for j in range(len(metrics))]
    for i, row in enumerate(matrix):
        scaled[i] = [row[j] / colmax[j] for j in range(len(metrics))]

    fig, ax = plt.subplots(figsize=(11.5, 7.0))
    im = ax.imshow(scaled, aspect="auto", cmap="YlGnBu", vmin=0, vmax=1)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=9)
    ax.set_yticks(range(len(strain_ids)))
    ax.set_yticklabels(strain_ids, fontsize=9)
    for i, row in enumerate(matrix):
        for j, val in enumerate(row):
            ax.text(j, i, f"{val:g}", ha="center", va="center", fontsize=8, color=PALETTE["ink"])
    ax.set_title("Special scan buckets by strain", fontsize=18, color=PALETTE["navy"], fontweight="bold")
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Column-scaled intensity; cell text gives exact count", fontsize=8)
    _footer(fig, data.source_file)
    png = _fig_path(out_dir, "fig_special_bucket_heatmap")
    _write_csv(out_dir / f"{_fig_meta('fig_special_bucket_heatmap')['visible_id']}_special_bucket_burden_by_strain_data.csv",
               ["strain_id"] + metrics,
               [[r.get("strain_id")] + [r.get(m) for m in metrics] for r in rows],
               "Sapote–Mamey special bucket heatmap data; image values are column-normalized")
    _save(fig, png)
    return _register_figure(out_dir, "fig_special_bucket_heatmap", png, png.with_name(png.stem + "_data.csv"), data_source=data.source_file)


def _fig_top_lead_boards(data: MasterFigureInput, out_dir: Path) -> dict[str, Any]:
    rows = data.strain_summary
    fig, axes = plt.subplots(1, 2, figsize=(16, 9), sharey=True)
    boards = [
        (axes[0], "Top antibacterial lead per strain", "top_antibacterial_score", "top_antibacterial_products", "top_antibacterial_locator", PALETTE["green"]),
        (axes[1], "Top antifungal lead per strain", "top_antifungal_score", "top_antifungal_products", "top_antifungal_locator", PALETTE["amber"]),
    ]
    sorted_rows = sorted(rows, key=lambda r: _num(r.get("top_antibacterial_score")), reverse=True)
    y = list(range(len(sorted_rows)))
    labels = [_text(r.get("strain_id")) for r in sorted_rows]
    for ax, title, score_key, prod_key, loc_key, color in boards:
        vals = [_num(r.get(score_key)) for r in sorted_rows]
        ax.barh(y, vals, color=color, alpha=0.88)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=9)
        ax.invert_yaxis()
        ax.set_xlim(0, max(vals) * 1.42 if vals else 100)
        ax.set_xlabel("Priority score")
        ax.set_title(title, fontsize=15, color=PALETTE["navy"], fontweight="bold")
        ax.grid(axis="x", alpha=0.18)
        for yi, r, v in zip(y, sorted_rows, vals):
            product = _short(r.get(prod_key), 38)
            locator = _short(r.get(loc_key), 20)
            ax.text(v + 1, yi, f"{v:g} · {locator} · {product}", va="center", fontsize=7.2, color=PALETTE["ink"])
    fig.suptitle("Lead-board summary: one best AB and AF candidate per strain", fontsize=20, color=PALETTE["navy"], fontweight="bold")
    _footer(fig, data.source_file)
    png = _fig_path(out_dir, "fig_top_lead_boards")
    _write_csv(out_dir / f"{_fig_meta('fig_top_lead_boards')['visible_id']}_top_lead_board_node_first_data.csv",
               ["strain_id", "top_antibacterial_locator", "top_antibacterial_products", "top_antibacterial_score", "top_antifungal_locator", "top_antifungal_products", "top_antifungal_score"],
               [[r.get("strain_id"), r.get("top_antibacterial_locator"), r.get("top_antibacterial_products"), r.get("top_antibacterial_score"),
                 r.get("top_antifungal_locator"), r.get("top_antifungal_products"), r.get("top_antifungal_score")] for r in rows],
               "Sapote–Mamey top-lead board figure data")
    _save(fig, png)
    return _register_figure(out_dir, "fig_top_lead_boards", png, png.with_name(png.stem + "_data.csv"), data_source=data.source_file)


def _fig_strain_card_atlas(data: MasterFigureInput, out_dir: Path) -> dict[str, Any]:
    rows = data.strain_summary[:12]
    fig, ax = plt.subplots(figsize=(16, 9))
    ax.axis("off")
    ax.text(0.02, 0.955, "Strain card atlas", fontsize=26, color=PALETTE["navy"], fontweight="bold")
    ax.text(0.02, 0.915, "One boss-facing card per completed strain; use the workbook/CSV sidecars for raw row details", fontsize=12.5, color=PALETTE["gray"])
    cols = 5 if len(rows) > 8 else 4
    tw = 0.94 / cols
    th = 0.25
    for i, r in enumerate(rows):
        col, row = i % cols, i // cols
        x = 0.025 + col * tw
        y = 0.625 - row * (th + 0.035)
        tier = _text(r.get("assembly_tier")).upper()
        accent = "red" if tier == "VERY_POOR" else "amber" if tier == "POOR" else "blue" if tier == "MODERATE" else "green"
        body = (
            f"{_wrap(r.get('display_name'), 30, 2)}\n"
            f"Genome: {_num(r.get('genome_bp'))/1_000_000:.2f} Mb · contigs: {_int(r.get('contigs')):,}\n"
            f"N50: {_int(r.get('n50')):,} · GC: {_num(r.get('gc_pct')):.1f}%\n"
            f"BGCs raw/corr: {_int(r.get('raw_bgcs'))} / {_num(r.get('corrected_bgcs')):.1f}\n"
            f"Interior/Edge/Full: {_int(r.get('interior_bgcs'))}/{_int(r.get('edge_bgcs'))}/{_int(r.get('full_contig_bgcs'))}\n"
            f"Top AB: {_short(r.get('top_antibacterial_products'), 33)}\n"
            f"Top AF: {_short(r.get('top_antifungal_products'), 33)}"
        )
        _card(ax, x, y, tw - 0.018, th, f"{_text(r.get('strain_id'))} · {tier}", body, accent, 8.5, 7.0)
    _footer(fig, data.source_file)
    png = _fig_path(out_dir, "fig_strain_card_atlas")
    _write_csv(out_dir / f"{_fig_meta('fig_strain_card_atlas')['visible_id']}_strain_card_atlas_data.csv",
               ["strain_id", "display_name", "assembly_tier", "genome_bp", "contigs", "n50", "gc_pct", "raw_bgcs", "corrected_bgcs"],
               [[r.get("strain_id"), r.get("display_name"), r.get("assembly_tier"), r.get("genome_bp"), r.get("contigs"), r.get("n50"), r.get("gc_pct"), r.get("raw_bgcs"), r.get("corrected_bgcs")] for r in rows],
               "Sapote–Mamey strain card atlas figure data")
    _save(fig, png)
    return _register_figure(out_dir, "fig_strain_card_atlas", png, png.with_name(png.stem + "_data.csv"), data_source=data.source_file)


def render_master_figure_atlas(workbook_path: str | os.PathLike[str], out_dir: str | os.PathLike[str], *, make_zip: bool = True) -> dict[str, Any]:
    """Render the six boss-ready master figures and package them.

    Failures are collected into the manifest rather than raised per figure, so a
    single nonessential plot failure does not prevent downstream package sealing.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = load_master_figure_input(workbook_path)
    manifest: dict[str, Any] = {
        "status": "PASS",
        "source_workbook": os.path.basename(str(workbook_path)),
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "n_strains": len(data.strain_summary),
        "figures": [],
        "errors": [],
    }
    renderers = [
        _fig_master_dashboard,
        _fig_bgc_assembly_landscape,
        _fig_dual_priority_atlas,
        _fig_special_bucket_heatmap,
        _fig_top_lead_boards,
        _fig_strain_card_atlas,
    ]
    for fn in renderers:
        try:
            manifest["figures"].append(fn(data, out))
        except Exception as exc:  # non-blocking render contract
            manifest["status"] = "PARTIAL"
            manifest["errors"].append({"figure": fn.__name__, "error": repr(exc)})
    _write_figure_index(out / "FIGURE_INDEX.csv", manifest["figures"])
    # v9.7.374 fix: both figure_manifest.json writes below were bare .write_text() -- see
    # _write_csv above for the failure mode. This manifest is the authoritative PASS/PARTIAL
    # status record for the whole atlas render.
    _atomic_write_text(out / "figure_manifest.json", json.dumps(manifest, indent=2))
    _write_remake_markdown(out / "FIGURE_REMAKE_GUIDE.md", manifest)
    if make_zip:
        import zipfile as _zipfile
        zip_path = out.with_suffix(".zip")
        with _zipfile.ZipFile(zip_path, "w", compression=_zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(out.rglob("*")):
                if p.is_file():
                    zf.write(p, p.relative_to(out))
        manifest["zip"] = str(zip_path)
        _atomic_write_text(out / "figure_manifest.json", json.dumps(manifest, indent=2))
    return manifest


def _write_remake_markdown(path: Path, manifest: dict[str, Any]) -> None:
    lines = [
        "# cohort Master Figure Atlas — Remake Guide",
        "",
        "## Exact command",
        "",
        "```bash",
        "python tools/build_master_figures.py --workbook <MASTER.xlsx> --out-dir master_figures",
        "```",
        "",
        "## Figure set",
        "",
        "These are deterministic Matplotlib figures generated from the master workbook sheets `Strain_Summary`, `Special_Buckets`, `Top_Antibacterial`, and `Top_Antifungal`.",
        "",
        "Every figure has a stable visible ID, long ID, source CSV, PDF/SVG/PNG outputs, and a markdown sidecar.",
        "",
        "| Visible ID | Figure | Purpose | Source CSV | Sidecar |",
        "|---|---|---|---|---|",
    ]
    for fig in manifest.get("figures", []):
        lines.append(
            f"| `{fig.get('visible_id','')}` | `{Path(fig.get('png','')).name}` | "
            f"{fig.get('purpose','master figure')} | `{Path(fig.get('source_csv','')).name}` | "
            f"`{Path(fig.get('sidecar_md','')).name}` |"
        )
    lines += [
        "",
        "## Layout-safety notes",
        "",
        "- Labels are wrapped before truncation and never intentionally shrunk below 7 pt.",
        "- The dashboard and strain-card atlas avoid raw wide tables.",
        "- Full labels and exact numeric values are preserved in sidecar CSV files.",
        "- Assembly-tier warnings are visible on the dashboard, including VERY_POOR assemblies.",
        "- Captions preserve claim-safety: deterministic priority/capacity, not wet-lab activity.",
    ]
    # v9.7.374 fix: was a bare path.write_text() -- see _write_csv above for the failure mode.
    _atomic_write_text(path, "\n".join(lines) + "\n")


__all__ = [
    "MasterFigureInput",
    "load_master_figure_input",
    "read_xlsx_table",
    "render_master_figure_atlas",
    "_wrap",
    "_short",
]
