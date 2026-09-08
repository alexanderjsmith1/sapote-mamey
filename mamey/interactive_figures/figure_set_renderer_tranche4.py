#!/usr/bin/env python3
"""Render 14 tailoring-like and regulator-like burden sets (tranche 4)."""

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
import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence

from .figure_set_registry import GLOBAL_CLAIM_CEILING, PROFILE, build_registry
from .figure_set_renderer import Chart, HOST_ORDER, _host, _load, _pct, _sha256, _validate_outputs, _write_rows, render_svg


SCHEMA_VERSION = "sapote-mamey.codex-figure-set-render.tranche4.v1"
IMPLEMENTED_IDS_4 = (
    "FS057", "FS058", "FS059", "FS060", "FS061", "FS062", "FS063",
    "FS065", "FS066", "FS067", "FS068", "FS069", "FS070", "FS071",
)


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _top(counter: Counter[str], n: int) -> list[str]:
    return [key for key, _value in sorted(counter.items(), key=lambda item: (-item[1], item[0].lower()))[:n]]


def _family_charts(
    group: str,
    ids: Sequence[str],
    title_root: str,
    rows: Sequence[dict[str, str]],
    all_rows: Sequence[dict[str, str]],
    bgcs: Sequence[dict[str, str]],
    memberships: Sequence[dict[str, str]],
    strains: dict[str, Any],
    governed: Sequence[str],
) -> list[Chart]:
    del group
    governed_set = set(governed)
    counts = Counter(row["feature_family"] for row in rows)
    families = _top(counts, 12)
    charts: list[Chart] = []
    charts.append(Chart(ids[0], "bar", f"{title_root} — governed cohort overview",
                        "Nonexclusive annotation-token families on deduplicated physical CDS; counts are capacity evidence, not validated biochemical function", [{"feature_family": family, "physical_genes": counts[family]} for family in families],
                        {"category": "feature_family", "value": "physical_genes", "x_label": "Physical CDS with annotation-token family"}))

    strain_rows = []
    for sid in governed:
        subset = [row for row in rows if row["strain"] == sid]
        strain_rows.append({"strain": sid, "feature_genes": len({row["physical_key"] for row in subset}), "distinct_feature_families": len({row["feature_family"] for row in subset}), "host": _host(strains[sid])})
    charts.append(Chart(ids[1], "scatter", f"{title_root} — every governed strain",
                        "Every governed strain is labelled; all annotation-token families remain visible without outlier filtering", strain_rows,
                        {"x": "feature_genes", "y": "distinct_feature_families", "label": "strain", "x_label": "Physical CDS with feature token", "y_label": "Distinct feature-token families", "x_min": 0, "y_min": 0}))

    class_counts = Counter(row["product_class"] for row in memberships)
    top_classes = _top(class_counts, 15)
    class_map: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in memberships: class_map[(row["strain"], row["bgc_id"])].add(row["product_class"])
    class_feature_counts: Counter[tuple[str, str]] = Counter()
    for row in rows:
        for cls in class_map.get((row["strain"], row["bgc_id"]), set()):
            class_feature_counts[(cls, row["feature_family"])] += 1
    class_rows = [{"class": cls, "feature_family": family, "genes_per_100_memberships": 100 * class_feature_counts[(cls, family)] / class_counts[cls] if class_counts[cls] else 0} for cls in top_classes for family in families]
    charts.append(Chart(ids[2], "heatmap", f"{title_root} by BGC class",
                        "Feature-token rows are normalized per 100 nonexclusive BGC-class memberships", class_rows,
                        {"row": "class", "column": "feature_family", "value": "genes_per_100_memberships", "legend": "Feature-token genes per 100 BGC-class memberships"}))

    boundary_bgc_counts = Counter(row["boundary"] for row in bgcs)
    boundary_feature_counts = Counter((row["boundary"], row["feature_family"]) for row in rows)
    boundary_rows = [{"boundary": boundary, "feature_family": family, "genes_per_100_bgcs": 100 * boundary_feature_counts[(boundary, family)] / boundary_bgc_counts[boundary] if boundary_bgc_counts[boundary] else 0} for boundary in ("Edge", "Full-contig", "Interior") for family in families]
    charts.append(Chart(ids[3], "heatmap", f"{title_root} by BGC boundary context",
                        "Feature-token rows are normalized per 100 physical BGC rows within each declared boundary state", boundary_rows,
                        {"row": "boundary", "column": "feature_family", "value": "genes_per_100_bgcs", "legend": "Feature-token genes per 100 physical BGCs"}))

    host_strain_counts = Counter(_host(strains[sid]) for sid in governed)
    host_feature_counts = Counter((row["host_group"], row["feature_family"]) for row in rows)
    host_rows = [{"host": host, "feature_family": family, "genes_per_strain": host_feature_counts[(host, family)] / host_strain_counts[host] if host_strain_counts[host] else 0} for host in HOST_ORDER for family in families]
    charts.append(Chart(ids[4], "heatmap", f"{title_root} by host cohort",
                        "Feature-token burden is normalized per governed strain; no host causality is inferred", host_rows,
                        {"row": "host", "column": "feature_family", "value": "genes_per_strain", "legend": "Feature-token genes per governed strain"}))

    availability = []
    present = {(row["strain"], row["feature_family"]) for row in rows}
    source_present = {row["strain"] for row in bgcs}
    for sid in governed:
        for family in families:
            state = "POPULATED" if (sid, family) in present else ("OBSERVED_ZERO" if sid in source_present else "MISSING")
            availability.append({"strain": sid, "feature_family": family, "state": state, "value": {"MISSING": -1, "OBSERVED_ZERO": 0, "POPULATED": 1}[state]})
    charts.append(Chart(ids[5], "state_heatmap", f"{title_root} evidence availability",
                        "Present CDS members distinguish observed-zero feature families from missing source evidence", availability,
                        {"row": "strain", "column": "feature_family", "value": "value", "state": "state"}))

    all_counts = Counter(row["feature_family"] for row in all_rows)
    charts.append(Chart(ids[6], "paired_dot", f"{title_root} — governance sensitivity",
                        "Governed and all-packaged annotation-token rows are paired by feature family", [{"feature_family": family, "governed": counts[family], "all_packaged": all_counts[family]} for family in _top(all_counts, 12)],
                        {"category": "feature_family", "a": "governed", "b": "all_packaged", "a_label": "Governed", "b_label": "All packaged", "x_label": "Physical CDS with annotation-token family"}))
    return charts


