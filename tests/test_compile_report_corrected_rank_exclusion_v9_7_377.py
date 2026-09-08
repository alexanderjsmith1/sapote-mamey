"""Regression test — BLACK_CHERRY_377_compile_report_code_adversarial_review.

`mamey/scoring.py::triage_bgcs()` leaves `corrected_rank` (written as the `Corrected_rank`
column of `_4_triage_board.csv`) BLANK for THREE independent lead-exclusion reasons
(`standing_rule_flag`, `primary_metabolism_flag`, OR `mobile_element_flag` — scoring.py:737's
three-flag gate). `compile_report.py::_decision_for()` (the §12 wet-lab decision matrix) and
`_key_findings()` (the always-populated, reader-facing Key Findings banner) previously detected
ONLY the first two reasons, by text-matching the `Standing_rule` / `Primary_metab_flag` columns.
A BGC excluded purely for mobile-element/IS-element dominance leaves both those columns empty,
so it fell through the exclusion check entirely.

Worse than a simple omission: `_decision_for()`'s rank-tier fallback,
`int(row.get("Corrected_rank") or row.get("Rank") or 999)`, resurrected the RAW, pre-exclusion
`Rank` (always populated 1..N for every triage row, exclusion-blind) whenever `Corrected_rank`
was blank — so an engine-excluded BGC that happened to score #1 on raw AB/AF could be labelled
"PRIORITY ISO" (the report's single highest wet-lab-actionable recommendation), directly
contradicting scoring.py's own exclusion. `_key_findings()` had the parallel gap: its `_excluded()`
helper never checked `Corrected_rank` at all, so the same BGC's raw KCB_score could headline the
report's Key Findings banner as the #1 finding.

This is the same bug CLASS as BLACK_CHERRY_377_tranche5_mobile_element_lead_exclusion_gap (an
engine-excluded BGC silently posing as a valid lead in a downstream consumer) but in the
compiled TEXT report itself rather than a figure family, and more severe: it does not merely
fail to say "EXCL", it can promote the excluded BGC all the way to "PRIORITY ISO".

Fix: both `_decision_for()` and `_key_findings()`'s `_excluded()` now also treat a
present-but-blank `Corrected_rank` column as an exclusion signal — the SSOT scoring.py already
writes for all three reasons, no new column needed (unlike the tranche5 figure-layer fix, which
had to plumb `mobile_element_flag` through `verdicts.json` because the figure bundle had no
equivalent column at all). A genuinely legacy package with no `Corrected_rank` column (key
absent from the row, not merely blank) still falls back to the pre-existing `Rank` behaviour.
"""
from mamey import compile_report as cr


# A synthetic row shaped exactly like what cli.py writes for a mobile-element-only exclusion:
# scoring.py's three-flag gate (scoring.py:737) left corrected_rank=None because
# mobile_element_flag was set, while standing_rule_flag and primary_metabolism_flag are both
# falsy — so Standing_rule and Primary_metab_flag are both empty in the CSV, and Corrected_rank
# is blank. Rank (raw, pre-exclusion, exclusion-blind) is populated as usual. A distinctive
# sentinel score (0.95 / "sentinel-95") stands in for "this BGC would otherwise be the #1 lead".
_MOBILE_EXCLUDED_ROW = {
    "BGC_ID": "BGC099",
    "Contig": "NODE_1", "Node_ID": "NODE_1", "antiSMASH_Region": "region001",
    "Rank": "1",                 # raw pre-exclusion rank: this BGC scored #1 on raw AB/AF
    "Corrected_rank": "",        # blank: scoring.py withheld it (mobile_element_flag)
    "Standing_rule": "",         # NOT a standing-rule exclusion — text-match alone misses this
    "Primary_metab_flag": "",    # NOT a primary-metabolism exclusion either
    "AB_auto": "0.95", "AF_auto": "0.10",
    "Novelty_auto": "HIGH",
    "KCB_score": "0.95", "KCB_top": "sentinel-95",
    "Products": "NRPS",
}


