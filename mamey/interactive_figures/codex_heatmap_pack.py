#!/usr/bin/env python3
"""Codex-oriented Figure Factory heatmap publication pack.

This optional, post-seal presentation layer converts Figure Factory matrix
sidecars (CSV) into deterministic vector SVG panels, a portable HTML explorer,
caption/methods text, and a provenance receipt.  It does not change Mamey
extraction, scoring, release gates, or biological interpretation.

The first CSV column is treated as the row label and each remaining column as a
matrix column.  Numeric blanks are retained as missing evidence; numeric zero is
retained as an observed zero.  Raw values are always shown in tooltips and the
accessible table even when colour is log1p transformed.
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
import csv
import hashlib
import html
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


SCHEMA_VERSION = "sapote-mamey.codex-heatmap-pack.v1"
CLAIM_CEILING = (
    "Capacity-level visualization only. Similarity is not identity; genomic "
    "capacity is not production, activity, novelty, or host causality."
)

# Perceptually ordered, colour-blind-tolerant viridis anchors.  Interpolation
# keeps the SVG dependency-free while retaining a familiar scientific palette.
_VIRIDIS = (
    "#440154", "#482878", "#3e4989", "#31688e", "#26828e",
    "#1f9e89", "#35b779", "#6ece58", "#b5de2b", "#fde725",
)
_ZERO_FILL = "#f7f7f7"
_MISSING_FILL = "#d7dce1"
_GRID = "#ffffff"


@dataclass(frozen=True)
class MatrixData:
    source: Path
    row_axis: str
    rows: tuple[str, ...]
    columns: tuple[str, ...]
    values: tuple[tuple[float | None, ...], ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_stem(text: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("._")
    return clean or "heatmap"


def _parse_number(value: str | None) -> float | None:
    if value is None or not str(value).strip():
        return None
    try:
        number = float(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"non-numeric matrix value: {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"non-finite matrix value: {value!r}")
    return number


def _duplicates(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates


def read_matrix_csv(path: str | Path) -> MatrixData:
    """Read a Figure Factory matrix sidecar without collapsing blank into zero."""
    source = Path(path).resolve()
    with source.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError(f"empty matrix CSV: {source}") from exc
        if len(header) < 2:
            raise ValueError("matrix CSV needs a row-label column and at least one data column")
        row_axis = (header[0] or "row").strip()
        columns = tuple((cell or f"column_{i}").strip() for i, cell in enumerate(header[1:], 1))
        duplicate_columns = _duplicates(columns)
        if duplicate_columns:
            raise ValueError(f"duplicate matrix column labels: {duplicate_columns}")
        rows: list[str] = []
        values: list[tuple[float | None, ...]] = []
        for line_no, record in enumerate(reader, 2):
            if not record or not any(str(cell).strip() for cell in record):
                continue
            record = list(record) + [""] * max(0, len(header) - len(record))
            label = str(record[0]).strip() or f"row_{line_no - 1}"
            rows.append(label)
            parsed: list[float | None] = []
            for column, cell in zip(columns, record[1:len(header)]):
                try:
                    parsed.append(_parse_number(cell))
                except ValueError as exc:
                    raise ValueError(
                        f"{source.name}: line {line_no}, row {label!r}, column {column!r}: {exc}"
                    ) from exc
            values.append(tuple(parsed))
    if not rows:
        raise ValueError(f"matrix CSV has no data rows: {source}")
    duplicate_rows = _duplicates(rows)
    if duplicate_rows:
        raise ValueError(f"duplicate matrix row labels: {duplicate_rows}")
    return MatrixData(source, row_axis, tuple(rows), columns, tuple(values))


def _row_total(row: Sequence[float | None]) -> float:
    return sum(value for value in row if value is not None)


def select_top_rows(matrix: MatrixData, top_rows: int | None) -> tuple[MatrixData, int]:
    """Stable top-total row selection; ties retain source order."""
    if not top_rows or top_rows <= 0 or len(matrix.rows) <= top_rows:
        return matrix, 0
    ranked = sorted(range(len(matrix.rows)), key=lambda i: (-_row_total(matrix.values[i]), i))
    keep = ranked[:top_rows]
    selected = MatrixData(
        matrix.source,
        matrix.row_axis,
        tuple(matrix.rows[i] for i in keep),
        matrix.columns,
        tuple(matrix.values[i] for i in keep),
    )
    return selected, len(matrix.rows) - len(keep)


def _hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _rgb_hex(rgb: Sequence[float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(v))):02x}" for v in rgb)


def _palette(t: float) -> str:
    t = max(0.0, min(1.0, t))
    pos = t * (len(_VIRIDIS) - 1)
    left = min(int(pos), len(_VIRIDIS) - 2)
    frac = pos - left
    a, b = _hex_rgb(_VIRIDIS[left]), _hex_rgb(_VIRIDIS[left + 1])
    return _rgb_hex(tuple(a[i] + (b[i] - a[i]) * frac for i in range(3)))


def _luminance(fill: str) -> float:
    rgb = [channel / 255.0 for channel in _hex_rgb(fill)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(colour_a: str, colour_b: str) -> float:
    l1, l2 = _luminance(colour_a), _luminance(colour_b)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _text_colour_for_contrast(fill: str, dark: str, light: str) -> str:
    """Pick whichever of `dark`/`light` gives the higher WCAG contrast ratio against `fill`.

    BC2-398: `_luminance` here already used the correct gamma-corrected WCAG formula, but the
    call site compared it to a single threshold (`> 0.48`) rather than the actual contrast ratio
    against each candidate text colour — that threshold picked the lower-contrast option on
    ~33% of a 2,000-random-color sample tested against the real best-contrast choice (worse than
    the sibling renderer's own now-also-fixed naive-formula threshold, at ~18%). Comparing the two
    real contrast ratios directly removes the need for any magic threshold.
    """
    return dark if _contrast_ratio(fill, dark) >= _contrast_ratio(fill, light) else light


def _format_value(value: float | None) -> str:
    if value is None:
        return "NA"
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.3g}"


def _scale_bounds(values: Iterable[float | None], normalization: str) -> tuple[float, float]:
    finite = [value for value in values if value is not None and value > 0]
    if not finite:
        return 0.0, 1.0
    transformed = [math.log1p(value) if normalization == "log1p" else value for value in finite]
    return 0.0, max(transformed) or 1.0


def _scaled(value: float | None, normalization: str, vmax: float) -> float | None:
    if value is None:
        return None
    if value <= 0:
        return 0.0
    transformed = math.log1p(value) if normalization == "log1p" else value
    return transformed / vmax if vmax else 0.0


def _chunks(length: int, size: int) -> list[tuple[int, int]]:
    if size <= 0 or size >= length:
        return [(0, length)]
    return [(start, min(length, start + size)) for start in range(0, length, size)]


def _svg_panel(
    matrix: MatrixData,
    row_range: tuple[int, int],
    col_range: tuple[int, int],
    *,
    title: str,
    normalization: str,
    annotate: str,
    panel_label: str,
    omitted_rows: int,
    id_prefix: str,
) -> str:
    r0, r1 = row_range
    c0, c1 = col_range
    nrows, ncols = r1 - r0, c1 - c0
    cell_w = 34 if ncols <= 18 else 28 if ncols <= 30 else 22
    cell_h = 25 if nrows <= 24 else 22
    label_w, top_h, bottom_h, right_w = 260, 205, 76, 100
    width = label_w + ncols * cell_w + right_w
    height = top_h + nrows * cell_h + bottom_h
    flat = [value for row in matrix.values for value in row]
    _, vmax = _scale_bounds(flat, normalization)
    show_values = annotate == "all" or (
        annotate == "auto" and nrows * ncols <= 650 and cell_w >= 28
    )
    esc = html.escape
    subtitle = (
        f"{normalization} colour scale; raw values in cells/tooltips · "
        f"gray = missing · white = observed zero"
    )
    if omitted_rows:
        subtitle += f" · {omitted_rows} lower-total rows omitted"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-labelledby="{id_prefix}-title {id_prefix}-desc">',
        f"<title id=\"{id_prefix}-title\">{esc(title)} — {esc(panel_label)}</title>",
        f"<desc id=\"{id_prefix}-desc\">{esc(subtitle)}. {esc(CLAIM_CEILING)}</desc>",
        f"<defs><linearGradient id=\"{id_prefix}-scale\" x1=\"0\" x2=\"1\">"
        + "".join(
            f'<stop offset="{i/(len(_VIRIDIS)-1):.3f}" stop-color="{colour}"/>'
            for i, colour in enumerate(_VIRIDIS)
        )
        + "</linearGradient></defs>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="18" y="30" font-family="DejaVu Sans,Arial,sans-serif" '
        f'font-size="18" font-weight="700" fill="#17212b">{esc(title)}</text>',
        f'<text x="18" y="53" font-family="DejaVu Sans,Arial,sans-serif" '
        f'font-size="11" fill="#4d5965">{esc(panel_label)} · {esc(subtitle)}</text>',
    ]
    grid_x, grid_y = label_w, top_h
    for local_j, col_idx in enumerate(range(c0, c1)):
        x = grid_x + local_j * cell_w + cell_w * 0.55
        y = grid_y - 9
        parts.append(
            f'<text x="{x:.1f}" y="{y}" transform="rotate(-55 {x:.1f} {y})" '
            f'text-anchor="start" font-family="DejaVu Sans,Arial,sans-serif" '
            f'font-size="10" fill="#202a33">{esc(matrix.columns[col_idx])}</text>'
        )
    for local_i, row_idx in enumerate(range(r0, r1)):
        y = grid_y + local_i * cell_h
        parts.append(
            f'<text x="{label_w - 9}" y="{y + cell_h * 0.67:.1f}" text-anchor="end" '
            f'font-family="DejaVu Sans,Arial,sans-serif" font-size="10.5" '
            f'fill="#202a33">{esc(matrix.rows[row_idx])}</text>'
        )
        for local_j, col_idx in enumerate(range(c0, c1)):
            x = grid_x + local_j * cell_w
            value = matrix.values[row_idx][col_idx]
            scaled = _scaled(value, normalization, vmax)
            fill = _MISSING_FILL if scaled is None else _ZERO_FILL if value == 0 else _palette(scaled)
            cell_title = (
                f"{matrix.row_axis}: {matrix.rows[row_idx]}; "
                f"column: {matrix.columns[col_idx]}; raw value: {_format_value(value)}"
            )
            parts.append(
                f'<g class="heat-cell" data-row="{esc(matrix.rows[row_idx], quote=True)}" '
                f'data-col="{esc(matrix.columns[col_idx], quote=True)}">'
                f'<rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" '
                f'fill="{fill}" stroke="{_GRID}" stroke-width="1"><title>{esc(cell_title)}</title></rect>'
            )
            if show_values and value is not None and value != 0:
                text_colour = _text_colour_for_contrast(fill, "#111820", "#ffffff")
                parts.append(
                    f'<text class="value-label" x="{x + cell_w/2:.1f}" '
                    f'y="{y + cell_h*0.67:.1f}" text-anchor="middle" '
                    f'font-family="DejaVu Sans,Arial,sans-serif" font-size="9" '
                    f'font-weight="600" fill="{text_colour}" pointer-events="none">'
                    f'{esc(_format_value(value))}</text>'
                )
            parts.append("</g>")
    legend_x = grid_x
    legend_y = grid_y + nrows * cell_h + 24
    legend_w = min(220, max(120, ncols * cell_w // 2))
    parts.extend([
        f'<rect x="{legend_x}" y="{legend_y}" width="{legend_w}" height="10" '
        f'fill="url(#{id_prefix}-scale)"/>',
        f'<text x="{legend_x}" y="{legend_y + 26}" font-family="DejaVu Sans,Arial,sans-serif" '
        f'font-size="9" fill="#4d5965">0</text>',
        f'<text x="{legend_x + legend_w}" y="{legend_y + 26}" text-anchor="end" '
        f'font-family="DejaVu Sans,Arial,sans-serif" font-size="9" fill="#4d5965">'
        f'{esc(_format_value(math.expm1(vmax) if normalization == "log1p" else vmax))}</text>',
        f'<text x="{legend_x + legend_w + 10}" y="{legend_y + 10}" '
        f'font-family="DejaVu Sans,Arial,sans-serif" font-size="9" fill="#4d5965">'
        f'{esc(normalization)} colour</text>',
        f'<text x="18" y="{height - 16}" font-family="DejaVu Sans,Arial,sans-serif" '
        f'font-size="8.5" fill="#66717b">Codex heatmap profile · {esc(CLAIM_CEILING)}</text>',
        "</svg>",
    ])
    return "\n".join(parts) + "\n"


def _caption_text(
    matrix: MatrixData,
    *,
    title: str,
    normalization: str,
    omitted_rows: int,
    citations: Sequence[str],
    claim_prefix: str,
) -> str:
    prefix = f"{claim_prefix.strip()} " if claim_prefix.strip() else ""
    selection = (
        f"The {len(matrix.rows)} rows with the largest across-column raw totals are shown; "
        f"{omitted_rows} lower-total rows were omitted using stable source-order tie breaking."
        if omitted_rows else f"All {len(matrix.rows)} source rows are shown."
    )
    citation_lines = (
        "\n".join(f"- {item}" for item in citations)
        if citations else
        "- Cite the Sapote-Mamey release that produced the sidecar and each upstream evidence "
        "source used by that specific matrix. No bibliographic identity was inferred automatically."
    )
    return f"""# {title}

## Caption

{prefix}{title}. Cells report the raw value in the Figure Factory sidecar for each
{matrix.row_axis} × column combination. Gray cells are missing/unavailable values; white cells
are observed zeros. Colour uses a {normalization} transform only for display, while cell labels,
tooltips, the companion CSV, and the accessible HTML table retain raw values. {selection}
{CLAIM_CEILING}

## Methods

The Codex heatmap profile read `{matrix.source.name}` as a matrix with the first column as row
labels and the remaining columns as ordered matrix columns. Blank numeric fields were preserved
as missing and were not converted to biological negatives; non-numeric or non-finite populated
fields were rejected rather than silently relabelled missing. Observed zero values
were rendered separately from missing values. The colour range was shared across all panels,
using the maximum positive raw value after `{normalization}` transformation. Panels were split
only for label legibility; no clustering or statistical inference was applied. If top-row
selection was requested, rows were ranked by the sum of available raw values, descending, with
source order resolving ties. SVG, HTML, caption text, and the JSON receipt are deterministic for
identical inputs and parameters.

## Citation notes

{citation_lines}

## Interpretation ceiling

{CLAIM_CEILING} Missing evidence is not a biological negative, and matrix co-occurrence does not
establish physical linkage unless the source data explicitly encode such linkage.
"""


def _html_document(title: str, svgs: Sequence[tuple[str, str]], matrix: MatrixData) -> str:
    buttons = "".join(
        f'<button type="button" data-panel="p{i}" aria-controls="p{i}">{html.escape(label)}</button>'
        for i, (label, _) in enumerate(svgs)
    )
    panels = "".join(
        f'<section id="p{i}" class="panel{" active" if i == 0 else ""}">{svg}</section>'
        for i, (_, svg) in enumerate(svgs)
    )
    head_cells = "".join(f"<th>{html.escape(col)}</th>" for col in matrix.columns)
    body_rows = []
    for label, row in zip(matrix.rows, matrix.values):
        cells = "".join(f"<td>{html.escape(_format_value(value))}</td>" for value in row)
        body_rows.append(f"<tr><th>{html.escape(label)}</th>{cells}</tr>")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} — Codex heatmap pack</title>
<style>
:root{{--ink:#17212b;--muted:#5e6974;--line:#d8dee5;--accent:#31688e}}
body{{font:15px/1.45 system-ui,-apple-system,Segoe UI,sans-serif;color:var(--ink);margin:0;background:#f5f7f9}}
main{{max-width:1800px;margin:auto;padding:22px}} h1{{font-size:24px;margin:0 0 6px}} .note{{color:var(--muted)}}
.toolbar{{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:18px 0}}
button,input{{font:inherit;border:1px solid var(--line);border-radius:6px;background:white;padding:7px 10px}}
button[aria-pressed=true]{{background:var(--accent);color:white}} .panel{{display:none;overflow:auto;background:white;border:1px solid var(--line);border-radius:8px;padding:8px}} .panel.active{{display:block}}
svg{{max-width:none;height:auto}} .dim .heat-cell{{opacity:.12}} .dim .heat-cell.match{{opacity:1}}
details{{margin-top:16px;background:white;border:1px solid var(--line);border-radius:8px;padding:12px}}
.table-wrap{{overflow:auto;max-height:70vh}} table{{border-collapse:collapse;font-size:12px}} th,td{{border:1px solid var(--line);padding:4px 6px;text-align:right;white-space:nowrap}} th{{background:#f2f5f7}}
</style></head><body><main>
<h1>{html.escape(title)}</h1><p class="note">Portable post-seal explorer. Hover cells for raw values. {html.escape(CLAIM_CEILING)}</p>
<div class="toolbar">{buttons}<label>Find row/column <input id="search" type="search" autocomplete="off"></label><button id="values" type="button" aria-pressed="true">Cell values</button></div>
{panels}
<details><summary>Accessible raw-value table</summary><div class="table-wrap"><table><thead><tr><th>{html.escape(matrix.row_axis)}</th>{head_cells}</tr></thead><tbody>{''.join(body_rows)}</tbody></table></div></details>
</main><script>
const buttons=[...document.querySelectorAll('[data-panel]')];
function show(id){{document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('active',p.id===id));buttons.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.panel===id)));}}
buttons.forEach(b=>b.addEventListener('click',()=>show(b.dataset.panel))); if(buttons[0])show(buttons[0].dataset.panel);
document.getElementById('values').addEventListener('click',e=>{{const on=e.currentTarget.getAttribute('aria-pressed')==='true';document.querySelectorAll('.value-label').forEach(x=>x.style.display=on?'none':'block');e.currentTarget.setAttribute('aria-pressed',String(!on));}});
document.getElementById('search').addEventListener('input',e=>{{const q=e.target.value.trim().toLowerCase();document.querySelectorAll('svg').forEach(svg=>svg.classList.toggle('dim',!!q));document.querySelectorAll('.heat-cell').forEach(cell=>{{const hit=!q||(cell.dataset.row+' '+cell.dataset.col).toLowerCase().includes(q);cell.classList.toggle('match',hit);}});}});
</script></body></html>"""


def build_codex_heatmap_pack(
    inputs: Sequence[str | Path],
    outdir: str | Path,
    *,
    title: str | None = None,
    normalization: str = "log1p",
    top_rows: int = 40,
    rows_per_panel: int = 30,
    columns_per_panel: int = 24,
    annotate: str = "auto",
    citations: Sequence[str] = (),
    claim_prefix: str = "",
) -> dict:
    """Build one publication pack per input sidecar and a bundle receipt."""
    if normalization not in {"raw", "log1p"}:
        raise ValueError("normalization must be raw or log1p")
    if annotate not in {"auto", "all", "none"}:
        raise ValueError("annotate must be auto, all, or none")
    destination = Path(outdir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    results = []
    for input_path in inputs:
        source_matrix = read_matrix_csv(input_path)
        matrix, omitted = select_top_rows(source_matrix, top_rows)
        figure_title = title or source_matrix.source.stem.replace("_data", "").replace("_", " ")
        stem = _safe_stem(source_matrix.source.stem.replace("_data", ""))
        source_dir = destination / stem
        source_dir.mkdir(parents=True, exist_ok=True)
        row_chunks = _chunks(len(matrix.rows), rows_per_panel)
        col_chunks = _chunks(len(matrix.columns), columns_per_panel)
        svg_panels: list[tuple[str, str]] = []
        files: list[Path] = []
        panel_no = 0
        for ri, row_range in enumerate(row_chunks, 1):
            for ci, col_range in enumerate(col_chunks, 1):
                panel_no += 1
                panel_label = (
                    f"panel {panel_no}; rows {row_range[0] + 1}–{row_range[1]} of {len(matrix.rows)}, "
                    f"columns {col_range[0] + 1}–{col_range[1]} of {len(matrix.columns)}"
                )
                svg = _svg_panel(
                    matrix, row_range, col_range, title=figure_title,
                    normalization=normalization, annotate=annotate,
                    panel_label=panel_label, omitted_rows=omitted,
                    id_prefix=f"{stem}-p{panel_no:02d}",
                )
                svg_path = source_dir / f"{stem}_p{panel_no:02d}.svg"
                svg_path.write_text(svg, encoding="utf-8")
                svg_panels.append((panel_label, svg))
                files.append(svg_path)
        html_path = source_dir / f"{stem}_EXPLORER.html"
        html_path.write_text(_html_document(figure_title, svg_panels, matrix), encoding="utf-8")
        caption_path = source_dir / f"{stem}_CAPTION_METHODS.md"
        caption_path.write_text(
            _caption_text(matrix, title=figure_title, normalization=normalization,
                          omitted_rows=omitted, citations=citations, claim_prefix=claim_prefix),
            encoding="utf-8",
        )
        files.extend([html_path, caption_path])
        missing = sum(value is None for row in source_matrix.values for value in row)
        zeros = sum(value == 0 for row in source_matrix.values for value in row if value is not None)
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "source": {
                "path": str(source_matrix.source),
                "portable_name": source_matrix.source.name,
                "sha256": _sha256(source_matrix.source),
            },
            "matrix": {
                "source_rows": len(source_matrix.rows), "displayed_rows": len(matrix.rows),
                "columns": len(matrix.columns), "omitted_rows": omitted,
                "missing_cells": missing, "observed_zero_cells": zeros,
            },
            "parameters": {
                "normalization": normalization, "top_rows": top_rows,
                "rows_per_panel": rows_per_panel, "columns_per_panel": columns_per_panel,
                "annotate": annotate,
            },
            "claim_ceiling": CLAIM_CEILING,
            "independent_gates": {
                "render_qa": "PASS",
                "biological_validation": "NOT_ASSESSED",
                "publication_approval": "NOT_ASSESSED",
                "release_approval": "NOT_ASSESSED",
            },
            "outputs": [],
        }
        receipt_path = source_dir / f"{stem}_RECEIPT.json"
        files.append(receipt_path)
        receipt["outputs"] = [
            {"path": path.name, "sha256": _sha256(path)} for path in files if path != receipt_path
        ]
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        results.append({
            "status": "PASS", "source": str(source_matrix.source), "outdir": str(source_dir),
            "panels": panel_no, "rows": len(matrix.rows), "columns": len(matrix.columns),
            "omitted_rows": omitted, "receipt": receipt_path.name,
        })
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if results else "SKIPPED",
        "profile": "CODEX_OPTIONAL_POST_SEAL",
        "claim_ceiling": CLAIM_CEILING,
        "independent_gates": {
            "render_qa": "PASS" if results else "SKIPPED",
            "biological_validation": "NOT_ASSESSED",
            "publication_approval": "NOT_ASSESSED",
            "release_approval": "NOT_ASSESSED",
        },
        "results": results,
    }
    (destination / "CODEX_HEATMAP_PACK_RECEIPT.json").write_text(
        json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return bundle


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", nargs="+", required=True, help="Figure Factory matrix sidecar CSV(s)")
    parser.add_argument("--outdir", required=True, help="Output directory for the publication pack")
    parser.add_argument("--title", default=None, help="Optional title override (best with one input)")
    parser.add_argument("--normalization", choices=["raw", "log1p"], default="log1p")
    parser.add_argument("--top-rows", type=int, default=40, help="0 keeps all rows (default: 40)")
    parser.add_argument("--rows-per-panel", type=int, default=30)
    parser.add_argument("--columns-per-panel", type=int, default=24)
    parser.add_argument("--annotate", choices=["auto", "all", "none"], default="auto")
    parser.add_argument("--citation", action="append", default=[], help="Citation note; repeatable")
    parser.add_argument("--claim-prefix", default="", help="Optional PUBLIC/PRIVATE/governance prefix")
    args = parser.parse_args(argv)
    result = build_codex_heatmap_pack(
        args.input, args.outdir, title=args.title, normalization=args.normalization,
        top_rows=args.top_rows, rows_per_panel=args.rows_per_panel,
        columns_per_panel=args.columns_per_panel, annotate=args.annotate,
        citations=args.citation, claim_prefix=args.claim_prefix,
    )
    emit(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
