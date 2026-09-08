#!/usr/bin/env python3
"""Render 25 ledger-gated lead-context figure sets (tranche 6)."""

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
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

from .figure_set_registry import GLOBAL_CLAIM_CEILING, PROFILE, build_registry
from .figure_set_renderer import Chart, _load, _sha256, _validate_outputs, _write_rows, build_charts, render_svg
from .figure_set_renderer_tranche2 import build_charts_2
from .figure_set_renderer_tranche3 import build_charts_3
from .figure_set_renderer_tranche4 import build_charts_4
from .figure_set_renderer_tranche5 import build_charts_5


SCHEMA_VERSION = "sapote-mamey.codex-figure-set-render.tranche6.v1"
SOURCE_TO_LEAD = (
    ("BND", "FS002", "FS008"), ("CLS", "FS010", "FS016"), ("COC", "FS018", "FS024"),
    ("LEN", "FS026", "FS032"), ("CDS", "FS034", "FS040"), ("MLN", "FS042", "FS048"),
    ("MRB", "FS050", "FS056"), ("TAL", "FS058", "FS064"), ("REG", "FS066", "FS072"),
    ("RES", "FS074", "FS080"), ("TRN", "FS082", "FS088"), ("TTA", "FS090", "FS096"),
    ("MPG", "FS098", "FS104"), ("KCB", "FS106", "FS112"), ("MOD", "FS114", "FS120"),
    ("SUB", "FS122", "FS128"), ("DOM", "FS130", "FS136"), ("ACT", "FS138", "FS144"),
    ("CCT", "FS146", "FS152"), ("MIS", "FS154", "FS160"), ("PRI", "FS162", "FS168"),
    ("NOV", "FS170", "FS176"), ("RGG", "FS178", "FS184"), ("HST", "FS186", "FS192"),
    ("EVD", "FS194", "FS200"),
)
IMPLEMENTED_IDS_6 = tuple(lead_id for _family, _source_id, lead_id in SOURCE_TO_LEAD)


def _read_lead_ledger(path: str | Path, governed: Sequence[str]) -> tuple[Path, list[dict[str, str]], dict[str, list[str]]]:
    ledger_path = Path(path).resolve()
    with ledger_path.open(newline="", encoding="utf-8-sig") as stream:
        lines = [ln for ln in stream if not ln.lstrip().startswith("#")]  # skip mamey provenance lines
    rows = list(csv.DictReader(lines))
    if not rows or "strain" not in (rows[0].keys() if rows else ()):
        raise ValueError("lead ledger must contain at least one row and a strain column")
    included = []
    by_strain: dict[str, list[str]] = defaultdict(list)
    governed_set = set(governed)
    for index, row in enumerate(rows, 2):
        state = (row.get("include_state") or row.get("state") or "INCLUDED").strip().upper()
        if state not in {"INCLUDED", "LEAD", "YES"}:
            continue
        strain = (row.get("strain") or "").strip()
        if not strain:
            raise ValueError(f"lead ledger row {index} has no strain")
        if strain not in governed_set:
            raise ValueError(f"lead ledger strain is outside the governed denominator: {strain}")
        bgc_id = (row.get("bgc_id") or "").strip()
        by_strain[strain].append(bgc_id or "STRAIN_LEVEL")
        included.append(row)
    if not by_strain:
        raise ValueError("lead ledger has no INCLUDED/LEAD/YES rows")
    return ledger_path, included, by_strain


def build_charts_6(payload: dict[str, Any], all_ids: Sequence[str], governed: Sequence[str], bundle: Path, leads: dict[str, list[str]]) -> list[Chart]:
    source_charts = []
    source_charts.extend(build_charts(payload, all_ids, governed))
    source_charts.extend(build_charts_2(payload, all_ids, governed, bundle))
    source_charts.extend(build_charts_3(payload, all_ids, governed, bundle))
    source_charts.extend(build_charts_4(payload, all_ids, governed, bundle))
    source_charts.extend(build_charts_5(payload, governed, bundle))
    lookup = {chart.figure_id: chart for chart in source_charts}
    charts = []
    for family, source_id, lead_id in SOURCE_TO_LEAD:
        source = lookup.get(source_id)
        if source is None or source.kind != "scatter":
            raise ValueError(f"lead-context source {source_id} is unavailable or not a scatter")
        rows = []
        for row in source.rows:
            strain = str(row.get(source.config["label"]) or "")
            rows.append({
                **row,
                "lead_context": "YES" if strain in leads else "NO",
                "declared_lead_scope": "; ".join(leads.get(strain, [])),
            })
        charts.append(Chart(
            lead_id, "scatter", f"{source.title} — lead context",
            "The full governed denominator is retained. Only ledger-declared leads are ringed and bold; all peers remain labelled adjacent to their nodes. Lead status is contextual prioritization, not an outlier requirement or biological validation.",
            rows, {**source.config, "highlight": "lead_context", "family": family, "source_figure_id": source_id},
        ))
    if tuple(chart.figure_id for chart in charts) != IMPLEMENTED_IDS_6:
        raise AssertionError("tranche 6 figure order does not match registry IDs")
    return charts


