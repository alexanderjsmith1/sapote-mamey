#!/usr/bin/env python3
"""Dependency-free renderer for Codex Figure Factory registry tranche 1.

Tranche 1 implements 20 registry sets from four source-complete families:
BGC boundary context (BND), BGC class composition (CLS), machinery gene
length (MLN), and machinery role burden (MRB).  It consumes the governed
``AS_All_Strains_Widget_Data.json`` aggregate emitted from sealed packages and
writes SVG, plotted-data CSV, caption/methods text, an HTML index, and QA
receipts.  No source package is modified.
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
import html
import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence
from xml.etree import ElementTree as ET

from mamey.figure_policy import (
    CAPTION_METHOD_SCHEMA,
    FigurePolicyError,
    preflight_chart_data,
    validate_caption_methods,
    validate_genus_comparison,
)

from .figure_set_registry import GLOBAL_CLAIM_CEILING, PROFILE, build_registry


SCHEMA_VERSION = "sapote-mamey.codex-figure-set-render.v1"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
IMPLEMENTED_IDS = (
    "FS001", "FS002", "FS003", "FS005", "FS007",
    "FS009", "FS010", "FS011", "FS013", "FS015",
    "FS041", "FS042", "FS043", "FS045", "FS047",
    "FS049", "FS050", "FS053", "FS054", "FS055",
)
ROLE_ORDER = (
    "Biosynthetic core", "Biosynthetic additional", "Resistance", "Transport", "Regulatory"
)
ROLE_SHORT = {
    "Biosynthetic core": "Core", "Biosynthetic additional": "Additional",
    "Resistance": "Resistance", "Transport": "Transport", "Regulatory": "Regulatory",
}
HOST_ORDER = ("BEE", "WASP", "ATTINE_ANT", "UNRESOLVED")
COLORS = ("#31688e", "#35b779", "#6f4c9b", "#e07b39", "#ba3c5d", "#7a8b99")
HEAT_COLORS = ("#440154", "#414487", "#2a788e", "#22a884", "#7ad151", "#fde725")


@dataclass
class Chart:
    figure_id: str
    kind: str
    title: str
    subtitle: str
    rows: list[dict[str, Any]]
    config: dict[str, Any]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _native_svg_rasterization_capability() -> dict[str, str]:
    """Probe the optional CairoSVG bridge without blocking native SVG output."""
    try:
        import cairosvg
        rendered = cairosvg.svg2png(
            bytestring=b'<svg xmlns="http://www.w3.org/2000/svg" width="2" height="2"/>',
            output_width=2,
        )
        if not isinstance(rendered, bytes) or not rendered.startswith(PNG_SIGNATURE):
            raise ValueError("non-PNG probe result")
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        return {
            "state": "NATIVE_SVG_UNAVAILABLE",
            "svg_render_path": "DIRECT_DETERMINISTIC_SVG",
            "png_pair_path": "NOT_EMITTED",
            "error_type": type(exc).__name__,
        }
    return {
        "state": "AVAILABLE_CAIROSVG",
        "svg_render_path": "DIRECT_DETERMINISTIC_SVG",
        "png_pair_path": "CAIROSVG",
        "error_type": "",
    }


def _strain_key(sid: str) -> tuple[int, str]:
    digits = "".join(ch for ch in sid if ch.isdigit())
    return (int(digits) if digits else 10**9, sid)


def _median(values: Iterable[float]) -> float:
    seq = list(values)
    return float(statistics.median(seq)) if seq else 0.0


def _quantile(values: Iterable[float], q: float) -> float:
    seq = sorted(float(v) for v in values)
    if not seq:
        return 0.0
    if len(seq) == 1:
        return seq[0]
    pos = (len(seq) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return seq[lo] if lo == hi else seq[lo] + (seq[hi] - seq[lo]) * (pos - lo)


def _load_with_benchmarks(
    path: str | Path,
    external_benchmark_ids: Sequence[str] = (),
) -> tuple[Path, dict[str, Any], list[str], list[str], list[str], list[str]]:
    source = Path(path).resolve()
    payload = json.loads(source.read_text(encoding="utf-8"))
    strains = payload.get("strains") or {}
    if not isinstance(strains, dict) or not strains:
        raise ValueError("widget data has no strains object")
    source_ids = sorted(strains, key=_strain_key)
    benchmark_ids: list[str] = []
    default_packaged: list[str] = []
    for sid in source_ids:
        record = strains[sid]
        role = str(record.get("cohort_role") or "STUDY").strip().upper()
        include_by_default = record.get("include_by_default", True)
        if not isinstance(include_by_default, bool):
            raise FigurePolicyError(
                "FIGURE_INCLUDE_BY_DEFAULT_INVALID",
                f"strain {sid!r} include_by_default must be boolean",
            )
        if role == "EXTERNAL_BENCHMARK":
            if include_by_default:
                raise FigurePolicyError(
                    "FIGURE_EXTERNAL_BENCHMARK_DEFAULT_ON",
                    f"external benchmark {sid!r} must declare include_by_default=false",
                )
            benchmark_ids.append(sid)
            continue
        if include_by_default:
            default_packaged.append(sid)
    requested = list(dict.fromkeys(str(sid) for sid in external_benchmark_ids))
    unknown = sorted(set(requested) - set(benchmark_ids), key=_strain_key)
    if unknown:
        raise FigurePolicyError(
            "FIGURE_EXTERNAL_BENCHMARK_SELECTION_INVALID",
            "requested identifiers are not typed external benchmarks: " + ", ".join(unknown),
        )
    all_ids = sorted([*default_packaged, *requested], key=_strain_key)
    governed = [
        sid for sid in default_packaged
        if strains[sid].get("governance") == "GOVERNED"
        and str(strains[sid].get("cohort_role") or "STUDY").strip().upper() == "STUDY"
    ]
    if not governed:
        raise ValueError("widget data has no GOVERNED strains")
    return source, payload, all_ids, governed, benchmark_ids, requested


def _load(path: str | Path) -> tuple[Path, dict[str, Any], list[str], list[str]]:
    """Preserve the four-value loader contract used by later renderer tranches.

    External benchmarks are still validated and remain default-off.  Tranche 1
    uses the extended loader below when an explicit comparison selection is
    requested; shared consumers keep receiving the historical four values.
    """
    source, payload, all_ids, governed, _, _ = _load_with_benchmarks(path)
    return source, payload, all_ids, governed


def _host(record: dict[str, Any]) -> str:
    group = str((record.get("hostContext") or {}).get("group") or "UNRESOLVED").upper()
    return group if group in HOST_ORDER else "UNRESOLVED"


def _class_totals(strains: dict[str, Any], ids: Sequence[str]) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for sid in ids:
        for cls, values in (strains[sid].get("classes") or {}).items():
            for field in ("total", "edge", "full", "interior"):
                result[cls][field] += float(values.get(field) or 0)
            result[cls]["strains"] += 1 if float(values.get("total") or 0) > 0 else 0
    return result


def _top_classes(totals: dict[str, dict[str, float]], n: int = 15) -> list[str]:
    return sorted(totals, key=lambda cls: (-totals[cls]["total"], cls.lower()))[:n]


def _role_values(strains: dict[str, Any], ids: Sequence[str], role: str) -> list[float]:
    values: list[float] = []
    for sid in ids:
        values.extend(float(v) for v in (strains[sid].get("machinery") or {}).get(role, []) if float(v) >= 0)
    return values


def _pk_values(record: dict[str, Any]) -> dict[str, float]:
    values = (record.get("classes") or {}).get("PKS") or {}
    return {field: float(values.get(field) or 0) for field in ("total", "edge", "full", "interior")}


def _pct(num: float, den: float) -> float:
    return 100.0 * num / den if den else 0.0


def build_charts(payload: dict[str, Any], all_ids: Sequence[str], governed: Sequence[str]) -> list[Chart]:
    strains = payload["strains"]
    totals = _class_totals(strains, governed)
    top = _top_classes(totals, 15)
    charts: list[Chart] = []

    # BND: five complementary boundary-context sets.
    rows = [{"class": cls, "strict_edge_pct": _pct(totals[cls]["edge"], totals[cls]["total"]),
             "edge_plus_full_pct": _pct(totals[cls]["edge"] + totals[cls]["full"], totals[cls]["total"]),
             "memberships": int(totals[cls]["total"])} for cls in top]
    charts.append(Chart("FS001", "paired_bar", "BGC boundary context — governed cohort overview",
                        "Nonexclusive class memberships; strict Edge and Edge + Full-contig shown separately", rows,
                        {"category": "class", "series": ["strict_edge_pct", "edge_plus_full_pct"],
                         "rate_denominator_field": "memberships", "rate_denominator_unit": "BGC-class memberships",
                         "series_labels": ["Strict Edge", "Edge + Full-contig"], "x_label": "Memberships (%)", "max": 100}))

    rows = []
    for sid in governed:
        values = _pk_values(strains[sid])
        rows.append({"strain": sid, "pk_memberships": values["total"],
                     "strict_edge_pct": _pct(values["edge"], values["total"]), "host": _host(strains[sid]),
                     "denominator_state": "OBSERVED" if values["total"] else "OBSERVED_ZERO"})
    charts.append(Chart("FS002", "scatter", "PKS boundary context — every governed strain",
                        "Every included strain is labelled next to its point; non-outliers remain visible", rows,
                        {"x": "pk_memberships", "y": "strict_edge_pct", "label": "strain",
                         "rate_denominator_field": "pk_memberships", "rate_denominator_unit": "PKS class memberships",
                         "x_label": "PKS class memberships", "y_label": "Strict Edge (%)",
                         "x_min": 0, "y_min": 0, "y_max": 100}))

    charts.append(Chart("FS003", "bar", "Boundary context by BGC product class",
                        "Governed cohort; top classes ranked by strict Edge percentage with raw denominators", rows := [
                            {"class": cls, "value": _pct(totals[cls]["edge"], totals[cls]["total"]),
                             "n": int(totals[cls]["total"])} for cls in top
                        ], {"category": "class", "value": "value", "x_label": "Strict Edge (%)", "max": 100, "n": "n",
                            "rate_denominator_field": "n", "rate_denominator_unit": "BGC-class memberships"}))

    host_rows = []
    for group in HOST_ORDER:
        ids = [sid for sid in governed if _host(strains[sid]) == group]
        agg = [(_pk_values(strains[sid])) for sid in ids]
        den = sum(item["total"] for item in agg)
        host_rows.append({"host": group, "strict_edge_pct": _pct(sum(item["edge"] for item in agg), den),
                          "edge_plus_full_pct": _pct(sum(item["edge"] + item["full"] for item in agg), den),
                          "memberships": int(den), "strains": len(ids)})
    charts.append(Chart("FS005", "paired_bar", "PKS boundary context by host cohort",
                        "Only provenance-supported host groups are pooled; unresolved strains remain unresolved", host_rows,
                        {"category": "host", "series": ["strict_edge_pct", "edge_plus_full_pct"],
                         "rate_denominator_field": "memberships", "rate_denominator_unit": "PKS class memberships",
                         "series_labels": ["Strict Edge", "Edge + Full-contig"], "x_label": "PKS memberships (%)", "max": 100}))

    sensitivity = []
    for sid in governed:
        values = _pk_values(strains[sid])
        if values["total"]:
            sensitivity.append({"strain": sid, "strict_edge_pct": _pct(values["edge"], values["total"]),
                                "edge_plus_full_pct": _pct(values["edge"] + values["full"], values["total"]),
                                "memberships": int(values["total"])})
    charts.append(Chart("FS007", "paired_dot", "PKS boundary denominator sensitivity by strain",
                        "Strict Edge is paired with the declared Edge + Full-contig context for every strain", sensitivity,
                        {"category": "strain", "a": "strict_edge_pct", "b": "edge_plus_full_pct",
                         "rate_denominator_field": "memberships", "rate_denominator_unit": "PKS class memberships",
                         "a_label": "Strict Edge", "b_label": "Edge + Full-contig", "x_label": "PKS memberships (%)", "max": 100}))

    # CLS: class burden, richness, prevalence, host, and governance sensitivity.
    class_rows = [{"class": cls, "memberships": int(totals[cls]["total"]),
                   "strain_prevalence": int(totals[cls]["strains"])} for cls in top]
    charts.append(Chart("FS009", "bar", "BGC class composition — governed cohort overview",
                        "Nonexclusive product-class memberships; hybrid BGCs may contribute to multiple classes", class_rows,
                        {"category": "class", "value": "memberships", "x_label": "BGC-class memberships"}))

    richness_rows = []
    for sid in governed:
        classes = strains[sid].get("classes") or {}
        richness_rows.append({"strain": sid, "class_richness": sum(1 for v in classes.values() if float(v.get("total") or 0) > 0),
                              "bgc_rows": int(strains[sid].get("bgcRows") or 0), "host": _host(strains[sid])})
    charts.append(Chart("FS010", "scatter", "BGC class richness — every governed strain",
                        "Every strain is labelled; richness counts class tokens, not unique compounds. Package BGC-row counts are assembly-sensitive context, not a biological ranking", richness_rows,
                        {"x": "bgc_rows", "y": "class_richness", "label": "strain",
                         "x_label": "Package BGC rows", "y_label": "Observed class-token richness", "x_min": 0}))

    charts.append(Chart("FS011", "bar", "BGC class prevalence across governed strains",
                        "Number of governed strains with at least one membership in each class", class_rows,
                        {"category": "class", "value": "strain_prevalence", "x_label": "Strains with class membership"}))

    host_richness = []
    for group in HOST_ORDER:
        values = [row["class_richness"] for row in richness_rows if row["host"] == group]
        host_richness.append({"host": group, "q1": _quantile(values, .25), "median": _median(values),
                              "q3": _quantile(values, .75), "strains": len(values)})
    charts.append(Chart("FS013", "dot_range", "BGC class richness by host cohort",
                        "Median and interquartile range; unresolved host context is retained", host_richness,
                        {"category": "host", "low": "q1", "mid": "median", "high": "q3",
                         "x_label": "Observed class-token richness"}))

    all_totals = _class_totals(strains, all_ids)
    union_top = _top_classes(all_totals, 15)
    class_sensitivity = [{"class": cls, "governed": int(totals.get(cls, {}).get("total", 0)),
                          "all_packaged": int(all_totals[cls]["total"])} for cls in union_top]
    charts.append(Chart("FS015", "paired_dot", "BGC class composition — governance sensitivity",
                        "Governed membership totals are paired with all packaged strains; exclusions are not silently pooled", class_sensitivity,
                        {"category": "class", "a": "governed", "b": "all_packaged",
                         "a_label": "Governed", "b_label": "All packaged", "x_label": "BGC-class memberships"}))

    # MLN: lengths from deduplicated machinery-role vectors.
    ecdf_rows = []
    for role in ROLE_ORDER:
        role_values = _role_values(strains, governed, role)
        for value in role_values:
            ecdf_rows.append({"role": ROLE_SHORT[role], "length_aa": value, "role_genes": len(role_values)})
    charts.append(Chart("FS041", "ecdf", "Machinery gene length — governed cohort overview",
                        "All deduplicated machinery-role genes; long proteins are retained without extending the display beyond 3,000 aa", ecdf_rows,
                        {"series": "role", "value": "length_aa", "x_label": "Protein length (aa)", "max": 3000,
                         "rate_denominator_field": "role_genes", "rate_denominator_unit": "deduplicated machinery-role genes"}))

    median_rows = []
    for sid in governed:
        machinery = strains[sid].get("machinery") or {}
        median_rows.append({"strain": sid,
                            "core_median_aa": _median(machinery.get("Biosynthetic core", [])),
                            "additional_median_aa": _median(machinery.get("Biosynthetic additional", [])),
                            "host": _host(strains[sid])})
    charts.append(Chart("FS042", "scatter", "Machinery gene length — every governed strain",
                        "Every strain is labelled; axes show within-strain medians for two declared machinery roles", median_rows,
                        {"x": "core_median_aa", "y": "additional_median_aa", "label": "strain",
                         "x_label": "Core median length (aa)", "y_label": "Additional median length (aa)"}))

    role_ranges = []
    for role in ROLE_ORDER:
        values = _role_values(strains, governed, role)
        role_ranges.append({"role": ROLE_SHORT[role], "q1": _quantile(values, .25), "median": _median(values),
                            "q3": _quantile(values, .75), "genes": len(values)})
    charts.append(Chart("FS043", "dot_range", "Machinery length by annotation role",
                        "Median and interquartile range of deduplicated physical CDS lengths", role_ranges,
                        {"category": "role", "low": "q1", "mid": "median", "high": "q3", "x_label": "Protein length (aa)"}))

    host_length_rows = []
    for group in HOST_ORDER:
        ids = [sid for sid in governed if _host(strains[sid]) == group]
        for role in ROLE_ORDER:
            values = _role_values(strains, ids, role)
            host_length_rows.append({"host": group, "role": ROLE_SHORT[role], "median_aa": _median(values), "genes": len(values)})
    charts.append(Chart("FS045", "heatmap", "Machinery length by host cohort and role",
                        "Cells are pooled-gene medians; unresolved host context remains a separate row", host_length_rows,
                        {"row": "host", "column": "role", "value": "median_aa", "legend": "Median protein length (aa)"}))

    ceiling_rows = []
    for role in ROLE_ORDER:
        values = _role_values(strains, governed, role)
        for ceiling in (1000, 1500, 2000, 3000):
            ceiling_rows.append({"role": ROLE_SHORT[role], "ceiling_aa": str(ceiling),
                                 "overflow_pct": _pct(sum(v >= ceiling for v in values), len(values)), "genes": len(values)})
    charts.append(Chart("FS047", "heatmap", "Machinery-length display-ceiling sensitivity",
                        "Overflow is display-only; every gene remains in the denominator", ceiling_rows,
                        {"row": "role", "column": "ceiling_aa", "value": "overflow_pct",
                         "rate_denominator_field": "genes", "rate_denominator_unit": "deduplicated machinery-role genes",
                         "legend": "Genes in overflow bin (%)", "allow_all_zero": True,
                         "all_zero_semantics": "NONE_ABOVE_DECLARED_CEILING",
                         "all_zero_meaning": "Zero means that no included observation exceeded the explicitly declared display ceiling; missing or unmeasured values are not encoded as zero."}))

    # MRB: count and rate burden from governed/all packaged aggregate.
    burden_rows = []
    for role in ROLE_ORDER:
        burden_rows.append({"role": ROLE_SHORT[role], "genes": len(_role_values(strains, governed, role))})
    charts.append(Chart("FS049", "bar", "Machinery role burden — governed cohort overview",
                        "Deduplicated physical CDS assigned by declared role precedence", burden_rows,
                        {"category": "role", "value": "genes", "x_label": "Machinery-role genes"}))

    fraction_rows = []
    for sid in governed:
        unique = float(strains[sid].get("uniquePhysicalGenes") or 0)
        machinery = float(strains[sid].get("machineryGenes") or 0)
        fraction_rows.append({"strain": sid, "unique_physical_genes": unique,
                              "machinery_pct": _pct(machinery, unique), "host": _host(strains[sid])})
    charts.append(Chart("FS050", "scatter", "Machinery role burden — every governed strain",
                        "Every strain is labelled; burden is normalized by deduplicated physical CDS", fraction_rows,
                        {"x": "unique_physical_genes", "y": "machinery_pct", "label": "strain",
                         "rate_denominator_field": "unique_physical_genes", "rate_denominator_unit": "unique physical CDS",
                         "x_label": "Unique physical CDS", "y_label": "Machinery-role genes (%)"}))

    host_burden = []
    for group in HOST_ORDER:
        ids = [sid for sid in governed if _host(strains[sid]) == group]
        den = sum(float(strains[sid].get("uniquePhysicalGenes") or 0) for sid in ids)
        for role in ROLE_ORDER:
            host_burden.append({"host": group, "role": ROLE_SHORT[role],
                                "genes_per_1000_cds": 1000 * len(_role_values(strains, ids, role)) / den if den else 0,
                                "strains": len(ids), "unique_physical_genes": den})
    charts.append(Chart("FS053", "heatmap", "Machinery role burden by host cohort",
                        "Role counts per 1,000 deduplicated physical CDS; unresolved strains remain separate", host_burden,
                        {"row": "host", "column": "role", "value": "genes_per_1000_cds", "legend": "Genes per 1,000 CDS",
                         "rate_denominator_field": "unique_physical_genes", "rate_denominator_unit": "unique physical CDS"}))

    availability = []
    for sid in governed:
        machinery = strains[sid].get("machinery") or {}
        for role in ROLE_ORDER:
            if role not in machinery:
                state = "MISSING"
            elif len(machinery.get(role) or []) == 0:
                state = "OBSERVED_ZERO"
            else:
                state = "POPULATED"
            availability.append({"strain": sid, "role": ROLE_SHORT[role], "state": state,
                                 "value": {"MISSING": -1, "OBSERVED_ZERO": 0, "POPULATED": 1}[state]})
    charts.append(Chart("FS054", "state_heatmap", "Machinery role evidence availability",
                        "Missing, observed zero, and populated remain distinct states", availability,
                        {"row": "strain", "column": "role", "value": "value", "state": "state",
                         "allow_all_zero": True,
                         "all_zero_semantics": "OBSERVED_ZERO_NOT_MISSING",
                         "all_zero_meaning": "Every plotted zero is an explicitly observed zero state; missing or unmeasured values use a separate typed state."}))

    sensitivity_roles = []
    for role in ROLE_ORDER:
        sensitivity_roles.append({"role": ROLE_SHORT[role],
                                  "governed": len(_role_values(strains, governed, role)),
                                  "all_packaged": len(_role_values(strains, all_ids, role))})
    charts.append(Chart("FS055", "paired_dot", "Machinery role burden — governance sensitivity",
                        "Governed counts are paired with all packaged strains; excluded/quarantined inputs are not silently promoted", sensitivity_roles,
                        {"category": "role", "a": "governed", "b": "all_packaged",
                         "a_label": "Governed", "b_label": "All packaged", "x_label": "Machinery-role genes"}))

    assert tuple(chart.figure_id for chart in charts) == IMPLEMENTED_IDS
    return charts


def _esc(value: Any) -> str:
    return html.escape(str(value))


def _wcag_luminance(colour: str) -> float:
    """WCAG 2.x relative luminance: sRGB channels gamma-corrected to linear light before the
    0.2126/0.7152/0.0722 weighted sum (not the raw-sRGB weighted sum, which is not luminance and
    is not usable for a WCAG contrast-ratio comparison)."""
    raw = colour.lstrip("#")
    rgb = [int(raw[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(colour_a: str, colour_b: str) -> float:
    l1, l2 = _wcag_luminance(colour_a), _wcag_luminance(colour_b)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _text_colour_for_contrast(fill: str, dark: str, light: str) -> str:
    """Pick whichever of `dark`/`light` gives the higher WCAG contrast ratio against `fill`.

    BC2-398: the prior single-threshold-on-raw-sRGB-luminance rule (`_luminance(fill) > .58`)
    picked the lower-contrast option on ~18% of a 2,000-random-color sample tested against the
    actual best-contrast choice — a real readability defect for scientific-figure text labels,
    not a hypothetical one. Comparing the two real contrast ratios directly removes the need for
    any magic threshold and cannot pick the worse option by construction.
    """
    return dark if _contrast_ratio(fill, dark) >= _contrast_ratio(fill, light) else light


def _base_svg(title: str, subtitle: str, width: int, height: int, content: str) -> str:
    # The canvas contains data and descriptive labels only.  Scientific scope,
    # methods, provenance, and governance live in the caption/receipt beneath
    # the figure, where an owner can revise prose without rerendering the plot.
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img"><title>{_esc(title)}</title><desc>{_esc(subtitle)}</desc><rect width="100%" height="100%" fill="#ffffff"/><text x="38" y="34" font-family="DejaVu Sans,Arial,sans-serif" font-size="19" font-weight="700" fill="#17212b">{_esc(title)}</text><text x="38" y="56" font-family="DejaVu Sans,Arial,sans-serif" font-size="10.5" fill="#596672">{_esc(subtitle)}</text>{content}</svg>\n'''


def _ticks(maximum: float, count: int = 5) -> list[float]:
    if maximum <= 0:
        return [0]
    return [maximum * i / count for i in range(count + 1)]


def _render_bar(chart: Chart, paired: bool = False) -> str:
    rows = chart.rows
    cat = chart.config["category"]
    if paired:
        keys = chart.config["series"]
        observed = [max(float(r[k]) for k in keys) for r in rows]
        maximum = float(chart.config.get("max") or (max(observed) if observed else 0) or 1)
    else:
        keys = [chart.config["value"]]
        observed = [float(r[keys[0]]) for r in rows]
        maximum = float(chart.config.get("max") or (max(observed) if observed else 0) or 1)
    width, row_h = 1220, 31
    left, top, plot_w = 245, 96, 875
    height = top + row_h * len(rows) + 88
    parts = []
    for tick in _ticks(maximum):
        x = left + plot_w * tick / maximum
        parts.append(f'<line x1="{x:.1f}" y1="{top-8}" x2="{x:.1f}" y2="{top+row_h*len(rows)}" stroke="#e3e8ed"/><text x="{x:.1f}" y="{top-16}" text-anchor="middle" font-family="Arial" font-size="9" fill="#596672">{tick:.0f}</text>')
    for i, row in enumerate(rows):
        y = top + i * row_h
        parts.append(f'<text x="{left-10}" y="{y+19}" text-anchor="end" font-family="Arial" font-size="10" fill="#17212b">{_esc(row[cat])}</text>')
        if paired:
            for j, key in enumerate(keys):
                value = float(row[key]); bar_h = 10; yy = y + 4 + j * 12
                parts.append(f'<rect x="{left}" y="{yy}" width="{plot_w*value/maximum:.1f}" height="{bar_h}" fill="{COLORS[j]}" opacity=".88"><title>{_esc(row[cat])}: {value:.2f}</title></rect>')
        else:
            value = float(row[keys[0]]); bar_w = plot_w * value / maximum
            parts.append(f'<rect x="{left}" y="{y+6}" width="{bar_w:.1f}" height="18" fill="{COLORS[0]}" opacity=".9"><title>{_esc(row[cat])}: {value:.2f}</title></rect><text x="{left+bar_w+6:.1f}" y="{y+19}" font-family="Arial" font-size="9" fill="#17212b">{value:.1f}{(" · n="+str(row.get(chart.config.get("n"),""))) if chart.config.get("n") else ""}</text>')
    if paired:
        labels = chart.config["series_labels"]
        for j, label in enumerate(labels):
            parts.append(f'<rect x="{left+j*190}" y="{height-58}" width="12" height="12" fill="{COLORS[j]}"/><text x="{left+18+j*190}" y="{height-47}" font-family="Arial" font-size="10">{_esc(label)}</text>')
    parts.append(f'<text x="{left+plot_w/2}" y="{height-42}" text-anchor="middle" font-family="Arial" font-size="10" fill="#596672">{_esc(chart.config["x_label"])}</text>')
    return _base_svg(chart.title, chart.subtitle, width, height, "".join(parts))


def _render_scatter(chart: Chart) -> str:
    width, height = 1600, 1020
    left, right, top, bottom = 112, 315, 118, 96
    plot_w, plot_h = width-left-right, height-top-bottom
    xk, yk, labelk = chart.config["x"], chart.config["y"], chart.config["label"]
    xs = [float(r[xk]) for r in chart.rows]; ys = [float(r[yk]) for r in chart.rows]
    xmin, xmax = min(xs, default=0), max(xs, default=1); ymin, ymax = min(ys, default=0), max(ys, default=1)
    if xmax == xmin: xmax = xmin + 1
    if ymax == ymin: ymax = ymin + 1
    # Padding keeps extreme points and adjacent labels away from titles/axes.
    xpad = max((xmax - xmin) * .06, 1.0)
    ypad = max((ymax - ymin) * .08, 1.0)
    xmin, xmax, ymin, ymax = xmin - xpad, xmax + xpad, ymin - ypad, ymax + ypad
    if chart.config.get("x_min") is not None: xmin = float(chart.config["x_min"])
    if chart.config.get("x_max") is not None: xmax = float(chart.config["x_max"])
    if chart.config.get("y_min") is not None: ymin = float(chart.config["y_min"])
    if chart.config.get("y_max") is not None: ymax = float(chart.config["y_max"])
    def xp(v): return left + (v-xmin)/(xmax-xmin)*plot_w
    def yp(v): return top + plot_h - (v-ymin)/(ymax-ymin)*plot_h
    parts = [f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" stroke="#8c98a4"/><line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="#8c98a4"/>']
    for tick in _ticks(xmax-xmin):
        value=xmin+tick; x=xp(value); parts.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top+plot_h}" stroke="#e8ecef"/><text x="{x:.1f}" y="{top+plot_h+20}" text-anchor="middle" font-family="Arial" font-size="9">{value:.0f}</text>')
    for tick in _ticks(ymax-ymin):
        value=ymin+tick; y=yp(value); parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_w}" y2="{y:.1f}" stroke="#e8ecef"/><text x="{left-9}" y="{y+3:.1f}" text-anchor="end" font-family="Arial" font-size="9">{value:.0f}</text>')
    points = sorted([(xp(float(r[xk])), yp(float(r[yk])), str(r[labelk]), r) for r in chart.rows], key=lambda p:(p[0],p[1],p[2]))
    # Reserve every point before placing any label so text does not cover a
    # neighboring node. Labels may sit to the right or left and move only up or
    # down; no leader lines or remote label rails are used.
    occupied: list[tuple[float, float, float, float]] = [
        (x - 5, y - 5, x + 5, y + 5) for x, y, _label, _row in points
    ]
    for x,y,label,row in points:
        ly = y
        label_w = max(34, min(78, 5.7 * len(label)))
        # Dense cohorts can contain dozens of coincident or nearly coincident
        # values. Continue the alternating vertical search across the usable
        # plot height so the fallback does not silently stack label text.
        candidates = [0]
        for distance in range(14, int(plot_h / 2) + 14, 14):
            candidates.extend((-distance, distance))
        placement = None
        for side in ("right", "left"):
            label_x = x + 9 if side == "right" else x - 9
            anchor = "start" if side == "right" else "end"
            for offset in candidates:
                candidate = max(top + 9, min(top + plot_h - 9, y + offset))
                box = ((label_x - 2, candidate - 9, label_x + label_w, candidate + 4)
                       if side == "right" else
                       (label_x - label_w, candidate - 9, label_x + 2, candidate + 4))
                intersects = any(not (box[2] < old[0] or box[0] > old[2] or box[3] < old[1] or box[1] > old[3]) for old in occupied)
                if not intersects and box[0] >= left and box[2] <= left + plot_w + right - 20:
                    ly = candidate
                    occupied.append(box)
                    placement = (label_x, anchor)
                    break
            if placement:
                break
        if placement:
            label_x, anchor = placement
        else:
            label_x, anchor = x + 9, "start"
            occupied.append((label_x - 2, ly - 9, label_x + label_w, ly + 4))
        highlighted = bool(chart.config.get("highlight") and str(row.get(chart.config["highlight"], "")).upper() in {"YES", "TRUE", "1", "LEAD"})
        colour = COLORS[4] if highlighted else COLORS[0]
        radius = 6.0 if highlighted else 4.5
        ring = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="none" stroke="{COLORS[4]}" stroke-width="1.8"/>' if highlighted else ""
        weight = "700" if highlighted else "400"
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" fill="{colour}" opacity=".9"><title>{_esc(label)}; {xk}={row[xk]}; {yk}={row[yk]}; ledger_lead={highlighted}</title></circle>{ring}<text x="{label_x:.1f}" y="{ly+3:.1f}" text-anchor="{anchor}" font-family="Arial" font-size="8.9" font-weight="{weight}" fill="#17212b" stroke="#ffffff" stroke-width="2.4" paint-order="stroke">{_esc(label)}</text>')
    if chart.config.get("highlight"):
        parts.append(f'<circle cx="{left+plot_w-205}" cy="{top-26}" r="6" fill="{COLORS[4]}"/><circle cx="{left+plot_w-205}" cy="{top-26}" r="8" fill="none" stroke="{COLORS[4]}" stroke-width="1.8"/><text x="{left+plot_w-191}" y="{top-22}" font-family="Arial" font-size="10" font-weight="700">Ledger-declared lead context</text>')
    parts.extend([f'<text x="{left+plot_w/2}" y="{height-42}" text-anchor="middle" font-family="Arial" font-size="11">{_esc(chart.config["x_label"])}</text>',f'<text x="24" y="{top+plot_h/2}" transform="rotate(-90 24 {top+plot_h/2})" text-anchor="middle" font-family="Arial" font-size="11">{_esc(chart.config["y_label"])}</text>'])
    return _base_svg(chart.title, chart.subtitle, width, height, "".join(parts))


def _render_heatmap(chart: Chart, states: bool = False) -> str:
    rk, ck, vk = chart.config["row"], chart.config["column"], chart.config["value"]
    row_labels=list(dict.fromkeys(str(r[rk]) for r in chart.rows)); col_labels=list(dict.fromkeys(str(r[ck]) for r in chart.rows))
    lookup={(str(r[rk]),str(r[ck])):float(r[vk]) for r in chart.rows}
    values=list(lookup.values()); vmax=max([v for v in values if v>0],default=1)
    cell_w=max(68,min(150,780//max(1,len(col_labels)))); cell_h=max(18,min(30,600//max(1,len(row_labels))))
    left,top=235,180; width=left+cell_w*len(col_labels)+150; height=top+cell_h*len(row_labels)+85
    parts=[]
    for j,col in enumerate(col_labels):
        x=left+j*cell_w+cell_w/2; parts.append(f'<text x="{x:.1f}" y="{top-10}" transform="rotate(-45 {x:.1f} {top-10})" text-anchor="start" font-family="Arial" font-size="10">{_esc(col)}</text>')
    for i,row in enumerate(row_labels):
        y=top+i*cell_h; parts.append(f'<text x="{left-8}" y="{y+cell_h*.68:.1f}" text-anchor="end" font-family="Arial" font-size="9.5">{_esc(row)}</text>')
        for j,col in enumerate(col_labels):
            value=lookup.get((row,col))
            if value is None: fill="#d7dce1"
            elif states: fill={-1:"#d7dce1",0:"#f7f7f7",1:COLORS[1]}.get(int(value),"#d7dce1")
            elif value==0: fill="#f7f7f7"
            else:
                t=min(1,value/vmax); idx=min(len(HEAT_COLORS)-1,int(t*(len(HEAT_COLORS)-1))); fill=HEAT_COLORS[idx]
            x=left+j*cell_w
            parts.append(f'<rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" fill="{fill}" stroke="#fff"><title>{_esc(row)}; {_esc(col)}; raw={value}</title></rect>')
            if value is not None and not states and cell_w>=60:
                text_colour = _text_colour_for_contrast(fill, "#17212b", "#ffffff")
                parts.append(f'<text x="{x+cell_w/2:.1f}" y="{y+cell_h*.67:.1f}" text-anchor="middle" font-family="Arial" font-size="8.5" fill="{text_colour}">{value:.1f}</text>')
    legend=chart.config.get("legend") or ("Missing / observed zero / populated" if states else "Raw value")
    parts.append(f'<text x="{left}" y="{height-45}" font-family="Arial" font-size="10" fill="#596672">{_esc(legend)} · gray = missing · white = observed zero</text>')
    return _base_svg(chart.title,chart.subtitle,width,height,"".join(parts))


def _render_dot_range(chart: Chart) -> str:
    rows=chart.rows; cat=chart.config["category"]; low=chart.config["low"]; mid=chart.config["mid"]; high=chart.config["high"]
    highs=[float(r[high]) for r in rows]
    maximum=(max(highs) if highs else 0) or 1; width=1100; left=210; top=105; plot_w=790; row_h=48; height=top+row_h*len(rows)+80
    parts=[]
    for i,row in enumerate(rows):
        y=top+i*row_h; x1=left+plot_w*float(row[low])/maximum; xm=left+plot_w*float(row[mid])/maximum; x2=left+plot_w*float(row[high])/maximum
        parts.append(f'<text x="{left-12}" y="{y+5}" text-anchor="end" font-family="Arial" font-size="10">{_esc(row[cat])}</text><line x1="{x1:.1f}" y1="{y}" x2="{x2:.1f}" y2="{y}" stroke="{COLORS[0]}" stroke-width="3"/><circle cx="{xm:.1f}" cy="{y}" r="6" fill="{COLORS[0]}"/><text x="{x2+8:.1f}" y="{y+4}" font-family="Arial" font-size="9">{float(row[mid]):.1f}</text>')
    parts.append(f'<text x="{left+plot_w/2}" y="{height-42}" text-anchor="middle" font-family="Arial" font-size="10">{_esc(chart.config["x_label"])}</text>')
    return _base_svg(chart.title,chart.subtitle,width,height,"".join(parts))


def _render_paired_dot(chart: Chart) -> str:
    rows=chart.rows; cat=chart.config["category"]; ak=chart.config["a"]; bk=chart.config["b"]
    observed=[max(float(r[ak]),float(r[bk])) for r in rows]
    maximum=float(chart.config.get("max") or (max(observed) if observed else 0) or 1)
    width=1220; left=235; top=100; plot_w=875; row_h=max(22,min(35,620//max(1,len(rows)))); height=top+row_h*len(rows)+90
    parts=[]
    for i,row in enumerate(rows):
        y=top+i*row_h; xa=left+plot_w*float(row[ak])/maximum; xb=left+plot_w*float(row[bk])/maximum
        parts.append(f'<text x="{left-10}" y="{y+4}" text-anchor="end" font-family="Arial" font-size="9">{_esc(row[cat])}</text><line x1="{xa:.1f}" y1="{y}" x2="{xb:.1f}" y2="{y}" stroke="#b9c2ca" stroke-width="2"/><circle cx="{xa:.1f}" cy="{y}" r="4" fill="{COLORS[0]}"/><circle cx="{xb:.1f}" cy="{y}" r="4" fill="{COLORS[1]}"/>')
    for j,(key,label) in enumerate(((ak,chart.config["a_label"]),(bk,chart.config["b_label"]))):
        parts.append(f'<circle cx="{left+j*190}" cy="{height-52}" r="5" fill="{COLORS[j]}"/><text x="{left+10+j*190}" y="{height-48}" font-family="Arial" font-size="10">{_esc(label)}</text>')
    return _base_svg(chart.title,chart.subtitle,width,height,"".join(parts))


def _render_ecdf(chart: Chart) -> str:
    width,height=1200,760; left,right,top,bottom=90,210,92,80; plot_w=width-left-right; plot_h=height-top-bottom
    sk,vk=chart.config["series"],chart.config["value"]; ceiling=float(chart.config.get("max") or 3000)
    groups=defaultdict(list)
    for row in chart.rows: groups[str(row[sk])].append(min(float(row[vk]),ceiling))
    parts=[f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" stroke="#8c98a4"/><line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="#8c98a4"/>']
    for tick in range(7):
        value = ceiling * tick / 6
        x = left + plot_w * tick / 6
        parts.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top+plot_h}" stroke="#e8ecef"/><text x="{x:.1f}" y="{top+plot_h+20}" text-anchor="middle" font-family="Arial" font-size="9">{value:.0f}</text>')
    for tick in range(6):
        value = tick / 5
        y = top + plot_h * (1 - value)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_w}" y2="{y:.1f}" stroke="#e8ecef"/><text x="{left-9}" y="{y+3:.1f}" text-anchor="end" font-family="Arial" font-size="9">{value:.1f}</text>')
    for idx,(name,values) in enumerate(groups.items()):
        seq=sorted(values); coords=[]
        for i,value in enumerate(seq): coords.append(f'{left+plot_w*value/ceiling:.1f},{top+plot_h*(1-(i+1)/len(seq)):.1f}')
        parts.append(f'<polyline points="{" ".join(coords)}" fill="none" stroke="{COLORS[idx%len(COLORS)]}" stroke-width="2"><title>{_esc(name)}; n={len(seq)}</title></polyline><line x1="{left+plot_w+18}" y1="{top+idx*22}" x2="{left+plot_w+38}" y2="{top+idx*22}" stroke="{COLORS[idx%len(COLORS)]}" stroke-width="3"/><text x="{left+plot_w+44}" y="{top+idx*22+4}" font-family="Arial" font-size="9">{_esc(name)} (n={len(seq)})</text>')
    parts.append(f'<text x="{left+plot_w/2}" y="{height-38}" text-anchor="middle" font-family="Arial" font-size="11">{_esc(chart.config["x_label"])}; values ≥ {ceiling:.0f} shown at ceiling</text><text x="22" y="{top+plot_h/2}" transform="rotate(-90 22 {top+plot_h/2})" text-anchor="middle" font-family="Arial" font-size="11">Cumulative fraction</text>')
    return _base_svg(chart.title,chart.subtitle,width,height,"".join(parts))


def render_svg(chart: Chart) -> str:
    if chart.kind == "bar": return _render_bar(chart)
    if chart.kind == "paired_bar": return _render_bar(chart, paired=True)
    if chart.kind == "scatter": return _render_scatter(chart)
    if chart.kind == "heatmap": return _render_heatmap(chart)
    if chart.kind == "state_heatmap": return _render_heatmap(chart, states=True)
    if chart.kind == "dot_range": return _render_dot_range(chart)
    if chart.kind == "paired_dot": return _render_paired_dot(chart)
    if chart.kind == "ecdf": return _render_ecdf(chart)
    raise ValueError(f"unsupported chart kind: {chart.kind}")


def _preflight_chart(chart: Chart) -> dict[str, Any]:
    """Map renderer configuration to the shared fail-before-write gate."""
    if chart.kind == "bar":
        fields = [chart.config["value"]]
    elif chart.kind == "paired_bar":
        fields = list(chart.config["series"])
    elif chart.kind == "scatter":
        fields = [chart.config["x"], chart.config["y"]]
    elif chart.kind in {"heatmap", "state_heatmap"}:
        fields = [chart.config["value"]]
    elif chart.kind == "dot_range":
        fields = [chart.config["low"], chart.config["mid"], chart.config["high"]]
    elif chart.kind == "paired_dot":
        fields = [chart.config["a"], chart.config["b"]]
    elif chart.kind == "ecdf":
        fields = [chart.config["value"]]
    else:
        raise ValueError(f"unsupported chart kind: {chart.kind}")
    allow_all_zero = bool(chart.config.get("allow_all_zero"))
    all_zero_meaning = str(chart.config.get("all_zero_meaning") or "")
    receipt = preflight_chart_data(
        chart.rows,
        chart_kind=chart.kind,
        numeric_fields=fields,
        allow_all_zero=allow_all_zero,
        all_zero_semantics=str(chart.config.get("all_zero_semantics") or "") or None,
        all_zero_meaning=all_zero_meaning or None,
    )
    return {"figure_set_id": chart.figure_id, **receipt}


def _visual_grammar(chart: Chart) -> str:
    """Describe every rendered mark using only the selected chart contract."""
    kind = chart.kind
    if kind == "bar":
        return f"Each bar is one {chart.config['category']} row; bar length encodes {chart.config['value']}; rows follow the renderer's declared ordering."
    if kind == "paired_bar":
        return f"Each row is one {chart.config['category']}; the two aligned bars encode {chart.config['series_labels'][0]} and {chart.config['series_labels'][1]} on one shared axis."
    if kind == "scatter":
        return f"Each point is one plotted row; x encodes {chart.config['x']}, y encodes {chart.config['y']}, and {chart.config['label']} is printed next to every point."
    if kind in {"heatmap", "state_heatmap"}:
        return f"Rows encode {chart.config['row']}, columns encode {chart.config['column']}, and cell fill encodes {chart.config['value']}; gray is missing and white is observed zero."
    if kind == "dot_range":
        return f"Each row is one {chart.config['category']}; the horizontal interval spans {chart.config['low']} to {chart.config['high']} and the point marks {chart.config['mid']}."
    if kind == "paired_dot":
        return f"Each row is one {chart.config['category']}; connected points encode {chart.config['a_label']} and {chart.config['b_label']} on a shared axis."
    if kind == "ecdf":
        return f"Each line is one {chart.config['series']} group; x encodes {chart.config['value']} and y is cumulative fraction; values beyond the display ceiling remain counted at the ceiling."
    raise ValueError(f"unsupported chart kind: {kind}")


def _statistics_uncertainty(chart: Chart) -> str:
    if chart.kind == "dot_range":
        return "Point is the median; interval endpoints are the first and third quartiles computed by linear interpolation."
    if chart.kind == "ecdf":
        return "Empirical cumulative fractions are calculated from every retained observation; no fitted model or confidence interval is displayed."
    return "Descriptive plotted values only; no fitted model, inferential test, confidence interval, standard error, or multiple-testing procedure is displayed."


def _caption_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.12g}"
    return str(value)


def _group_denominator_summary(chart: Chart) -> str:
    """Describe the actual plotted group denominator fields without inventing totals."""
    available = {key for row in chart.rows for key in row}
    group_field = next((field for field in ("host", "class", "role") if field in available), None)
    rate_fields = sorted(
        key for key in available if key.endswith("_pct") or "_per_" in key
    )
    if chart.kind == "ecdf":
        rate_fields.append("cumulative_fraction")
    rate_denominator_field = str(chart.config.get("rate_denominator_field") or "").strip()
    rate_denominator_unit = str(chart.config.get("rate_denominator_unit") or "").strip()
    if rate_denominator_field and not rate_fields:
        rate_fields.append(str(chart.config.get("value") or chart.config.get("y") or "declared_rate"))
    if rate_fields and (not rate_denominator_field or not rate_denominator_unit):
        raise FigurePolicyError(
            "FIGURE_CAPTION_RATE_DENOMINATOR_CONTRACT_MISSING",
            f"{chart.figure_id} rate fields require an explicit denominator field and unit",
        )
    if rate_denominator_field:
        missing_rows = [index for index, row in enumerate(chart.rows, 1) if rate_denominator_field not in row]
        if missing_rows:
            raise FigurePolicyError(
                "FIGURE_CAPTION_RATE_DENOMINATOR_FIELD_MISSING",
                f"{chart.figure_id} denominator field {rate_denominator_field!r} is absent from plotted rows {missing_rows}",
            )
    denominator_fields = tuple(dict.fromkeys((
        "strains", "memberships", "n", "genes", "strain_prevalence", "governed", "all_packaged",
        rate_denominator_field,
    )))
    rate_prefix = (
        f"rate_fields={'|'.join(rate_fields)}; denominator_field={rate_denominator_field}; "
        f"denominator_unit={rate_denominator_unit}; "
        if rate_fields else ""
    )
    if group_field is None:
        details = [f"rows={len(chart.rows)}"]
        if rate_denominator_field:
            values = sorted({_caption_value(row[rate_denominator_field]) for row in chart.rows})
            details.append(f"{rate_denominator_field}={'|'.join(values)}")
        return f"{rate_prefix}grouping=NONE; all_rows({'; '.join(details)})."
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in chart.rows:
        groups[str(row.get(group_field) or "UNRESOLVED")].append(row)
    parts = []
    for group in sorted(groups, key=str.casefold):
        subset = groups[group]
        details = [f"rows={len(subset)}"]
        for field in denominator_fields:
            values = sorted(
                {_caption_value(row[field]) for row in subset if row.get(field) not in (None, "")}
            )
            if values:
                details.append(f"{field}={'|'.join(values)}")
        parts.append(f"{group}({'; '.join(details)})")
    return f"{rate_prefix}grouping={group_field}; " + "; ".join(parts) + "."


def _typed_missingness_summary(chart: Chart) -> str:
    state_fields = [
        field for field in ("state", "denominator_state")
        if any(field in row for row in chart.rows)
    ]
    if not state_fields:
        return (
            f"plotted_rows={len(chart.rows)}; NO_TYPED_STATE_COLUMN_IN_PLOTTED_ROWS; "
            "upstream missing, held, unmeasured, or "
            "not-applicable records cannot be inferred from this figure data."
        )
    summaries = [f"plotted_rows={len(chart.rows)}"]
    for field in state_fields:
        typed_rows = [row for row in chart.rows if field in row]
        counts = Counter(str(row.get(field) or "UNRESOLVED") for row in typed_rows)
        states = "; ".join(f"{field}={state}: {counts[state]}" for state in sorted(counts))
        summaries.append(
            f"{field}(typed_rows={len(typed_rows)}; "
            f"rows_missing_state_key={len(chart.rows) - len(typed_rows)}; {states})"
        )
    return "; ".join(summaries) + "."


def _caption_metadata(
    chart: Chart,
    spec: dict[str, Any],
    *,
    source: Path,
    payload: dict[str, Any],
    all_ids: Sequence[str],
    governed: Sequence[str],
    benchmark_ids: Sequence[str],
    selected_benchmarks: Sequence[str],
) -> dict[str, str]:
    source_release = str((payload.get("meta") or {}).get("sourceRelease") or "UNDECLARED_SOURCE_RELEASE")
    host_grouped = "host cohort" in chart.title.lower()
    genus_note = (
        "NOT_APPLICABLE_TO_INFERENCE: the widget source has no governed genus field. Host-group panels are descriptive only; genus composition is neither controlled nor inferentially compared."
        if host_grouped else
        "NOT_APPLICABLE: this renderer does not perform a genus-level comparison; any later cohort interpretation must use a separate genus-aware source."
    )
    source_sha = _sha256(source)
    source_bytes = source.stat().st_size
    return {
        "caption_schema_version": CAPTION_METHOD_SCHEMA,
        "figure_question": str(spec.get("scientific_question") or ""),
        "source": f"{source.name}; sha256={source_sha}; declared artifacts={','.join(spec.get('source_artifacts') or [])}",
        "source_bindings": (
            f"widget_data(locator={source.name}; sha256={source_sha}; bytes={source_bytes}); "
            f"declared_artifact_names={','.join(spec.get('source_artifacts') or [])}; "
            "declared_artifact_hashes=NOT_SUPPLIED_BY_WIDGET."
        ),
        "source_release": source_release,
        "software_versions": f"Sapote-Mamey source release: {source_release}; renderer schema: {SCHEMA_VERSION}",
        "unit_of_analysis": str(spec.get("unit") or ""),
        "inclusion_exclusion_roles": (
            f"Included study cohort: {len(governed)} GOVERNED STUDY records. "
            f"Active comparison roster: {len(all_ids)}. External benchmarks available: {len(benchmark_ids)}; "
            f"explicitly selected for sensitivity comparison: {len(selected_benchmarks)} "
            f"({','.join(selected_benchmarks) or 'none'}). External benchmarks never enter study n or percentages."
        ),
        "denominator": (
            f"source_records={len(payload.get('strains') or {})}; study_strains={len(governed)}; "
            f"default_and_selected_comparison_records={len(all_ids)}; plotted_rows={len(chart.rows)}; "
            f"available_external_benchmarks={len(benchmark_ids)}; selected_external_benchmarks={len(selected_benchmarks)}."
        ),
        "group_denominators": _group_denominator_summary(chart),
        "typed_missingness": _typed_missingness_summary(chart),
        "benchmark_sensitivity": (
            f"available={len(benchmark_ids)} ({','.join(benchmark_ids) or 'none'}); "
            f"selected={len(selected_benchmarks)} ({','.join(selected_benchmarks) or 'none'}); "
            "default_off=true; selected benchmarks remain excluded from study n and percentages."
        ),
        "transformation": str(spec.get("transform") or ""),
        "visual_grammar": _visual_grammar(chart),
        "statistics_uncertainty": _statistics_uncertainty(chart),
        "comparison_group": chart.subtitle,
        "genus_control": genus_note,
        "contradictions": (
            "The widget aggregate does not carry a complete assembly-edge, overmerge, source-binding, or Mode B contradiction ledger. "
            "Those upstream records must be reconciled before publication; missing contradiction metadata is not evidence that no contradiction exists."
        ),
        "interpretation_boundary": str(spec.get("claim_ceiling") or GLOBAL_CLAIM_CEILING),
    }


def _caption_block(metadata: dict[str, str]) -> str:
    labels = (
        ("Caption schema", "caption_schema_version"),
        ("Figure question", "figure_question"),
        ("Source and release", "source"),
        ("Source bindings", "source_bindings"),
        ("Declared source release", "source_release"),
        ("Software/version context", "software_versions"),
        ("Unit of analysis", "unit_of_analysis"),
        ("Inclusion, exclusion, and roles", "inclusion_exclusion_roles"),
        ("Denominators", "denominator"),
        ("Per-group denominators", "group_denominators"),
        ("Typed missingness", "typed_missingness"),
        ("Benchmark sensitivity", "benchmark_sensitivity"),
        ("Transformation and counting rule", "transformation"),
        ("Visual grammar", "visual_grammar"),
        ("Statistics and uncertainty", "statistics_uncertainty"),
        ("Comparison group", "comparison_group"),
        ("Genus control", "genus_control"),
        ("Contradictions and limitations", "contradictions"),
        ("Interpretation boundary", "interpretation_boundary"),
    )
    return "\n\n".join(f"**{label}.** {metadata[key]}" for label, key in labels)


def _write_rows(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    fields=list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w",newline="",encoding="utf-8") as stream:
        writer=_SafeDictWriter(stream,fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def _validate_outputs(
    destination: Path,
    manifest: Sequence[dict[str, Any]],
    governed: Sequence[str],
    expected_ids: Sequence[str] = IMPLEMENTED_IDS,
    label_ids: Sequence[str] = ("FS002", "FS010", "FS042", "FS050"),
) -> list[dict[str, Any]]:
    """Reconcile rendered artifacts without treating visual review as automated."""
    checks: list[dict[str, Any]] = []

    def record(check_id: str, passed: bool, detail: str) -> None:
        checks.append({"check_id": check_id, "status": "PASS" if passed else "FAIL", "detail": detail})

    expected = len(expected_ids)
    record("IMPLEMENTED_COUNT", len(manifest) == expected, f"observed={len(manifest)} expected={expected}")
    ids = [item["figure_set_id"] for item in manifest]
    record("IMPLEMENTED_IDS", tuple(ids) == tuple(expected_ids), f"observed={','.join(ids)}")
    svg_hashes: set[str] = set()
    row_mismatches: list[str] = []
    xml_failures: list[str] = []
    caption_scope_failures: list[str] = []
    canvas_governance_failures: list[str] = []
    for item in manifest:
        figure_id = item["figure_set_id"]
        svg_path = destination / item["svg"]
        csv_path = destination / item["data_csv"]
        text_path = destination / item["caption_methods"]
        try:
            ET.parse(svg_path)
        except (ET.ParseError, OSError):
            xml_failures.append(figure_id)
        svg_hashes.add(_sha256(svg_path))
        with csv_path.open(newline="", encoding="utf-8") as stream:
            row_count = sum(1 for _ in csv.DictReader(stream))
        if row_count != int(item["rows"]):
            row_mismatches.append(f"{figure_id}:{row_count}!={item['rows']}")
        svg_text = svg_path.read_text(encoding="utf-8")
        caption_text = text_path.read_text(encoding="utf-8")
        if GLOBAL_CLAIM_CEILING not in caption_text:
            caption_scope_failures.append(figure_id)
        if GLOBAL_CLAIM_CEILING in svg_text or PROFILE in svg_text:
            canvas_governance_failures.append(figure_id)
    record("SVG_XML", not xml_failures, "failures=" + (",".join(xml_failures) or "none"))
    record("CSV_ROW_RECONCILIATION", not row_mismatches, "mismatches=" + (",".join(row_mismatches) or "none"))
    record("UNIQUE_SVG_HASHES", len(svg_hashes) == expected, f"unique={len(svg_hashes)} expected={expected}")
    record("CAPTION_SCIENTIFIC_SCOPE", not caption_scope_failures, "failures=" + (",".join(caption_scope_failures) or "none"))
    record("NO_GOVERNANCE_FOOTER_ON_CANVAS", not canvas_governance_failures, "failures=" + (",".join(canvas_governance_failures) or "none"))
    label_failures: list[str] = []
    for figure_id in label_ids:
        svg_text = (destination / "figures" / f"{figure_id}.svg").read_text(encoding="utf-8")
        missing = [sid for sid in governed if sid not in svg_text]
        if missing:
            label_failures.append(f"{figure_id}:{','.join(missing)}")
    record("ALL_STRAIN_LABELS_EMBEDDED", not label_failures, "missing=" + (";".join(label_failures) or "none"))
    record("VISUAL_REVIEW_BOUNDARY", True, "automated checks do not substitute for raster visual review")
    return checks


def render_tranche(
    widget_data: str | Path,
    outdir: str | Path,
    *,
    external_benchmark_ids: Sequence[str] = (),
) -> dict[str, Any]:
    source,payload,all_ids,governed,benchmark_ids,selected_benchmarks=_load_with_benchmarks(
        widget_data, external_benchmark_ids
    )
    native_svg_rasterization = _native_svg_rasterization_capability()
    charts=build_charts(payload,all_ids,governed)
    # Validate every chart before the output root or any partial artifact is
    # created.  This prevents one-point/all-zero placeholder figures from
    # looking like successful analytical output.
    registry={r["figure_set_id"]:r for r in build_registry()}
    preflight={chart.figure_id:_preflight_chart(chart) for chart in charts}
    caption_metadata = {
        chart.figure_id: _caption_metadata(
            chart, registry[chart.figure_id], source=source, payload=payload,
            all_ids=all_ids, governed=governed, benchmark_ids=benchmark_ids,
            selected_benchmarks=selected_benchmarks,
        )
        for chart in charts
    }
    caption_receipts = {
        figure_id: validate_caption_methods(metadata, nonstandard_visual=True)
        for figure_id, metadata in caption_metadata.items()
    }
    genus_receipts = {
        chart.figure_id: validate_genus_comparison("NOT_APPLICABLE") for chart in charts
    }
    destination=Path(outdir).resolve(); destination.mkdir(parents=True,exist_ok=True)
    figures_dir=destination/"figures"; data_dir=destination/"data"; text_dir=destination/"text"
    for directory in (figures_dir,data_dir,text_dir): directory.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for chart in charts:
        svg_path=figures_dir/f"{chart.figure_id}.svg"; csv_path=data_dir/f"{chart.figure_id}_data.csv"; text_path=text_dir/f"{chart.figure_id}_CAPTION_METHODS.md"
        svg_path.write_text(render_svg(chart),encoding="utf-8"); _write_rows(csv_path,chart.rows)
        spec=registry[chart.figure_id]
        detailed_caption = _caption_block(caption_metadata[chart.figure_id])
        text_path.write_text(f"# {chart.figure_id} — {chart.title}\n\n## Traveling caption and methods\n\n{detailed_caption}\n\n## Short registry summary\n\n{spec['caption_template']}\n\n## Additional registry method note\n\n{spec['methods_template']}\n\n## Render-specific note\n\n{chart.subtitle}\n\n## Citation status\n\nCitations must be reviewed against the source release and upstream evidence channels at manuscript freeze.\n",encoding="utf-8")
        manifest.append({"figure_set_id":chart.figure_id,"title":chart.title,"kind":chart.kind,"rows":len(chart.rows),
                         "svg":str(svg_path.relative_to(destination)),"data_csv":str(csv_path.relative_to(destination)),
                         "caption_methods":str(text_path.relative_to(destination)),"svg_sha256":_sha256(svg_path),
                         "data_sha256":_sha256(csv_path),"text_sha256":_sha256(text_path),
                         "caption":spec["caption_template"],"methods":spec["methods_template"],
                         "caption_schema_version":CAPTION_METHOD_SCHEMA,
                         "render_note":chart.subtitle,"preflight":preflight[chart.figure_id],
                         "caption_metadata":caption_metadata[chart.figure_id],
                         "caption_validation":caption_receipts[chart.figure_id],
                         "genus_validation":genus_receipts[chart.figure_id]})
    cards="".join(f'<article><h2>{_esc(item["figure_set_id"])} — {_esc(item["title"])}</h2><img src="{_esc(item["svg"])}" alt="{_esc(item["title"])}"><div class="caption"><strong>Caption.</strong> {"<br><br>".join(_esc(part) for part in _caption_block(item["caption_metadata"]).split(chr(10)+chr(10)))}</div><details><summary>Registry summary and method note</summary><p>{_esc(item["caption"])} {_esc(item["methods"])}</p></details><p><a href="{_esc(item["data_csv"])}">Plotted data</a> · <a href="{_esc(item["caption_methods"])}">Caption and methods</a></p></article>' for item in manifest)
    index=destination/"OPEN_FIGURE_SET_TRANCHE_1.html"
    index.write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Codex Figure Factory tranche 1</title><style>body{{font:15px/1.45 system-ui;margin:0;background:#f4f6f8;color:#17212b}}header,main{{max-width:1500px;margin:auto;padding:22px}}article{{background:white;border:1px solid #d8dee5;border-radius:8px;padding:14px;margin:0 0 20px}}img{{max-width:100%;height:auto}}h1{{margin-bottom:4px}}h2{{font-size:18px}}a{{color:#31688e}}.caption{{margin-top:12px;padding:12px 14px;background:#f7f1e4;border-left:4px solid #168c8c}}details{{margin-top:10px}}</style></head><body><header><h1>Codex Figure Factory tranche 1</h1><p>20 implemented strain- and cohort-specific sets from the governed 200-set registry. {_esc(GLOBAL_CLAIM_CEILING)}</p></header><main>{cards}</main></body></html>''',encoding="utf-8")
    checks = _validate_outputs(destination, manifest, governed)
    receipt={"schema_version":SCHEMA_VERSION,"status":"PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL","profile":PROFILE,"source":{"path":str(source),"sha256":_sha256(source)},
             "governed_strains":len(governed),"all_packaged_strains":len(all_ids),
             "source_strains":len(payload["strains"]),
             "native_svg_rasterization":native_svg_rasterization,
             "external_benchmarks":{"available":list(benchmark_ids),"selected":list(selected_benchmarks),"default_off":True},
             "implemented_count":len(manifest),
             "implemented_ids":list(IMPLEMENTED_IDS),"claim_ceiling":GLOBAL_CLAIM_CEILING,
             "caption_schema_version":CAPTION_METHOD_SCHEMA,"figures":manifest,
             "preflight_receipts":list(preflight.values()),"caption_validation_receipts":caption_receipts,
             "genus_validation_receipts":genus_receipts,"machine_checks":checks,"index":{"path":index.name,"sha256":_sha256(index)}}
    (destination/"TRANCHE_1_QA_RECEIPT.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (destination/"FIGURE_MANIFEST.json").write_text(json.dumps({"schema_version":SCHEMA_VERSION,"figures":manifest},indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--widget-data",required=True)
    parser.add_argument("--outdir",required=True)
    parser.add_argument("--external-benchmark",action="append",default=[],
                        help="exact source identifier typed EXTERNAL_BENCHMARK; repeat to select")
    args=parser.parse_args(argv)
    receipt=render_tranche(args.widget_data,args.outdir,external_benchmark_ids=args.external_benchmark); emit(json.dumps(receipt,indent=2))
    return 0 if receipt["status"]=="PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
