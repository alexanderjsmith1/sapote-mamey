#!/usr/bin/env python3
"""Bring admitted per-well bioassay tables into the Figure Factory observation table, and derive the
best-value table the paper activity renderers read.

Two commands:

  observations --profile profile.json --out observations.tsv
      Reads every per-well table the profile names (one row per well reading, already admitted by the owner),
      applies an optional corrections table, and writes the canonical observation table
      (examples/bioassay_observations_template.tsv columns, in order) plus `<out>.receipt.json`.
  best-table --observations observations.tsv --out best.tsv [--dose-384 120] [--floor 0]
      Per strain x target x material: the higher of the best 96-well reading (any recorded dose) and the best
      384-well reading at one final concentration. Included rows only. A combination never read has no row:
      not tested, never zero.

Every study-specific choice lives in the profile, never in this code: which tables, their column names, how a
material group maps to a material type, which targets are verified or ambiguous, and which control state the owner
assigns to each calibration basis. A calibration basis the profile does not name gets control_state UNRECORDED and
the row is held, so an expected-OD normalization is never included silently (docs/BIOASSAY_FIGURE_FACTORY.md).
Values are copied as recorded: percent inhibition is not clipped in the observation table, and the best table
applies only the floor it is given. Profile format: docs/BIOASSAY_FIGURE_FACTORY.md and
examples/bioassay_admitted_profile_example.json.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

PROFILE_SCHEMA = "sapote.bioassay-admitted-profile.v1"
FIELDS = (
    "observation_id", "strain_id", "experiment_id", "assay_plate_id", "plate_format",
    "well", "material_id", "material_type", "parent_material_id", "lineage_state",
    "material_amount_mg", "dose_state", "stock_concentration_mg_ml", "delivered_amount_ug",
    "final_concentration_ug_ml",
    "target_raw", "target_state", "target_canonical", "timepoint_hours", "replicate_id",
    "replicate_type", "inhibition_pct", "control_state", "inclusion_state",
    "exclusion_reason", "source_locator",
)
MATERIAL_TYPES = {"CRUDE_EXTRACT", "FLASH_FRACTION", "HPLC_FRACTION", "PURIFIED_COMPOUND", "OTHER"}
TARGET_STATES = {"VERIFIED", "AS_RECORDED", "AMBIGUOUS"}
DOSE_STATES = {"VERIFIED", "AS_RECORDED", "UNRECORDED"}
CONTROL_STATES = {
    "VALID", "NOT_APPLICABLE", "POSITIVE_CONTROL_MISSING",
    "POSITIVE_CONTROL_LOCATION_UNRESOLVED", "EXPECTED_OD_NORMALIZATION_HOLD", "UNRECORDED",
}
REPLICATE_TYPES = {"SINGLETON", "TECHNICAL", "BIOLOGICAL", "UNSPECIFIED"}
MATERIAL_LABELS = {"CRUDE_EXTRACT": "Crude extract", "FLASH_FRACTION": "Fraction", "HPLC_FRACTION": "HPLC fraction",
                   "PURIFIED_COMPOUND": "Purified compound", "OTHER": "Material unresolved"}
REQUIRED_COLUMNS = ("strain", "plate", "well", "target", "material_group", "value", "timepoint", "calibration")
_SLUG = re.compile(r"[^A-Za-z0-9._-]+")


class AdmittedProfileHold(ValueError):
    """A typed refusal: the profile or an input table cannot be mapped without a guess."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _slug(value: str) -> str:
    return _SLUG.sub("-", value.strip()).strip("-") or "x"


def _number(value: str) -> float | None:
    try:
        number = float(str(value).strip())
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _hours(value: str) -> float | None:
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*(?:h|hr|hrs|hours?)?\s*", str(value), re.I)
    return float(match.group(1)) if match else None


def _fmt(number: float | None) -> str:
    return "" if number is None else f"{number:g}"


