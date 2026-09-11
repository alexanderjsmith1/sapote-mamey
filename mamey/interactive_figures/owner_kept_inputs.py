#!/usr/bin/env python3
"""Build current-data inputs for owner-kept Figure Factory designs.

This adapter does not render figures.  It projects the governed, hash-verified
``figure_source_bundle`` into the four tidy tables used by the retained legacy
designs and records whether each retained figure has enough source/context data
to be rebuilt.  External benchmarks remain default-off and never enter study
denominators.
"""

from __future__ import annotations

import csv
try:
    from ..csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import io
import json
import os
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from .figure_set_renderer import _load_with_benchmarks


SCHEMA_VERSION = "sapote-mamey.owner-kept-figure-inputs.v1"
REQUIRED_SOURCE_TABLES = (
    "BGC_CLASS_MEMBERSHIPS.csv",
    "BGC_RECORDS.csv",
    "STRAIN_CONTEXT.csv",
    "DOMAIN_CATEGORY_COUNTS.csv",
    "CASSETTE_FAMILY_COUNTS.csv",
    "RESISTANCE_FAMILY_COUNTS.csv",
    "BGC_EXTENDED_EVIDENCE.csv",
    "MANIFEST_SOURCE_SCAN_COUNTS.csv",
)
FIGURE_REQUIREMENTS = {
    "F03a": ("domain",),
    "F03b": ("domain", "genus"),
    "F03c": ("domain", "genus"),
    "F04f": ("class", "genus"),
    "F04g": ("class", "genus"),
    "F05a": ("cassette",),
    "F06d": ("resistance", "genus"),
    "F09a": ("class", "genus"),
    "F09e": ("bgc_density", "genus"),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def _csv_text(fields: Sequence[str], rows: Sequence[dict[str, Any]]) -> str:
    stream = io.StringIO(newline="")
    writer = _SafeDictWriter(stream, fieldnames=list(fields), extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def _write_text(path: Path, text: str) -> None:
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)


def _truth(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _source_outputs(receipt: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("path")): row for row in receipt.get("outputs") or []}


def build_owner_kept_inputs(
    widget_data: str | Path,
    source_bundle: str | Path,
    outdir: str | Path,
    *,
    external_benchmark_ids: Sequence[str] = (),
) -> dict[str, Any]:
    widget_path, payload, selected_ids, study_ids, benchmarks, selected_benchmarks = _load_with_benchmarks(
        widget_data, external_benchmark_ids
    )
    bundle = Path(source_bundle).resolve()
    destination = Path(outdir).resolve()
    if destination.exists():
        raise ValueError("FIGURE_INPUT_OUTPUT_EXISTS: choose a new output directory")
    receipt_path = bundle / "SOURCE_BUNDLE_RECEIPT.json"
    if not receipt_path.is_file():
        raise ValueError("FIGURE_INPUT_SOURCE_RECEIPT_MISSING")
    source_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if source_receipt.get("status") not in {"PASS", "PASS_WITH_ISSUES"}:
        raise ValueError("FIGURE_INPUT_SOURCE_BUNDLE_NOT_USABLE")
    source_widget_sha = str((source_receipt.get("source") or {}).get("widget_sha256") or "")
    if source_widget_sha != _sha256(widget_path):
        raise ValueError("FIGURE_INPUT_WIDGET_BINDING_MISMATCH")
    bound_outputs = _source_outputs(source_receipt)
    for name in REQUIRED_SOURCE_TABLES:
        path = bundle / name
        record = bound_outputs.get(name)
        if not path.is_file() or not record or record.get("sha256") != _sha256(path):
            raise ValueError(f"FIGURE_INPUT_SOURCE_TABLE_BINDING_FAILED: {name}")

    selected = set(selected_ids)
    study = set(study_ids)
    context_rows = [row for row in _read_csv(bundle / "STRAIN_CONTEXT.csv") if row.get("strain") in selected]
    context = {row["strain"]: row for row in context_rows}
    if set(selected_ids) != set(context):
        raise ValueError("FIGURE_INPUT_CONTEXT_KEYSET_MISMATCH")

    domain_rows = [row for row in _read_csv(bundle / "DOMAIN_CATEGORY_COUNTS.csv") if row.get("strain") in selected]
    cassette_rows = [row for row in _read_csv(bundle / "CASSETTE_FAMILY_COUNTS.csv") if row.get("strain") in selected]
    resistance_rows = [row for row in _read_csv(bundle / "RESISTANCE_FAMILY_COUNTS.csv") if row.get("strain") in selected]
    extended_rows = [row for row in _read_csv(bundle / "BGC_EXTENDED_EVIDENCE.csv") if row.get("strain") in selected]
    scan_rows = [row for row in _read_csv(bundle / "MANIFEST_SOURCE_SCAN_COUNTS.csv") if row.get("strain") in selected]
    membership_rows = [row for row in _read_csv(bundle / "BGC_CLASS_MEMBERSHIPS.csv") if row.get("strain") in selected]
    bgc_rows = [row for row in _read_csv(bundle / "BGC_RECORDS.csv") if row.get("strain") in selected]

    class_counts = Counter((row["strain"], row["product_class"]) for row in membership_rows)
    adapted = {
        "domain_counts.csv": (
            ["strain", "domain_category", "count"],
            [{"strain": row["strain"], "domain_category": row["domain_category"], "count": row["count"]}
             for row in domain_rows],
        ),
        "class_by_strain.csv": (
            ["strain", "product_class", "n_bgcs"],
            [{"strain": strain, "product_class": product, "n_bgcs": count}
             for (strain, product), count in sorted(class_counts.items())],
        ),
        "cassette_types.csv": (
            ["strain", "cassette_type", "count"],
            [{"strain": row["strain"], "cassette_type": row["cassette_family"], "count": row["count"]}
             for row in cassette_rows],
        ),
        "resistance_families.csv": (
            ["strain", "family", "count"],
            [{"strain": row["strain"], "family": row["resistance_family"], "count": row["count"]}
             for row in resistance_rows],
        ),
        "strain_context.csv": (
            ["strain", "governance", "host_group", "cohort_role", "include_by_default", "study_denominator",
             "taxonomy", "genus", "genome_bp", "corrected_bgcs", "assembly_tier", "snapshot_state",
             "antismash_version", "antismash_version_source"],
            [{**row, "study_denominator": row["strain"] in study} for row in context_rows],
        ),
    }
    adapted["a8_boundary_inventory.csv"] = (
        ["strain", "node_or_contig", "region", "bgc_id", "complete_identity", "boundary"],
        [{key: row.get(key, "") for key in ("strain", "node_or_contig", "region", "bgc_id", "complete_identity", "boundary")}
         for row in bgc_rows],
    )
    adapted["a8_architecture_features.csv"] = (
        ["strain", "node_or_contig", "region", "bgc_id", "complete_identity", "arch", "arch_capacity", "class_conf", "products"],
        [{key: row.get(key, "") for key in ("strain", "node_or_contig", "region", "bgc_id", "complete_identity", "arch", "arch_capacity", "class_conf", "products")}
         for row in extended_rows],
    )
    adapted["a8_manifest_scan_counts.csv"] = (
        ["strain", "scan", "token", "hit_count", "value_state", "source_state", "source_field"],
        [{key: row.get(key, "") for key in ("strain", "scan", "token", "hit_count", "value_state", "source_state", "source_field")}
         for row in scan_rows],
    )
    adapted["a8_resistance_routing.csv"] = (
        ["strain", "node_or_contig", "region", "bgc_id", "complete_identity", "resistance_tier"],
        [{key: row.get(key, "") for key in ("strain", "node_or_contig", "region", "bgc_id", "complete_identity", "resistance_tier")}
         for row in extended_rows],
    )
    a9_rows = []
    for row in bgc_rows:
        if row.get("strain") not in study:
            continue
        ctx = context.get(row["strain"], {})
        a9_rows.append({
            **{key: row.get(key, "") for key in (
                "strain", "node_or_contig", "region", "bgc_id", "complete_identity",
                "kcb_top", "kcb_score", "needs_manual_kcb_check", "parse_confidence",
                "closest_product_provenance", "denominator_type",
            )},
            "antismash_version": ctx.get("antismash_version", ""),
            "antismash_version_source": ctx.get("antismash_version_source", ""),
        })
    adapted["a9_kcb_scores.csv"] = (
        ["strain", "node_or_contig", "region", "bgc_id", "complete_identity", "kcb_top", "kcb_score",
         "needs_manual_kcb_check", "parse_confidence", "closest_product_provenance", "denominator_type",
         "antismash_version", "antismash_version_source"],
        a9_rows,
    )

    genus_rows = []
    for genus in sorted({row.get("genus") or "" for row in context_rows if row.get("genus")}):
        ids = sorted(row["strain"] for row in context_rows if row.get("genus") == genus)
        genus_rows.append({
            "genus": genus,
            "selected_records": len(ids),
            "study_denominator_records": sum(sid in study for sid in ids),
            "external_benchmark_records": sum(sid in selected_benchmarks for sid in ids),
            "default_plot_state": "INCLUDE" if any(sid in study for sid in ids) else "COMPARATOR_ONLY",
            "owner_override": "AVAILABLE",
        })
    adapted["genus_selection.tsv"] = (
        ["genus", "selected_records", "study_denominator_records", "external_benchmark_records", "default_plot_state", "owner_override"],
        genus_rows,
    )

    counts_by_kind = {
        "domain": len(domain_rows),
        "class": len(class_counts),
        "cassette": len(cassette_rows),
        "resistance": len(resistance_rows),
        "bgc_density": len(bgc_rows),
    }
    missing_genus = sorted(sid for sid in study if not (context.get(sid) or {}).get("genus"))
    missing_density = sorted(
        sid for sid in study
        if not (context.get(sid) or {}).get("genome_bp") or not (context.get(sid) or {}).get("corrected_bgcs")
    )
    readiness_rows = []
    for figure_id, requirements in FIGURE_REQUIREMENTS.items():
        holds = []
        for requirement in requirements:
            if requirement == "genus" and missing_genus:
                holds.append("MISSING_STUDY_GENUS")
            elif requirement == "bgc_density" and missing_density:
                holds.append("MISSING_STUDY_DENSITY_INPUT")
            elif requirement in counts_by_kind and counts_by_kind[requirement] == 0:
                holds.append(f"NO_{requirement.upper()}_ROWS")
        readiness_rows.append({
            "figure_id": figure_id,
            "requirements": ";".join(requirements),
            "status": "REBUILD_READY" if not holds else "HOLD",
            "holds": ";".join(holds),
            "study_denominator": len(study),
            "selected_external_benchmarks": len(selected_benchmarks),
        })
    adapted["FIGURE_REBUILD_READINESS.tsv"] = (
        ["figure_id", "requirements", "status", "holds", "study_denominator", "selected_external_benchmarks"],
        readiness_rows,
    )

    missing_identity = sum(not row.get("complete_identity") for row in extended_rows)
    a8_readiness = []
    for figure_id, requirements, available in (
        ("Q008_BW01", "Boundary;governed cohort;complete identity", bool(bgc_rows)),
        ("Q013_F14", "Arch;Arch_Capacity;Class_Conf;Products;complete identity", bool(extended_rows)),
        ("Q015_G01", "manifest cctt hits;all admitted BGC rows", any(r.get("scan") == "cctt" for r in scan_rows)),
        ("Q017_SCI01A", "Products;scope ruling", bool(extended_rows)),
        ("Q019_SCI01C_F10R", "transporters hits;regulators hits;Resistance_tier", bool(extended_rows) and any(r.get("scan") in {"transporters", "regulators"} for r in scan_rows)),
    ):
        holds = []
        if not available:
            holds.append("SOURCE_ROWS_MISSING")
        if figure_id in {"Q008_BW01", "Q013_F14", "Q017_SCI01A", "Q019_SCI01C_F10R"} and missing_identity:
            holds.append("COMPLETE_BGC_IDENTITY_MISSING")
        if figure_id == "Q017_SCI01A":
            holds.append("SCOPE_1_VS_RENDER_CONTRADICTION")
        a8_readiness.append({
            "figure_id": figure_id, "binding_state": "PROVISIONAL_BINDING",
            "status": "PROVISIONAL_READY" if not holds else "HOLD", "requirements": requirements,
            "holds": ";".join(holds), "study_denominator": len(study),
        })
    adapted["A8_PROVISIONAL_READINESS.tsv"] = (
        ["figure_id", "binding_state", "status", "requirements", "holds", "study_denominator"],
        a8_readiness,
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.stage-", dir=destination.parent))
    outputs = []
    try:
        for name, (fields, rows) in adapted.items():
            path = stage / name
            _write_text(path, _csv_text(fields, rows))
            outputs.append({"path": name, "rows": len(rows), "bytes": path.stat().st_size, "sha256": _sha256(path)})
        result = {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS" if all(row["status"] == "REBUILD_READY" for row in readiness_rows) else "PASS_WITH_HOLDS",
            "source": {
                "widget_data": widget_path.name,
                "widget_sha256": _sha256(widget_path),
                "source_bundle_receipt_sha256": _sha256(receipt_path),
            },
            "study_denominator": len(study),
            "selected_records": len(selected_ids),
            "external_benchmarks": {
                "available": benchmarks,
                "selected": selected_benchmarks,
                "default_off": True,
                "enter_study_denominator": False,
            },
            "figures": readiness_rows,
            "a8_figures": a8_readiness,
            "outputs": outputs,
        }
        _write_text(stage / "FIGURE_INPUT_RECEIPT.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
        os.replace(stage, destination)
        return result
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
