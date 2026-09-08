"""AMBER_06 (v9.7.349): the fragment-adequacy gate on the external activity channel.

Resolves the BGC-MLM fragment problem at the interface, not in a model: a fragment-inadequate
cluster (edge/short/padded) can never be IN_DOMAIN, so a padding/length-sensitive prediction is
recorded but never treated as in-domain evidence. The dimension is OPTIONAL — legacy rows without
`fragment_adequacy` are unaffected (the .348 gate stays green). Score-neutral by construction.
"""
from __future__ import annotations

import hashlib
from mamey import activity_predictions as ap


def H(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def valid_pred(**over):
    p = {
        "strain": "AS-XXX", "bgc_id": "BGC001", "contig_region": "NODE_3.region001",
        "model_id": "walker_clardy_npfunction", "model_version": "1.0",
        "model_sha256": H("model"), "environment_sha256": H("env"),
        "feature_schema": "antismash8_pfam_v1", "feature_schema_sha256": H("fs"),
        "input_package_sha256": H("pkg"),
        "antibacterial_probability": 0.78, "antifungal_probability": 0.22,
        "reference_threshold": 0.5, "activity_call": "PREDICTED_POSITIVE",
        "boundary_status": "Interior", "applicability_status": "IN_DOMAIN",
        "warning_codes": [], "feature_receipt_sha256": H("fr"),
        "run_timestamp_utc": "2026-08-02T00:00:00Z",
    }
    p.update(over)
    return p


def doc(*preds):
    return {"schema_version": ap.SCHEMA_VERSION, "source_package_sha256": H("src"),
            "predictions": list(preds)}


def codes(d):
    return {e["code"] for e in ap.validate_activity_predictions(d)}


# --- legacy rows (no fragment_adequacy) are unaffected -------------------------------------
def test_legacy_row_without_field_still_valid():
    assert ap.validate_activity_predictions(doc(valid_pred())) == []


def test_complete_in_domain_is_valid():
    d = doc(valid_pred(fragment_adequacy="COMPLETE"))
    assert ap.validate_activity_predictions(d) == []


# --- the gate: fragment-inadequate cannot be IN_DOMAIN -------------------------------------
def test_edge_in_domain_is_rejected():
    d = doc(valid_pred(fragment_adequacy="EDGE", boundary_status="Edge",
                       applicability_status="IN_DOMAIN"))
    assert "FRAGMENT_NOT_INDOMAIN" in codes(d)


def test_short_in_domain_is_rejected():
    assert "FRAGMENT_NOT_INDOMAIN" in codes(doc(valid_pred(fragment_adequacy="SHORT")))


def test_padded_in_domain_is_rejected():
    assert "FRAGMENT_NOT_INDOMAIN" in codes(doc(valid_pred(fragment_adequacy="PADDED")))


def test_edge_as_limited_is_allowed_probability_recorded():
    # LIMITED keeps the probability (recorded, flagged) — the honest "don't trust it" state
    d = doc(valid_pred(fragment_adequacy="EDGE", boundary_status="Edge",
                       applicability_status="LIMITED",
                       warning_codes=["FRAGMENT_EDGE"]))
    assert ap.validate_activity_predictions(d) == []


def test_short_routed_out_of_domain_is_quarantined():
    # OUT_OF_DOMAIN + null probs + HOLD — fully quarantined via the existing null-state rule
    d = doc(valid_pred(fragment_adequacy="SHORT", applicability_status="OUT_OF_DOMAIN",
                       antibacterial_probability=None, antifungal_probability=None,
                       activity_call="HOLD", warning_codes=["FRAGMENT_SHORT"]))
    assert ap.validate_activity_predictions(d) == []


def test_bad_fragment_adequacy_value_rejected():
    assert "BAD_FRAGMENT_ADEQUACY" in codes(doc(valid_pred(fragment_adequacy="TRUNCATED")))


def test_fragment_adequacy_is_not_an_unknown_key():
    # optional key must be accepted, not flagged UNKNOWN_KEY
    assert "UNKNOWN_KEY" not in codes(doc(valid_pred(fragment_adequacy="COMPLETE")))
    # but a genuine typo still is
    p = valid_pred()
    p["fragment_adequcy"] = "COMPLETE"  # typo
    assert "UNKNOWN_KEY" in codes(doc(p))


# --- the derivation helper ----------------------------------------------------------------
def test_derive_precedence():
    assert ap.derive_fragment_adequacy("Interior") == "COMPLETE"
    assert ap.derive_fragment_adequacy("Edge") == "EDGE"
    assert ap.derive_fragment_adequacy("Unknown") == "UNKNOWN"
    assert ap.derive_fragment_adequacy(None) == "UNKNOWN"
    # SHORT beats EDGE; PADDED beats everything
    assert ap.derive_fragment_adequacy("Edge", region_length_kb=3.0, model_min_length_kb=8.0) == "SHORT"
    assert ap.derive_fragment_adequacy("Interior", padded=True) == "PADDED"
    # complete interior long enough
    assert ap.derive_fragment_adequacy("Interior", region_length_kb=40.0, model_min_length_kb=8.0) == "COMPLETE"


def test_derive_output_feeds_gate_consistently():
    # a derived EDGE row set IN_DOMAIN is caught by the validator (end-to-end coherence)
    fa = ap.derive_fragment_adequacy("Edge")
    d = doc(valid_pred(fragment_adequacy=fa, boundary_status="Edge",
                       applicability_status="IN_DOMAIN"))
    assert "FRAGMENT_NOT_INDOMAIN" in codes(d)