def load_profile(path: Path) -> dict:
    profile = json.loads(path.read_text(encoding="utf-8"))
    if profile.get("schema_version") != PROFILE_SCHEMA:
        raise AdmittedProfileHold(f"PROFILE_SCHEMA_HOLD: expected schema_version {PROFILE_SCHEMA}")
    tables = profile.get("tables") or []
    if not tables:
        raise AdmittedProfileHold("PROFILE_TABLES_HOLD: the profile names no tables")
    keys = set()
    for table in tables:
        if table.get("platform") not in {"96", "384"}:
            raise AdmittedProfileHold(f"PROFILE_PLATFORM_HOLD: {table.get('key')!r} platform must be '96' or '384'")
        if not table.get("key") or table["key"] in keys:
            raise AdmittedProfileHold(f"PROFILE_KEY_HOLD: every table needs a unique key ({table.get('key')!r})")
        keys.add(table["key"])
        missing = [c for c in REQUIRED_COLUMNS if not table.get("columns", {}).get(c)]
        if missing:
            raise AdmittedProfileHold(f"PROFILE_COLUMNS_HOLD: {table['key']} lacks {','.join(missing)}")
    for group, mtype in profile.get("material_types", {}).items():
        if mtype not in MATERIAL_TYPES:
            raise AdmittedProfileHold(f"PROFILE_MATERIAL_HOLD: {group!r} -> {mtype!r}")
    for target, state in profile.get("targets", {}).items():
        if state not in TARGET_STATES:
            raise AdmittedProfileHold(f"PROFILE_TARGET_HOLD: {target!r} -> {state!r}")
    for basis, entry in profile.get("control_states", {}).items():
        if entry.get("state") not in CONTROL_STATES or not entry.get("basis"):
            raise AdmittedProfileHold(f"PROFILE_CONTROL_HOLD: {basis!r} needs a known state and a written basis")
    for platform, state in profile.get("dose_states", {}).items():
        if state not in DOSE_STATES - {"UNRECORDED"}:
            raise AdmittedProfileHold(f"PROFILE_DOSE_HOLD: platform {platform!r} -> {state!r}")
    if profile.get("replicate_type", "UNSPECIFIED") not in REPLICATE_TYPES:
        raise AdmittedProfileHold(f"PROFILE_REPLICATE_HOLD: {profile.get('replicate_type')!r}")
    return profile


def _resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base / path)


def _corrections(profile: dict, base: Path) -> tuple[dict, dict | None]:
    spec = profile.get("corrections")
    if not spec:
        return {}, None
    path = _resolve(base, spec["path"])
    match, platform_column = spec["match_columns"], spec["platform_column"]
    fixes = {}
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            key = (row[platform_column],) + tuple(row[c] for c in match)
            if key in fixes and fixes[key] != row:
                raise AdmittedProfileHold(f"CORRECTIONS_CONFLICT_HOLD: two different corrections for {key}")
            fixes[key] = row
    return fixes, {"path": str(path), "sha256": sha256_file(path), "rows": len(fixes)}


