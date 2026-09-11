#!/usr/bin/env python3
"""gen_figure_r_manifest.py — derive FIGURE_R_MANIFEST.tsv from the Python figure sources.

The R templates need to know, per figure: which sidecar schema it uses, which geometry to draw, and
which colormap / colourbar label the Python renderer used. Hand-typing that table would rot the
moment `cohort_figures.py` changes, and it would be a second, unverifiable copy of the render policy.

So the manifest is GENERATED: colormap and colourbar labels come from an AST walk over the renderer
calls in mamey/cohort_figures.py, and the schema family comes from the sidecar header when a rendered
example is available. Run with --check in CI to fail when the two drift apart.

Usage:
  python tools/gen_figure_r_manifest.py --apply [--examples <dir with *_data.csv>]
  python tools/gen_figure_r_manifest.py --check [--examples <dir>]
"""
from __future__ import annotations

import os as _os, sys as _sys  # resolve the tools-local emitter from any cwd (v9.7.407 convention)
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import ast
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tools" / "FIGURE_R_MANIFEST.tsv"
SOURCES = ("mamey/cohort_figures.py", "mamey/cohort_figures_extended.py")

# Renderer function -> the geometry an R template must draw. These are the Python renderers, so the
# mapping is one-directional and checkable: a new renderer name shows up as UNMAPPED rather than
# being silently dropped.
GEOMETRY = {
    "hmap": "heatmap",
    "heatmap": "heatmap",
    "bubble_matrix": "bubble",
    "grouped_bars": "grouped_bar",
    "stacked_bars": "stacked_bar",
}

FIELDS = ["figure_id", "geometry", "schema", "cmap", "cbar_label", "source", "notes"]


def _literal(src: str, node: ast.AST | None) -> str:
    """Source text of a keyword value, reduced to a bare string when it is a plain literal.

    Several cmaps are written as `"rocket_r" if "rocket_r" in plt.colormaps() else "magma_r"` — a
    seaborn palette with a matplotlib fallback. Record the PREFERRED name plus the fallback so the R
    side can mirror the same preference instead of silently picking one.
    """
    if node is None:
        return ""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.IfExp):
        body = _literal(src, node.body)
        orelse = _literal(src, node.orelse)
        return f"{body}|{orelse}" if body and orelse else (body or orelse)
    text = ast.get_source_segment(src, node) or ""
    return f"<expr:{text.strip()}>" if text else ""


def scan_sources() -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for rel in SOURCES:
        path = ROOT / rel
        if not path.is_file():
            continue
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            geometry = GEOMETRY.get(node.func.id)
            if geometry is None:
                continue
            kw = {k.arg: k.value for k in node.keywords if k.arg}
            fid = None
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    v = arg.value
                    if "_" in v and " " not in v:
                        fid = v
                        break
            if not fid:
                continue  # the renderer's own internal call, or a variable fid (loop-driven)
            found[fid] = {
                "figure_id": fid,
                "geometry": geometry,
                "cmap": _literal(src, kw.get("cmap")),
                "cbar_label": _literal(src, kw.get("cbar")),
                "source": f"{rel}:{node.lineno}",
            }
    return found


def scan_schemas(examples: Path | None) -> dict[str, str]:
    """Classify each rendered example's sidecar by its header shape.

    WIDE_MATRIX : <key>,<series...>  — one numeric column per strain/class
    TIDY        : anything else — already long-form, plot as-is
    """
    schemas: dict[str, str] = {}
    if not examples or not examples.is_dir():
        return schemas
    for csv_path in sorted(examples.glob("*_data.csv")):
        fid = csv_path.name[: -len("_data.csv")]
        with csv_path.open(newline="", encoding="utf-8", errors="replace") as handle:
            rows = list(csv.reader(
                line for line in handle if not line.startswith("#")  # strain-series provenance banner
            ))
        if len(rows) < 2:
            continue
        header, first_row = rows[0], rows[1]
        if len(header) < 2 or len(first_row) < 2:
            continue

        def numeric(cell: str) -> bool:
            try:
                float(cell)
            except ValueError:
                return False
            return True

        # WIDE_MATRIX means: one label column, then a numeric column PER SERIES (per strain/class).
        # Decide on the DATA, not the column names — `F11_active_site_completeness` starts with a
        # `strain` column but continues `tier, catalytic_genes, completeness_pct`, which is a tidy
        # per-strain record, not a matrix. Keying on the header name alone misfiled it (and F12, F13,
        # G15) as WIDE_MATRIX and would have pointed the heatmap renderer at a tidy table.
        wide = all(numeric(cell) for cell in first_row[1:])
        schemas[fid] = "WIDE_MATRIX" if wide else "TIDY"
    return schemas


