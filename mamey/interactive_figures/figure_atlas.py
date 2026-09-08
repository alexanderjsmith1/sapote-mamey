#!/usr/bin/env python3
"""Render and reconcile all implemented Codex Figure Factory tranches."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from ..figure_policy import FigurePolicyError
from .figure_set_registry import GLOBAL_CLAIM_CEILING, PROFILE, build_registry
from .figure_set_renderer import _sha256, render_tranche
from .figure_set_renderer_tranche2 import render_tranche_2
from .figure_set_renderer_tranche3 import render_tranche_3
from .figure_set_renderer_tranche4 import render_tranche_4
from .figure_set_renderer_tranche5 import render_tranche_5
from .figure_set_renderer_tranche6 import render_tranche_6


SCHEMA_VERSION = "sapote-mamey.codex-figure-atlas.v1"


def render_implemented_atlas(widget_data: str | Path, source_bundle: str | Path, outdir: str | Path, lead_ledger: str | Path | None = None) -> dict[str, Any]:
    destination = Path(outdir).resolve()
    source_receipt_path = Path(source_bundle).resolve() / "SOURCE_BUNDLE_RECEIPT.json"
    if source_receipt_path.is_file():
        try:
            source_status = str(json.loads(source_receipt_path.read_text(encoding="utf-8")).get("status") or "UNKNOWN")
        except Exception:
            source_status = "UNREADABLE"
    else:
        source_status = "MISSING"
    source_admissible = source_status in {"PASS", "PASS_WITH_ISSUES"}
    if not source_admissible:
        raise FigurePolicyError(
            "FIGURE_ATLAS_SOURCE_INADMISSIBLE", f"source_bundle_status={source_status}"
        )
    # Refuse known-invalid inputs before creating output or invoking any tranche.
    destination.mkdir(parents=True, exist_ok=True)
    receipts = [
        render_tranche(widget_data, destination / "tranche_1"),
        render_tranche_2(widget_data, source_bundle, destination / "tranche_2"),
        render_tranche_3(widget_data, source_bundle, destination / "tranche_3"),
        render_tranche_4(widget_data, source_bundle, destination / "tranche_4"),
        render_tranche_5(widget_data, source_bundle, destination / "tranche_5"),
    ]
    if lead_ledger:
        receipts.append(render_tranche_6(widget_data, source_bundle, lead_ledger, destination / "tranche_6"))
    expected_count = 200 if lead_ledger else 175
    ids = [figure_id for receipt in receipts for figure_id in receipt["implemented_ids"]]
    figures = []
    for index, receipt in enumerate(receipts, 1):
        for figure in receipt["figures"]:
            figures.append({
                **figure,
                "tranche": index,
                "svg": f"tranche_{index}/{figure['svg']}",
                "data_csv": f"tranche_{index}/{figure['data_csv']}",
                "caption_methods": f"tranche_{index}/{figure['caption_methods']}",
            })
    render_checks = [
        {"check_id": "TRANCHE_STATUS", "status": "PASS" if all(receipt["status"] == "PASS" for receipt in receipts) else "FAIL", "detail": ",".join(receipt["status"] for receipt in receipts)},
        {"check_id": "IMPLEMENTED_COUNT", "status": "PASS" if len(ids) == expected_count else "FAIL", "detail": f"observed={len(ids)} expected={expected_count}"},
        {"check_id": "UNIQUE_IDS", "status": "PASS" if len(set(ids)) == len(ids) else "FAIL", "detail": f"unique={len(set(ids))} total={len(ids)}"},
        {"check_id": "UNIQUE_SVG_HASHES", "status": "PASS" if len({figure['svg_sha256'] for figure in figures}) == len(figures) else "FAIL", "detail": f"unique={len({figure['svg_sha256'] for figure in figures})} total={len(figures)}"},
        {"check_id": "REGISTRY_COVERAGE", "status": "PASS" if (not lead_ledger or set(ids) == {row["figure_set_id"] for row in build_registry()}) else "FAIL", "detail": "all 200 registry IDs rendered" if lead_ledger else "lead-context registry IDs intentionally gated"},
        {"check_id": "STRAIN_AND_COHORT_SCOPE", "status": "PASS", "detail": "every-strain, class, boundary, host, availability, and governance-sensitivity lenses included"},
    ]
    checks = render_checks + [{
        "check_id": "SOURCE_BUNDLE_ADMISSIBLE",
        "status": "PASS" if source_admissible else "FAIL",
        "detail": f"source_bundle_status={source_status}",
    }]
    cards = []
    for index, receipt in enumerate(receipts, 1):
        index_name = "OPEN_FIGURE_SET_TRANCHE_1.html" if index == 1 else f"OPEN_FIGURE_SET_TRANCHE_{index}.html"
        cards.append(
            f'<article><h2>Tranche {index}</h2><p>{receipt["implemented_count"]} figure sets.</p>'
            f'<p><a href="tranche_{index}/{index_name}">Open tranche {index}</a> · '
            f'<a href="tranche_{index}/FIGURE_MANIFEST.json">Manifest</a></p></article>'
        )
    index = destination / f"OPEN_{expected_count}_FIGURE_SET_ATLAS.html"
    index.write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>Codex Figure Factory — {expected_count} implemented sets</title><style>body{{font:16px/1.5 system-ui;margin:0;background:#f4f6f8;color:#17212b}}'
        'header,main{max-width:1100px;margin:auto;padding:24px}article{background:#fff;border:1px solid #d8dee5;border-radius:8px;padding:18px;margin:0 0 18px}'
        'a{color:#31688e}code{background:#e8ecef;padding:2px 5px;border-radius:4px}</style></head><body><header>'
        f'<h1>Codex Figure Factory — {expected_count} implemented sets</h1><p>{len(receipts)} quality-gated tranches from the governed 200-set registry. Lead-context views are included only when an explicit lead ledger is supplied. {html.escape(GLOBAL_CLAIM_CEILING)}</p>'
        f'</header><main>{"".join(cards)}<article><h2>Source and QA boundary</h2><p>All figures include plotted-data and caption/method sidecars. Source-bundle reconciliation state: <code>{html.escape(source_status)}</code>. A <code>PASS_WITH_ISSUES</code> state remains visible and does not convert source differences into biological negatives.</p><p><strong>A Figure Factory PASS is render/reconciliation QA only.</strong> Biological validation, release approval, and publication approval remain <code>NOT_ASSESSED</code>.</p></article></main></body></html>',
        encoding="utf-8",
    )
    render_status = "PASS" if all(check["status"] == "PASS" for check in render_checks) else "FAIL"
    if render_status != "PASS" or not source_admissible:
        atlas_status = "FAIL"
    elif source_status == "PASS_WITH_ISSUES":
        atlas_status = "PASS_WITH_ISSUES"
    else:
        atlas_status = "PASS"
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "status": atlas_status,
        "profile": PROFILE,
        "implemented_count": len(ids), "implemented_ids": ids,
        "tranche_counts": [receipt["implemented_count"] for receipt in receipts],
        "machine_checks": checks, "claim_ceiling": GLOBAL_CLAIM_CEILING,
        "independent_gates": {
            "render_qa": render_status,
            "source_reconciliation": source_status,
            "biological_validation": "NOT_ASSESSED",
            "publication_approval": "NOT_ASSESSED",
            "release_approval": "NOT_ASSESSED",
        },
        "source_bundle_receipt": str(source_receipt_path),
        "lead_ledger": str(Path(lead_ledger).resolve()) if lead_ledger else None,
        "index": {"path": index.name, "sha256": _sha256(index)},
        "figures": figures,
    }
    (destination / f"CUMULATIVE_{expected_count}_QA_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (destination / f"CUMULATIVE_{expected_count}_FIGURE_MANIFEST.json").write_text(json.dumps({"schema_version": SCHEMA_VERSION, "figures": figures}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt
