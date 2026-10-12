"""Report-only source availability. Never infer an upstream search or biology."""
from pathlib import Path
import json

SCHEMA = "rrefinder_evidence_state_v1"
STATES = {"NOT_REQUESTED", "SOURCE_UNAVAILABLE", "PARSE_FAILED", "SOURCE_HELD",
          "SOURCE_PARTIAL", "SOURCE_OBSERVED_EMPTY", "SOURCE_OBSERVED_HITS",
          "SOURCE_CONFLICT", "UNKNOWN_COMPLETENESS"}


def _state(state, count, completeness="UNKNOWN", receipt=None, *, raw_count=None):
    return {"schema": SCHEMA, "state": state, "source_rows": count,
            "retained_rows": count, "raw_source_rows": raw_count,
            "source_completeness": completeness, "upstream_search": "UNKNOWN",
            "biological_absence": "NOT_ESTABLISHED", "extraction_receipt": receipt}


def source_identity_conflict(row):
    containing = str(row.get("record_id") or "")
    declared = str(row.get("module_record_id") or "")
    return bool(row.get("identity_conflict")) or bool(containing and declared and containing != declared)


def _count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _receipt_state(receipt, requested, row_count, raw_count):
    """Reconcile recorded extraction metadata; this cannot attest upstream search."""
    def result(state, completeness="UNKNOWN"):
        return _state(state, row_count, completeness, receipt, raw_count=raw_count)

    if isinstance(receipt, dict):
        declared = receipt.get("rrefinder_requested")
        if requested is not None and declared is not None and requested != declared:
            return result("SOURCE_CONFLICT")
        requested = declared if declared is not None else requested
    if requested is False:
        return result("SOURCE_CONFLICT" if row_count or raw_count else "NOT_REQUESTED")
    if not isinstance(receipt, dict) or receipt.get("schema") != "record_extraction_receipt_v1":
        return result("UNKNOWN_COMPLETENESS")
    files = receipt.get("files", [])
    handlers = receipt.get("handlers", [])
    archive_errors = receipt.get("archive_errors", [])
    if (not isinstance(files, list) or not all(isinstance(item, dict) for item in files)
            or not isinstance(handlers, list) or not isinstance(archive_errors, list)
            or not _count(raw_count) or not _count(row_count) or row_count > raw_count
            or not _count(receipt.get("rrefinder_hit_count"))
            or requested is not True or "_rrefinder_from_rec" not in handlers
            or receipt.get("rrefinder_hit_count") != raw_count):
        return result("SOURCE_CONFLICT")
    for item in files:
        errors = item.get("errors", [])
        counters = item.get("error_counts", {})
        if (not all(_count(item.get(key, 0)) for key in
                    ("records_seen", "rrefinder_modules_read", "rrefinder_identity_conflicts"))
                or not isinstance(errors, list) or not all(isinstance(error, dict) for error in errors)
                or not isinstance(counters, dict) or not _count(counters.get("_rrefinder_from_rec", 0))
                or item.get("rrefinder_modules_read", 0) > item.get("records_seen", 0)
                or item.get("rrefinder_identity_conflicts", 0) > item.get("records_seen", 0)):
            return result("SOURCE_CONFLICT")
    if any(item.get("rrefinder_identity_conflicts", 0) for item in files):
        return result("SOURCE_CONFLICT", "CONFLICTED_IDENTITY")
    errors = list(archive_errors)
    errors += [error for item in files for error in item.get("errors", [])
               if error.get("handler") in ("FILE_READER", "_rrefinder_from_rec")]
    records = sum(item.get("records_seen", 0) for item in files)
    modules = sum(item.get("rrefinder_modules_read", 0) for item in files)
    failed = errors or any(item.get("status") == "PARSE_FAILED"
                           or item.get("error_counts", {}).get("_rrefinder_from_rec", 0)
                           for item in files)
    held = any(item.get("status") == "HELD_SIZE_CAP" for item in files)
    complete = bool(files) and all(item.get("status") == "READ_COMPLETE" for item in files)
    if failed or held:
        state = ("SOURCE_PARTIAL" if row_count or modules else
                 "PARSE_FAILED" if failed else "SOURCE_HELD")
        return result(state, "PARTIAL" if state == "SOURCE_PARTIAL" else "INCOMPLETE")
    if not records or not modules:
        return result("SOURCE_UNAVAILABLE", "INCOMPLETE")
    if not complete or modules < records:
        return result("SOURCE_PARTIAL", "PARTIAL")
    return result("SOURCE_OBSERVED_HITS" if row_count else "SOURCE_OBSERVED_EMPTY",
                  "COMPLETE_FOR_SELECTED_SOURCE_RECORDS")


