#!/usr/bin/env python3
"""ingest_field_collection.py -- normalize Alex's field-collection workbook into a per-strain
collection-metadata TSV the rest of the engine can bind (placement host/origin tables, bioassay
cohort grouping, strain-metadata reconciliation).

FIRST-PASS / PRELIMINARY (peer-lane, first staged at v9.7.427). Reads the `Isolate Index` sheet of
`Field_Collection_Master_Data.xlsx` -- one row per AS code with the collector's own fields
(Experiment, Sample, Description, Simple Group, Category, Location, Date) -- and emits a normalized
TSV keyed by canonical AS id.

GOVERNANCE (governing, do not soften):
  * This is DESCRIPTIVE COLLECTION-RECORD provenance -- the collector's field note of what the
    isolate was picked off and where. It is NOT a tested host association and NOT authority over
    deposited GenBank /host metadata; it is a source to RECONCILE against those, per the standing
    rulings ([[deposited-genbank-is-a-provenance-source]], [[strain-summary-is-not-an-ecology-source]]).
  * Raw values are copied VERBATIM. This tool does not categorize, does not force a value into a
    fixed palette, and does not invent a mapping ([[report-isolation-source-do-not-categorize]]).
    `category_raw` / `location_raw` are exactly the cells; any bucketing is a downstream decision.
  * A duplicated AS code with conflicting non-empty values is REFUSED (typed), never silently
    merged -- an identity conflict is a hold, not a pick.

No workspace path is baked in: the workbook is an explicit --input. Emission is via sys.stdout/
sys.stderr only (no print()/emit()), keeping the strict-health print_calls ratchet flat.

Usage:
  ingest_field_collection.py --input <Field_Collection_Master_Data.xlsx> --out <collection.tsv>
      [--sheet "Isolate Index"]
"""
from __future__ import annotations

import argparse
import collections
import re
import sys

SOURCE_COLUMNS = ("AS code", "Experiment", "Sample", "Description", "Simple Group",
                  "Category", "Location", "Date")
# output column -> source column (raw is preserved; only the AS id is canonicalized)
OUT_FIELDS = (
    ("as_id", "AS code"),
    ("category_raw", "Category"),
    ("simple_group_raw", "Simple Group"),
    ("location_raw", "Location"),
    ("date", "Date"),
    ("experiment", "Experiment"),
    ("sample", "Sample"),
    ("description_raw", "Description"),
)
_TYPED_CODES = frozenset({"FIELD_COLLECTION_SCHEMA", "FIELD_COLLECTION_EMPTY",
                          "FIELD_COLLECTION_IDENTITY_CONFLICT"})


def _refuse(code: str, detail: str) -> "NoReturn":  # type: ignore[name-defined]
    sys.stderr.write(f"{code}: {detail}\n")
    raise SystemExit(2)


def _canon_as(raw) -> str:
    """Canonicalize a strain cell to AS-<n> / SID-<n>; '' if it is not a strain code."""
    s = ("" if raw is None else str(raw)).strip()
    if not s:
        return ""
    m = re.search(r"(AS|SID)[\s\-_]*0*([0-9]+)", s.upper())
    return f"{m.group(1)}-{m.group(2)}" if m else ""


def _clean(v) -> str:
    return "" if v is None else str(v).strip()


def load_isolate_rows(path: str, sheet: str):
    """Return list[dict] of the sheet's rows keyed by the source header, or raise a typed code."""
    try:
        import openpyxl  # declared bundle dep (>=3.1.2)
    except ImportError:
        _refuse("FIELD_COLLECTION_SCHEMA", "openpyxl is required to read the .xlsx workbook")
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001 -- surface the real reason, do not swallow
        _refuse("FIELD_COLLECTION_SCHEMA", f"cannot open workbook {path}: {exc}")
    if sheet not in wb.sheetnames:
        _refuse("FIELD_COLLECTION_SCHEMA",
                f"sheet {sheet!r} not found; available: {wb.sheetnames}")
    ws = wb[sheet]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise ValueError("FIELD_COLLECTION_EMPTY")
    header = [_clean(c) for c in rows[0]]
    missing = [c for c in SOURCE_COLUMNS if c not in header]
    if missing:
        raise ValueError("FIELD_COLLECTION_SCHEMA")
    idx = {name: header.index(name) for name in SOURCE_COLUMNS}
    out = []
    for r in rows[1:]:
        rec = {name: (r[i] if i < len(r) else None) for name, i in idx.items()}
        out.append(rec)
    return out


def normalize(rows):
    """Collapse to one record per canonical AS id; refuse on a genuine value conflict."""
    by_id = {}
    dropped_no_code = 0
    for rec in rows:
        aid = _canon_as(rec.get("AS code"))
        if not aid:
            dropped_no_code += 1
            continue
        norm = {out: _clean(rec.get(src)) for out, src in OUT_FIELDS}
        norm["as_id"] = aid
        if aid in by_id:
            prev = by_id[aid]
            for k in norm:
                if k == "as_id":
                    continue
                if norm[k] and prev[k] and norm[k] != prev[k]:
                    raise ValueError("FIELD_COLLECTION_IDENTITY_CONFLICT")
                if norm[k] and not prev[k]:
                    prev[k] = norm[k]
        else:
            by_id[aid] = norm
    if not by_id:
        raise ValueError("FIELD_COLLECTION_EMPTY")
    return by_id, dropped_no_code


def main():
    ap = argparse.ArgumentParser(allow_abbrev=False, description=__doc__)
    ap.add_argument("--input", required=True, help="Field_Collection_Master_Data.xlsx")
    ap.add_argument("--out", required=True, help="output normalized collection-metadata TSV")
    ap.add_argument("--sheet", default="Isolate Index", help="worksheet name (default 'Isolate Index')")
    a = ap.parse_args()

    rows = load_isolate_rows(a.input, a.sheet)
    by_id, dropped = normalize(rows)

    fields = [out for out, _ in OUT_FIELDS]
    with open(a.out, "w", encoding="utf-8", newline="") as fh:
        fh.write("\t".join(fields) + "\n")
        for aid in sorted(by_id):
            fh.write("\t".join(by_id[aid][f] for f in fields) + "\n")

    cats = collections.Counter(v["category_raw"] for v in by_id.values() if v["category_raw"])
    sys.stdout.write(
        f"[field-collection] {len(by_id)} strains -> {a.out}"
        f" ({dropped} non-strain rows skipped);"
        f" top raw categories: {', '.join(f'{k}={n}' for k, n in cats.most_common(6))}\n")
    sys.stdout.write("[field-collection] NOTE: collection-record provenance, verbatim; reconcile "
                     "against deposited GenBank /host -- not authority over it, not a tested "
                     "host association.\n")
    return 0


def _run_or_refuse():
    try:
        return main()
    except ValueError as exc:
        code = str(exc)
        if code not in _TYPED_CODES:
            raise
        _refuse(code, "input contract violated; no output was written. The code above names the "
                      "contract that failed.")


if __name__ == "__main__":
    sys.exit(_run_or_refuse())