def render_tranche_6(widget_data: str | Path, source_bundle: str | Path, lead_ledger: str | Path, outdir: str | Path) -> dict[str, Any]:
    widget_path, payload, all_ids, governed = _load(widget_data)
    bundle = Path(source_bundle).resolve(); source_receipt = bundle / "SOURCE_BUNDLE_RECEIPT.json"
    if not source_receipt.is_file(): raise ValueError("source bundle has no SOURCE_BUNDLE_RECEIPT.json")
    ledger_path, ledger_rows, leads = _read_lead_ledger(lead_ledger, governed)
    destination = Path(outdir).resolve(); destination.mkdir(parents=True, exist_ok=True)
    figures_dir, data_dir, text_dir = destination / "figures", destination / "data", destination / "text"
    for directory in (figures_dir, data_dir, text_dir): directory.mkdir(parents=True, exist_ok=True)
    registry = {record["figure_set_id"]: record for record in build_registry()}
    charts = build_charts_6(payload, all_ids, governed, bundle, leads)
    manifest = []
    for chart in charts:
        svg_path = figures_dir / f"{chart.figure_id}.svg"; csv_path = data_dir / f"{chart.figure_id}_data.csv"; text_path = text_dir / f"{chart.figure_id}_CAPTION_METHODS.md"
        svg_path.write_text(render_svg(chart), encoding="utf-8"); _write_rows(csv_path, chart.rows)
        spec = registry[chart.figure_id]
        text_path.write_text(
            f"# {chart.figure_id} — {chart.title}\n\n## Caption\n\n{spec['caption_template']}\n\n"
            f"## Methods\n\n{spec['methods_template']}\n\n## Lead-ledger method\n\n{chart.subtitle}\n\n"
            f"Ledger SHA-256: `{_sha256(ledger_path)}`. Declared lead strains: {', '.join(sorted(leads))}. "
            "BGC-specific entries, where supplied, are retained in the plotted-data sidecar; strain-level highlighting does not elevate every BGC in that strain.\n\n"
            f"## Claim ceiling\n\n{GLOBAL_CLAIM_CEILING}\n\n## Citation status\n\n"
            "Citations and lead-ledger provenance must be reviewed at manuscript freeze.\n",
            encoding="utf-8",
        )
        manifest.append({"figure_set_id": chart.figure_id, "title": chart.title, "kind": chart.kind, "rows": len(chart.rows), "svg": str(svg_path.relative_to(destination)), "data_csv": str(csv_path.relative_to(destination)), "caption_methods": str(text_path.relative_to(destination)), "svg_sha256": _sha256(svg_path), "data_sha256": _sha256(csv_path), "text_sha256": _sha256(text_path)})
    cards = "".join(f'<article><h2>{html.escape(item["figure_set_id"])} — {html.escape(item["title"])}</h2><img src="{html.escape(item["svg"])}" alt="{html.escape(item["title"])}"><p><a href="{html.escape(item["data_csv"])}">Plotted data</a> · <a href="{html.escape(item["caption_methods"])}">Caption and methods</a></p></article>' for item in manifest)
    index = destination / "OPEN_FIGURE_SET_TRANCHE_6.html"
    index.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Codex Figure Factory tranche 6</title><style>body{font:15px/1.45 system-ui;margin:0;background:#f4f6f8;color:#17212b}header,main{max-width:1500px;margin:auto;padding:22px}article{background:white;border:1px solid #d8dee5;border-radius:8px;padding:14px;margin:0 0 20px}img{max-width:100%;height:auto}h2{font-size:18px}a{color:#31688e}</style></head><body><header>' + f'<h1>Codex Figure Factory tranche 6</h1><p>25 private-review, ledger-gated lead-context sets. {html.escape(GLOBAL_CLAIM_CEILING)}</p></header><main>{cards}</main></body></html>', encoding="utf-8")
    checks = _validate_outputs(destination, manifest, governed, IMPLEMENTED_IDS_6, IMPLEMENTED_IDS_6)
    highlighted_failures = []
    for figure in manifest:
        svg_text = (destination / figure["svg"]).read_text(encoding="utf-8")
        if "Ledger-declared lead context" not in svg_text or not all(strain in svg_text for strain in leads): highlighted_failures.append(figure["figure_set_id"])
    checks.append({"check_id": "LEAD_CONTEXT_RENDERED", "status": "PASS" if not highlighted_failures else "FAIL", "detail": "failures=" + (",".join(highlighted_failures) or "none")})
    receipt = {
        "schema_version": SCHEMA_VERSION, "status": "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL",
        "profile": PROFILE, "release_scope": "PRIVATE_REVIEW", "governed_strains": len(governed), "all_packaged_strains": len(all_ids),
        "implemented_count": len(manifest), "implemented_ids": list(IMPLEMENTED_IDS_6),
        "source": {"widget_data": str(widget_path), "widget_sha256": _sha256(widget_path), "source_bundle": str(bundle), "source_bundle_receipt_sha256": _sha256(source_receipt), "lead_ledger": str(ledger_path), "lead_ledger_sha256": _sha256(ledger_path)},
        "lead_strains": sorted(leads), "lead_ledger_rows": len(ledger_rows), "machine_checks": checks,
        "claim_ceiling": GLOBAL_CLAIM_CEILING, "figures": manifest, "index": {"path": index.name, "sha256": _sha256(index)},
    }
    (destination / "TRANCHE_6_QA_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (destination / "FIGURE_MANIFEST.json").write_text(json.dumps({"schema_version": SCHEMA_VERSION, "figures": manifest}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--widget-data", required=True); parser.add_argument("--source-bundle", required=True); parser.add_argument("--lead-ledger", required=True); parser.add_argument("--outdir", required=True)
    args = parser.parse_args(); result = render_tranche_6(args.widget_data, args.source_bundle, args.lead_ledger, args.outdir); emit(json.dumps(result, indent=2)); raise SystemExit(0 if result["status"] == "PASS" else 1)