def test_decision_for_excludes_mobile_element_flag_via_blank_corrected_rank():
    """§12 wet-lab decision matrix: a BGC scoring.py excluded purely for mobile-element
    dominance must render EXCL, never PRIORITY ISO/HIGH SEQ — even though its Standing_rule and
    Primary_metab_flag text fields carry no visible reason and its raw Rank is #1."""
    action, rationale = cr._decision_for(_MOBILE_EXCLUDED_ROW)
    assert action == "EXCL", (
        f"engine-excluded BGC (Corrected_rank blank) leaked into the decision matrix as "
        f"{action!r} ({rationale!r}) instead of EXCL — the raw pre-exclusion Rank resurrected it"
    )


def test_decision_for_still_excludes_standing_rule_and_primary_metab(tmp_path=None):
    """Non-regression: the pre-existing text-match exclusion paths (standing rule /
    primary-metabolism) must still fire exactly as before this fix."""
    assert cr._decision_for({"Standing_rule": "saccharide", "Corrected_rank": "5"})[0] == "EXCL"
    assert cr._decision_for({"Primary_metab_flag": "1", "Corrected_rank": "5"})[0] == "EXCL"


def test_decision_for_legacy_schema_without_corrected_rank_column_uses_raw_rank():
    """A genuinely old package predating the Corrected_rank column (key ABSENT from the row
    dict, not merely blank) must keep falling back to the raw Rank column as before — this fix
    must not regress legacy-schema packages that never had Corrected_rank at all."""
    legacy_row = {"AB_auto": "0.95", "Rank": "1", "Novelty_auto": "HIGH"}
    assert "Corrected_rank" not in legacy_row
    action, _ = cr._decision_for(legacy_row)
    assert action == "PRIORITY ISO"  # unchanged legacy behaviour


def test_decision_tiers_still_calibrated_with_populated_corrected_rank():
    """Non-regression: normal (non-blank) Corrected_rank tiering is unaffected."""
    assert cr._decision_for({"AB_auto": "0.9", "Corrected_rank": "1", "Novelty_auto": "MED"})[0] == "PRIORITY ISO"
    assert cr._decision_for({"AB_auto": "0.85", "Corrected_rank": "9", "Novelty_auto": "MED"})[0] == "HIGH SEQ"
    assert cr._decision_for({"AB_auto": "0.45", "Corrected_rank": "12"})[0] == "MEDIUM ACT"
    assert cr._decision_for({"AB_auto": "0.2", "Corrected_rank": "20"})[0] == "LOW"


def test_key_findings_excludes_mobile_element_flagged_bgc(tmp_path):
    """The reader-facing Key Findings banner must not headline a BGC scoring.py excluded purely
    for mobile-element dominance, even though it carries the package's highest KCB_score."""
    import csv
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    with (pkg / "AS-XXX_4_triage_board.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["BGC_ID", "Contig", "Node_ID", "antiSMASH_Region", "AB_auto", "AF_auto",
                    "Novelty_auto", "Standing_rule", "Primary_metab_flag", "Corrected_rank",
                    "KCB_score", "KCB_top", "Products"])
        # BGC099: mobile-element excluded (Corrected_rank blank), but the package's highest
        # KCB_score — a distinctive sentinel — so it would headline the banner if the exclusion
        # check missed it.
        w.writerow(["BGC099", "NODE_1", "NODE_1", "region001", "0.95", "0.10", "HIGH",
                    "", "", "", "99.0", "sentinel-mobile", "NRPS"])
        w.writerow(["BGC001", "NODE_2", "NODE_2", "region002", "0.40", "0.30", "MED",
                    "", "", "1", "10.0", "other-hit", "PKS"])

    m = {"assembly_tier": "GOOD", "interior_pct": 74, "raw_bgcs": 2, "corrected_bgcs": 1}
    out = cr._key_findings(pkg, m)
    assert "sentinel-mobile" not in out, (
        "mobile-element-excluded BGC's KCB comparator leaked into the always-populated "
        "Key Findings banner despite scoring.py withholding its corrected_rank"
    )
    assert "other-hit" in out  # the genuinely eligible BGC still headlines
