"""Tree-aligned quantitative heatmap panel — Figure Factory × phylogenomics integration.

Closes the gap the owner named on 2026-09-02: the categorical annotation tracks
(`tools/tree_bgc_overlay.py`, `mamey/phylogeny_figure_factory.py`) had no quantitative
companion, so tree + KS-burden / class-depth heatmap panels required manual assembly.

This module CONSUMES an already-built, sanity-gated tree — it never builds, re-roots,
re-orders, or relabels one (tree-source separation; the tip order of the bound Newick is
the one and only row order). All inputs are digest-bound; matrix blanks stay missing and
are never rendered as zero; an `Other` column is scaled separately so it cannot wash out
named categories (shared heatmap policy). Output is vector SVG with live text.

Claim ceiling: a panel displays its declared inputs. It makes no novelty, activity, or
identity claim; the mandatory caption/methods block carries denominators and limits.
"""
from __future__ import annotations

import csv
import hashlib
import html
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Mapping

from .figure_theme import CLAIM_SAFETY

SCHEMA = "sapote.tree-heatmap-panel.v1"
TRANSFORMS = {"linear", "log1p"}
OTHER_COLUMN_NAMES = {"other", "Other", "OTHER"}

# Neutral sequential ramp (light -> dark); a deliberate single-hue scale so genus/group
# color semantics stay free for the tree side. 6 steps, printable.
RAMP = ("#f3f6fa", "#d3e0ee", "#a9c3de", "#7aa1c9", "#4d7cab", "#2b5580")
MISSING_FILL = "#ffffff"
MISSING_STROKE = "#b9b9b9"
FIGURE_SET_ID = re.compile(r"^FS[0-9]{3}$")


class PanelHold(ValueError):
    """Typed fail-closed refusal raised before any output artifact is written."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _hold(code: str, detail: str) -> None:
    raise PanelHold(code, detail)


_OVERLAY = None


def _overlay():
    """Load the renderer-owned parsing/binding helpers by path (the
    phylogeny_figure_factory reuse pattern) — one Newick parser, not two."""
    global _OVERLAY
    if _OVERLAY is None:
        path = Path(__file__).resolve().parents[1] / "tools" / "tree_bgc_overlay.py"
        spec = importlib.util.spec_from_file_location("_thp_tree_bgc_overlay", path)
        if spec is None or spec.loader is None:
            _hold("THP_BINDING_HOLD", "tree_bgc_overlay renderer is unavailable")
        module = importlib.util.module_from_spec(spec)
        sys.modules["_thp_tree_bgc_overlay"] = module
        spec.loader.exec_module(module)
        _OVERLAY = module
    return _OVERLAY


def _bound_file(root: Path, descriptor: Mapping[str, Any], name: str) -> Path:
    if not isinstance(descriptor, Mapping):
        _hold("THP_BINDING_HOLD", f"{name}: descriptor required")
    locator, expected = descriptor.get("logical_locator"), descriptor.get("sha256")
    if not isinstance(locator, str) or not locator or Path(locator).is_absolute():
        _hold("THP_BINDING_HOLD", f"{name}: portable relative locator required")
    if ".." in Path(locator).parts:
        _hold("THP_BINDING_HOLD", f"{name}: parent traversal refused")
    path = (root / locator).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        _hold("THP_BINDING_HOLD", f"{name}: locator escapes the panel root")
    if not path.is_file():
        _hold("THP_BINDING_HOLD", f"{name}: bound file is missing")
    if not isinstance(expected, str) or len(expected) != 64:
        _hold("THP_BINDING_HOLD", f"{name}: sha256 required")
    actual = _overlay().sha256_file(path)
    if actual != expected:
        _hold("THP_BINDING_HOLD", f"{name}: SHA-256 mismatch")
    return path


def load_matrix(path: Path) -> tuple[list[str], dict[str, dict[str, float | None]]]:
    """Strain-keyed quantitative matrix. Blanks stay None (missing != zero);
    non-numeric cells and duplicate strains refuse."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames or []
        if not fields or fields[0] != "strain" or len(fields) < 2:
            _hold("THP_MATRIX_HOLD", "matrix needs a leading 'strain' column plus >=1 feature column")
        columns = list(fields[1:])
        rows: dict[str, dict[str, float | None]] = {}
        for number, row in enumerate(reader, 1):
            strain = (row.get("strain") or "").strip()
            if not strain:
                _hold("THP_MATRIX_HOLD", f"matrix row {number}: blank strain id")
            if strain in rows:
                _hold("THP_MATRIX_HOLD", f"duplicate matrix strain: {strain}")
            values: dict[str, float | None] = {}
            for column in columns:
                raw = (row.get(column) or "").strip()
                if raw == "":
                    values[column] = None
                    continue
                try:
                    values[column] = float(raw)
                except ValueError:
                    _hold("THP_MATRIX_HOLD",
                          f"matrix row {number} ({strain}), column {column!r}: non-numeric {raw!r}")
            rows[strain] = values
    if not rows:
        _hold("THP_MATRIX_HOLD", "matrix has no data rows")
    return columns, rows