def build_charts_4(payload: dict[str, Any], all_ids: Sequence[str], governed: Sequence[str], bundle: Path) -> list[Chart]:
    strains = payload["strains"]; governed_set, all_set = set(governed), set(all_ids)
    features = _read(bundle / "BGC_GENE_FEATURE_TOKENS.csv")
    bgcs_all = _read(bundle / "BGC_RECORDS.csv")
    memberships_all = _read(bundle / "BGC_CLASS_MEMBERSHIPS.csv")
    bgcs = [row for row in bgcs_all if row["strain"] in governed_set]
    memberships = [row for row in memberships_all if row["strain"] in governed_set]
    tailoring_all = [row for row in features if row["strain"] in all_set and row["feature_group"] == "TAILORING_LIKE"]
    regulator_all = [row for row in features if row["strain"] in all_set and row["feature_group"] == "REGULATOR_LIKE"]
    charts = _family_charts("TAILORING_LIKE", IMPLEMENTED_IDS_4[:7], "Tailoring-like annotation burden", [row for row in tailoring_all if row["strain"] in governed_set], tailoring_all, bgcs, memberships, strains, governed)
    charts.extend(_family_charts("REGULATOR_LIKE", IMPLEMENTED_IDS_4[7:], "Regulator-like annotation burden", [row for row in regulator_all if row["strain"] in governed_set], regulator_all, bgcs, memberships, strains, governed))
    assert tuple(chart.figure_id for chart in charts) == IMPLEMENTED_IDS_4
    return charts