def derive_rrefinder_state(evidence, row_count):
    raw_rows = evidence.get("rrefinder_hits", [])
    raw_count = len(raw_rows) if isinstance(raw_rows, list) else None
    receipt = evidence.get("record_extraction")
    if raw_count is None or not all(isinstance(row, dict) for row in raw_rows):
        return _state("SOURCE_CONFLICT", row_count, receipt=receipt, raw_count=raw_count)
    if any(source_identity_conflict(row) for row in raw_rows):
        return _state("SOURCE_CONFLICT", row_count, "CONFLICTED_IDENTITY", receipt, raw_count=raw_count)
    return _receipt_state(receipt, evidence.get("record_extras_requested"), row_count, raw_count)


def state_from_structured(structured):
    rows = structured.get("rrefinder", [])
    count = len(rows) if isinstance(rows, list) else 0
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        return _state("SOURCE_CONFLICT", count)
    state = structured.get("rrefinder_evidence_state")
    if not isinstance(state, dict) or not state:
        return _state("UNKNOWN_COMPLETENESS", count)
    if (state.get("schema") != SCHEMA or not isinstance(state.get("state"), str)
            or state.get("state") not in STATES
            or not _count(state.get("source_rows")) or state["source_rows"] != count
            or ("retained_rows" in state and (not _count(state["retained_rows"]) or state["retained_rows"] != count))
            or state.get("upstream_search") != "UNKNOWN"
            or state.get("biological_absence") != "NOT_ESTABLISHED"
            or not isinstance(state.get("source_completeness"), str)
            or state.get("source_completeness") not in {"UNKNOWN", "INCOMPLETE", "PARTIAL",
                 "COMPLETE_FOR_SELECTED_SOURCE_RECORDS", "CONFLICTED_IDENTITY"}
            or (state.get("state") in ("NOT_REQUESTED", "SOURCE_OBSERVED_EMPTY") and count != 0)
            or (state.get("state") == "SOURCE_OBSERVED_HITS" and count == 0)):
        return _state("SOURCE_CONFLICT", count)
    if any(not isinstance(row.get("record_id", ""), str)
           or not isinstance(row.get("contig", ""), str)
           or ("module_record_id" in row and not isinstance(row["module_record_id"], str))
           or source_identity_conflict(row)
           or bool(row.get("record_id") and row.get("contig") and row["record_id"] != row["contig"])
           or row.get("mapping_status") == "IDENTITY_CONFLICT_SOURCE_RECORD"
           or str(row.get("mapping_method") or "").startswith("SOURCE_RECORD_ID_CONFLICT:")
           for row in rows):
        return _state("SOURCE_CONFLICT", count, "CONFLICTED_IDENTITY")
    receipt = state.get("extraction_receipt")
    if not isinstance(receipt, dict) or receipt.get("schema") != "record_extraction_receipt_v1":
        if state["state"] == "NOT_REQUESTED" and state["source_completeness"] == "UNKNOWN":
            return state
        if state["state"] == "SOURCE_CONFLICT": return _state("SOURCE_CONFLICT", count)
        return _state("UNKNOWN_COMPLETENESS", count)
    raw_count = state.get("raw_source_rows", receipt.get("rrefinder_hit_count"))
    expected = _receipt_state(receipt, receipt.get("rrefinder_requested"), count, raw_count)
    if (state["state"] != expected["state"]
            or state["source_completeness"] != expected["source_completeness"]):
        return _state("SOURCE_CONFLICT", count, receipt=receipt, raw_count=raw_count)
    return state


def read_package_state(package_dir, strain):
    pkg = Path(package_dir)
    path = pkg / (str(strain) + "_3_antismash_structured.json")
    # Exact bound strain filename; no first-match fallback to another strain.
    if path.parent != pkg or not path.is_file():
        return _state("SOURCE_UNAVAILABLE", None)
    try:
        structured = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(structured, dict):
            raise ValueError("STRUCTURED_TABLE_NOT_OBJECT")
        return state_from_structured(structured)
    except (OSError, ValueError, TypeError):
        return _state("PARSE_FAILED", None)


def describe_state(state):
    count = state["source_rows"]
    displayed_count = "unavailable" if count is None else str(count)
    return (f"RREfinder: {state['state']}; retained source rows: {displayed_count}; "
            f"source completeness: {state['source_completeness']}. "
            "Upstream search completion is UNKNOWN. Biological absence is not established.")
