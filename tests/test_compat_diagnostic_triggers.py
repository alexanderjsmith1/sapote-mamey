"""Patch A — diagnostic CCTT trigger counting must cover the full T43 trigger set.

compat_v941 used to compute diagnostic_count from a hand-typed token subset
("DKP","HAL","LAN","ENE","PHO","THA","LASSO","TET"). That subset:
  * silently dropped T43-IDC, T43-NUC, T43-BLA, T43-AMC, T43-NN (under-tiering e.g. an indolocarbazole-core BGC,
    whose only diagnostic trigger is T43-IDC_indolocarbazole), and
  * matched T43-PTM and T43-XHAL only by substring accident ("TET" in "tetramate", "HAL" in "XHAL").

The fix derives the diagnostic set from the active scanning backend (source_scans.CCTT_PATTERNS) and
matches on the full trigger name. These tests pin both the completeness and the no-accident property,
and guard against the count drifting out of sync with the trigger set again.
"""
from types import SimpleNamespace

import mamey.compat_v941 as compat
from mamey.source_scans import CCTT_PATTERNS

# The five triggers the old hand-typed subset genuinely dropped (XHAL/PTM were substring accidents).
PREVIOUSLY_MISSED = (
    "T43-IDC_indolocarbazole",
    "T43-NUC_nucleoside",
    "T43-BLA_betalactam",
    "T43-AMC_aminocyclitol",
    "T43-NN_n_n_bond",
)


def test_diagnostic_set_is_sourced_from_scanning_backend():
    """SSOT guard: the diagnostic trigger set IS the source_scans CCTT_PATTERNS key set, not a copy."""
    assert set(compat._DIAGNOSTIC_CCTT_TRIGGERS) == set(CCTT_PATTERNS.keys())
    assert len(compat._DIAGNOSTIC_CCTT_TRIGGERS) == 18


def test_all_t43_triggers_count_as_diagnostic():
    for trig in CCTT_PATTERNS.keys():
        assert compat._is_diagnostic_cctt(trig), f"{trig} should be diagnostic"


def test_previously_missed_triggers_now_diagnostic():
    for trig in PREVIOUSLY_MISSED:
        assert compat._is_diagnostic_cctt(trig), f"regression: {trig} not counted as diagnostic"


def test_no_substring_false_positives():
    # Strings that contain a 3-letter code as a substring but are NOT T43 triggers must NOT count
    # (the old "TET" in "tetramate" / "HAL" in "chitin-hydrolase" class of accident).
    for noise in ("some_tetramate_thing", "alpha_phosphono_lyase", "generic_hydrolase", "lantern"):
        assert not compat._is_diagnostic_cctt(noise), f"false positive on {noise!r}"


def _stub_bgc(bgc_id="BGC013", **over):
    base = dict(bgc_id=bgc_id, products=["indole", "other"], kcb_top="BGC0000809.3",
                kcb_cumulative=3780.0, closest_product_provenance="UNRESOLVED",
                product_claim_ceiling="unresolved; do not use product name")
    base.update(over)
    return SimpleNamespace(**base)


def _stub_ss(bgc_id, cctt_hits):
    return SimpleNamespace(
        cctt={"bgc_coupling": {bgc_id: list(cctt_hits)}},
        per_bgc_dss={}, resistance_tiers={},
    )


def test_idc_only_bgc_is_tier1_diagnostic():
    """Report §7.1: a BGC whose only trigger is T43-IDC must export TIER_1_DIAGNOSTIC (was TIER_2)."""
    bgc = _stub_bgc("BGC013")
    ss = _stub_ss("BGC013", ["T43-IDC_indolocarbazole"])
    out = compat.claim_calibration_fields_for_bgc(bgc, None, ss)
    assert out["evidence_weight_tier"] == "TIER_1_DIAGNOSTIC", out
    assert out["claim_confidence"] in {"MODERATE", "HIGH"}, out
    assert out["diagnostic_signal_score"] >= 3, out  # diagnostic_count(1)*3


def test_nuc_only_bgc_is_tier1_diagnostic():
    bgc = _stub_bgc("BGC162", products=["other"])
    ss = _stub_ss("BGC162", ["T43-NUC_nucleoside"])
    out = compat.claim_calibration_fields_for_bgc(bgc, None, ss)
    assert out["evidence_weight_tier"] == "TIER_1_DIAGNOSTIC", out
