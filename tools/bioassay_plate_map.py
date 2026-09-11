#!/usr/bin/env python3
"""Map source-plate wells to destination wells with an explicit geometry profile.

This utility performs plate geometry only. It does not infer sample identity,
bioactivity, biological replication, or compound identity.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import tempfile
from pathlib import Path

try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

PROFILE = "96_TO_384_QUADRANT_120_60_30_15"
CONCENTRATIONS = {"TL": 120.0, "TR": 60.0, "BL": 30.0, "BR": 15.0}
ROWS_96 = "ABCDEFGH"
ROWS_384 = "ABCDEFGHIJKLMNOP"
OUTPUT_FIELDS = (
    "mapping_profile", "source_well", "destination_well", "quadrant",
    "final_concentration_ug_ml", "mapping_state",
)
WELL_RE = re.compile(r"^([A-Pa-p])\s*0*([1-9]|1[0-9]|2[0-4])$")


class PlateMapRefusal(ValueError):
    """Typed refusal for invalid profile or table input."""


def build_profile(profile: str) -> list[dict[str, str]]:
    if profile != PROFILE:
        raise PlateMapRefusal(f"PLATE_MAP_PROFILE_UNKNOWN: {profile}")
    rows = []
    for source_row_index, source_row in enumerate(ROWS_96):
        top = ROWS_384[source_row_index * 2]
        bottom = ROWS_384[source_row_index * 2 + 1]
        for source_col in range(1, 13):
            source_well = f"{source_row}{source_col}"
            left = source_col * 2 - 1
            right = source_col * 2
            for quadrant, destination in (
                ("TL", f"{top}{left}"), ("TR", f"{top}{right}"),
                ("BL", f"{bottom}{left}"), ("BR", f"{bottom}{right}"),
            ):
                rows.append({
                    "mapping_profile": profile,
                    "source_well": source_well,
                    "destination_well": destination,
                    "quadrant": quadrant,
                    "final_concentration_ug_ml": f"{CONCENTRATIONS[quadrant]:g}",
                    "mapping_state": "MAPPED",
                })
    return rows


def _delimiter(path: Path) -> str:
    return "\t" if path.suffix.lower() in {".tsv", ".tab"} else ","


def _canonical_destination_well(value: object) -> str:
    match = WELL_RE.fullmatch(str(value or "").strip())
    return f"{match.group(1).upper()}{int(match.group(2))}" if match else ""


def _read_table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter=_delimiter(path))
        fields = list(reader.fieldnames or [])
        return fields, list(reader)


def _atomic_write(path: Path, fields: list[str] | tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as handle:
            writer = _SafeDictWriter(handle, fieldnames=fields, delimiter=_delimiter(path), extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def emit(profile: str, output: Path) -> None:
    _atomic_write(output, OUTPUT_FIELDS, build_profile(profile))


def annotate(profile: str, source: Path, output: Path, well_column: str) -> int:
    fields, rows = _read_table(source)
    if well_column not in fields:
        raise PlateMapRefusal(f"PLATE_MAP_SCHEMA: missing destination-well column {well_column!r}")
    index = {row["destination_well"]: row for row in build_profile(profile)}
    additions = list(OUTPUT_FIELDS)
    output_fields = fields + [field for field in additions if field not in fields]
    unmapped = 0
    for row_number, row in enumerate(rows, start=2):
        raw_destination = str(row.get(well_column, "")).strip()
        destination = _canonical_destination_well(raw_destination)
        mapped = index.get(destination)
        if mapped is None:
            unmapped += 1
            row.update({
                "mapping_profile": profile, "source_well": "", "destination_well": raw_destination,
                "quadrant": "", "final_concentration_ug_ml": "", "mapping_state": "UNMAPPED",
            })
        else:
            row.update(mapped)
    _atomic_write(output, output_fields, rows)
    return unmapped


def validate(profile: str, source: Path) -> None:
    fields, rows = _read_table(source)
    required = set(OUTPUT_FIELDS) - {"mapping_state"}
    if not required.issubset(fields):
        raise PlateMapRefusal(f"PLATE_MAP_SCHEMA: missing columns {sorted(required - set(fields))}")
    expected = {(r["source_well"], r["destination_well"]): r for r in build_profile(profile)}
    observed = {}
    for row_number, row in enumerate(rows, start=2):
        key = (str(row["source_well"]).strip().upper(), str(row["destination_well"]).strip().upper())
        if key in observed:
            raise PlateMapRefusal(f"PLATE_MAP_DUPLICATE: row {row_number} repeats {key}")
        observed[key] = row
    if set(observed) != set(expected):
        missing = len(set(expected) - set(observed))
        extra = len(set(observed) - set(expected))
        raise PlateMapRefusal(f"PLATE_MAP_COVERAGE: missing={missing}; extra={extra}")
    for key, wanted in expected.items():
        got = observed[key]
        for field in ("mapping_profile", "quadrant", "final_concentration_ug_ml"):
            if str(got[field]).strip() != wanted[field]:
                raise PlateMapRefusal(f"PLATE_MAP_MISMATCH: {key} {field}={got[field]!r}; expected={wanted[field]!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(allow_abbrev=False, description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list-profiles")
    for command in ("emit", "annotate", "validate"):
        child = sub.add_parser(command)
        child.add_argument("--profile", required=True, choices=[PROFILE])
        if command != "validate":
            child.add_argument("--out", type=Path, required=True)
        if command != "emit":
            child.add_argument("--input", type=Path, required=True)
        if command == "annotate":
            child.add_argument("--well-column", default="Well_384")
    args = parser.parse_args(argv)
    if args.command == "list-profiles":
        sys.stdout.write(f"{PROFILE}\t96-well source to 384-well 2x2 quadrants at 120/60/30/15 ug/mL\n")
        return 0
    if args.command == "emit":
        emit(args.profile, args.out)
        sys.stdout.write(f"PLATE_MAP_WRITTEN: {args.out}\n")
        return 0
    if args.command == "validate":
        validate(args.profile, args.input)
        sys.stdout.write(f"PLATE_MAP_VALID: {args.input}\n")
        return 0
    unmapped = annotate(args.profile, args.input, args.out, args.well_column)
    state = "PASS" if unmapped == 0 else "PASS_WITH_HOLDS"
    sys.stdout.write(f"PLATE_MAP_{state}: rows with mapping_state=UNMAPPED: {unmapped}; output={args.out}\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PlateMapRefusal as exc:
        sys.stderr.write(f"{exc}\n")
        raise SystemExit(2)