def render_tranche_4(widget_data: str | Path, source_bundle: str | Path, outdir: str | Path) -> dict[str, Any]:
    widget_path, payload, all_ids, governed = _load(widget_data)
    bundle = Path(source_bundle).resolve(); source_receipt = bundle / "SOURCE_BUNDLE_RECEIPT.json"
    if not source_receipt.is_file(): raise ValueError("source bundle has no SOURCE_BUNDLE_RECEIPT.json")
    destination = Path(outdir).resolve(); destination.mkdir(parents=True, exist_ok=True)
    figures_dir, data_dir, text_dir = destination / "figures", destination / "data", destination / "text"
    for directory in (figures_dir, data_dir, text_dir): directory.mkdir(parents=True, exist_ok=True)
    registry = {record["figure_set_id"]: record for record in build_registry()}
    charts = build_charts_4(payload, all_ids, governed, bundle); manifest = []
    for chart in charts:
        svg_path, csv_path, text_path = figures_dir / f"{chart.figure_id}.svg", data_dir / f"{chart.figure_id}_data.csv", text_dir / f"{chart.figure_id}_CAPTION_METHODS.md"
        svg_path.write_text(render_svg(chart), encoding="utf-8"); _write_rows(csv_path, chart.rows); spec = registry[chart.figure_id]
        text_path.write_text(f"# {chart.figure_id} — {chart.title}\n\n## Caption\n\n{spec['caption_template']}\n\n## Methods\n\n{spec['methods_template']}\n\n## Render-specific note\n\n{chart.subtitle}\n\nAnnotation-token matches are nonexclusive capacity evidence and do not validate enzymatic function, pathway completion, metabolite identity, expression, production, activity, novelty, or physical linkage.\n\n## Citation status\n\nCitations must be reviewed against the source release and upstream evidence channels at manuscript freeze.\n", encoding="utf-8")
        manifest.append({"figure_set_id": chart.figure_id, "title": chart.title, "kind": chart.kind, "rows": len(chart.rows), "svg": str(svg_path.relative_to(destination)), "data_csv": str(csv_path.relative_to(destination)), "caption_methods": str(text_path.relative_to(destination)), "svg_sha256": _sha256(svg_path), "data_sha256": _sha256(csv_path), "text_sha256": _sha256(text_path)})
    cards = "".join(f'<article><h2>{html.escape(item["figure_set_id"])} — {html.escape(item["title"])}</h2><img src="{html.escape(item["svg"])}" alt="{html.escape(item["title"])}"><p><a href="{html.escape(item["data_csv"])}">Plotted data</a> · <a href="{html.escape(item["caption_methods"])}">Caption and methods</a></p></article>' for item in manifest)
    index = destination / "OPEN_FIGURE_SET_TRANCHE_4.html"
    index.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Codex Figure Factory tranche 4</title><style>body{font:15px/1.45 system-ui;margin:0;background:#f4f6f8;color:#17212b}header,main{max-width:1500px;margin:auto;padding:22px}article{background:white;border:1px solid #d8dee5;border-radius:8px;padding:14px;margin:0 0 20px}img{max-width:100%;height:auto}h1{margin-bottom:4px}h2{font-size:18px}a{color:#31688e}</style></head><body><header>' + f'<h1>Codex Figure Factory tranche 4</h1><p>14 tailoring-like and regulator-like annotation-burden sets. {html.escape(GLOBAL_CLAIM_CEILING)}</p></header><main>{cards}</main></body></html>', encoding="utf-8")
    checks = _validate_outputs(destination, manifest, governed, IMPLEMENTED_IDS_4, ("FS058", "FS066"))
    receipt = {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL", "profile": PROFILE, "source": {"widget_data": str(widget_path), "widget_sha256": _sha256(widget_path), "source_bundle": str(bundle), "source_bundle_receipt_sha256": _sha256(source_receipt)}, "governed_strains": len(governed), "all_packaged_strains": len(all_ids), "implemented_count": len(manifest), "implemented_ids": list(IMPLEMENTED_IDS_4), "claim_ceiling": GLOBAL_CLAIM_CEILING, "machine_checks": checks, "figures": manifest, "index": {"path": index.name, "sha256": _sha256(index)}}
    (destination / "TRANCHE_4_QA_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (destination / "FIGURE_MANIFEST.json").write_text(json.dumps({"schema_version": SCHEMA_VERSION, "figures": manifest}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--widget-data", required=True); parser.add_argument("--source-bundle", required=True); parser.add_argument("--outdir", required=True)
    args = parser.parse_args(); result = render_tranche_4(args.widget_data, args.source_bundle, args.outdir); emit(json.dumps(result, indent=2)); raise SystemExit(0 if result["status"] == "PASS" else 1)
