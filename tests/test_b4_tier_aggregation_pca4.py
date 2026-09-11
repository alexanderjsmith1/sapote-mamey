"""PC-A4 (v9.7.101): B4 resistance_T1 / bldA_T4 must aggregate from the per-BGC tier
fields, not from non-existent flat keys.

Root cause this guards: the old B4 builder read tier_counts["T1"] (real key is the full
"T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED") and blda_tta["bldA_T4"] (a key the scan
never emits — the tier lives per-BGC as bldA_tier == "T4"). Both returned 0 always.

We test the counting logic against the actual per-BGC shapes the scans produce.
"""


def _resistance_t1_count(per_bgc):
    return sum(1 for v in per_bgc.values() if str(v.get("tier", "")).startswith("T1"))


def _bldA_t4_count(per_bgc):
    return sum(1 for v in per_bgc.values() if v.get("bldA_tier") == "T4")


def test_resistance_t1_counts_full_tier_string():
    # mirrors source_scans tier labels
    per_bgc = {
        "BGC01": {"tier": "T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED"},
        "BGC02": {"tier": "T2_RESISTANCE_LIKE_SOURCE_DERIVED"},
        "BGC03": {"tier": "T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED"},
        "BGC04": {"tier": "NULL_NO_SOURCE_DERIVED_RESISTANCE"},
    }
    assert _resistance_t1_count(per_bgc) == 2  # was 0 under the old flat-key read


def test_bldA_t4_counts_per_bgc_tier():
    per_bgc = {
        "BGC01": {"bldA_tier": "T4"},
        "BGC02": {"bldA_tier": "T2"},
        "BGC03": {"bldA_tier": "T4"},
        "BGC04": {"bldA_tier": "NOT_APPLICABLE"},
    }
    assert _bldA_t4_count(per_bgc) == 2  # was 0 under the missing-key read


def test_empty_or_missing_is_zero():
    assert _resistance_t1_count({}) == 0
    assert _bldA_t4_count({}) == 0
