"""Typed bioassay observations for Figure Factory.

The input is a canonical long-form table, not a raw plate export. Raw 96- and
384-well layouts vary, so a mapping/admission step must make controls,
exclusions, targets, time points, replicates, and material lineage explicit
before this module summarizes or renders anything.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

from .csv_safety import SafeDictWriter


SCHEMA = "sapote.bioassay-figure-factory.v1"
FIGURE_KIND = "bioassay_observation_summary_v1"
PLAN_SCHEMA = "sapote.bioassay-plan.v1"
PLAN_KIND = "bioassay_project_plan_v1"
FIELDS = (
    "observation_id", "strain_id", "experiment_id", "assay_plate_id", "plate_format",
    "well", "material_id", "material_type", "parent_material_id", "lineage_state",
    "material_amount_mg", "dose_state", "stock_concentration_mg_ml", "delivered_amount_ug",
    "final_concentration_ug_ml",
    "target_raw", "target_state", "target_canonical", "timepoint_hours", "replicate_id",
    "replicate_type", "inhibition_pct", "control_state", "inclusion_state",
    "exclusion_reason", "source_locator",
)
PLATE_FORMATS = {"96", "384", "OTHER"}
MATERIAL_TYPES = {"CRUDE_EXTRACT", "FLASH_FRACTION", "HPLC_FRACTION", "PURIFIED_COMPOUND", "OTHER"}
LINEAGE_STATES = {"VERIFIED", "PARTIAL", "UNRECORDED"}
DOSE_STATES = {"VERIFIED", "AS_RECORDED", "UNRECORDED"}
TARGET_STATES = {"VERIFIED", "AS_RECORDED", "AMBIGUOUS"}
REPLICATE_TYPES = {"SINGLETON", "TECHNICAL", "BIOLOGICAL", "UNSPECIFIED"}
CONTROL_STATES = {
    "VALID", "NOT_APPLICABLE", "POSITIVE_CONTROL_MISSING",
    "POSITIVE_CONTROL_LOCATION_UNRESOLVED", "EXPECTED_OD_NORMALIZATION_HOLD", "UNRECORDED",
}
INCLUSION_STATES = {"INCLUDE", "EXCLUDE", "HOLD"}
_LOCATOR = re.compile(r"^(?:[A-Za-z][A-Za-z0-9+.-]*://)?[A-Za-z0-9][A-Za-z0-9._/-]*$")


class BioassayFigureHold(ValueError):
    """A typed refusal before summarization or rendering."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_plan(config_path: Path) -> dict[str, object]:
    """Inventory heterogeneous assay inputs and emit a user-reviewable figure/analysis plan."""
    config_path = config_path.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != PLAN_SCHEMA or config.get("figure_kind") != PLAN_KIND:
        raise BioassayFigureHold(f"BIOASSAY_PLAN_CONFIG_HOLD: expected {PLAN_SCHEMA} / {PLAN_KIND}")
    root = Path(config.get("external_data_root", "")).expanduser().resolve()
    datasets = list(config.get("datasets", []))
    if not datasets:
        raise BioassayFigureHold("BIOASSAY_PLAN_EMPTY_HOLD: datasets are required")
    allowed_states = {"RAW_OD", "PRECOMPUTED_PERCENT_INHIBITION", "MIC_TABLE", "IN_VIVO", "OTHER"}
    allowed_scopes = {"CRUDE_EXTRACT", "FLASH_FRACTION", "HPLC_FRACTION", "PURIFIED_COMPOUND", "MIXED"}
    seen = set(); admitted = []
    for number, raw in enumerate(datasets, 1):
        row = dict(raw)
        dataset_id = str(row.get("dataset_id", "")).strip()
        if not dataset_id or dataset_id in seen:
            raise BioassayFigureHold(f"BIOASSAY_PLAN_DATASET_HOLD: row {number}: missing/duplicate dataset_id")
        seen.add(dataset_id)
        data_state = str(row.get("data_state", "")).strip()
        material_scope = str(row.get("material_scope", "")).strip()
        if data_state not in allowed_states or material_scope not in allowed_scopes:
            raise BioassayFigureHold(f"BIOASSAY_PLAN_DATASET_HOLD: row {number}: unsupported state/scope")
        locator = _portable_locator(str(row.get("logical_locator", "")), "input")
        source = (root / locator).resolve()
        try:
            source.relative_to(root)
        except ValueError as exc:
            raise BioassayFigureHold("BIOASSAY_PLAN_INPUT_LOCATOR_HOLD: input escapes root") from exc
        expected = str(row.get("sha256", "")).lower()
        if not source.is_file() or not re.fullmatch(r"[0-9a-f]{64}", expected) or sha256_file(source) != expected:
            raise BioassayFigureHold(f"BIOASSAY_PLAN_INPUT_HOLD: {dataset_id} missing or hash mismatch")
        admitted.append({
            "dataset_id": dataset_id, "data_state": data_state, "plate_format": str(row.get("plate_format", "")),
            "material_scope": material_scope, "targets": list(row.get("targets", [])),
            "timepoints_hours": list(row.get("timepoints_hours", [])),
            "final_concentrations_ug_ml": list(row.get("final_concentrations_ug_ml", [])),
            "replication": str(row.get("replication", "UNRECORDED")),
            "controls": str(row.get("controls", "UNRECORDED")),
            "material_amounts_available": bool(row.get("material_amounts_available", False)),
            "logical_locator": locator, "sha256": expected, "bytes": source.stat().st_size,
        })
    figures = []
    if any(row["data_state"] == "RAW_OD" for row in admitted):
        figures.append("control_and_normalization_QC_before_activity_figures")
    if any(row["material_scope"] in {"FLASH_FRACTION", "HPLC_FRACTION", "MIXED"} for row in admitted):
        figures += ["fraction_series_activity_map", "explicit_fraction_set_max_overview"]
    if any(row["material_amounts_available"] for row in admitted):
        figures.append("activity_breadth_and_material_yield")
    if any(len(row["final_concentrations_ug_ml"]) >= 3 for row in admitted):
        figures.append("dose_response_preview")
    if any(row["data_state"] == "MIC_TABLE" or row["material_scope"] == "PURIFIED_COMPOUND" for row in admitted):
        figures.append("MIC_or_pure_compound_endpoint")
    figures += ["target_specific_coverage_matrix", "selected_endpoint_phylogeny_overlay"]
    questions = [
        "Confirm which files contain raw OD values and which contain user-precomputed percent inhibition.",
        "For every precomputed table, record the formula, blank/control wells, and any omitted plates or wells.",
        "Resolve target labels that could refer to different organisms before species-specific pooling.",
        "Choose discovery views (fraction series, maximum within a named set, yield) separately from MIC views.",
        "Choose one target, time point, final concentration, material scope, and experiment roster for each tree track.",
        "Choose whether captions show individual experiments or an exact-group summary and name the replication level.",
    ]
    output = Path(config["output_dir"])
    if not output.is_absolute():
        output = (config_path.parent / output).resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".bioassay_project_plan.", dir=output.parent))
    try:
        plan = {
            "schema_version": PLAN_SCHEMA, "figure_kind": PLAN_KIND, "status": "PASS_REVIEW_REQUIRED",
            "project_label": str(config.get("project_label", "Bioassay project")),
            "datasets": admitted, "proposed_previews": list(dict.fromkeys(figures)),
            "user_review_questions": questions,
            "statistics_gate": (
                "Descriptive discovery summaries may proceed after admission. Inferential statistics require "
                "a separately declared comparable design, biological replicate unit, endpoint, exclusions, and model."
            ),
        }
        json_path = stage / "bioassay_project_plan.json"
        json_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        md_path = stage / "bioassay_project_plan.md"
        md = [f"# {plan['project_label']} — bioassay figure plan", "", "## Admitted datasets", "",
              "| Dataset | State | Plate | Material | Targets | Time points | Concentrations (ug/mL) | Replication | Controls |",
              "|---|---|---|---|---|---|---|---|---|"]
        for row in admitted:
            md.append(f"| {row['dataset_id']} | {row['data_state']} | {row['plate_format'] or 'unrecorded'} | "
                      f"{row['material_scope']} | {', '.join(map(str, row['targets'])) or 'unrecorded'} | "
                      f"{', '.join(map(str, row['timepoints_hours'])) or 'unrecorded'} | "
                      f"{', '.join(map(str, row['final_concentrations_ug_ml'])) or 'unrecorded'} | "
                      f"{row['replication']} | {row['controls']} |")
        md += ["", "## Proposed previews", ""] + [f"- `{item}`" for item in plan["proposed_previews"]]
        md += ["", "## Confirm with the user", ""] + [f"- {item}" for item in questions]
        md += ["", "## Statistics gate", "", str(plan["statistics_gate"]), ""]
        md_path.write_text("\n".join(md), encoding="utf-8")
        receipt = {
            "schema_version": PLAN_SCHEMA, "figure_kind": PLAN_KIND, "status": "PASS_REVIEW_REQUIRED",
            "outputs": [{"logical_locator": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size}
                        for path in (json_path, md_path)],
        }
        receipt_path = stage / "bioassay_project_plan_receipt.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        stage.replace(output)
        return receipt
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def _portable_locator(value: str, field: str) -> str:
    value = value.strip()
    if (not value or value.startswith(("/", "~", "\\")) or re.match(r"^[A-Za-z]:", value)
            or ".." in value.split("/") or not _LOCATOR.fullmatch(value)):
        raise BioassayFigureHold(f"BIOASSAY_{field.upper()}_LOCATOR_HOLD: {value!r}")
    return value


