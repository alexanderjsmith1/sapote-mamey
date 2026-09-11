#!/usr/bin/env python3
"""Add deposited source text by exact versioned accession to new metadata.

Reads a frozen SQLite record table; never updates it or the original metadata.
An accession lookup identifies a record, not sequence identity or shared habitat.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sqlite3
import sys

from _console import emit
import logging
_LOG = logging.getLogger(__name__)

from collapse_near_identical import binding, read_meta, tsv_bytes, write_exclusive
from tip_label import accession, accession_candidates, _text

SOURCE_COLUMNS = ("isolation_source", "host", "geo_loc_name")
ADDED_COLUMNS = ("source_label_state", "source_record_accession", "source_record_field",
                 "source_record_value", "source_record_json")


def enrich(meta, db, output):
    meta, db, output = map(Path, (meta, db, output))
    receipt_path = Path(str(output) + ".receipt.json")
    if any(p.exists() or p.is_symlink() for p in (output, receipt_path)):
        raise ValueError("OUTPUT_EXISTS")
    if output.resolve() in {meta.resolve(), db.resolve()}:
        raise ValueError("OUTPUT_ALIASES_INPUT")
    if not db.is_file():
        raise ValueError("SOURCE_DATABASE_MISSING")
    if any(Path(str(db) + suffix).exists() for suffix in ("-wal", "-journal")):
        raise ValueError("SOURCE_DATABASE_REQUIRES_FROZEN_CHECKPOINTED_SNAPSHOT")
    inputs = {"metadata": binding(meta, output.parent.resolve()), "database": binding(db, output.parent.resolve())}
    header, rows = read_meta(meta)
    if set(ADDED_COLUMNS) & set(header) or "display_members" in header:
        raise ValueError("SOURCE_LABELS_REQUIRE_ORIGINAL_METADATA")
    con = sqlite3.connect(db.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        columns = {r[1] for r in con.execute("PRAGMA table_info(record)")}
        if "acc_version" not in columns:
            raise ValueError("DATABASE_REQUIRES_record_acc_version")
        available = [c for c in SOURCE_COLUMNS if c in columns]
        output_rows = []
        for original in rows:
            row = dict(original, **{c: "" for c in ADDED_COLUMNS})
            row["source_label_state"] = "NOT_REFERENCE"
            if row["role"] != "reference":
                output_rows.append(row)
                continue
            # Reuse the canonical candidate parser. Multiple distinct tokens,
            # versionless tokens and field conflicts never select a record.
            candidate = accession_candidates(" ".join(row.get(c, "") for c in ("tip", "label", "accession")))
            acc = accession(row.get("accession", "")) if row.get("accession") else accession(" ".join((row["tip"], row["label"])))
            if candidate["state"] == "AMBIGUOUS" or not acc or "." not in acc:
                row["source_label_state"] = "ACCESSION_UNBOUND_OR_CONFLICTING"
            elif not available:
                row["source_label_state"] = "DATABASE_SOURCE_FIELDS_UNAVAILABLE"
            else:
                records = con.execute("SELECT acc_version," + ",".join(available) +
                                      " FROM record WHERE acc_version=?", (acc,)).fetchall()
                if len(records) != 1:
                    row["source_label_state"] = "RECORD_MISSING" if not records else "RECORD_AMBIGUOUS"
                else:
                    record = dict(zip(["acc_version"] + available, records[0]))
                    row["source_record_accession"] = acc
                    row["source_record_json"] = json.dumps(record, sort_keys=True, ensure_ascii=True)
                    field = next((c for c in available if str(record[c] or "").strip()), "")
                    value = str(record[field]).strip() if field else ""
                    row["source_record_field"], row["source_record_value"] = field, value
                    if not value:
                        row["source_label_state"] = "DEPOSITED_SOURCE_NOT_RECORDED"
                    elif "[" in row["label"]:
                        row["source_label_state"] = "EXISTING_LABEL_RETAINED_REVIEW_SOURCE"
                    else:
                        _text(value)
                        # Preserve the full existing organism/strain/type/accession
                        # label instead of re-parsing the organism or shortening it.
                        marker = row["label"].find(" (T)")
                        if marker < 0:
                            marker = row["label"].find(" (" + acc + ")")
                        if marker < 0:
                            marker = len(row["label"])
                        # Geographic fallback is explicitly geographic, not habitat.
                        display = "location: " + value if field == "geo_loc_name" else value
                        row["label"] = row["label"][:marker] + " [" + display + "]" + row["label"][marker:]
                        row["source_label_state"] = "EXACT_VERSION_RECORD_SOURCE_ADDED"
            output_rows.append(row)
    finally:
        con.close()
    if inputs != {"metadata": binding(meta, output.parent.resolve()), "database": binding(db, output.parent.resolve())}:
        raise ValueError("INPUT_CHANGED_DURING_SOURCE_LOOKUP")
    write_exclusive(output, tsv_bytes(header + list(ADDED_COLUMNS), output_rows))
    receipt = {"schema": "sapote.reference-source-labels.v1", "inputs": inputs,
               "output": binding(output, output.parent.resolve()),
               "authority": "DEPOSITED_RECORD_TEXT_ONLY_NOT_SEQUENCE_IDENTITY"}
    write_exclusive(receipt_path, (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())
    return output_rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    ap.add_argument("meta"); ap.add_argument("--db", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    try:
        rows = enrich(a.meta, a.db, a.out)
        refs = [r for r in rows if r["role"] == "reference"]
        changed = sum(r["source_label_state"] == "EXACT_VERSION_RECORD_SOURCE_ADDED" for r in refs)
        _LOG.info(f"References: {len(refs)}; deposited source added: {changed}; other states retained in metadata")
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        _LOG.error(f"REFUSED [REFERENCE_SOURCE_LABELS]: {exc}")
        return 2


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    raise SystemExit(main())
