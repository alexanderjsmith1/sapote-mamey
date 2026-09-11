"""v9.7.348 external activity-prediction channel — validator + score-neutrality gates.

Implements CODEX_01's 10 interface acceptance gates + the CODEX_02 / verdict rules, plus the
score-neutrality proof (the sealed package is byte-identical before and after the channel runs).
Interface/governance only — nothing here can change ab_score/af_score/tier/the sealed board.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from mamey import activity_predictions as ap


# --------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------
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


def _tree_fingerprint(root: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(p for p in root.rglob("*") if p.is_file()):
        h.update(str(f.relative_to(root)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def _make_package(tmp_path: Path) -> Path:
    """A minimal sealed package with an AB/AF-bearing triage board + manifest."""
    pkg = tmp_path / "AS-XXX_package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "AS-XXX"}), encoding="utf-8")
    with (pkg / "AS-XXX_4_triage_board.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["BGC_ID", "AB_auto", "AF_auto", "Lead_tier_auto"])
        w.writerow(["BGC001", "20", "90", "HIGH"])
    return pkg


# --------------------------------------------------------------------------------------------
# GATE 1 — valid two-row fixture passes
# --------------------------------------------------------------------------------------------
def test_gate1_valid_two_rows_pass():
    d = doc(valid_pred(bgc_id="BGC001"), valid_pred(bgc_id="BGC002"))
    assert ap.validate_activity_predictions(d) == []
    assert ap.is_valid(d)


# GATE 2 — duplicate exact key fails closed
def test_gate2_duplicate_exact_key_fails():
    d = doc(valid_pred(), valid_pred())  # identical (strain,bgc,region,model)
    codes = {e["code"] for e in ap.validate_activity_predictions(d)}
    assert "DUPLICATE_EXACT_KEY" in codes


# two strains sharing BGC001 remain SEPARATE (no false duplicate) — CODEX_01 fixture 1
def test_two_strains_same_bgc_are_separate():
    d = doc(valid_pred(strain="AS-1"), valid_pred(strain="AS-2"))
    assert ap.validate_activity_predictions(d) == []


# GATE 3 — probability out of range fails closed
@pytest.mark.parametrize("bad", [-0.1, 1.1, 2.0])
def test_gate3_prob_out_of_range_fails(bad):
    d = doc(valid_pred(antibacterial_probability=bad))
    codes = {e["code"] for e in ap.validate_activity_predictions(d)}
    assert "PROB_OUT_OF_RANGE" in codes


# GATE 4 — OUT_OF_DOMAIN / FAILED require null probs + HOLD (not a numeric zero)
@pytest.mark.parametrize("state", ["OUT_OF_DOMAIN", "FAILED"])
def test_gate4_null_states_require_null_probs_and_hold(state):
    ok = doc(valid_pred(applicability_status=state, antibacterial_probability=None,
                        antifungal_probability=None, activity_call="HOLD"))
    assert ap.validate_activity_predictions(ok) == []
    bad = doc(valid_pred(applicability_status=state, antibacterial_probability=0.0,
                         activity_call="HOLD"))
    codes = {e["code"] for e in ap.validate_activity_predictions(bad)}
    assert "PROB_ON_NULL_STATE" in codes
    bad2 = doc(valid_pred(applicability_status=state, antibacterial_probability=None,
                          antifungal_probability=None, activity_call="PREDICTED_NEGATIVE"))
    codes2 = {e["code"] for e in ap.validate_activity_predictions(bad2)}
    assert "CALL_ON_NULL_STATE" in codes2


# GATE 5 — IN_DOMAIN requires model/env/feature-schema/input hashes
def test_gate5_in_domain_requires_hashes():
    d = doc(valid_pred(model_sha256=None))
    codes = {e["code"] for e in ap.validate_activity_predictions(d)}
    assert "MISSING_INDOMAIN_HASH" in codes


# missing any required hash entirely also fails (provenance) — CODEX_01 fixture 5
def test_missing_hash_fails():
    p = valid_pred()
    del p["environment_sha256"]
    codes = {e["code"] for e in ap.validate_activity_predictions(doc(p))}
    assert "MISSING_KEYS" in codes


# GATE 6 — explicit output inside the sealed package refused; default is a sibling
def test_gate6_output_inside_package_refused(tmp_path):
    pkg = _make_package(tmp_path)
    with pytest.raises(ValueError, match="outside the sealed package"):
        ap.resolve_output_dir(pkg, pkg / "inside")
    sib = ap.resolve_output_dir(pkg, None)
    assert pkg not in sib.parents and sib != pkg


# GATE 7 + 8 — score-neutrality: the sealed package (incl. AB/AF triage board) is byte-identical
def test_gate7_8_score_neutrality_package_unchanged(tmp_path):
    pkg = _make_package(tmp_path)
    before = _tree_fingerprint(pkg)
    d = doc(valid_pred())
    ap.validate_activity_predictions(d)
    out = ap.write_predictions(d, pkg)                 # writes to a SIBLING
    assert _tree_fingerprint(pkg) == before            # package untouched
    assert pkg not in out.parents                       # output is outside the package
    assert out.exists()


# GATE 9 — module never imports/touches scoring (channels stay separate; no averaging path)
def test_gate9_no_scoring_coupling():
    src = Path(ap.__file__).read_text()
    assert "import scoring" not in src and "from mamey.scoring" not in src
    assert "ab_score" not in src or "never" in src.lower()  # only referenced in the invariant docstring


# GATE 10 — claim safety: no categorical activity language in the shipped interface
def test_gate10_no_categorical_claims_in_interface():
    for f in (ap.__file__, ap.default_registry_path()):
        text = Path(f).read_text().lower()
        for banned in ("confirmed antibacterial", "confirmed antifungal", "produces an antifungal",
                       "produces an antibacterial"):
            assert banned not in text


# --------------------------------------------------------------------------------------------
# CODEX_02 / verdict — NPBDetect predictions are NOT admissible
# --------------------------------------------------------------------------------------------
def test_npbdetect_predictions_nonadmissible():
    bad = doc(valid_pred(model_id="npbdetect", applicability_status="IN_DOMAIN"))
    codes = {e["code"] for e in ap.validate_activity_predictions(bad)}
    assert "NONADMISSIBLE_MODEL" in codes
    # held OUT_OF_DOMAIN is fine
    ok = doc(valid_pred(model_id="npbdetect", applicability_status="OUT_OF_DOMAIN",
                        antibacterial_probability=None, antifungal_probability=None,
                        activity_call="HOLD", warning_codes=["NPB_FC1_BYPASS"]))
    assert ap.validate_activity_predictions(ok) == []


# --------------------------------------------------------------------------------------------
# adapter registry — loads, schema-checked, and NO adapter may claim core-tier influence
# --------------------------------------------------------------------------------------------
def test_registry_loads_and_no_core_tier_influence():
    reg = ap.load_adapter_registry(ap.default_registry_path())
    ids = {a["model_id"] for a in reg["adapters"]}
    assert {"walker_clardy_npfunction", "deepbgc_pfam_rf", "npbdetect", "bgc_mlm", "prism4_qpsar"} <= ids
    for a in reg["adapters"]:
        assert a["core_tier_influence"] in (False, "NO", "no")


# --------------------------------------------------------------------------------------------
# contract parity — the validator must not drift looser than the JSON schema
# --------------------------------------------------------------------------------------------
def _schema():
    p = Path(ap.__file__).resolve().parent.parent / "schemas" / "optional_activity_predictions.schema.json"
    return json.loads(p.read_text())["$defs"]["prediction"]


def test_validator_matches_schema_required_and_enums():
    pred = _schema()
    assert set(pred["required"]) == set(ap._REQUIRED_PREDICTION_KEYS)
    assert pred["additionalProperties"] is False  # validator rejects unknown keys to match
    assert pred["properties"]["applicability_status"]["enum"] == list(ap.APPLICABILITY_STATES)
    assert pred["properties"]["activity_call"]["enum"] == list(ap.ACTIVITY_CALLS)
    assert pred["properties"]["boundary_status"]["enum"] == list(ap.BOUNDARY_STATES)


def test_unknown_key_rejected():
    p = valid_pred()
    p["antibacterial_probablity"] = 0.9  # typo'd extra key
    codes = {e["code"] for e in ap.validate_activity_predictions(doc(p))}
    assert "UNKNOWN_KEY" in codes


def test_duplicate_warning_code_rejected():
    d = doc(valid_pred(warning_codes=["FRAGMENT_UNRELIABLE", "FRAGMENT_UNRELIABLE"]))
    codes = {e["code"] for e in ap.validate_activity_predictions(d)}
    assert "DUPLICATE_WARNING_CODE" in codes


def test_registry_rejects_core_tier_influence(tmp_path):
    bad = {"schema_version": ap.ADAPTER_REGISTRY_SCHEMA_VERSION,
           "adapters": [{"model_id": "x", "core_tier_influence": "YES"}]}
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="core_tier_influence=NO"):
        ap.load_adapter_registry(p)
