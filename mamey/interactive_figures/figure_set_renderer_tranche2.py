#!/usr/bin/env python3
"""Render 21 source-complete Codex Figure Factory sets (tranche 2)."""

from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from ..console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from mamey.console import emit

import csv
import hashlib
import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

from .figure_set_registry import GLOBAL_CLAIM_CEILING, PROFILE, build_registry
from .figure_set_renderer import (
    Chart,
    HOST_ORDER,
    ROLE_ORDER,
    ROLE_SHORT,
    _host,
    _load,
    _median,
    _pct,
    _quantile,
    _sha256,
    _validate_outputs,
    _write_rows,
    render_svg,
)


SCHEMA_VERSION = "sapote-mamey.codex-figure-set-render.tranche2.v1"
IMPLEMENTED_IDS_2 = (
    "FS004", "FS006", "FS012", "FS014",
    "FS017", "FS018", "FS019", "FS020", "FS022", "FS023",
    "FS044", "FS046", "FS051", "FS052",
    "FS185", "FS186", "FS187", "FS188", "FS189", "FS190", "FS191",
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _top(counter: Counter[str], n: int) -> list[str]:
    return [key for key, _value in sorted(counter.items(), key=lambda item: (-item[1], item[0].lower()))[:n]]


def _pair_label(row: dict[str, str]) -> str:
    return f"{row['class_a']} + {row['class_b']}"


def build_charts_2(payload: dict[str, Any], all_ids: Sequence[str], governed: Sequence[str], source_bundle: Path) -> list[Chart]:
    strains = payload["strains"]
    bgcs = _read_csv(source_bundle / "BGC_RECORDS.csv")
    memberships = _read_csv(source_bundle / "BGC_CLASS_MEMBERSHIPS.csv")
    pairs = _read_csv(source_bundle / "BGC_CLASS_PAIRS.csv")
    genes = _read_csv(source_bundle / "BGC_MACHINERY_ASSIGNMENTS.csv")
    governed_set = set(governed)
    all_set = set(all_ids)
    g_bgcs = [row for row in bgcs if row["strain"] in governed_set]
    g_memberships = [row for row in memberships if row["strain"] in governed_set]
    g_pairs = [row for row in pairs if row["strain"] in governed_set]
    g_genes = [row for row in genes if row["strain"] in governed_set]
    class_counts = Counter(row["product_class"] for row in g_memberships)
    top_classes = _top(class_counts, 15)
    pair_counts = Counter(_pair_label(row) for row in g_pairs)
    top_pairs = _top(pair_counts, 15)
    charts: list[Chart] = []

    # Boundary and class-composition source completeness.
    bnd_rows = []
    for sid in governed:
        subset = [row for row in g_bgcs if row["strain"] == sid]
        total = len(subset)
        counts = Counter(row["boundary"] for row in subset)
        for boundary in ("Edge", "Full-contig", "Interior"):
            bnd_rows.append({"strain": sid, "boundary": boundary, "bgc_pct": _pct(counts[boundary], total), "bgcs": counts[boundary], "total_bgcs": total})
    charts.append(Chart("FS004", "heatmap", "BGC boundary context — every governed strain",
                        "Percent of physical BGC rows in each declared boundary state; no class-membership duplication", bnd_rows,
                        {"row": "strain", "column": "boundary", "value": "bgc_pct", "legend": "Physical BGC rows (%)"}))

    availability = []
    for sid in governed:
        subset = [row for row in g_bgcs if row["strain"] == sid]
        fields = {
            "Inventory rows": bool(subset),
            "Boundary populated": bool(subset) and all(row["boundary"] not in {"", "MISSING"} for row in subset),
            "Length populated": bool(subset) and all(str(row["length_kb"]).strip() for row in subset),
            "Product token populated": bool(subset) and all(str(row["products"]).strip() for row in subset),
        }
        for field, populated in fields.items():
            availability.append({"strain": sid, "field": field, "state": "POPULATED" if populated else "MISSING", "value": 1 if populated else -1})
    charts.append(Chart("FS006", "state_heatmap", "BGC boundary evidence availability",
                        "Inventory, boundary, length, and product-token availability remain explicit per strain", availability,
                        {"row": "strain", "column": "field", "value": "value", "state": "state"}))

    class_boundary = []
    for cls in top_classes:
        subset = [row for row in g_memberships if row["product_class"] == cls]
        counts = Counter(row["boundary"] for row in subset)
        for boundary in ("Edge", "Full-contig", "Interior"):
            class_boundary.append({"class": cls, "boundary": boundary, "membership_pct": _pct(counts[boundary], len(subset)), "memberships": counts[boundary]})
    charts.append(Chart("FS012", "heatmap", "BGC class composition by boundary state",
                        "Top nonexclusive class memberships partitioned within class across Edge, Full-contig, and Interior", class_boundary,
                        {"row": "class", "column": "boundary", "value": "membership_pct", "legend": "Within-class memberships (%)"}))

    class_availability = []
    member_keys = {(row["strain"], row["product_class"]) for row in g_memberships}
    for sid in governed:
        source_present = any(row["strain"] == sid for row in g_bgcs)
        for cls in top_classes:
            state = "POPULATED" if (sid, cls) in member_keys else ("OBSERVED_ZERO" if source_present else "MISSING")
            class_availability.append({"strain": sid, "class": cls, "state": state, "value": {"MISSING": -1, "OBSERVED_ZERO": 0, "POPULATED": 1}[state]})
    charts.append(Chart("FS014", "state_heatmap", "BGC class-membership evidence availability",
                        "Complete inventory absence is missing; absent class membership in a present inventory is observed zero", class_availability,
                        {"row": "strain", "column": "class", "value": "value", "state": "state"}))

    # Physical-BGC class co-occurrence.
    charts.append(Chart("FS017", "bar", "BGC class co-occurrence — governed cohort overview",
                        "Pairs occur within the same physical BGC row; top nonexclusive pairs only", [{"class_pair": pair, "hybrid_bgcs": pair_counts[pair]} for pair in top_pairs],
                        {"category": "class_pair", "value": "hybrid_bgcs", "x_label": "Physical BGCs with class pair"}))

    strain_pair_rows = []
    for sid in governed:
        subset = [row for row in g_pairs if row["strain"] == sid]
        labels = {_pair_label(row) for row in subset}
        hybrid_bgcs = {(row["strain"], row["bgc_id"]) for row in subset}
        strain_pair_rows.append({"strain": sid, "hybrid_bgcs": len(hybrid_bgcs), "distinct_class_pairs": len(labels), "host": _host(strains[sid])})
    charts.append(Chart("FS018", "scatter", "BGC class co-occurrence — every governed strain",
                        "Every governed strain is labelled; zero-pair strains remain in the denominator", strain_pair_rows,
                        {"x": "hybrid_bgcs", "y": "distinct_class_pairs", "label": "strain", "x_label": "Physical hybrid BGC rows", "y_label": "Distinct within-BGC class pairs", "x_min": 0, "y_min": 0}))

    anchor_classes = _top(class_counts, 12)
    pair_lookup = Counter()
    for row in g_pairs:
        pair_lookup[(row["class_a"], row["class_b"])] += 1
        pair_lookup[(row["class_b"], row["class_a"])] += 1
    pair_matrix = [{"anchor_class": a, "partner_class": b, "physical_bgcs": pair_lookup[(a, b)]} for a in anchor_classes for b in anchor_classes]
    charts.append(Chart("FS019", "heatmap", "BGC class co-occurrence matrix",
                        "Symmetric counts of physical BGC rows containing both class tokens; diagonal is observed zero by definition", pair_matrix,
                        {"row": "anchor_class", "column": "partner_class", "value": "physical_bgcs", "legend": "Physical BGCs with pair"}))

    pair_boundary = []
    for pair in top_pairs:
        subset = [row for row in g_pairs if _pair_label(row) == pair]
        counts = Counter(row["boundary"] for row in subset)
        for boundary in ("Edge", "Full-contig", "Interior"):
            pair_boundary.append({"class_pair": pair, "boundary": boundary, "hybrid_bgcs": counts[boundary]})
    charts.append(Chart("FS020", "heatmap", "BGC class co-occurrence by boundary state",
                        "Top within-BGC class pairs stratified without collapsing Edge, Full-contig, or Interior", pair_boundary,
                        {"row": "class_pair", "column": "boundary", "value": "hybrid_bgcs", "legend": "Physical hybrid BGC rows"}))

    pair_availability = []
    pair_keys = {(row["strain"], _pair_label(row)) for row in g_pairs}
    for sid in governed:
        source_present = any(row["strain"] == sid for row in g_bgcs)
        for pair in top_pairs[:12]:
            state = "POPULATED" if (sid, pair) in pair_keys else ("OBSERVED_ZERO" if source_present else "MISSING")
            pair_availability.append({"strain": sid, "class_pair": pair, "state": state, "value": {"MISSING": -1, "OBSERVED_ZERO": 0, "POPULATED": 1}[state]})
    charts.append(Chart("FS022", "state_heatmap", "BGC class-pair evidence availability",
                        "Present inventories distinguish observed-zero pairs from missing source evidence", pair_availability,
                        {"row": "strain", "column": "class_pair", "value": "value", "state": "state"}))

    all_pair_counts = Counter(_pair_label(row) for row in pairs if row["strain"] in all_set)
    sensitivity = [{"class_pair": pair, "governed": pair_counts[pair], "all_packaged": all_pair_counts[pair]} for pair in _top(all_pair_counts, 15)]
    charts.append(Chart("FS023", "paired_dot", "BGC class co-occurrence — governance sensitivity",
                        "Governed physical-BGC pair counts are paired with all packaged counts", sensitivity,
                        {"category": "class_pair", "a": "governed", "b": "all_packaged", "a_label": "Governed", "b_label": "All packaged", "x_label": "Physical BGCs with class pair"}))

    # Machinery length and burden joined to the retained physical-BGC projection.
    valid_genes = [row for row in g_genes if row["length_state"] == "POPULATED" and _number(row["length_aa"]) > 0]
    boundary_lengths = []
    for boundary in ("Edge", "Full-contig", "Interior", "MISSING"):
        values = [_number(row["length_aa"]) for row in valid_genes if row["boundary"] == boundary]
        if values:
            boundary_lengths.append({"boundary": boundary, "q1": _quantile(values, .25), "median": _median(values), "q3": _quantile(values, .75), "genes": len(values)})
    charts.append(Chart("FS044", "dot_range", "Machinery gene length by BGC boundary context",
                        "Median and interquartile range use the source-bundle physical-CDS projection; boundary assignment remains explicit", boundary_lengths,
                        {"category": "boundary", "low": "q1", "mid": "median", "high": "q3", "x_label": "Protein length (aa)"}))

    length_availability = []
    for role in ROLE_ORDER:
        assignments = [row for row in g_genes if row["role"] == role]
        valid = [row for row in assignments if row["length_state"] == "POPULATED" and _number(row["length_aa"]) > 0]
        strains_with = {row["strain"] for row in valid}
        length_availability.append({"role": ROLE_SHORT[role], "valid_length_pct": _pct(len(valid), len(assignments)), "strain_coverage_pct": _pct(len(strains_with), len(governed)), "assignments": len(assignments)})
    charts.append(Chart("FS046", "paired_bar", "Machinery-gene length evidence availability",
                        "Valid-length assignment rate and governed-strain coverage are shown separately", length_availability,
                        {"category": "role", "series": ["valid_length_pct", "strain_coverage_pct"], "series_labels": ["Assignments with valid length", "Governed strains represented"], "x_label": "Availability (%)", "max": 100}))

    class_role_counts: Counter[tuple[str, str]] = Counter()
    class_bgc_counts = Counter(row["product_class"] for row in g_memberships)
    for row in g_genes:
        for cls in {token.strip() for token in row["products"].split(";") if token.strip()}:
            class_role_counts[(cls, row["role"])] += 1
    class_role_rows = []
    for cls in top_classes:
        for role in ROLE_ORDER:
            class_role_rows.append({"class": cls, "role": ROLE_SHORT[role], "genes_per_100_bgc_memberships": 100 * class_role_counts[(cls, role)] / class_bgc_counts[cls] if class_bgc_counts[cls] else 0})
    charts.append(Chart("FS051", "heatmap", "Machinery role burden by BGC class",
                        "Role genes per 100 nonexclusive BGC-class memberships; retained physical-BGC projection is declared", class_role_rows,
                        {"row": "class", "column": "role", "value": "genes_per_100_bgc_memberships", "legend": "Role genes per 100 BGC-class memberships"}))

    boundary_bgc_counts = Counter(row["boundary"] for row in g_bgcs)
    boundary_role_counts = Counter((row["boundary"], row["role"]) for row in g_genes)
    boundary_role_rows = []
    for boundary in ("Edge", "Full-contig", "Interior", "MISSING"):
        if not boundary_bgc_counts[boundary]:
            continue
        for role in ROLE_ORDER:
            boundary_role_rows.append({"boundary": boundary, "role": ROLE_SHORT[role], "genes_per_bgc": boundary_role_counts[(boundary, role)] / boundary_bgc_counts[boundary]})
    charts.append(Chart("FS052", "heatmap", "Machinery role burden by BGC boundary context",
                        "Role assignments per physical BGC row, stratified by declared boundary state", boundary_role_rows,
                        {"row": "boundary", "column": "role", "value": "genes_per_bgc", "legend": "Role assignments per physical BGC row"}))

    # Host/niche provenance and cohort comparisons.
    host_counts = Counter(_host(strains[sid]) for sid in governed)
    charts.append(Chart("FS185", "bar", "Host and niche cohorts — governed overview",
                        "Only explicit host-context assignments are counted; unresolved remains a cohort", [{"host": group, "strains": host_counts[group]} for group in HOST_ORDER],
                        {"category": "host", "value": "strains", "x_label": "Governed strains"}))

    host_scatter = [{"strain": sid, "bgc_rows": int(strains[sid].get("bgcRows") or 0), "unique_physical_genes": int(strains[sid].get("uniquePhysicalGenes") or 0), "host": _host(strains[sid])} for sid in governed]
    charts.append(Chart("FS186", "scatter", "Host and niche context — every governed strain",
                        "Every strain is labelled; host context is retained in plotted data and is not inferred from position", host_scatter,
                        {"x": "unique_physical_genes", "y": "bgc_rows", "label": "strain", "x_label": "Unique physical CDS", "y_label": "Package BGC rows", "x_min": 0, "y_min": 0}))

    host_class_rows = []
    for group in HOST_ORDER:
        ids = {sid for sid in governed if _host(strains[sid]) == group}
        denom = len(ids)
        counts = Counter(row["product_class"] for row in g_memberships if row["strain"] in ids)
        for cls in top_classes:
            host_class_rows.append({"host": group, "class": cls, "memberships_per_strain": counts[cls] / denom if denom else 0})
    charts.append(Chart("FS187", "heatmap", "BGC class profile by host cohort",
                        "Nonexclusive class memberships are normalized per governed strain within each explicit host group", host_class_rows,
                        {"row": "host", "column": "class", "value": "memberships_per_strain", "legend": "BGC-class memberships per strain"}))

    host_boundary_rows = []
    for group in HOST_ORDER:
        subset = [row for row in g_bgcs if row["host_group"] == group]
        counts = Counter(row["boundary"] for row in subset)
        for boundary in ("Edge", "Full-contig", "Interior"):
            host_boundary_rows.append({"host": group, "boundary": boundary, "bgc_pct": _pct(counts[boundary], len(subset)), "bgcs": counts[boundary]})
    charts.append(Chart("FS188", "heatmap", "BGC boundary context by host cohort",
                        "Physical BGC rows are normalized within explicit host groups; unresolved remains separate", host_boundary_rows,
                        {"row": "host", "column": "boundary", "value": "bgc_pct", "legend": "Physical BGC rows within host group (%)"}))

    host_ranges = []
    for group in HOST_ORDER:
        values = [int(strains[sid].get("bgcRows") or 0) for sid in governed if _host(strains[sid]) == group]
        host_ranges.append({"host": group, "q1": _quantile(values, .25), "median": _median(values), "q3": _quantile(values, .75), "strains": len(values)})
    charts.append(Chart("FS189", "dot_range", "Package BGC-row context by host cohort",
                        "Median and interquartile range are assembly-sensitive context, not host causality or biological ranking", host_ranges,
                        {"category": "host", "low": "q1", "mid": "median", "high": "q3", "x_label": "Package BGC rows"}))

    host_availability = []
    for sid in governed:
        context = strains[sid].get("hostContext") or {}
        for field, value in (("Host group", context.get("group")), ("Source", context.get("source")), ("Host species", context.get("hostSpecies")), ("Location", context.get("location"))):
            populated = bool(str(value or "").strip()) and not (field == "Host group" and str(value).upper() == "UNRESOLVED")
            state = "POPULATED" if populated else "OBSERVED_ZERO"
            host_availability.append({"strain": sid, "field": field, "state": state, "value": 1 if populated else 0})
    charts.append(Chart("FS190", "state_heatmap", "Host-context evidence availability",
                        "Host group, provenance source, host species, and location are kept as separate evidence fields", host_availability,
                        {"row": "strain", "column": "field", "value": "value", "state": "state"}))

    all_host_bgc = Counter()
    governed_host_bgc = Counter()
    for row in bgcs:
        all_host_bgc[row["host_group"]] += 1
        if row["strain"] in governed_set:
            governed_host_bgc[row["host_group"]] += 1
    charts.append(Chart("FS191", "paired_dot", "Host-cohort denominator sensitivity",
                        "Governed physical-BGC counts are paired with all packaged counts; exclusions are not silently pooled", [{"host": group, "governed": governed_host_bgc[group], "all_packaged": all_host_bgc[group]} for group in HOST_ORDER],
                        {"category": "host", "a": "governed", "b": "all_packaged", "a_label": "Governed", "b_label": "All packaged", "x_label": "Physical BGC rows"}))

    assert tuple(chart.figure_id for chart in charts) == IMPLEMENTED_IDS_2
    return charts


def render_tranche_2(widget_data: str | Path, source_bundle: str | Path, outdir: str | Path) -> dict[str, Any]:
    widget_path, payload, all_ids, governed = _load(widget_data)
    bundle = Path(source_bundle).resolve()
    source_receipt = bundle / "SOURCE_BUNDLE_RECEIPT.json"
    if not source_receipt.is_file():
        raise ValueError("source bundle has no SOURCE_BUNDLE_RECEIPT.json")
    destination = Path(outdir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    figures_dir, data_dir, text_dir = destination / "figures", destination / "data", destination / "text"
    for directory in (figures_dir, data_dir, text_dir): directory.mkdir(parents=True, exist_ok=True)
    registry = {record["figure_set_id"]: record for record in build_registry()}
    charts = build_charts_2(payload, all_ids, governed, bundle)
    manifest = []
    for chart in charts:
        svg_path = figures_dir / f"{chart.figure_id}.svg"
        csv_path = data_dir / f"{chart.figure_id}_data.csv"
        text_path = text_dir / f"{chart.figure_id}_CAPTION_METHODS.md"
        svg_path.write_text(render_svg(chart), encoding="utf-8")
        _write_rows(csv_path, chart.rows)
        spec = registry[chart.figure_id]
        text_path.write_text(
            f"# {chart.figure_id} — {chart.title}\n\n## Caption\n\n{spec['caption_template']}\n\n"
            f"## Methods\n\n{spec['methods_template']}\n\n## Render-specific note\n\n{chart.subtitle}\n\n"
            "## Citation status\n\nCitations must be reviewed against the source release and upstream evidence channels at manuscript freeze.\n",
            encoding="utf-8",
        )
        manifest.append({
            "figure_set_id": chart.figure_id, "title": chart.title, "kind": chart.kind, "rows": len(chart.rows),
            "svg": str(svg_path.relative_to(destination)), "data_csv": str(csv_path.relative_to(destination)),
            "caption_methods": str(text_path.relative_to(destination)), "svg_sha256": _sha256(svg_path),
            "data_sha256": _sha256(csv_path), "text_sha256": _sha256(text_path),
        })
    cards = "".join(
        f'<article><h2>{html.escape(item["figure_set_id"])} — {html.escape(item["title"])}</h2>'
        f'<img src="{html.escape(item["svg"])}" alt="{html.escape(item["title"])}">'
        f'<p><a href="{html.escape(item["data_csv"])}">Plotted data</a> · '
        f'<a href="{html.escape(item["caption_methods"])}">Caption and methods</a></p></article>'
        for item in manifest
    )
    index = destination / "OPEN_FIGURE_SET_TRANCHE_2.html"
    index.write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Codex Figure Factory tranche 2</title><style>body{font:15px/1.45 system-ui;margin:0;background:#f4f6f8;color:#17212b}'
        'header,main{max-width:1500px;margin:auto;padding:22px}article{background:white;border:1px solid #d8dee5;border-radius:8px;padding:14px;margin:0 0 20px}'
        'img{max-width:100%;height:auto}h1{margin-bottom:4px}h2{font-size:18px}a{color:#31688e}</style></head><body><header>'
        f'<h1>Codex Figure Factory tranche 2</h1><p>21 additional source-complete strain- and cohort-specific sets. {html.escape(GLOBAL_CLAIM_CEILING)}</p>'
        f'</header><main>{cards}</main></body></html>', encoding="utf-8")
    checks = _validate_outputs(destination, manifest, governed, IMPLEMENTED_IDS_2, ("FS018", "FS186"))
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL",
        "profile": PROFILE,
        "source": {
            "widget_data": str(widget_path), "widget_sha256": _sha256(widget_path),
            "source_bundle": str(bundle), "source_bundle_receipt_sha256": _sha256(source_receipt),
        },
        "governed_strains": len(governed), "all_packaged_strains": len(all_ids),
        "implemented_count": len(manifest), "implemented_ids": list(IMPLEMENTED_IDS_2),
        "claim_ceiling": GLOBAL_CLAIM_CEILING, "machine_checks": checks, "figures": manifest,
        "index": {"path": index.name, "sha256": _sha256(index)},
    }
    (destination / "TRANCHE_2_QA_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (destination / "FIGURE_MANIFEST.json").write_text(json.dumps({"schema_version": SCHEMA_VERSION, "figures": manifest}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--widget-data", required=True)
    parser.add_argument("--source-bundle", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args(argv)
    receipt = render_tranche_2(args.widget_data, args.source_bundle, args.outdir)
    emit(json.dumps(receipt, indent=2))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
