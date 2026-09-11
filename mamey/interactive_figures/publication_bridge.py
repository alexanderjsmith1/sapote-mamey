#!/usr/bin/env python3
"""Deterministic AS widget-to-publication figure bridge.

The bridge does not screenshot a widget. It resolves the selected widget state
against the canonical aggregate, constructs one vector drawing, and renders that
same drawing to SVG and PDF. A 300 dpi PNG is rasterized from the PDF. Each build
also emits plotted data, caption/method text, references, checksums, and QA.
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
try:
    from ..csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import json
import math
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# Vendored into mamey.interactive_figures. reportlab is an OPTIONAL, render-only
# dependency: the analysis/aggregation helpers (load_data, resolve_scope,
# aggregate_boundary, machinery_summary, list_scopes, percentile) work without it.
# Import is therefore soft-guarded so the module imports even when reportlab is
# absent; the actual error is deferred to the render/build path.
try:
    from reportlab.graphics import renderPDF, renderSVG
    from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
    from reportlab.lib.colors import HexColor

    _HAVE_REPORTLAB = True
except ImportError:  # pragma: no cover - environment guard
    _HAVE_REPORTLAB = False
    renderPDF = renderSVG = None  # type: ignore
    Circle = Drawing = Line = Rect = String = None  # type: ignore

    def HexColor(value):  # type: ignore
        # Harmless placeholder so module-level color constants import cleanly.
        # These are only consumed inside reportlab drawings, which are gated by
        # _require_reportlab() before any rendering happens.
        return value


def _require_reportlab() -> None:
    if not _HAVE_REPORTLAB:
        raise SystemExit(
            "reportlab is required for figure rendering. Use the Codex bundled Python "
            "runtime or install reportlab (with pypdf, pypdfium2, and Pillow)."
        )


ROOT = Path(__file__).resolve().parent
DEFAULT_DATA = ROOT.parent / "AS_All_Strains_Widget_Data.json"
DEFAULT_OUTPUT = ROOT / "output"
WIDTH = 518.4  # 7.2 inches
HEIGHT = 345.6  # 4.8 inches

INK = HexColor("#17202A")
MUTED = HexColor("#52606D")
GRID = HexColor("#D5D8DC")
BLUE = HexColor("#0072B2")
ORANGE = HexColor("#D55E00")
GREEN = HexColor("#009E73")
PURPLE = HexColor("#6A51A3")
LIGHT_BLUE = HexColor("#DDEFF8")
LIGHT_GREEN = HexColor("#DDF3EC")

ANTISMASH_BIB = """@article{duddela2025antismash8,
  title = {antiSMASH 8.0: extended gene cluster detection capabilities and analyses of chemistry, enzymology, and regulation},
  author = {Duddela, Srikanth and others},
  journal = {Nucleic Acids Research},
  volume = {53},
  number = {W1},
  pages = {W32--W38},
  year = {2025},
  doi = {10.1093/nar/gkaf334},
  url = {https://doi.org/10.1093/nar/gkaf334}
}
"""


def ascii_text(value: Any) -> str:
    """Use PDF-safe punctuation while retaining ordinary scientific text."""
    return (
        str(value)
        .replace("\u2014", " - ")
        .replace("\u2013", "-")
        .replace("\u2011", "-")
        .replace("\u2212", "-")
        .replace("\u2265", ">=")
        .replace("\u2264", "<=")
    )


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


class PublicationBridgeRefusal(RuntimeError):
    """Typed refusal for figure receipts that cannot enter publication."""


def validate_figure_receipt_for_publication(receipt: dict[str, Any]) -> None:
    """Refuse provisional Figure Factory evidence before publication rendering."""
    if receipt.get("binding_state") == "PROVISIONAL_BINDING":
        raise PublicationBridgeRefusal(
            "FIGURE_PUBLICATION_PROVISIONAL_BINDING: owner binding is required"
        )


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def percentile(values: list[float], q: float) -> float:
    if not values:
        return math.nan
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    low = int(math.floor(pos))
    high = int(math.ceil(pos))
    if low == high:
        return xs[low]
    return xs[low] * (high - pos) + xs[high] * (pos - low)


def load_data(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("strains"), dict) or not isinstance(data.get("meta"), dict):
        raise ValueError("Widget aggregate must contain object-valued 'meta' and 'strains'.")
    return data


def resolve_scope(data: dict[str, Any], scope: str) -> tuple[list[str], str, str]:
    strains = data["strains"]
    meta = data["meta"]
    if scope == "GOVERNED":
        ids = [s for s, record in strains.items() if record.get("governance") == "GOVERNED"]
        return sorted(ids), "Governed AS cohort", ""
    if scope == "ALL_PACKAGED":
        return sorted(strains), "All packaged AS strains", "Includes excluded or quarantined records."
    if scope in meta.get("cohorts", {}):
        spec = meta["cohorts"][scope]
        ids = [s for s in spec.get("strains", []) if s in strains]
        return ids, ascii_text(spec.get("label", scope)), ascii_text(spec.get("warning", ""))
    if scope in strains:
        warning = "" if strains[scope].get("governance") == "GOVERNED" else ascii_text(
            strains[scope].get("governance", "")
        )
        return [scope], scope, warning
    choices = ["GOVERNED", "ALL_PACKAGED", *sorted(meta.get("cohorts", {})), *sorted(strains)]
    raise ValueError(f"Unknown scope {scope!r}. Available: {', '.join(choices)}")


def add_common_frame(d: Drawing, title: str, subtitle: str) -> None:
    d.add(String(44, HEIGHT - 27, ascii_text(title), fontName="Helvetica-Bold", fontSize=12, fillColor=INK))
    d.add(String(44, HEIGHT - 42, ascii_text(subtitle), fontName="Helvetica", fontSize=7.5, fillColor=MUTED))


def aggregate_boundary(data: dict[str, Any], strain_ids: Iterable[str], min_memberships: int) -> list[dict[str, Any]]:
    totals: dict[str, dict[str, int]] = {}
    for strain_id in strain_ids:
        for product_class, counts in data["strains"][strain_id].get("classes", {}).items():
            row = totals.setdefault(product_class, {"total": 0, "edge": 0, "full": 0, "interior": 0})
            for key in row:
                row[key] += int(counts.get(key, 0))
    result = []
    for product_class, counts in totals.items():
        total = counts["total"]
        if total < min_memberships:
            continue
        if total != counts["edge"] + counts["full"] + counts["interior"]:
            raise ValueError(f"Boundary counts do not reconcile for {product_class}.")
        result.append(
            {
                "product_class": product_class,
                **counts,
                "strict_edge_pct": 100.0 * counts["edge"] / total,
                "edge_plus_full_pct": 100.0 * (counts["edge"] + counts["full"]) / total,
            }
        )
    result.sort(key=lambda row: (row["strict_edge_pct"], row["total"]), reverse=True)
    return result


def boundary_drawing(rows: list[dict[str, Any]], scope_label: str, n_strains: int) -> Drawing:
    shown = rows[:14]
    d = Drawing(WIDTH, HEIGHT)
    add_common_frame(
        d,
        "BGC boundary status by product-class membership",
        f"{scope_label}; n={n_strains} strains; nonexclusive class memberships",
    )
    left, right, bottom, top = 122, 26, 39, HEIGHT - 68
    plot_w = WIDTH - left - right
    plot_h = top - bottom
    for tick in range(0, 101, 20):
        x = left + plot_w * tick / 100
        d.add(Line(x, bottom, x, top, strokeColor=GRID, strokeWidth=0.45))
        d.add(String(x - 5, bottom - 13, str(tick), fontName="Helvetica", fontSize=6.5, fillColor=MUTED))
    d.add(String(left + plot_w / 2 - 35, 11, "BGC memberships (%)", fontName="Helvetica", fontSize=7, fillColor=INK))
    row_h = plot_h / max(len(shown), 1)
    bar_h = min(5.2, row_h * 0.32)
    for i, row in enumerate(shown):
        cy = top - (i + 0.5) * row_h
        label = ascii_text(row["product_class"])
        if len(label) > 22:
            label = label[:20] + "..."
        d.add(String(left - 7, cy - 2, label, textAnchor="end", fontName="Helvetica", fontSize=6.6, fillColor=INK))
        strict = row["strict_edge_pct"]
        broad = row["edge_plus_full_pct"]
        d.add(Rect(left, cy + 1.4, plot_w * broad / 100, bar_h, fillColor=ORANGE, strokeColor=None))
        d.add(Rect(left, cy - bar_h - 1.4, plot_w * strict / 100, bar_h, fillColor=BLUE, strokeColor=None))
        d.add(String(min(left + plot_w * broad / 100 + 3, WIDTH - 28), cy + 2.2, f"{broad:.1f}", fontName="Helvetica", fontSize=5.7, fillColor=INK))
        d.add(String(min(left + plot_w * strict / 100 + 3, WIDTH - 28), cy - bar_h - 0.8, f"{strict:.1f}", fontName="Helvetica", fontSize=5.7, fillColor=INK))
    legend_y = HEIGHT - 58
    d.add(Rect(WIDTH - 195, legend_y, 8, 5, fillColor=BLUE, strokeColor=None))
    d.add(String(WIDTH - 183, legend_y - 0.5, "Edge", fontName="Helvetica", fontSize=6.5, fillColor=INK))
    d.add(Rect(WIDTH - 135, legend_y, 8, 5, fillColor=ORANGE, strokeColor=None))
    d.add(String(WIDTH - 123, legend_y - 0.5, "Edge + full-contig", fontName="Helvetica", fontSize=6.5, fillColor=INK))
    return d


def machinery_summary(data: dict[str, Any], strain_ids: Iterable[str], axis_ceiling: int) -> list[dict[str, Any]]:
    role_order = data["meta"].get("machineryAssignmentPrecedence", [])
    summary = []
    for role in role_order:
        values: list[float] = []
        for strain_id in strain_ids:
            values.extend(float(v) for v in data["strains"][strain_id].get("machinery", {}).get(role, []))
        if not values:
            continue
        summary.append(
            {
                "role": role,
                "n": len(values),
                "p05_aa": percentile(values, 0.05),
                "q1_aa": percentile(values, 0.25),
                "median_aa": statistics.median(values),
                "mean_aa": statistics.fmean(values),
                "q3_aa": percentile(values, 0.75),
                "p95_aa": percentile(values, 0.95),
                "overflow_n": sum(v > axis_ceiling for v in values),
                "max_aa": max(values),
            }
        )
    return summary


def machinery_drawing(rows: list[dict[str, Any]], scope_label: str, n_strains: int, axis_ceiling: int) -> Drawing:
    d = Drawing(WIDTH, HEIGHT)
    add_common_frame(
        d,
        "Machinery-role protein length distributions",
        f"{scope_label}; n={n_strains} strains; physical CDS deduplicated before role assignment",
    )
    left, right, bottom, top = 142, 105, 46, HEIGHT - 69
    plot_w = WIDTH - left - right
    plot_h = top - bottom
    for tick in range(0, axis_ceiling + 1, max(250, axis_ceiling // 4)):
        x = left + plot_w * tick / axis_ceiling
        d.add(Line(x, bottom, x, top, strokeColor=GRID, strokeWidth=0.5))
        d.add(String(x - 8, bottom - 14, f"{tick:,}", fontName="Helvetica", fontSize=6.5, fillColor=MUTED))
    d.add(String(left + plot_w / 2 - 35, 13, "Protein length (aa)", fontName="Helvetica", fontSize=7, fillColor=INK))
    row_h = plot_h / max(len(rows), 1)
    for i, row in enumerate(rows):
        cy = top - (i + 0.5) * row_h
        scale = lambda value: left + plot_w * min(float(value), axis_ceiling) / axis_ceiling
        d.add(String(left - 8, cy - 2.5, ascii_text(row["role"]), textAnchor="end", fontName="Helvetica", fontSize=7.2, fillColor=INK))
        d.add(Line(scale(row["p05_aa"]), cy, scale(row["p95_aa"]), cy, strokeColor=PURPLE, strokeWidth=1.2))
        d.add(Line(scale(row["p05_aa"]), cy - 4, scale(row["p05_aa"]), cy + 4, strokeColor=PURPLE, strokeWidth=1))
        d.add(Line(scale(row["p95_aa"]), cy - 4, scale(row["p95_aa"]), cy + 4, strokeColor=PURPLE, strokeWidth=1))
        d.add(Rect(scale(row["q1_aa"]), cy - 7, max(1, scale(row["q3_aa"]) - scale(row["q1_aa"])), 14, fillColor=LIGHT_GREEN, strokeColor=GREEN, strokeWidth=1))
        d.add(Line(scale(row["median_aa"]), cy - 7, scale(row["median_aa"]), cy + 7, strokeColor=INK, strokeWidth=1.5))
        d.add(Circle(scale(row["mean_aa"]), cy, 2.3, fillColor=ORANGE, strokeColor=None))
        overflow = f"n={row['n']:,}; >{axis_ceiling:,}: {row['overflow_n']:,}"
        d.add(String(left + plot_w + 5, cy - 2.3, overflow, fontName="Helvetica", fontSize=5.8, fillColor=MUTED))
    legend_y = HEIGHT - 58
    d.add(Rect(WIDTH - 225, legend_y - 1, 12, 7, fillColor=LIGHT_GREEN, strokeColor=GREEN, strokeWidth=0.7))
    d.add(String(WIDTH - 209, legend_y, "IQR", fontName="Helvetica", fontSize=6.5, fillColor=INK))
    d.add(Line(WIDTH - 169, legend_y + 2, WIDTH - 157, legend_y + 2, strokeColor=PURPLE, strokeWidth=1.2))
    d.add(String(WIDTH - 153, legend_y, "P5-P95", fontName="Helvetica", fontSize=6.5, fillColor=INK))
    d.add(Circle(WIDTH - 91, legend_y + 2, 2.2, fillColor=ORANGE, strokeColor=None))
    d.add(String(WIDTH - 84, legend_y, "mean", fontName="Helvetica", fontSize=6.5, fillColor=INK))
    return d


def boundary_text(scope_label: str, n_strains: int, rows: list[dict[str, Any]], min_memberships: int, release: str, warning: str) -> tuple[str, str]:
    warning_text = f" Governance note: {warning}" if warning else ""
    caption = (
        f"BGC boundary status by nonexclusive antiSMASH product-class membership for {scope_label} "
        f"(n = {n_strains} strains). Blue bars show strict Edge memberships; orange bars show Edge plus "
        f"Full-contig memberships. Classes were retained at >= {min_memberships} memberships and the "
        f"14 highest strict-edge percentages are displayed. Hybrid BGCs contribute once to each listed "
        f"class, so class denominators are not mutually exclusive. Values are descriptive assembly and "
        f"annotation context, not evidence of metabolite identity, production, activity, novelty, or host causality [1]."
        f"{warning_text}"
    )
    methods = (
        f"Source data were the frozen {release} AS widget aggregate. For every selected strain, one sealed "
        f"inventory row was treated as one strain-BGC record. Semicolon-delimited product memberships had "
        f"already been deduplicated within each BGC. For each product class, strict edge percentage was "
        f"100 x Edge / total memberships; the broader assembly-boundary context was 100 x (Edge + Full-contig) "
        f"/ total memberships. Every class was required to reconcile as total = Edge + Full-contig + Interior. "
        f"antiSMASH calls were generated with the antiSMASH 8 series [1]."
    )
    return caption, methods


def machinery_text(scope_label: str, n_strains: int, rows: list[dict[str, Any]], axis_ceiling: int, release: str, warning: str) -> tuple[str, str]:
    total = sum(int(row["n"]) for row in rows)
    overflow = sum(int(row["overflow_n"]) for row in rows)
    warning_text = f" Governance note: {warning}" if warning else ""
    caption = (
        f"Machinery-role protein-length distributions for {scope_label} (n = {n_strains} strains; "
        f"{total:,} role-assigned genes). Boxes show the interquartile range, vertical lines show medians, "
        f"whiskers span the 5th-95th percentiles, and orange points show means. The display ceiling is "
        f"{axis_ceiling:,} amino acids; {overflow:,} longer proteins remain counted and are reported as overflow. "
        f"Role labels describe annotation-supported capacity, not confirmed biochemical function or production [1]."
        f"{warning_text}"
    )
    methods = (
        f"Source data were the frozen {release} AS widget aggregate. Physical CDS were deduplicated upstream by "
        f"strain, contig, locus tag, start, and end. When annotations overlapped, each CDS was assigned once using "
        f"the declared precedence: Biosynthetic additional, Biosynthetic core, Resistance, Transport, Regulatory. "
        f"Lengths are amino-acid counts. Quantiles use linear interpolation over sorted observations. The axis ceiling "
        f"changes display only and does not filter the denominator. antiSMASH annotations were generated with the "
        f"antiSMASH 8 series [1]."
    )
    return caption, methods


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = _SafeDictWriter(stream, fieldnames=list(rows[0]) if rows else ["empty"])
        writer.writeheader()
        writer.writerows(rows)


def render_outputs(drawing: Drawing, stem: Path) -> dict[str, Path]:
    _require_reportlab()
    import pypdfium2 as pdfium
    from pypdf import PdfReader, PdfWriter

    stem.parent.mkdir(parents=True, exist_ok=True)
    svg = stem.with_suffix(".svg")
    pdf = stem.with_suffix(".pdf")
    png = stem.with_suffix(".png")
    renderSVG.drawToFile(drawing, str(svg))
    renderPDF.drawToFile(drawing, str(pdf), "AS publication figure")
    reader = PdfReader(str(pdf))
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    writer.add_metadata(
        {
            "/Title": stem.name,
            "/Author": "Not supplied",
            "/Subject": "Claim-safe descriptive AS strain figure",
            "/Creator": "AS Widget Publication Bridge v0.1",
        }
    )
    metadata_pdf = pdf.with_suffix(".metadata.pdf")
    with metadata_pdf.open("wb") as stream:
        writer.write(stream)
    metadata_pdf.replace(pdf)
    document = pdfium.PdfDocument(str(pdf))
    if len(document) != 1:
        raise RuntimeError(f"Expected one PDF page, observed {len(document)}: {pdf}")
    bitmap = document[0].render(scale=300 / 72)
    bitmap.to_pil().save(png, format="PNG", dpi=(300, 300))
    if not png.exists():
        raise RuntimeError(f"Expected PNG was not produced: {png}")
    return {"svg": svg, "pdf": pdf, "png": png}


def qa_outputs(paths: dict[str, Path]) -> dict[str, Any]:
    from PIL import Image
    from pypdf import PdfReader

    reader = PdfReader(str(paths["pdf"]))
    with Image.open(paths["png"]) as image:
        png_size = list(image.size)
        bbox = image.convert("RGB").getbbox()
    svg_text = paths["svg"].read_text(encoding="utf-8")
    checks = {
        "pdf_pages": len(reader.pages),
        "png_pixels": png_size,
        "png_nonblank_bbox": list(bbox) if bbox else None,
        "svg_has_vector_elements": any(token in svg_text for token in ("<rect", "<line", "<path")),
        "files_nonempty": all(path.stat().st_size > 500 for path in paths.values()),
    }
    checks["status"] = "PASS" if (
        checks["pdf_pages"] == 1
        and checks["png_nonblank_bbox"] is not None
        and checks["svg_has_vector_elements"]
        and checks["files_nonempty"]
    ) else "FAIL"
    return checks


def build_one(
    data_path: Path,
    output: Path,
    figure: str,
    scope: str,
    min_memberships: int,
    axis_ceiling: int,
) -> dict[str, Any]:
    data = load_data(data_path)
    strain_ids, scope_label, warning = resolve_scope(data, scope)
    release = ascii_text(data["meta"].get("sourceRelease", "unknown source release"))
    figure_id = f"as-{figure}-{slug(scope)}"
    if figure == "bgc-boundary":
        rows = aggregate_boundary(data, strain_ids, min_memberships)
        if not rows:
            raise ValueError("No product classes meet the requested membership threshold.")
        drawing = boundary_drawing(rows, scope_label, len(strain_ids))
        caption, methods = boundary_text(scope_label, len(strain_ids), rows, min_memberships, release, warning)
        parameters = {"min_memberships": min_memberships, "displayed_classes": min(14, len(rows))}
    elif figure == "machinery-length":
        rows = machinery_summary(data, strain_ids, axis_ceiling)
        if not rows:
            raise ValueError("No machinery-role lengths are available for the requested scope.")
        drawing = machinery_drawing(rows, scope_label, len(strain_ids), axis_ceiling)
        caption, methods = machinery_text(scope_label, len(strain_ids), rows, axis_ceiling, release, warning)
        parameters = {"axis_ceiling_aa": axis_ceiling, "overflow_is_display_only": True}
    else:
        raise ValueError(f"Unsupported figure recipe: {figure}")

    figure_stem = output / "figures" / figure_id
    rendered = render_outputs(drawing, figure_stem)
    data_csv = output / "data" / f"{figure_id}.csv"
    write_csv(data_csv, rows)
    text_dir = output / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    caption_path = text_dir / f"{figure_id}.caption.md"
    methods_path = text_dir / f"{figure_id}.methods.md"
    package_path = text_dir / f"{figure_id}.publication-text.md"
    caption_path.write_text(f"# Caption\n\n{caption}\n", encoding="utf-8")
    methods_path.write_text(f"# Methods\n\n{methods}\n", encoding="utf-8")
    package_path.write_text(
        f"# {figure_id}\n\n## Caption\n\n{caption}\n\n## Methods\n\n{methods}\n\n"
        "## Reference\n\n[1] Duddela S, et al. antiSMASH 8.0. Nucleic Acids Research. 2025;53(W1):W32-W38. "
        "https://doi.org/10.1093/nar/gkaf334\n",
        encoding="utf-8",
    )
    qa = qa_outputs(rendered)
    qa_path = output / "qa" / f"{figure_id}.qa.json"
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    qa_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")

    artifacts = {**rendered, "data_csv": data_csv, "caption": caption_path, "methods": methods_path, "publication_text": package_path, "qa": qa_path}
    record = {
        "figure_id": figure_id,
        "recipe": figure,
        "scope": scope,
        "scope_label": scope_label,
        "strain_ids": strain_ids,
        "warning": warning,
        "source_release": release,
        "source_data": str(data_path.resolve()),
        "source_sha256": sha256(data_path),
        "parameters": parameters,
        "claim_ceiling": "Descriptive extraction-layer evidence; similarity is not identity and capacity is not production or activity.",
        "citation_keys": ["duddela2025antismash8"],
        "qa_status": qa["status"],
        "artifacts": {key: {"path": str(path.resolve()), "sha256": sha256(path)} for key, path in artifacts.items()},
    }
    return record


def build(args: argparse.Namespace) -> int:
    _require_reportlab()
    figures = ["bgc-boundary", "machinery-length"] if args.figure == "all" else [args.figure]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    stale_visual_receipt = output / "qa" / "VISUAL_QA_RECEIPT.json"
    if stale_visual_receipt.exists():
        stale_visual_receipt.unlink()
    (output / "references.bib").write_text(ANTISMASH_BIB, encoding="utf-8")
    records = [
        build_one(
            args.data.resolve(),
            output,
            figure,
            args.scope,
            args.min_memberships,
            args.axis_ceiling,
        )
        for figure in figures
    ]
    manifest = {
        "schema": "as_widget_publication_bridge_v0.1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(r["qa_status"] == "PASS" for r in records) else "FAIL",
        "renderer": {"python": sys.version.split()[0], "reportlab": __import__("reportlab").Version},
        "figures": records,
        "independent_gates": {
            "engineering_build": "PASS",
            "render_qa": "PASS" if all(r["qa_status"] == "PASS" for r in records) else "FAIL",
            "biological_validation": "NOT_ASSESSED",
            "publication_approval": "NOT_ASSESSED",
        },
    }
    manifest_path = output / "FIGURE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    checksums = []
    for path in sorted(p for p in output.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"):
        checksums.append(f"{sha256(path)}  {path.relative_to(output)}")
    (output / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    emit(json.dumps({"status": manifest["status"], "manifest": str(manifest_path), "figures": [r["figure_id"] for r in records]}, indent=2))
    return 0 if manifest["status"] == "PASS" else 1


def list_scopes(data_path: Path) -> int:
    data = load_data(data_path)
    emit("GOVERNED\tGoverned AS cohort", "ALL_PACKAGED\tAll packaged AS strains", sep="\n")
    for key, spec in sorted(data["meta"].get("cohorts", {}).items()):
        emit(f"{key}\t{ascii_text(spec.get('label', key))}")
    for key in sorted(data["strains"]):
        emit(f"{key}\tIndividual strain")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    build_p = sub.add_parser("build", help="Build publication artifacts from a frozen widget scope.")
    build_p.add_argument("--data", type=Path, default=DEFAULT_DATA)
    build_p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    build_p.add_argument("--figure", choices=["all", "bgc-boundary", "machinery-length"], default="all")
    build_p.add_argument("--scope", default="GOVERNED")
    build_p.add_argument("--min-memberships", type=int, default=10)
    build_p.add_argument("--axis-ceiling", type=int, choices=[1000, 1500, 2000, 3000], default=2000)
    list_p = sub.add_parser("list-scopes", help="List supported cohort and strain scopes.")
    list_p.add_argument("--data", type=Path, default=DEFAULT_DATA)
    return p


def main() -> int:
    args = parser().parse_args()
    if args.command == "build":
        return build(args)
    return list_scopes(args.data.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
