# Synthetic regression inputs only; no strain, prediction or hash here is real evidence.
"""The activity-prediction validator refuses a null or blank model_id and inexact digests.

A null model_id skipped the duplicate-key check, and `match` with `$` accepted a 64-hex digest
followed by a newline.
"""
from __future__ import annotations

import hashlib

from mamey import activity_predictions as ap


def _h(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def _pred(**over):
    p = {
        "strain": "STRAIN_X", "bgc_id": "BGC001", "contig_region": "NODE_3.region001",
        "model_id": "example_model", "model_version": "1.0",
        "model_sha256": _h("model"), "environment_sha256": _h("env"),
        "feature_schema": "schema_v1", "feature_schema_sha256": _h("fs"),
        "input_package_sha256": _h("pkg"),
        "antibacterial_probability": 0.7, "antifungal_probability": 0.2,
        "reference_threshold": 0.5, "activity_call": "PREDICTED_POSITIVE",
        "boundary_status": "Interior", "applicability_status": "IN_DOMAIN",
        "warning_codes": [], "feature_receipt_sha256": _h("fr"),
        "run_timestamp_utc": "2026-08-02T00:00:00Z",
    }
    p.update(over)
    return p


def _doc(*preds, src=None):
    return {"schema_version": ap.SCHEMA_VERSION, "source_package_sha256": src or _h("src"),
            "predictions": list(preds)}


def _codes(errors):
    return {e["code"] for e in errors}


def test_valid_document_still_passes():
    assert ap.validate_activity_predictions(_doc(_pred())) == []


def test_null_model_id_is_refused_even_when_rows_repeat():
    errs = ap.validate_activity_predictions(_doc(_pred(model_id=None), _pred(model_id=None)))
    assert "BAD_MODEL_ID" in _codes(errs)
    assert sum(e["code"] == "BAD_MODEL_ID" for e in errs) == 2


def test_blank_model_id_is_refused():
    assert "BAD_MODEL_ID" in _codes(ap.validate_activity_predictions(_doc(_pred(model_id="  "))))


def test_digest_with_trailing_newline_is_refused():
    errs = ap.validate_activity_predictions(_doc(_pred(model_sha256=_h("model") + "\n")))
    assert "BAD_HASH" in _codes(errs)
    errs = ap.validate_activity_predictions(_doc(_pred(), src=_h("src") + "\n"))
    assert "BAD_SOURCE_HASH" in _codes(errs)


def test_bgc_alias_and_warning_codes_with_trailing_newline_are_refused():
    errs = ap.validate_activity_predictions(_doc(_pred(bgc_id="BGC001\n")))
    assert "BAD_BGC_ID" in _codes(errs)
    errs = ap.validate_activity_predictions(_doc(_pred(warning_codes=["LOW_COVERAGE\n"])))
    assert "BAD_WARNING_CODES" in _codes(errs)
