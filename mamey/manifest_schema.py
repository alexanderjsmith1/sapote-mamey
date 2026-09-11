"""manifest_schema.py — canonical manifest field names + a fail-loud accessor.

SSOT for every read of manifest.json / manifest_short.json across the engine.
Closes the phantom-schema class: the v9.7.149a session_resume bug read a
top-level `assembly_tier` from manifest.json (a field that lives in
manifest_short.json, or nested under manifest.json["bgc_counts"]) and silently
got None -> "UNKNOWN". That fix corrected one call site; this module removes the
*mechanism* by which a hallucinated field name compiles and fails silently.

Field constants below are validated against a real v9.7.158 gold package
(S_laurentii). MANIFEST_FIELDS and MANIFEST_SHORT_FIELDS are the declared
schemas; read_manifest_field() RAISES UnknownManifestField on any name not in
the union, so a typo or hallucinated key fails loudly at call time (and in
tests) instead of returning None against a real package.

Design note: assembly_tier / interior_pct / n50 / contigs are the classic trap.
The first two live in manifest_short.json (flat) OR
manifest.json["bgc_counts"] (nested); n50 / contigs live under
manifest.json["assembly"]. None is a top-level manifest.json field.
read_manifest_field() knows the fallback so callers
stop hand-rolling `ms.get("assembly_tier") or man["assembly"]["tier"]` chains
(the compile_report pattern) inconsistently.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


class UnknownManifestField(KeyError):
    """Raised when code asks for a manifest field name not in the declared schema."""


# ---- manifest.json top-level fields (validated: S_laurentii v9.7.158 gold) ----
MANIFEST_FIELDS: frozenset[str] = frozenset({
    "strain_id", "display_name", "workflow_version", "bundle_version",
    "release", "privacy_tier", "privacy_assignment_state",
    "analysis_date", "mode",
    "taxonomy", "source", "bioactivity", "assembly", "bgc_counts", "bgcs",
    "scan_status", "source_scans", "bgc_crosswalk", "top_bgc_targets",
    "split_pathway_candidates", "hallucination_traps_triggered",
    "resistance_gene_summary", "wet_lab_priorities", "metabolomics_targets",
    "missingness", "recommended_next_steps", "cross_strain_context", "issues",
    "antismash_profile", "package_dir", "package_status", "claim_safety_status",
    "files", "terminal_status", "issue_count",
    # AUDIT_374: 4 real, currently-written top-level manifest.json fields confirmed
    # missing from this schema by tracing MameyRun.to_dict() (models.py) and cli.py's
    # post-processing manifest_data[...] assignments. Their absence made
    # read_manifest_field() raise UnknownManifestField on genuinely real field names, and
    # made validate_manifest_keys() flag them as permanent false "drift" on every real
    # sealed package -- invisible in this environment only because both real-manifest
    # tests in test_manifest_schema.py SKIP without a local gold package on disk.
    "source_provenance", "source_provenance_note", "input_zip", "input_zip_sha256",
    "reporting_features", "project_privacy", "genome_state", "bioassay_scope",
    "repro_fingerprint", "repro_fingerprint_components",
})

# ---- manifest_short.json fields (validated: S_laurentii v9.7.158 gold) ----
MANIFEST_SHORT_FIELDS: frozenset[str] = frozenset({
    "strain_id", "status", "mamey_version", "release",
    "assembly_tier", "interior_pct", "raw_bgcs", "corrected_bgcs",
    "top_3_ab", "top_3_af",
    "gene_context_jsonl", "gene_by_gene_csv", "gene_by_gene_all_bgcs_csv",
    "timing_json", "phase_receipts_path",
})

# named constants for the trap fields (import these instead of string literals)
F_ASSEMBLY_TIER = "assembly_tier"          # manifest_short OR manifest["bgc_counts"]["assembly_tier"]
F_INTERIOR_PCT = "interior_pct"            # manifest_short OR manifest["bgc_counts"]["interior_pct"]
F_CORRECTED_BGCS = "corrected_bgcs"        # manifest_short OR manifest["bgc_counts"]["corrected"]
F_RAW_BGCS = "raw_bgcs"                    # manifest_short OR manifest["bgc_counts"]["raw"]
F_N50 = "n50"                              # manifest["assembly"]["n50"] (NOT top-level)
F_CONTIGS = "contigs"                      # manifest["assembly"]["contigs"] (NOT top-level)
F_STRAIN_ID = "strain_id"
F_MODE = "mode"
F_SOURCE_SCANS = "source_scans"
F_ISSUES = "issues"                        # manifest.json top-level list[str] — run-level red flags
                                            # (CONTAMINATION_SUSPECT, RECORD_LIMIT_TRUNCATION, …)

# fields that are NOT top-level in manifest.json but live in a nested dict or in
# manifest_short — the accessor knows where to look so callers stop guessing.
_ASSEMBLY_NESTED = {F_N50: "n50", F_CONTIGS: "contigs"}
_BGC_COUNTS_NESTED = {
    F_ASSEMBLY_TIER: "assembly_tier", F_INTERIOR_PCT: "interior_pct",
    F_CORRECTED_BGCS: "corrected", F_RAW_BGCS: "raw",
}

# the full set the accessor will answer for (union + the nested-only names)
_KNOWN = MANIFEST_FIELDS | MANIFEST_SHORT_FIELDS | {F_N50, F_CONTIGS}


def read_manifest_field(field: str, *, manifest: dict | None = None,
                        manifest_short: dict | None = None,
                        default: Any = None) -> Any:
    """Read a manifest field by its canonical name, from whichever file owns it.

    Raises UnknownManifestField if `field` is not a declared schema name — this
    is the guard that turns a hallucinated/typo'd field name into a loud failure
    (at call time, and in any test that exercises the path) instead of a silent
    None against a real package.

    Resolution order for the trap fields (assembly_tier / interior_pct / n50 /
    contigs / corrected_bgcs / raw_bgcs): manifest_short flat value first, then
    the nested manifest.json location, then `default`.
    """
    if field not in _KNOWN:
        raise UnknownManifestField(
            f"{field!r} is not a declared manifest field. "
            f"Add it to MANIFEST_FIELDS/MANIFEST_SHORT_FIELDS in manifest_schema.py "
            f"if it is real, or fix the typo. (This guard exists to stop the "
            f"session_resume-class silent-None bug.)"
        )
    ms = manifest_short or {}
    man = manifest or {}

    # 1) flat value in manifest_short wins
    if field in ms and ms[field] not in (None, ""):
        return ms[field]

    # 2) nested locations in manifest.json for the trap fields
    if field in _ASSEMBLY_NESTED:
        assembly = man.get("assembly") or {}
        val = assembly.get(_ASSEMBLY_NESTED[field])
        if val not in (None, ""):
            return val
    if field in _BGC_COUNTS_NESTED:
        counts = man.get("bgc_counts") or {}
        val = counts.get(_BGC_COUNTS_NESTED[field])
        if val not in (None, ""):
            return val

    # 3) plain top-level manifest.json field
    if field in man and man[field] not in (None, ""):
        return man[field]

    return default


def validate_manifest_keys(manifest: dict, *, strict: bool = False) -> list[str]:
    """Return manifest.json keys not in the declared schema (drift detector).

    strict=True raises on any undeclared key; default just reports them so a new
    engine field surfaces in review instead of silently diverging.
    """
    unknown = [k for k in manifest if k not in MANIFEST_FIELDS]
    if strict and unknown:
        raise UnknownManifestField(f"manifest.json carries undeclared keys: {unknown}")
    return unknown


def _matches_json_type(value: Any, expected: str | list[str]) -> bool:
    expected_types = [expected] if isinstance(expected, str) else expected
    checks = {
        "null": lambda item: item is None,
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "boolean": lambda item: isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
    }
    return any(name in checks and checks[name](value) for name in expected_types)


def _validate_json_value(value: Any, schema: dict, path: str, errors: list[dict]) -> None:
    expected = schema.get("type")
    if expected is not None and not _matches_json_type(value, expected):
        errors.append({
            "code": "TYPE_MISMATCH",
            "path": path,
            "expected": expected,
            "observed": type(value).__name__,
        })
        return
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append({"code": "REQUIRED_KEY_MISSING", "path": f"{path}.{key}"})
        properties = schema.get("properties", {})
        for key, child in properties.items():
            if key in value:
                _validate_json_value(value[key], child, f"{path}.{key}", errors)
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            _validate_json_value(item, schema["items"], f"{path}[{index}]", errors)


def _load_object(path: Path, logical_name: str, errors: list[dict]) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append({
            "code": "JSON_UNREADABLE", "path": logical_name,
            "observed": type(exc).__name__,
        })
        return None
    if not isinstance(value, dict):
        errors.append({"code": "TYPE_MISMATCH", "path": logical_name,
                       "expected": "object", "observed": type(value).__name__})
        return None
    return value


def _one_suffix(root: Path, suffix: str) -> Path | None:
    matches = sorted(path for path in root.glob(f"*{suffix}") if path.is_file())
    return matches[0] if len(matches) == 1 else None


def _producer_workflow_version(root: Path) -> str | None:
    """The engine that sealed this package, read from manifest.json.

    Returns None when the manifest is absent or unreadable -- the contract check
    reports that separately as ARTIFACT_MISSING, so this stays quiet rather than
    inventing a second error for the same cause.
    """
    try:
        data = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return data.get("workflow_version") if isinstance(data, dict) else None


def check_package_contract(package_dir: str | Path,
                           schema_path: str | Path | None = None) -> dict[str, Any]:
    """Read-only package contract check; advisory unless a caller elects otherwise.

    The JSON document is draft 2020-12. This dependency-free engine implements
    the contract subset the package uses (type/properties/required/items) and
    the package-level CSV/XLSX extensions declared under x-package-contract.
    """
    root = Path(package_dir)
    schema_file = (Path(schema_path) if schema_path else
                   Path(__file__).resolve().parent.parent / "schemas" / "manifest_contract.json")
    errors: list[dict] = []
    checked: list[str] = []
    try:
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {
            "checker": "mamey_manifest_contract_v1",
            "status": "FAIL",
            "checked_artifacts": [],
            "errors": [{"code": "SCHEMA_UNREADABLE", "path": "schemas/manifest_contract.json",
                        "observed": type(exc).__name__}],
        }

    json_contracts = (
        ("manifest.json", "manifest", True),
        ("gate_validation.json", "gate_validation", True),
        ("project_registry_status.json", "project_registry_status", False),
    )
    for filename, definition, required in json_contracts:
        path = root / filename
        if not path.is_file():
            if required:
                errors.append({"code": "ARTIFACT_MISSING", "path": filename})
            continue
        value = _load_object(path, filename, errors)
        checked.append(filename)
        if value is not None:
            _validate_json_value(value, schema["$defs"][definition], filename, errors)

    for rule in schema.get("x-package-contract", {}).get("artifacts", []):
        suffix = rule["suffix"]
        path = _one_suffix(root, suffix)
        if path is None:
            if rule.get("required", False):
                errors.append({"code": "ARTIFACT_MISSING_OR_AMBIGUOUS", "path": f"*{suffix}"})
            continue
        checked.append(f"*{suffix}")
        kind = rule["kind"]
        if kind == "json":
            value = _load_object(path, f"*{suffix}", errors)
            if value is not None:
                for key in rule.get("required_keys", []):
                    if key not in value:
                        errors.append({"code": "REQUIRED_KEY_MISSING", "path": f"*{suffix}.{key}"})
        elif kind == "csv":
            try:
                with path.open(newline="", encoding="utf-8-sig") as handle:
                    header = next(csv.reader(handle), [])
            except (OSError, UnicodeError, csv.Error) as exc:
                errors.append({"code": "CSV_UNREADABLE", "path": f"*{suffix}",
                               "observed": type(exc).__name__})
                continue
            for column in rule.get("required_columns", []):
                if column not in header:
                    errors.append({"code": "REQUIRED_COLUMN_MISSING",
                                   "path": f"*{suffix}.columns.{column}"})
        elif kind == "xlsx":
            try:
                from openpyxl import load_workbook
                workbook = load_workbook(path, read_only=True, data_only=True)
                sheets = set(workbook.sheetnames)
                workbook.close()
            except Exception as exc:
                errors.append({"code": "XLSX_UNREADABLE", "path": f"*{suffix}",
                               "observed": type(exc).__name__})
                continue
            for sheet in rule.get("required_sheets", []):
                if sheet not in sheets:
                    errors.append({"code": "REQUIRED_SHEET_MISSING",
                                   "path": f"*{suffix}.sheets.{sheet}"})

    # The contract describes the CURRENT manifest shape. A package sealed by an older
    # engine can only fail it, and does so for provenance reasons rather than defects:
    # every historical package in this workspace fails on fields that engine simply did
    # not emit yet. Reporting the producing engine alongside the verdict lets a reader
    # tell "this package is stale relative to the contract" from "this package is
    # broken" without opening the manifest. Advisory-only either way; nothing is gated.
    return {
        "checker": "mamey_manifest_contract_v1",
        "schema_draft": "https://json-schema.org/draft/2020-12/schema",
        "status": "PASS" if not errors else "FAIL",
        "checked_artifacts": checked,
        "checked_artifact_count": len(checked),
        "error_count": len(errors),
        "errors": errors,
        "advisory_only": True,
        "producer_workflow_version": _producer_workflow_version(root),
    }
