"""External activity-prediction channel — validator + adapter registry (v9.7.348).

INTERFACE / GOVERNANCE ONLY. This module validates optional, post-seal, external ML activity
predictions and declares the adapter registry. It NEVER touches Mamey scoring: it does not import
scoring/triage/models, does not read or write ab_score/af_score/ab_recall/af_recall/lead tier/the
sealed triage board, and its writer refuses to write inside a sealed package. Predicted activity is
never measured activity; a failed/unavailable model is never a biological negative.

Validation is hand-rolled (no jsonschema dependency), mirroring the list[dict]-of-errors idiom in
`citation_compact.validate_priority_citation_coverage`. The schema contract lives at
`schemas/optional_activity_predictions.schema.json` (CODEX_01); the NPBDetect guard rules follow
CODEX_02 and the Developer or User's v9.7.348 verdict (NPBDetect predictions are not admissible).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "sapote.optional_activity_predictions/1"
ADAPTER_REGISTRY_SCHEMA_VERSION = "sapote.activity_adapters/1"

APPLICABILITY_STATES = ("IN_DOMAIN", "LIMITED", "OUT_OF_DOMAIN", "FAILED")
ACTIVITY_CALLS = ("PREDICTED_POSITIVE", "PREDICTED_NEGATIVE", "HOLD")
BOUNDARY_STATES = ("Interior", "Edge", "Full-contig", "Unknown")
# OPTIONAL fragment-adequacy dimension (v9.7.349 fragment gate). Whether the cluster was
# long/complete enough for the model to be trustworthy. Non-COMPLETE forces the row away from
# IN_DOMAIN — a fragile fragment prediction is recorded but never treated as in-domain evidence.
FRAGMENT_ADEQUACY_STATES = ("COMPLETE", "EDGE", "SHORT", "PADDED", "UNKNOWN")
# fragment states that a model cannot be IN_DOMAIN on (padding-/edge-/length-sensitive)
_FRAGMENT_INADEQUATE = ("EDGE", "SHORT", "PADDED")

# applicability states whose probabilities MUST be null and call MUST be HOLD
_NULL_PROB_STATES = ("OUT_OF_DOMAIN", "FAILED")

# hashes that must be present (non-null 64-hex) for an IN_DOMAIN row to be admissible
_REQUIRED_INDOMAIN_HASHES = (
    "model_sha256", "environment_sha256", "feature_schema_sha256", "input_package_sha256",
)

_REQUIRED_PREDICTION_KEYS = (
    "strain", "bgc_id", "contig_region", "model_id", "model_version", "model_sha256",
    "environment_sha256", "feature_schema", "feature_schema_sha256", "input_package_sha256",
    "antibacterial_probability", "antifungal_probability", "reference_threshold", "activity_call",
    "boundary_status", "applicability_status", "warning_codes", "feature_receipt_sha256",
    "run_timestamp_utc",
)
# OPTIONAL keys — accepted but not required, so legacy documents remain valid. A key that is
# neither required nor optional is still rejected as UNKNOWN_KEY (schema additionalProperties:false).
_OPTIONAL_PREDICTION_KEYS = (
    "fragment_adequacy",
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_BGC_RE = re.compile(r"^BGC[0-9]+$")
_WARN_RE = re.compile(r"^[A-Z0-9_:-]+$")

# model_ids for which predictions are NOT admissible per the Developer or User's v9.7.348 verdict — any such row must
# be held OUT_OF_DOMAIN/FAILED (never IN_DOMAIN/LIMITED). NPBDetect: released fc1 bypass + the
# checked-in example does not reproduce + first-50-CDS boundary/order sensitivity.
_NONADMISSIBLE_MODELS = ("npbdetect",)


def _err(errors: list[dict[str, str]], severity: str, code: str, message: str,
         index: int | None = None) -> None:
    rec = {"severity": severity, "code": code, "error": message}
    if index is not None:
        rec["prediction_index"] = str(index)
    errors.append(rec)


def _is_prob(value: Any) -> bool:
    return value is None or (isinstance(value, (int, float)) and not isinstance(value, bool)
                             and 0.0 <= float(value) <= 1.0)


def validate_activity_predictions(doc: Any) -> list[dict[str, str]]:
    """Return a list of validation errors (empty list == valid).

    Fail-closed: duplicate exact keys, out-of-range probabilities, absent required hashes,
    unknown enum states, numeric probabilities on OUT_OF_DOMAIN/FAILED rows, and non-admissible
    model predictions all produce errors. This does not mutate anything and never touches scoring.
    """
    errors: list[dict[str, str]] = []
    if not isinstance(doc, dict):
        _err(errors, "HIGH", "NOT_AN_OBJECT", "activity predictions document must be a JSON object")
        return errors

    if doc.get("schema_version") != SCHEMA_VERSION:
        _err(errors, "HIGH", "BAD_SCHEMA_VERSION",
             f"schema_version must be {SCHEMA_VERSION!r}, got {doc.get('schema_version')!r}")

    if not (isinstance(doc.get("source_package_sha256"), str)
            and _SHA256_RE.match(doc["source_package_sha256"])):
        _err(errors, "HIGH", "BAD_SOURCE_HASH", "source_package_sha256 must be a 64-hex sha256")

    preds = doc.get("predictions")
    if not isinstance(preds, list):
        _err(errors, "HIGH", "PREDICTIONS_NOT_LIST", "predictions must be a list")
        return errors

    seen_keys: dict[tuple, int] = {}
    for i, p in enumerate(preds):
        if not isinstance(p, dict):
            _err(errors, "HIGH", "PREDICTION_NOT_OBJECT", "prediction must be an object", i)
            continue

        missing = [k for k in _REQUIRED_PREDICTION_KEYS if k not in p]
        if missing:
            _err(errors, "HIGH", "MISSING_KEYS", f"missing required keys: {sorted(missing)}", i)
        # schema is additionalProperties:false — reject unknown/typo'd keys (contract parity).
        # Optional keys (e.g. fragment_adequacy) are permitted; a typo remains UNKNOWN_KEY.
        unknown = [k for k in p
                   if k not in _REQUIRED_PREDICTION_KEYS and k not in _OPTIONAL_PREDICTION_KEYS]
        if unknown:
            _err(errors, "HIGH", "UNKNOWN_KEY", f"unknown keys not in the contract: {sorted(unknown)}", i)

        # exact-key identity (strain, bgc_id, contig_region, model_id) — duplicate fails closed
        key = (p.get("strain"), p.get("bgc_id"), p.get("contig_region"), p.get("model_id"))
        if all(x is not None for x in key):
            if key in seen_keys:
                _err(errors, "HIGH", "DUPLICATE_EXACT_KEY",
                     f"duplicate (strain,bgc_id,contig_region,model_id)={key!r} "
                     f"(first at index {seen_keys[key]})", i)
            else:
                seen_keys[key] = i

        if not (isinstance(p.get("strain"), str) and p.get("strain")):
            _err(errors, "HIGH", "BAD_STRAIN", "strain must be a nonempty string", i)
        if not (isinstance(p.get("bgc_id"), str) and _BGC_RE.match(str(p.get("bgc_id")))):
            _err(errors, "HIGH", "BAD_BGC_ID", "bgc_id must match ^BGC[0-9]+$", i)
        if not (isinstance(p.get("contig_region"), str) and p.get("contig_region")):
            _err(errors, "HIGH", "BAD_CONTIG_REGION", "contig_region must be a nonempty string", i)

        for hk in ("model_sha256", "environment_sha256", "feature_schema_sha256",
                   "input_package_sha256", "feature_receipt_sha256"):
            v = p.get(hk)
            if v is not None and not (isinstance(v, str) and _SHA256_RE.match(v)):
                _err(errors, "HIGH", "BAD_HASH", f"{hk} must be a 64-hex sha256 or null", i)

        for pk in ("antibacterial_probability", "antifungal_probability", "reference_threshold"):
            if not _is_prob(p.get(pk)):
                _err(errors, "HIGH", "PROB_OUT_OF_RANGE", f"{pk} must be null or a number in [0,1]", i)

        call = p.get("activity_call")
        if call not in ACTIVITY_CALLS:
            _err(errors, "HIGH", "BAD_ACTIVITY_CALL", f"activity_call must be one of {ACTIVITY_CALLS}", i)
        if p.get("boundary_status") not in BOUNDARY_STATES:
            _err(errors, "HIGH", "BAD_BOUNDARY", f"boundary_status must be one of {BOUNDARY_STATES}", i)

        app = p.get("applicability_status")
        if app not in APPLICABILITY_STATES:
            _err(errors, "HIGH", "BAD_APPLICABILITY",
                 f"applicability_status must be one of {APPLICABILITY_STATES}", i)

        wc = p.get("warning_codes")
        if not (isinstance(wc, list) and all(isinstance(w, str) and _WARN_RE.match(w) for w in wc)):
            _err(errors, "MEDIUM", "BAD_WARNING_CODES",
                 "warning_codes must be a list of ^[A-Z0-9_:-]+$ tokens", i)
        elif len(set(wc)) != len(wc):
            _err(errors, "MEDIUM", "DUPLICATE_WARNING_CODE",
                 "warning_codes must be unique (schema uniqueItems)", i)

        # conditional: OUT_OF_DOMAIN / FAILED -> null probabilities + HOLD call.
        # Missing/failed/out-of-domain is NOT a numeric zero and NOT a biological negative.
        if app in _NULL_PROB_STATES:
            for pk in ("antibacterial_probability", "antifungal_probability"):
                if p.get(pk) is not None:
                    _err(errors, "HIGH", "PROB_ON_NULL_STATE",
                         f"{app} row must have null {pk} (a failed/OOD model is not a numeric negative)", i)
            if call != "HOLD":
                _err(errors, "HIGH", "CALL_ON_NULL_STATE", f"{app} row must have activity_call=HOLD", i)

        # IN_DOMAIN admissibility: model/env/feature-schema/input hashes required
        if app == "IN_DOMAIN":
            for hk in _REQUIRED_INDOMAIN_HASHES:
                if p.get(hk) is None:
                    _err(errors, "HIGH", "MISSING_INDOMAIN_HASH",
                         f"IN_DOMAIN row requires non-null {hk}", i)

        # non-admissible models (verdict): must be held OOD/FAILED
        mid = str(p.get("model_id", "")).lower()
        if any(mid.startswith(m) for m in _NONADMISSIBLE_MODELS) and app not in _NULL_PROB_STATES:
            _err(errors, "HIGH", "NONADMISSIBLE_MODEL",
                 f"model_id {p.get('model_id')!r} predictions are not admissible "
                 f"(must be OUT_OF_DOMAIN or FAILED per the v9.7.348 verdict)", i)

        # fragment gate (OPTIONAL dimension). Only fires when fragment_adequacy is present, so
        # legacy rows are unaffected. A fragment-inadequate cluster (edge/short/padded) cannot be
        # IN_DOMAIN: MIBiG-trained activity models swing on short/padded input, so their probability
        # is recorded but never treated as in-domain evidence (LIMITED keeps it flagged;
        # OUT_OF_DOMAIN/FAILED nulls it via the existing null-state rule). predicted != measured.
        if "fragment_adequacy" in p:
            fa = p.get("fragment_adequacy")
            if fa not in FRAGMENT_ADEQUACY_STATES:
                _err(errors, "HIGH", "BAD_FRAGMENT_ADEQUACY",
                     f"fragment_adequacy must be one of {FRAGMENT_ADEQUACY_STATES}", i)
            elif fa in _FRAGMENT_INADEQUATE and app == "IN_DOMAIN":
                _err(errors, "HIGH", "FRAGMENT_NOT_INDOMAIN",
                     f"fragment_adequacy={fa} cannot be IN_DOMAIN — a fragment-inadequate cluster "
                     f"must be LIMITED, OUT_OF_DOMAIN, or FAILED (predictions are padding/length "
                     f"sensitive; recorded, not scored)", i)

    return errors


def derive_fragment_adequacy(boundary_status: str | None,
                             region_length_kb: float | None = None,
                             model_min_length_kb: float | None = None,
                             padded: bool = False) -> str:
    """Deterministically classify a cluster's fragment-adequacy for the fragment gate.

    Precedence: PADDED (the model padded a short input) > SHORT (below the model's minimum-length
    contract) > EDGE (antiSMASH on-contig-edge) > UNKNOWN (boundary not determinable) > COMPLETE.
    An adapter calls this to populate `fragment_adequacy`; the validator enforces the resulting gate.
    Pure; unit-tested. This never touches scoring.
    """
    if padded:
        return "PADDED"
    if (region_length_kb is not None and model_min_length_kb is not None
            and region_length_kb < model_min_length_kb):
        return "SHORT"
    if boundary_status == "Edge":
        return "EDGE"
    if boundary_status in (None, "Unknown", ""):
        return "UNKNOWN"
    return "COMPLETE"


def is_valid(doc: Any) -> bool:
    return not validate_activity_predictions(doc)


# --------------------------------------------------------------------------------------------
# adapter registry (declared, NOT bundled) — mirrors companion_tools.load pattern
# --------------------------------------------------------------------------------------------
def load_adapter_registry(path: str | Path) -> dict[str, Any]:
    """Load and lightly validate the activity-adapter registry JSON."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != ADAPTER_REGISTRY_SCHEMA_VERSION:
        raise ValueError(
            f"activity_adapters.json: unexpected schema_version {data.get('schema_version')!r}")
    adapters = data.get("adapters")
    if not isinstance(adapters, list):
        raise ValueError("activity_adapters.json: 'adapters' must be a list")
    # governance invariant: no adapter may claim core-tier influence in this cut
    for a in adapters:
        if a.get("core_tier_influence") not in (False, "NO", "no"):
            raise ValueError(
                f"adapter {a.get('model_id')!r} must declare core_tier_influence=NO "
                f"(no external model may affect scores in this cut)")
    return data