def build(examples: Path | None) -> list[dict[str, str]]:
    """One row per figure, joining the source spec to the rendered example.

    The two halves are keyed differently and must be joined, not unioned: the renderer call passes a
    BARE id (`product_class_heatmap`) and the series prefix (`F03_`) is prepended when the file is
    written. So `F03_product_class_heatmap` and `product_class_heatmap` are the same figure. Match on
    the suffix after the leading `<LETTER><digits>_`, and fall back to identity.
    """
    specs = scan_sources()
    schemas = scan_schemas(examples)

    def bare(fid: str) -> str:
        head, sep, tail = fid.partition("_")
        return tail if sep and len(head) <= 4 and head[:1].isalpha() and head[1:].isdigit() else fid

    # Prefer the emitted id (it is what a user actually has on disk) and carry the spec onto it.
    by_bare = {bare(fid): fid for fid in schemas}
    rows: list[dict[str, str]] = []
    claimed: set[str] = set()

    for fid in sorted(schemas):
        spec = specs.get(fid) or specs.get(bare(fid)) or {}
        if spec:
            claimed.add(spec["figure_id"])
        notes = []
        if not spec:
            notes.append("no renderer call found in source (loop-driven id, or drawn by another "
                         "module); geometry inferred from the sidecar schema only")
        rows.append({
            "figure_id": fid,
            "geometry": spec.get("geometry", ""),
            "schema": schemas.get(fid, ""),
            "cmap": spec.get("cmap", ""),
            "cbar_label": spec.get("cbar_label", ""),
            "source": spec.get("source", ""),
            "notes": "; ".join(notes),
        })

    # Source specs with no rendered example: keep them, flagged, so a figure that exists in code but
    # was never produced in this workspace is visible rather than silently absent.
    for fid, spec in sorted(specs.items()):
        if fid in claimed or fid in by_bare or fid in schemas:
            continue
        rows.append({
            "figure_id": fid, "geometry": spec.get("geometry", ""), "schema": "",
            "cmap": spec.get("cmap", ""), "cbar_label": spec.get("cbar_label", ""),
            "source": spec.get("source", ""),
            "notes": "no rendered example in this workspace; schema unverified",
        })
    return sorted(rows, key=lambda r: r["figure_id"])


def write(rows: list[dict[str, str]]) -> str:
    lines = ["\t".join(FIELDS)]
    lines += ["\t".join(r[f].replace("\t", " ") for f in FIELDS) for r in rows]
    return "\n".join(lines) + "\n"


def _report(code: int, message: str) -> int:
    """The tool's single terminal-emission site.

    tools/repo_health.py::check_print_calls counts emission SITES — `print` and `_console.emit`
    alike — against a ratchet the suite requires to have ZERO headroom. Funnelling every outcome
    through one call keeps a new tool's cost to the ratchet at 1 instead of 8.
    """
    emit(message)
    return code


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--check", action="store_true")
    ap.add_argument("--examples", type=Path, default=None,
                    help="directory of rendered *_data.csv sidecars used to classify schemas")
    args = ap.parse_args()

    text = write(build(args.examples))
    rel = MANIFEST.relative_to(ROOT)
    if args.apply:
        MANIFEST.write_text(text, encoding="utf-8")
        return _report(0, f"wrote {rel} ({len(text.splitlines()) - 1} figures)")

    if not MANIFEST.is_file():
        return _report(1, f"FAIL: {rel} does not exist; run --apply")
    current = MANIFEST.read_text(encoding="utf-8")
    if args.examples is not None:
        if current == text:
            return _report(0, f"PASS: {rel} matches the figure sources and examples")
        return _report(1, f"FAIL: {rel} has drifted; run --apply")

    # Without --examples the schema column and the row SET cannot be re-derived (both come from
    # rendered sidecars, which are workspace artifacts and are not in the bundle). Check the half
    # that IS derivable from source alone: for every manifest row that names a source location, the
    # geometry, colormap and colourbar label must still match what that source says today. That is
    # the drift this guard exists to catch — a colormap changed in Python and not mirrored in R.
    specs = scan_sources()
    by_bare = {}
    for fid, spec in specs.items():
        by_bare[fid] = spec

    def bare(fid: str) -> str:
        head, sep, tail = fid.partition("_")
        return tail if sep and len(head) <= 4 and head[:1].isalpha() and head[1:].isdigit() else fid

    problems: list[str] = []
    rows = list(csv.DictReader(current.splitlines(), delimiter="\t"))
    if not rows:
        return _report(1, "FAIL: manifest is empty; run --apply")
    checked = 0
    for row in rows:
        if not row.get("source"):
            continue
        spec = by_bare.get(row["figure_id"]) or by_bare.get(bare(row["figure_id"]))
        if spec is None:
            problems.append(f"{row['figure_id']}: manifest names a source but no renderer call "
                            f"was found there any more ({row['source']})")
            continue
        checked += 1
        for field in ("geometry", "cmap", "cbar_label"):
            if (row.get(field) or "") != (spec.get(field) or ""):
                problems.append(f"{row['figure_id']}.{field}: manifest has "
                                f"{row.get(field)!r}, source has {spec.get(field)!r}")
    if problems:
        return _report(1, "\n".join(
            [f"FAIL: {rel} has drifted from the figure sources; run --apply"]
            + [f"  - {p}" for p in problems]))
    return _report(0, f"PASS: {checked} source-bound figure(s) match mamey/cohort_figures.py "
                      "(schema column not re-checked; pass --examples to include it)")


if __name__ == "__main__":
    raise SystemExit(main())
