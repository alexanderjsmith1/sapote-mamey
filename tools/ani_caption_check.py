#!/usr/bin/env python3
"""Check that a caption/table names ANI versus AAI honestly and flags boundary values.

The tool reads already-computed values.  It does not run ANI, AAI, alignment,
or tree software.  Its receipt must bind the input bytes and name exactly one
metric: ``nucleotide_ANI`` or ``core_SCG_AAI``.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path


ALLOWED_METRICS = {"nucleotide_ANI": "ANI", "core_SCG_AAI": "AAI"}
BOUNDARY_LOW = 94.0
BOUNDARY_HIGH = 96.0
_PERCENT = re.compile(r"(?<![\w.])(\d{1,3}(?:\.\d+)?)\s*%")


class CaptionMetricError(ValueError):
    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(f"{code}: {detail}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _receipt(path: Path, source: Path) -> tuple[str, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CaptionMetricError("ANI_RECEIPT_INVALID", type(exc).__name__) from exc
    if not isinstance(payload, dict):
        raise CaptionMetricError("ANI_RECEIPT_INVALID", "JSON object required")
    metric = str(payload.get("metric") or "").strip()
    if metric not in ALLOWED_METRICS:
        raise CaptionMetricError("ANI_METRIC_INVALID", repr(metric))
    expected_hash = str(payload.get("input_sha256") or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash) or expected_hash != _sha256(source):
        raise CaptionMetricError("ANI_INPUT_HASH_MISMATCH", source.name)
    value_column = str(payload.get("value_column") or "").strip() or None
    return metric, value_column


def _table_values(path: Path, text: str, value_column: str | None) -> list[float]:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    rows = list(csv.DictReader(text.splitlines(), delimiter=delimiter))
    if not rows or not rows[0]:
        raise CaptionMetricError("ANI_VALUE_MISSING", "table has no data rows")
    column = value_column or next(
        (name for name in rows[0] if name and name.strip().casefold() in {"value", "percent", "identity_pct"}),
        None,
    )
    if column is None or column not in rows[0]:
        raise CaptionMetricError("ANI_VALUE_COLUMN_MISSING", value_column or "value|percent|identity_pct")
    values: list[float] = []
    for row_number, row in enumerate(rows, start=2):
        raw = str(row.get(column) or "").strip().removesuffix("%").strip()
        if not raw:
            continue
        try:
            values.append(float(raw))
        except ValueError as exc:
            raise CaptionMetricError("ANI_VALUE_INVALID", f"row {row_number} column {column}") from exc
    return values


def check_caption_or_table(source: str | Path, receipt: str | Path) -> dict[str, object]:
    source_path = Path(source)
    receipt_path = Path(receipt)
    try:
        text = source_path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        raise CaptionMetricError("ANI_INPUT_INVALID", type(exc).__name__) from exc
    metric, value_column = _receipt(receipt_path, source_path)
    expected = ALLOWED_METRICS[metric]
    forbidden = "AAI" if expected == "ANI" else "ANI"
    label_text = re.sub(r"[_-]+", " ", text.upper())
    if re.search(rf"\b{forbidden}\b", label_text):
        raise CaptionMetricError("ANI_AAI_LABEL_CONFLICT", f"receipt={metric}; text names {forbidden}")
    if not re.search(rf"\b{expected}\b", label_text):
        raise CaptionMetricError("ANI_METRIC_LABEL_MISSING", f"text must name {expected}")

    if source_path.suffix.lower() in {".csv", ".tsv"}:
        values = _table_values(source_path, text, value_column)
    else:
        values = [float(match) for match in _PERCENT.findall(text)]
    if not values:
        raise CaptionMetricError("ANI_VALUE_MISSING", source_path.name)
    invalid = [value for value in values if not 0.0 <= value <= 100.0]
    if invalid:
        raise CaptionMetricError("ANI_VALUE_INVALID", repr(invalid))
    boundary = [value for value in values if BOUNDARY_LOW <= value <= BOUNDARY_HIGH]
    return {
        "status": "BOUNDARY" if boundary else "NON_BOUNDARY",
        "metric": metric,
        "display_label": expected,
        "values_pct": values,
        "boundary_values_pct": boundary,
        "input_sha256": _sha256(source_path),
        "claim_ceiling": (
            "Values from 94.0% through 96.0% are boundary/indeterminate, not a confident "
            "same-species call. AAI is not ANI. This check does not validate taxonomy or a tree."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="UTF-8 caption, Markdown, CSV, or TSV")
    parser.add_argument("--receipt", required=True, help="JSON metric and input-hash receipt")
    args = parser.parse_args(argv)
    try:
        result = check_caption_or_table(args.input, args.receipt)
    except CaptionMetricError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 2
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