def default_registry_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "activity_adapters.json"


# --------------------------------------------------------------------------------------------
# sibling writer — refuses to write inside a sealed package (mirrors widget_deliverable guard)
# --------------------------------------------------------------------------------------------
def resolve_output_dir(package_dir: str | Path, out_dir: str | Path | None) -> Path:
    """Resolve a SIBLING output dir; refuse any path inside the sealed package."""
    package = Path(package_dir).resolve()
    target = Path(out_dir).resolve() if out_dir else package.parent / f"{package.name}_activity_predictions"
    if target == package or package in target.parents:
        raise ValueError("activity-prediction output must be outside the sealed package directory")
    return target


def write_predictions(doc: Any, package_dir: str | Path, out_dir: str | Path | None = None) -> Path:
    """Validate then write predictions to a SIBLING dir. Never mutates the sealed package.

    Raises ValueError if the document is invalid (fail-closed) or if the target is inside the
    package. Returns the written file path. This is the only write path and it touches nothing
    under `package_dir`.
    """
    problems = validate_activity_predictions(doc)
    if problems:
        raise ValueError(f"refusing to write invalid activity predictions: {problems[:3]}")
    target = resolve_output_dir(package_dir, out_dir)
    target.mkdir(parents=True, exist_ok=True)
    out = target / "optional_activity_predictions.json"
    # CORE-P04 (mirrors packaging.py::_atomic_write_text): write to a temp sibling then
    # atomically replace, so a crash/kill mid-write never leaves a truncated predictions
    # file that a later reader silently loads as valid-but-incomplete JSON.
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(out)
    return out