def align_rows(tips: list[str], crosswalk: Mapping[str, Mapping[str, str]],
               matrix: Mapping[str, Mapping[str, float | None]]) -> list[dict[str, Any]]:
    """One heatmap row per tip, in TREE order — the tree is the only sort authority.
    Every tip must resolve through the crosswalk to exactly one matrix row; every matrix
    row must be consumed. No prefix repair, no fuzzy match, no silent drops."""
    aligned: list[dict[str, Any]] = []
    used: set[str] = set()
    for tip in tips:
        entry = crosswalk.get(tip)
        if entry is None:
            _hold("THP_ALIGNMENT_HOLD", f"tree tip {tip!r} has no crosswalk row")
        strain = entry["strain"]
        if strain not in matrix:
            _hold("THP_ALIGNMENT_HOLD",
                  f"tip {tip!r} -> strain {strain!r} has no matrix row (no repair attempted)")
        used.add(strain)
        aligned.append({"tip": tip, "strain": strain,
                        "display_label": entry["display_label"], "role": entry["role"],
                        "genus": entry["genus"], "values": dict(matrix[strain])})
    orphans = sorted(set(matrix) - used)
    if orphans:
        _hold("THP_ALIGNMENT_HOLD", f"matrix rows with no tree tip: {orphans}")
    return aligned


def _column_scale(values: list[float], transform: str) -> tuple[float, float]:
    if transform == "log1p":
        values = [math.log1p(v) for v in values]
    lo, hi = min(values), max(values)
    return lo, (hi if hi > lo else lo + 1.0)


def _cell_fraction(value: float, lo: float, hi: float, transform: str) -> float:
    v = math.log1p(value) if transform == "log1p" else value
    return max(0.0, min(1.0, (v - lo) / (hi - lo)))


