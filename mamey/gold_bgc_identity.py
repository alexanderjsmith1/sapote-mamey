"""Same-package native Gold identity admission; no scans, inference or package writes."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from pathlib import Path

from .exact_identity import (
    ExactLocusIdentityError,
    exact_locus_from_native_inventory_row,
    exact_locus_from_native_manifest_bgc,
)

SCHEMA = "gold_bgc_identity_v1"
CHANNELS = ("architecture", "tta", "resistance", "umed", "cctt_triggers")


class GoldBGCIdentityError(ValueError):
    """A content-free reason code safe for public hold receipts."""


def _hold(code):
    raise GoldBGCIdentityError(code)


def canonical_digest(value):
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError):
        _hold("GOLD_IDENTITY_PAYLOAD_INVALID")
    return hashlib.sha256(raw).hexdigest()


def _key(identity):
    return (identity.strain, identity.full_contig, identity.region, identity.bgc_alias)


def _identity_dict(identity):
    return {"strain_id": identity.strain, "contig": identity.full_contig,
            "node_id": identity.normalized_node_id, "antismash_region": identity.region,
            "bgc_id": identity.bgc_alias}


def _admit_records(strain, records, adapter):
    if not isinstance(records, list):
        _hold("GOLD_IDENTITY_RECORDS_UNAVAILABLE")
    admitted, physical = {}, set()
    for record in records:
        if not isinstance(record, dict):
            _hold("GOLD_IDENTITY_RECORD_INVALID")
        try:
            identity = adapter(strain, record)
        except (ExactLocusIdentityError, TypeError, ValueError):
            _hold("GOLD_IDENTITY_COMPONENT_CONFLICT")
        key = _key(identity)
        if key in admitted:
            _hold("GOLD_IDENTITY_DUPLICATE")
        if key[:3] in physical:
            _hold("GOLD_IDENTITY_PHYSICAL_CONFLICT")
        physical.add(key[:3])
        admitted[key] = (identity, record)
    return admitted


def _count(value):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0 or int(value) != value):
        _hold("GOLD_MEASUREMENT_INVALID")


def _validate_measurements(record):
    if record.get("coverage") != {channel: "MEASURED" for channel in CHANNELS}:
        _hold("GOLD_MEASUREMENT_COVERAGE_UNAVAILABLE")
    architecture = record.get("architecture")
    if not isinstance(architecture, dict) or not isinstance(architecture.get("domain_counts"), dict):
        _hold("GOLD_MEASUREMENT_COVERAGE_UNAVAILABLE")
    if not isinstance(architecture.get("domains"), list):
        _hold("GOLD_MEASUREMENT_COVERAGE_UNAVAILABLE")
    for name, count in architecture["domain_counts"].items():
        if not isinstance(name, str):
            _hold("GOLD_MEASUREMENT_INVALID")
        _count(count)
    for name in ("module_count", "domain_hit_count"):
        _count(architecture.get(name))
    if architecture["domain_hit_count"] != len(architecture["domains"]):
        _hold("GOLD_MEASUREMENT_INVALID")
    if not isinstance(architecture.get("core_summary"), list):
        _hold("GOLD_MEASUREMENT_COVERAGE_UNAVAILABLE")
    tta, resistance, umed = record.get("tta"), record.get("resistance"), record.get("umed")
    if not all(isinstance(part, dict) for part in (tta, resistance, umed)):
        _hold("GOLD_MEASUREMENT_COVERAGE_UNAVAILABLE")
    for name in ("tta_codons", "tta_cds"):
        _count(tta.get(name))
    for value in (resistance.get("tier"), umed.get("verdict")):
        if not isinstance(value, str) or not value.strip():
            _hold("GOLD_MEASUREMENT_COVERAGE_UNAVAILABLE")
    triggers = record.get("cctt_triggers")
    if not isinstance(triggers, list) or any(not isinstance(x, str) or not x for x in triggers):
        _hold("GOLD_MEASUREMENT_COVERAGE_UNAVAILABLE")


def load_gold_identity_context(package_dir, strain, snapshot=None):
    """Bind the producer ledger to actual native inventory and manifest records.

    This reader intentionally supports pre-seal native packages. The normal
    package seal owns produced files later; no self-referential manifest hash is
    introduced. Stored receipts are never accepted in place of actual records.
    """
    package = Path(package_dir)
    try:
        manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or manifest.get("strain_id") != strain:
            _hold("GOLD_IDENTITY_STRAIN_CONFLICT")
        files = list(package.glob("*_2_inventory.csv"))
        if len(files) != 1:
            _hold("GOLD_IDENTITY_INVENTORY_UNAVAILABLE")
        inventory_raw = files[0].read_bytes()
        with io.StringIO(inventory_raw.decode("utf-8"), newline="") as stream:
            reader = csv.DictReader(stream)
            required = ("Strain", "Contig", "Node_ID", "antiSMASH_Region", "BGC_ID")
            if any((reader.fieldnames or []).count(name) != 1 for name in required):
                _hold("GOLD_IDENTITY_INVENTORY_HEADERS_INVALID")
            inventory = list(reader)
        native = _admit_records(strain, manifest.get("bgcs"), exact_locus_from_native_manifest_bgc)
        board = _admit_records(strain, inventory, exact_locus_from_native_inventory_row)
        if set(native) != set(board):
            _hold("GOLD_IDENTITY_INVENTORY_MEMBERSHIP_CONFLICT")
        if any(_identity_dict(native[k][0]) != _identity_dict(board[k][0]) for k in native):
            _hold("GOLD_IDENTITY_INVENTORY_VALUE_CONFLICT")
        ledger = manifest.get("source_scans", {}).get("domain_architecture", {}).get("native_bgc_profiles_v1")
        if not isinstance(ledger, dict) or ledger.get("schema_version") != "native_bgc_profiles_v1":
            _hold("GOLD_IDENTITY_NATIVE_LEDGER_UNAVAILABLE")
        records = ledger.get("records")
        if not isinstance(records, list) or any(not isinstance(r, dict) for r in records):
            _hold("GOLD_IDENTITY_NATIVE_LEDGER_INVALID")
        anchors = _admit_records(strain, [r.get("identity") for r in records],
                                 exact_locus_from_native_manifest_bgc)
        if set(anchors) != set(native) or len(records) != len(native):
            _hold("GOLD_IDENTITY_SOURCE_MEMBERSHIP_CONFLICT")
        if snapshot is not None:
            if not isinstance(snapshot, dict) or snapshot.get("strain_id") != strain:
                _hold("GOLD_IDENTITY_SNAPSHOT_CONFLICT")
            if canonical_digest(snapshot.get("bgcs")) != canonical_digest(manifest.get("bgcs")):
                _hold("GOLD_IDENTITY_SNAPSHOT_CONFLICT")
            other = snapshot.get("source_scans", {}).get("domain_architecture", {}).get("native_bgc_profiles_v1")
            if canonical_digest(other) != canonical_digest(ledger):
                _hold("GOLD_IDENTITY_SNAPSHOT_CONFLICT")
        bound = []
        for index, record in enumerate(records, 1):
            if type(record.get("source_record_index")) is not int or record["source_record_index"] != index:
                _hold("GOLD_IDENTITY_SOURCE_ORDER_CONFLICT")
            identity = exact_locus_from_native_manifest_bgc(strain, record["identity"])
            key = _key(identity)
            if _identity_dict(identity) != _identity_dict(native[key][0]):
                _hold("GOLD_IDENTITY_SOURCE_VALUE_CONFLICT")
            _validate_measurements(record)
            bound.append({**record, "bgc_identity": _identity_dict(board[key][0]),
                          "exact_locus": board[key][0].exact_locus})
        receipt = {"schema_version": SCHEMA, "status": "BOUND_NATIVE_INVENTORY",
                   "records": len(bound), "inventory_sha256": hashlib.sha256(inventory_raw).hexdigest(),
                   "manifest_identity_sha256": canonical_digest([_identity_dict(v[0]) for v in native.values()]),
                   "native_ledger_sha256": canonical_digest(ledger)}
        return {"records": bound, "receipt": receipt}
    except GoldBGCIdentityError:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError, csv.Error):
        _hold("GOLD_IDENTITY_CONTEXT_UNAVAILABLE")


def admit_gold_profiles(package_dir, strain, deep, gene):
    """Re-read same-package sources and compare exact identity and measurements."""
    from .deep_data import extract_profiles
    context = load_gold_identity_context(package_dir, strain)
    receipt = context["receipt"]
    if deep.get("bgc_identity_contract") != receipt or gene.get("bgc_identity_contract") != receipt:
        _hold("GOLD_IDENTITY_BINDING_CHANGED")
    profiles, architectures, _ = extract_profiles(strain, {}, identity_context=context)
    if deep.get("bgc_profile") != profiles:
        _hold("GOLD_IDENTITY_PROFILE_SOURCE_CONFLICT")
    actual_architectures = gene.get("domain_arch")
    if not isinstance(actual_architectures, list) or len(actual_architectures) != len(architectures):
        _hold("GOLD_IDENTITY_PROFILE_SOURCE_CONFLICT")
    # The historical architecture string preserves source dict insertion order.
    # A final manifest rewrite can change key order without changing evidence.
    # Compare its literal measurement shape, never eval or reinterpret classifiers.
    import ast
    for actual, expected in zip(actual_architectures, architectures):
        if not isinstance(actual, dict):
            _hold("GOLD_IDENTITY_PROFILE_SOURCE_CONFLICT")
        if {k: v for k, v in actual.items() if k != "architecture"} != {k: v for k, v in expected.items() if k != "architecture"}:
            _hold("GOLD_IDENTITY_PROFILE_SOURCE_CONFLICT")
        try:
            observed = ast.literal_eval(actual["architecture"])
            projected = ast.literal_eval(expected["architecture"])
        except (ValueError, TypeError, SyntaxError, KeyError):
            _hold("GOLD_IDENTITY_PROFILE_SOURCE_CONFLICT")
        if not isinstance(observed, dict) or canonical_digest(observed) != canonical_digest(projected):
            _hold("GOLD_IDENTITY_PROFILE_SOURCE_CONFLICT")
    return profiles, context
