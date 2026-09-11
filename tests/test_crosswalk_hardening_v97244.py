"""v9.7.244 — bunny hop, hopped from tab_reconcile (which resolves --bgc through the crosswalk).

`mamey/crosswalk.py` is the cohort join key: 218 loc, imported by 11 modules. Two defects:

1. `region_label("region003")` raised ValueError. Several callers read `antismash_region`, whose value
   IS the string "region003". A crash in a join key is worse than a wrong answer only because it is
   louder — and this one was never hit because callers happened to pass ints.
2. `region_number = get("region_number") or get("Region")` — `or` treats 0 as absent. Region numbers
   are 1-based, so 0 is invalid input, not a fallback trigger. The old code silently answered with a
   different field's value.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mamey.crosswalk import region_label, assembly_locator, contig_key


def test_region_label_accepts_an_already_formatted_label():
    assert region_label("region003") == "region003"       # was ValueError
    assert region_label("Region 12") == "region012"


def test_region_label_accepts_ints_and_numeric_strings():
    assert region_label(3) == region_label("3") == region_label("003") == "region003"


def test_region_label_rejects_invalid_and_missing():
    for bad in (0, None, "", "no digits here"):
        assert region_label(bad) == "region_unknown"      # 0 used to render as "region000"


def test_zero_region_number_does_not_fall_through_to_another_field():
    loc = assembly_locator({"bgc_id": "BGC001", "node_id": "NODE_1", "region_number": 0, "Region": 7})
    assert "region007" not in loc and "region_unknown" in loc


def test_contig_key_normalises_spades_cov_suffix_but_leaves_genbank_alone():
    assert contig_key("NODE_2_length_553361_cov_80.858698") == "NODE_2_length_553361"
    assert contig_key("NODE_2_length_553361_cov_80.0858698") == "NODE_2_length_553361"   # same contig
    assert contig_key("NZ_ARHC01000001.1") == "NZ_ARHC01000001.1"                        # type-strain cohort


def test_region_label_rejects_negatives_the_regex_would_have_eaten():
    """v9.7.245, found by an outside verifier: `re.search(r"(\\d+)", "-1")` matches "1" — the sign is
    not part of \\d+ — so region_label(-1) returned "region001", contradicting this function's own
    stated rule that anything <= 0 is unknown. Unreachable from antiSMASH, real against the design."""
    from mamey.crosswalk import region_label
    for bad in (-1, -7, "-1", " -12 "):
        assert region_label(bad) == "region_unknown", bad
    assert region_label(3) == "region003"        # positives unaffected