def build_observations(profile_path: Path) -> tuple[list[dict[str, str]], dict]:
    profile = load_profile(profile_path)
    base = profile_path.resolve().parent
    fixes, fix_receipt = _corrections(profile, base)
    spec = profile.get("corrections") or {}
    platform_values = spec.get("platform_values", {})
    rows, seen, tables_receipt = [], set(), []
    applied = 0
    for table in profile["tables"]:
        path, cols, platform, key = _resolve(base, table["path"]), table["columns"], table["platform"], table["key"]
        delimiter = "\t" if path.suffix.lower() in {".tsv", ".tab"} else ","
        count = 0
        with open(path, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            absent = [c for c in cols.values() if c and c not in (reader.fieldnames or [])]
            if absent:
                raise AdmittedProfileHold(f"TABLE_COLUMNS_HOLD: {key} has no column(s) {','.join(absent)}")
            for line, src in enumerate(reader, 2):
                count += 1
                if fixes:
                    fix_key = (platform_values.get(platform, platform),) + tuple(src[c] for c in spec["match_columns"])
                    fix = fixes.get(fix_key)
                    if fix is not None:
                        src = dict(src, **{target: fix[source] for target, source in spec["apply"].items()})
                        applied += 1
                rows.append(_observation(src, cols, platform, key, line, profile))
                if rows[-1]["observation_id"] in seen:
                    raise AdmittedProfileHold(f"DUPLICATE_OBSERVATION_HOLD: {rows[-1]['observation_id']}")
                seen.add(rows[-1]["observation_id"])
        tables_receipt.append({"key": key, "platform": platform, "path": str(path), "sha256": sha256_file(path),
                               "rows": count})
    counts = defaultdict(int)
    for row in rows:
        counts[(row["inclusion_state"], row["exclusion_reason"])] += 1
    receipt = {
        "tool": "tools/bioassay_admitted_observations.py observations",
        "profile": str(profile_path), "profile_sha256": sha256_file(profile_path),
        "tables": tables_receipt, "corrections": fix_receipt, "corrections_applied": applied,
        "control_states": profile.get("control_states", {}),
        "rows": len(rows),
        "inclusion_counts": [{"inclusion_state": s, "reason": r, "rows": n} for (s, r), n in sorted(counts.items())],
    }
    return rows, receipt


def _observation(src: dict, cols: dict, platform: str, key: str, line: int, profile: dict) -> dict[str, str]:
    get = lambda name: (src.get(cols[name]) or "").strip() if cols.get(name) else ""
    strain, target, group = get("strain"), get("target"), get("material_group")
    holds = []
    material_type = profile.get("material_types", {}).get(group)
    if material_type is None:
        material_type = "OTHER"
        holds.append(f"MATERIAL_GROUP_UNMAPPED:{group or 'blank'}")
    target_state = profile.get("targets", {}).get(target, "AS_RECORDED")
    dose = _number(get("dose")) if cols.get("dose") else None
    dose_state = profile.get("dose_states", {}).get(platform, "AS_RECORDED") if dose is not None else "UNRECORDED"
    calibration = get("calibration")
    control = profile.get("control_states", {}).get(calibration, {}).get("state", "UNRECORDED")
    if control not in {"VALID", "NOT_APPLICABLE"}:
        holds.append(f"CONTROL_{control}:{calibration or 'blank'}")
    value = _number(get("value"))
    hours = _hours(get("timepoint"))
    if value is None or hours is None:
        holds.append("MEASUREMENT_NOT_NUMERIC")
    if not strain or not target:
        holds.append("IDENTITY_BLANK")
    plate, well = get("plate"), get("well")
    row_id = get("row_id") or f"row{line}"
    material_id = get("material_id") or f"{strain}:{group}"
    experiment = get("experiment") or f"{key}:{plate}"
    return {
        "observation_id": f"{key}|{row_id}|{plate}|{well}|{target}|{_fmt(dose)}",
        "strain_id": strain or "UNRECORDED", "experiment_id": experiment, "assay_plate_id": plate or "UNRECORDED",
        "plate_format": platform, "well": well, "material_id": material_id, "material_type": material_type,
        "parent_material_id": "", "lineage_state": "UNRECORDED", "material_amount_mg": "",
        "dose_state": dose_state, "stock_concentration_mg_ml": "", "delivered_amount_ug": "",
        "final_concentration_ug_ml": _fmt(dose),
        "target_raw": target or "UNRECORDED", "target_state": target_state,
        "target_canonical": target if target_state == "VERIFIED" else "",
        "timepoint_hours": _fmt(hours), "replicate_id": get("replicate") or "1",
        "replicate_type": profile.get("replicate_type", "UNSPECIFIED"),
        "inhibition_pct": get("value"), "control_state": control,
        "inclusion_state": "HOLD" if holds else "INCLUDE", "exclusion_reason": ";".join(holds),
        "source_locator": f"{_slug(key)}/plate-{_slug(plate)}/{_slug(well)}/{line}",
    }


def write_tsv(path: Path, rows: list[dict], fields) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=list(fields), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def best_table(observations: Path, dose_384: float = 120.0, floor: float | None = 0.0) -> list[dict[str, str]]:
    """Higher of the best 96-well reading (any recorded dose) and the best 384-well reading at `dose_384`."""
    best = defaultdict(lambda: {"96": None, "384": None, "n96": 0, "n384": 0})
    with open(observations, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise AdmittedProfileHold("OBSERVATION_SCHEMA_HOLD: canonical observation columns are required")
        for row in reader:
            if row["inclusion_state"] != "INCLUDE":
                continue
            platform = row["plate_format"]
            if platform == "384" and _number(row["final_concentration_ug_ml"]) != dose_384:
                continue
            if platform not in {"96", "384"}:
                continue
            value = float(row["inhibition_pct"])
            if floor is not None:
                value = max(value, floor)
            label = MATERIAL_LABELS.get(row["material_type"], row["material_type"])
            cell = best[(row["strain_id"], row["target_canonical"] or row["target_raw"], label)]
            cell["n" + platform] += 1
            if cell[platform] is None or value > cell[platform]:
                cell[platform] = value
    dose = f"{dose_384:g}"
    out = []
    for (strain, target, label), cell in sorted(best.items()):
        values = [v for v in (cell["96"], cell["384"]) if v is not None]
        read_on = "both" if len(values) == 2 else ("96-well" if cell["96"] is not None else "384-well")
        out.append({"strain": strain, "organism": target, "material": label, "best_pct": f"{max(values):.2f}",
                    "best_96": "" if cell["96"] is None else f"{cell['96']:.2f}",
                    f"best_384_{dose}": "" if cell["384"] is None else f"{cell['384']:.2f}",
                    "read_on": read_on, "n_96": str(cell["n96"]), f"n_384_{dose}": str(cell["n384"])})
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    obs = sub.add_parser("observations", help="admitted per-well tables -> canonical observation table")
    obs.add_argument("--profile", required=True, type=Path)
    obs.add_argument("--out", required=True, type=Path)
    best = sub.add_parser("best-table", help="observation table -> best value per strain x target x material")
    best.add_argument("--observations", required=True, type=Path)
    best.add_argument("--out", required=True, type=Path)
    best.add_argument("--dose-384", type=float, default=120.0,
                      help="the one 384-well final concentration (ug/mL) that counts (default 120)")
    best.add_argument("--floor", type=float, default=0.0,
                      help="lower floor applied to each reading before taking the best (default 0)")
    best.add_argument("--no-floor", action="store_true", help="take readings as recorded, with no floor")
    args = parser.parse_args(argv)
    try:
        if args.command == "observations":
            if args.out.exists():
                raise AdmittedProfileHold(f"OUTPUT_EXISTS_HOLD: {args.out} exists; choose a new path")
            rows, receipt = build_observations(args.profile)
            write_tsv(args.out, rows, FIELDS)
            receipt.update(output=str(args.out), output_sha256=sha256_file(args.out))
            Path(str(args.out) + ".receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            held = sum(1 for r in rows if r["inclusion_state"] != "INCLUDE")
            sys.stdout.write(f"{len(rows)} observations; {len(rows) - held} included; {held} held\n")
        else:
            if args.out.exists():
                raise AdmittedProfileHold(f"OUTPUT_EXISTS_HOLD: {args.out} exists; choose a new path")
            rows = best_table(args.observations, args.dose_384, None if args.no_floor else args.floor)
            if not rows:
                raise AdmittedProfileHold("BEST_TABLE_EMPTY_HOLD: no included observations")
            write_tsv(args.out, rows, list(rows[0]))
            receipt = {"tool": "tools/bioassay_admitted_observations.py best-table",
                       "observations": str(args.observations), "observations_sha256": sha256_file(args.observations),
                       "dose_384_ug_ml": args.dose_384, "floor": None if args.no_floor else args.floor,
                       "rows": len(rows), "output": str(args.out), "output_sha256": sha256_file(args.out)}
            Path(str(args.out) + ".receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            sys.stdout.write(f"{len(rows)} strain x target x material rows\n")
    except AdmittedProfileHold as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