def _well_ok(well: str, plate_format: str) -> bool:
    match = re.fullmatch(r"([A-Za-z]+)0*([1-9][0-9]*)", well.strip())
    if not match:
        return False
    row, column = match.group(1).upper(), int(match.group(2))
    limits = {"96": ("H", 12), "384": ("P", 24)}
    if plate_format == "OTHER":
        return True
    last_row, last_column = limits[plate_format]
    return len(row) == 1 and "A" <= row <= last_row and column <= last_column


def _read(path: Path) -> list[dict[str, str]]:
    delimiter = "\t" if path.suffix.lower() in {".tsv", ".tab"} else ","
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if reader.fieldnames is None or tuple(reader.fieldnames) != FIELDS:
            raise BioassayFigureHold(
                "BIOASSAY_SCHEMA_HOLD: canonical columns and order are required; "
                f"expected={','.join(FIELDS)}"
            )
        return list(reader)


def validate_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    if not rows:
        raise BioassayFigureHold("BIOASSAY_EMPTY_HOLD: no observation rows")
    seen: set[str] = set()
    admitted: list[dict[str, object]] = []
    for line, raw in enumerate(rows, 2):
        row = {key: (raw.get(key) or "").strip() for key in FIELDS}
        oid = row["observation_id"]
        required = ("observation_id", "strain_id", "experiment_id", "assay_plate_id", "plate_format",
                    "well", "material_id", "material_type", "lineage_state", "dose_state", "target_raw",
                    "target_state", "replicate_id", "replicate_type", "control_state", "inclusion_state",
                    "source_locator")
        blank = [field for field in required if not row[field]]
        if blank:
            raise BioassayFigureHold(f"BIOASSAY_REQUIRED_FIELD_HOLD: row {line}: {','.join(blank)}")
        if oid in seen:
            raise BioassayFigureHold(f"BIOASSAY_DUPLICATE_OBSERVATION_HOLD: {oid}")
        seen.add(oid)
        for field, accepted in (
            ("plate_format", PLATE_FORMATS), ("material_type", MATERIAL_TYPES),
            ("lineage_state", LINEAGE_STATES), ("target_state", TARGET_STATES),
            ("dose_state", DOSE_STATES),
            ("replicate_type", REPLICATE_TYPES), ("control_state", CONTROL_STATES),
            ("inclusion_state", INCLUSION_STATES),
        ):
            if row[field] not in accepted:
                raise BioassayFigureHold(f"BIOASSAY_{field.upper()}_HOLD: row {line}: {row[field]!r}")
        if not _well_ok(row["well"], row["plate_format"]):
            raise BioassayFigureHold(f"BIOASSAY_WELL_HOLD: row {line}: {row['well']!r} for {row['plate_format']}")
        if row["target_state"] == "VERIFIED" and not row["target_canonical"]:
            raise BioassayFigureHold(f"BIOASSAY_TARGET_HOLD: row {line}: VERIFIED requires target_canonical")
        if row["target_state"] != "VERIFIED" and row["target_canonical"]:
            raise BioassayFigureHold(f"BIOASSAY_TARGET_HOLD: row {line}: unresolved target cannot carry target_canonical")
        if row["lineage_state"] == "VERIFIED" and row["material_type"] != "CRUDE_EXTRACT" and not row["parent_material_id"]:
            raise BioassayFigureHold(f"BIOASSAY_LINEAGE_HOLD: row {line}: VERIFIED derived material needs parent_material_id")
        numeric_optional = ("material_amount_mg", "stock_concentration_mg_ml",
                            "delivered_amount_ug", "final_concentration_ug_ml")
        for field in numeric_optional:
            if row[field]:
                try:
                    value = float(row[field])
                except ValueError as exc:
                    raise BioassayFigureHold(f"BIOASSAY_DOSE_HOLD: row {line}: {field} must be numeric") from exc
                if not math.isfinite(value) or value < 0:
                    raise BioassayFigureHold(f"BIOASSAY_DOSE_HOLD: row {line}: {field} must be finite and non-negative")
                row[field] = value
            else:
                row[field] = None
        if row["dose_state"] == "VERIFIED" and row["final_concentration_ug_ml"] is None:
            raise BioassayFigureHold(
                f"BIOASSAY_DOSE_HOLD: row {line}: VERIFIED requires final_concentration_ug_ml"
            )
        if row["dose_state"] == "UNRECORDED" and any(row[field] is not None for field in numeric_optional[1:]):
            raise BioassayFigureHold(
                f"BIOASSAY_DOSE_HOLD: row {line}: UNRECORDED cannot carry stock/delivered/final dose"
            )
        if row["inclusion_state"] in {"HOLD", "EXCLUDE"} and not row["exclusion_reason"]:
            raise BioassayFigureHold(f"BIOASSAY_DISPOSITION_HOLD: row {line}: reason required")
        if row["inclusion_state"] == "INCLUDE" and row["control_state"] not in {"VALID", "NOT_APPLICABLE"}:
            raise BioassayFigureHold(f"BIOASSAY_CONTROL_HOLD: row {line}: invalid control cannot be included")
        try:
            timepoint = float(row["timepoint_hours"])
            inhibition = float(row["inhibition_pct"])
        except ValueError as exc:
            if row["inclusion_state"] == "INCLUDE":
                raise BioassayFigureHold(f"BIOASSAY_MEASUREMENT_HOLD: row {line}: numeric timepoint and inhibition required") from exc
            timepoint = inhibition = math.nan
        if row["inclusion_state"] == "INCLUDE" and (not math.isfinite(timepoint) or timepoint <= 0 or not math.isfinite(inhibition)):
            raise BioassayFigureHold(f"BIOASSAY_MEASUREMENT_HOLD: row {line}: invalid included measurement")
        row["source_locator"] = _portable_locator(row["source_locator"], "source")
        row["timepoint_hours"] = timepoint
        row["inhibition_pct"] = inhibition
        admitted.append(row)
    return admitted


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    buckets: dict[tuple[str, ...], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        if row["inclusion_state"] != "INCLUDE":
            continue
        target = str(row["target_canonical"] or row["target_raw"])
        key = (
            str(row["strain_id"]), str(row["material_id"]), str(row["material_type"]),
            str(row["parent_material_id"]), str(row["lineage_state"]), target,
            str(row["target_state"]), f"{float(row['timepoint_hours']):g}", str(row["dose_state"]),
            "" if row["stock_concentration_mg_ml"] is None else f"{float(row['stock_concentration_mg_ml']):g}",
            "" if row["delivered_amount_ug"] is None else f"{float(row['delivered_amount_ug']):g}",
            "" if row["final_concentration_ug_ml"] is None else f"{float(row['final_concentration_ug_ml']):g}",
        )
        buckets[key].append(row)
    output = []
    for key, values in sorted(buckets.items()):
        nums = [float(row["inhibition_pct"]) for row in values]
        (strain, material, material_type, parent, lineage, target, target_state, timepoint,
         dose_state, stock_concentration, delivered_amount, final_concentration) = key
        amounts = {row["material_amount_mg"] for row in values if row["material_amount_mg"] is not None}
        if len(amounts) > 1:
            raise BioassayFigureHold(
                f"BIOASSAY_MATERIAL_AMOUNT_HOLD: conflicting amount for {strain}/{material}"
            )
        output.append({
            "strain_id": strain, "material_id": material, "material_type": material_type,
            "parent_material_id": parent, "lineage_state": lineage, "target": target,
            "target_state": target_state, "timepoint_hours": timepoint,
            "material_amount_mg": next(iter(amounts)) if amounts else "",
            "dose_state": dose_state, "stock_concentration_mg_ml": stock_concentration,
            "delivered_amount_ug": delivered_amount,
            "final_concentration_ug_ml": final_concentration,
            "observation_count": len(values),
            "experiment_count": len({str(row["experiment_id"]) for row in values}),
            "replicate_count": len({(str(row["experiment_id"]), str(row["replicate_id"])) for row in values}),
            "mean_inhibition_pct": round(sum(nums) / len(nums), 6),
            "min_inhibition_pct": min(nums), "max_inhibition_pct": max(nums),
        })
    if not output:
        raise BioassayFigureHold("BIOASSAY_NO_INCLUDED_ROWS_HOLD: all observations are held or excluded")
    return output


def _write_tsv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = SafeDictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def _select_tree_track(summary: list[dict[str, object]], selection: dict[str, object]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Create one explicit strain-level BIOASSAY track for a later tree-tip crosswalk.

    A material ID is selected independently for every strain. This deliberately prevents pooling
    differently named fraction material or choosing the strongest observation automatically.
    """
    required = ("selection_id", "target", "target_state", "timepoint_hours", "material_type",
                "strain_roster", "material_ids_by_strain")
    missing = [key for key in required if key not in selection]
    if missing:
        raise BioassayFigureHold(f"BIOASSAY_TREE_SELECTION_HOLD: missing {','.join(missing)}")
    aggregation = str(selection.get("aggregation", "mean_inhibition_pct"))
    if aggregation not in {"mean_inhibition_pct", "fraction_set_max"}:
        raise BioassayFigureHold(
            "BIOASSAY_TREE_SELECTION_HOLD: aggregation must be mean_inhibition_pct or fraction_set_max"
        )
    roster = [str(value).strip() for value in selection["strain_roster"]]
    raw_material_map = dict(selection["material_ids_by_strain"])
    material_map = {}
    for key, value in raw_material_map.items():
        strain = str(key).strip()
        values = value if isinstance(value, list) else [value]
        material_map[strain] = [str(item).strip() for item in values]
    if not roster or any(not value for value in roster) or len(roster) != len(set(roster)):
        raise BioassayFigureHold("BIOASSAY_TREE_SELECTION_HOLD: strain_roster must be nonempty and unique")
    if (set(material_map) != set(roster)
            or any(not values or any(not value for value in values) or len(values) != len(set(values))
                   for values in material_map.values())):
        raise BioassayFigureHold(
            "BIOASSAY_TREE_SELECTION_HOLD: material_ids_by_strain must bind every roster strain exactly"
        )
    target = str(selection["target"]).strip()
    target_state = str(selection["target_state"]).strip()
    material_type = str(selection["material_type"]).strip()
    if not target or target_state not in TARGET_STATES or material_type not in MATERIAL_TYPES:
        raise BioassayFigureHold("BIOASSAY_TREE_SELECTION_HOLD: unsupported target_state or material_type")
    try:
        timepoint_number = float(selection["timepoint_hours"])
    except (TypeError, ValueError) as exc:
        raise BioassayFigureHold("BIOASSAY_TREE_SELECTION_HOLD: timepoint_hours must be numeric") from exc
    if not math.isfinite(timepoint_number) or timepoint_number <= 0:
        raise BioassayFigureHold("BIOASSAY_TREE_SELECTION_HOLD: timepoint_hours must be finite and positive")
    timepoint = f"{timepoint_number:g}"
    if "final_concentration_ug_ml" not in selection:
        raise BioassayFigureHold(
            "BIOASSAY_TREE_SELECTION_HOLD: final_concentration_ug_ml is required"
        )
    try:
        final_concentration_number = float(selection["final_concentration_ug_ml"])
    except (TypeError, ValueError) as exc:
        raise BioassayFigureHold(
            "BIOASSAY_TREE_SELECTION_HOLD: final_concentration_ug_ml must be numeric"
        ) from exc
    if not math.isfinite(final_concentration_number) or final_concentration_number <= 0:
        raise BioassayFigureHold(
            "BIOASSAY_TREE_SELECTION_HOLD: final_concentration_ug_ml must be finite and positive"
        )
    final_concentration = f"{final_concentration_number:g}"
    if aggregation == "mean_inhibition_pct" and any(len(values) != 1 for values in material_map.values()):
        raise BioassayFigureHold(
            "BIOASSAY_TREE_SELECTION_HOLD: mean_inhibition_pct requires one material ID per strain"
        )
    try:
        active_threshold = float(selection["active_threshold_pct"]) if aggregation == "fraction_set_max" else math.nan
    except (KeyError, TypeError, ValueError) as exc:
        raise BioassayFigureHold(
            "BIOASSAY_TREE_SELECTION_HOLD: fraction_set_max requires numeric active_threshold_pct"
        ) from exc
    if aggregation == "fraction_set_max" and (
            not math.isfinite(active_threshold) or not 0 <= active_threshold <= 100):
        raise BioassayFigureHold(
            "BIOASSAY_TREE_SELECTION_HOLD: active_threshold_pct must be finite and between 0 and 100"
        )
    index: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in summary:
        if (str(row["target"]) == target and str(row["target_state"]) == target_state
                and str(row["timepoint_hours"]) == timepoint
                and str(row["material_type"]) == material_type
                and str(row["final_concentration_ug_ml"]) == final_concentration):
            index[(str(row["strain_id"]), str(row["material_id"]))].append(row)
    feature = str(selection["selection_id"]).strip()
    if not feature or re.search(r"[\t\r\n]", feature):
        raise BioassayFigureHold("BIOASSAY_TREE_SELECTION_HOLD: invalid selection_id")
    output, details = [], []
    for strain in roster:
        matches = []
        for material in material_map[strain]:
            material_matches = index.get((strain, material), [])
            if len(material_matches) > 1:
                raise BioassayFigureHold(
                    f"BIOASSAY_TREE_SELECTION_HOLD: selection is not unique for {strain}/{material}"
                )
            matches.extend(material_matches)
        if aggregation == "fraction_set_max" and matches and len(matches) != len(material_map[strain]):
            observed = {str(row["material_id"]) for row in matches}
            absent = [material for material in material_map[strain] if material not in observed]
            raise BioassayFigureHold(
                f"BIOASSAY_TREE_SELECTION_HOLD: incomplete named fraction set for {strain}; "
                f"missing {','.join(absent)}"
            )
        selected = (max(matches, key=lambda row: float(row["mean_inhibition_pct"]))
                    if matches and aggregation == "fraction_set_max"
                    else matches[0] if matches else None)
        output.append({
            "strain": strain,
            "channel": "BIOASSAY",
            "feature": feature,
            "value": selected["mean_inhibition_pct"] if selected else "",
            "state": "OBSERVED" if selected else "NOT_MEASURED",
        })
        unique_amounts = {str(row["material_id"]): row["material_amount_mg"] for row in matches
                          if row["material_amount_mg"] != ""}
        details.append({
            "strain": strain, "aggregation": aggregation,
            "target": target, "timepoint_hours": timepoint,
            "final_concentration_ug_ml": final_concentration,
            "requested_material_count": len(material_map[strain]),
            "measured_material_count": len(matches),
            "active_material_count": (sum(float(row["mean_inhibition_pct"]) >= active_threshold
                                          for row in matches)
                                      if aggregation == "fraction_set_max" else ""),
            "active_threshold_pct": active_threshold if aggregation == "fraction_set_max" else "",
            "selected_material_id": str(selected["material_id"]) if selected else "",
            "selected_value": selected["mean_inhibition_pct"] if selected else "",
            "total_recorded_material_amount_mg": (round(sum(float(value) for value in unique_amounts.values()), 6)
                                                  if unique_amounts else ""),
            "state": "OBSERVED" if selected else "NOT_MEASURED",
        })
    return output, details


def build_tree_track(summary: list[dict[str, object]], selection: dict[str, object]) -> list[dict[str, object]]:
    """Public compatibility wrapper returning the annotation rows only."""
    return _select_tree_track(summary, selection)[0]


def build(config_path: Path) -> dict[str, object]:
    config_path = config_path.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != SCHEMA or config.get("figure_kind") != FIGURE_KIND:
        raise BioassayFigureHold(f"BIOASSAY_CONFIG_HOLD: expected {SCHEMA} / {FIGURE_KIND}")
    root = Path(config.get("external_data_root", "")).expanduser().resolve()
    spec = dict(config.get("observations", {}))
    locator = _portable_locator(str(spec.get("logical_locator", "")), "input")
    source = (root / locator).resolve()
    try:
        source.relative_to(root)
    except ValueError as exc:
        raise BioassayFigureHold("BIOASSAY_INPUT_LOCATOR_HOLD: input escapes root") from exc
    if not source.is_file():
        raise FileNotFoundError(locator)
    expected = str(spec.get("sha256", "")).lower()
    actual = sha256_file(source)
    if not re.fullmatch(r"[0-9a-f]{64}", expected) or actual != expected:
        raise BioassayFigureHold("BIOASSAY_INPUT_HASH_HOLD: exact SHA-256 does not match")
    rows = validate_rows(_read(source)); summary = summarize(rows)
    output = Path(config["output_dir"])
    if not output.is_absolute():
        output = (config_path.parent / output).resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".bioassay_figure_factory.", dir=output.parent))
    try:
        clean = stage / "bioassay_observations_admitted.tsv"
        clean_rows = [{k: ("" if isinstance(v, float) and math.isnan(v) else v) for k, v in row.items()} for row in rows]
        _write_tsv(clean, clean_rows, list(FIELDS))
        summary_path = stage / "bioassay_summary.tsv"
        _write_tsv(summary_path, summary, list(summary[0]))
        caption = stage / "bioassay_caption_methods.json"
        tree_state = "REQUIRES_EXPLICIT_MATERIAL_TARGET_TIMEPOINT_SELECTION"
        selection = config.get("tree_track_selection")
        if selection is not None:
            tree_rows, detail_rows = _select_tree_track(summary, dict(selection))
            tree_path = stage / "bioassay_tree_track.tsv"
            _write_tsv(tree_path, tree_rows, ["strain", "channel", "feature", "value", "state"])
            detail_path = stage / "bioassay_tree_selection_details.tsv"
            _write_tsv(detail_path, detail_rows, list(detail_rows[0]))
            artifacts = [clean, summary_path, tree_path, detail_path]
            tree_state = "EMITTED_EXPLICIT_SELECTION"
        else:
            artifacts = [clean, summary_path]
        caption.write_text(json.dumps({
            "input_sha256": actual,
            "included_observations": sum(row["inclusion_state"] == "INCLUDE" for row in rows),
            "held_observations": sum(row["inclusion_state"] == "HOLD" for row in rows),
            "excluded_observations": sum(row["inclusion_state"] == "EXCLUDE" for row in rows),
            "summary_rows": len(summary),
            "aggregation": "arithmetic mean within exact strain/material/target/timepoint/dose groups; raw range and counts retained",
            "tree_overlay_state": tree_state,
            "tree_track_selection": selection,
            "compound_structure_state": "REFERENCE_CONTEXT_NOT_ASSAY_IDENTITY",
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        artifacts.append(caption)
        render = bool(config.get("render_with_r", False))
        status = "PASS_DATA_READY_R_NOT_REQUESTED"
        if render:
            rscript = str(config.get("rscript", "Rscript"))
            script = Path(__file__).resolve().parents[1] / "tools" / "sapote_bioassay_figure.R"
            prefix = stage / "bioassay_summary"
            proc = subprocess.run([rscript, str(script), str(summary_path), str(prefix),
                                   str(config.get("profile", "SINGLE_COLUMN")),
                                   str(config.get("title", "Bioassay observations"))],
                                  capture_output=True, text=True)
            if proc.returncode:
                raise BioassayFigureHold(f"BIOASSAY_R_RENDER_HOLD: {proc.stderr[-500:]}")
            graphics = [Path(str(prefix) + suffix) for suffix in (".svg", ".png")]
            if not all(path.is_file() for path in graphics):
                raise BioassayFigureHold("BIOASSAY_R_RENDER_HOLD: renderer did not emit SVG and PNG")
            artifacts.extend(graphics); status = "PASS_FIGURE_FACTORY_RENDERED"
        receipt = {
            "schema_version": SCHEMA, "figure_kind": FIGURE_KIND, "status": status,
            "input": {"logical_locator": locator, "sha256": actual, "bytes": source.stat().st_size},
            "outputs": [{"logical_locator": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size}
                        for path in artifacts],
            "claim_ceiling": "Measured assay observations at the recorded material level; no automatic locus or compound attribution.",
        }
        receipt_path = stage / "bioassay_figure_factory_receipt.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        stage.replace(output)
        return receipt
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