def build_panel(config_path: str | Path) -> dict[str, Any]:
    """Validate, align, render. Returns the panel receipt (also written beside the SVG)."""
    from mamey.figure_policy import validate_caption_methods

    config_path = Path(config_path)
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _hold("THP_BINDING_HOLD", f"panel config unreadable: {exc}")
    root = config_path.resolve().parent
    figure_set_id = str(config.get("figure_set_id") or "")
    if not FIGURE_SET_ID.fullmatch(figure_set_id):
        _hold("THP_REGISTRY_HOLD", "figure_set_id must name one Figure Factory registry row (FS###)")

    # 1. Tree sanity gate: an Amber-lane receipt with status PASS, digest-bound.
    sanity_path = _bound_file(root, config.get("tree_sanity_receipt"), "tree_sanity_receipt")
    try:
        sanity = json.loads(sanity_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _hold("THP_TREE_SANITY_HOLD", f"sanity receipt unreadable: {exc}")
    if sanity.get("status") != "PASS":
        _hold("THP_TREE_SANITY_HOLD",
              f"tree sanity receipt status is {sanity.get('status')!r}, not PASS — "
              "an unapproved tree is never rendered")

    # 2. Bound tree plus the Figure Factory evidence-admission receipt. A generic PASS
    #    token is not sufficient: the receipt must name the exact tree and outgroup.
    overlay = _overlay()
    tree_path = _bound_file(root, config.get("tree"), "tree")
    tree_hash = config["tree"]["sha256"]
    if sanity.get("tree_sha256") != tree_hash:
        _hold("THP_TREE_SANITY_MISMATCH", "tree sanity receipt is not bound to the selected tree")
    evidence_path = _bound_file(
        root, config.get("phylogeny_evidence_receipt"), "phylogeny_evidence_receipt")
    try:
        evidence_receipt = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _hold("THP_PHYLO_EVIDENCE_HOLD", f"phylogeny evidence receipt unreadable: {exc}")
    if not isinstance(evidence_receipt, Mapping):
        _hold("THP_PHYLO_EVIDENCE_HOLD", "phylogeny evidence receipt must be a JSON object")
    if (evidence_receipt.get("schema_version") != "sapote.phylogeny-figure-factory.v1" or
            evidence_receipt.get("figure_kind") != "phylogeny_evidence_receipt_widget_v1" or
            evidence_receipt.get("status") != "PASS_EVIDENCE_WIDGET_READY"):
        _hold("THP_PHYLO_EVIDENCE_HOLD", "a PASS Figure Factory phylogeny evidence receipt is required")
    evidence = (evidence_receipt.get("bound_inputs") or {}).get("tree_evidence") or {}
    admitted = evidence.get("admitted_signoff") or {}
    if ((evidence.get("tree") or {}).get("sha256") != tree_hash or
            admitted.get("tree_sha256") != tree_hash):
        _hold("THP_PHYLO_EVIDENCE_MISMATCH", "phylogeny evidence receipt names a different tree")
    outgroup_tip = evidence_receipt.get("outgroup_tip")
    if not isinstance(outgroup_tip, str) or not outgroup_tip:
        _hold("THP_PHYLO_EVIDENCE_HOLD", "phylogeny evidence receipt lacks an exact outgroup tip")
    tree_root = overlay.parse_newick(tree_path.read_text(encoding="utf-8"))
    tips = overlay.tip_order(tree_root)
    crosswalk_path = _bound_file(root, config.get("tip_crosswalk"), "tip_crosswalk")
    try:
        crosswalk = overlay.load_crosswalk(crosswalk_path)
    except ValueError as exc:
        _hold("THP_ALIGNMENT_HOLD", f"crosswalk invalid: {exc}")
    declared_outgroups = sorted(
        tip for tip, row in crosswalk.items() if row.get("role") == "OUTGROUP")
    if declared_outgroups != [outgroup_tip]:
        _hold(
            "THP_OUTGROUP_MISMATCH",
            f"crosswalk OUTGROUP rows {declared_outgroups!r} do not equal admitted outgroup {outgroup_tip!r}",
        )

    # 3. Bound matrix + per-column policy.
    matrix_path = _bound_file(root, config.get("matrix"), "matrix")
    columns, matrix = load_matrix(matrix_path)
    transforms: dict[str, str] = {}
    for column in columns:
        transform = str((config.get("column_transforms") or {}).get(column, "linear"))
        if transform not in TRANSFORMS:
            _hold("THP_MATRIX_HOLD", f"unknown transform for {column!r}: {transform!r}")
        transforms[column] = transform

    # 4. Mandatory caption/methods block (figure_policy owns the schema).
    caption = config.get("caption_methods")
    if not isinstance(caption, Mapping):
        _hold("THP_CAPTION_HOLD", "caption_methods block is mandatory")
    try:
        validate_caption_methods(dict(caption))
    except Exception as exc:
        _hold("THP_CAPTION_HOLD", f"caption/methods rejected by figure_policy: {exc}")

    # 5. Align (tree order is authoritative) and scale per column. `Other` columns are
    #    flagged and scaled on their own axis so they cannot wash out named categories.
    aligned = align_rows(tips, crosswalk, matrix)
    scales: dict[str, tuple[float, float]] = {}
    missing_counts: dict[str, int] = {}
    for column in columns:
        present = [row["values"][column] for row in aligned if row["values"][column] is not None]
        missing_counts[column] = len(aligned) - len(present)
        if not present:
            _hold("THP_MATRIX_HOLD", f"column {column!r} has no present values at all")
        scales[column] = _column_scale(present, transforms[column])

    svg = _render_svg(aligned, columns, transforms, scales, config)
    out_dir = root / str(config.get("output_dir") or "panel_out")
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = str(config.get("panel_id") or "tree_heatmap_panel")
    svg_path = out_dir / f"{stem}.svg"
    svg_path.write_text(svg, encoding="utf-8")

    receipt = {
        "schema": SCHEMA,
        "panel_id": stem,
        "figure_id": stem,
        "figure_set_id": figure_set_id,
        "tree_sha256": tree_hash,
        "crosswalk_sha256": config["tip_crosswalk"]["sha256"],
        "matrix_sha256": config["matrix"]["sha256"],
        "tree_sanity_receipt_sha256": config["tree_sanity_receipt"]["sha256"],
        "phylogeny_evidence_receipt_sha256": config["phylogeny_evidence_receipt"]["sha256"],
        "outgroup_tip": outgroup_tip,
        "tip_count": len(aligned),
        "columns": columns,
        "column_transforms": transforms,
        "other_columns_isolated": sorted(c for c in columns if c in OTHER_COLUMN_NAMES),
        "missing_cells_by_column": missing_counts,
        "missingness_note": "blank cells are MISSING, rendered as hollow cells, never zero",
        "row_order_authority": "tree tip order (never re-sorted by matrix)",
        "svg": svg_path.name,
        "outputs": [{"logical_locator": svg_path.name,
                     "sha256": hashlib.sha256(svg_path.read_bytes()).hexdigest(),
                     "bytes": svg_path.stat().st_size}],
        "claim_footer": CLAIM_SAFETY + " Judgment deferred.",
        "claim_note": ("Display of declared inputs only; class-level context; no novelty, "
                       "activity, or identity claim; judgment deferred."),
    }
    (out_dir / f"{stem}_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def _render_svg(aligned, columns, transforms, scales, config) -> str:
    """Pure-vector SVG: label gutter + one rect per cell, live text everywhere, labels in
    dedicated gutters so no text can touch the data rectangle by construction."""
    row_h, cell_w, label_w, header_h, pad = 16, 46, 210, 54, 8
    width = label_w + cell_w * len(columns) + pad * 2
    footer_h = 34
    height = header_h + row_h * len(aligned) + pad * 2 + footer_h
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif">',
        f'<title>{html.escape(str(config.get("panel_id", "tree_heatmap_panel")))}</title>',
        f'<metadata>figure_id={html.escape(str(config.get("panel_id", "tree_heatmap_panel")))};figure_set_id={html.escape(str(config.get("figure_set_id", "")))}</metadata>',
    ]
    for ci, column in enumerate(columns):
        x = label_w + ci * cell_w + cell_w / 2 + pad
        suffix = " (log1p)" if transforms[column] == "log1p" else ""
        iso = " [isolated]" if column in OTHER_COLUMN_NAMES else ""
        parts.append(f'<text x="{x}" y="{header_h - 14}" font-size="10" text-anchor="middle">'
                     f'{html.escape(str(column))}{suffix}{iso}</text>')
    for ri, row in enumerate(aligned):
        y = header_h + ri * row_h + pad
        parts.append(f'<text x="{label_w - 6}" y="{y + row_h - 5}" font-size="10" '
                     f'text-anchor="end">{html.escape(str(row["display_label"]))}</text>')
        for ci, column in enumerate(columns):
            x = label_w + ci * cell_w + pad
            value = row["values"][column]
            if value is None:
                parts.append(f'<rect x="{x}" y="{y}" width="{cell_w - 2}" height="{row_h - 2}" '
                             f'fill="{MISSING_FILL}" stroke="{MISSING_STROKE}" '
                             f'stroke-dasharray="2,2"/>')
                continue
            lo, hi = scales[column]
            fraction = _cell_fraction(value, lo, hi, transforms[column])
            fill = RAMP[min(len(RAMP) - 1, int(fraction * len(RAMP)))]
            parts.append(f'<rect x="{x}" y="{y}" width="{cell_w - 2}" height="{row_h - 2}" '
                         f'fill="{fill}"><title>{html.escape(str(row["strain"]))} '
                         f'{html.escape(str(column))}={value}</title></rect>')
    parts.append(
        f'<text x="{pad}" y="{height - 9}" font-size="8.5" fill="#52606D">'
        f'{html.escape(CLAIM_SAFETY + " Judgment deferred.")}</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)
