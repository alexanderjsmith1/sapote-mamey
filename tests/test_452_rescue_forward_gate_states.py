"""P300-114: the analysis-forward rescue sections explain each lead from its recorded gate states.

The old text called every HIGH a concordant split and every MODERATE a geometry pass with unconfirmed
concordance. Synthetic leads only, produced by diagnostic_rescue.assess_pair.
"""
import json

from mamey import diagnostic_rescue as DR
from mamey import package_addons as PA

HIGH = "DIAGNOSTIC_RESCUE_HIGH_CONFIDENCE"
MODERATE = "DIAGNOSTIC_RESCUE_MODERATE"
FMAP = {"by_accession": {"BGC0000809": "indolocarbazole"}, "compatible_pairs": []}
KCB = "BGC0000809.3 | AT2433-A1"
GOOD = {"best_scaffold": "NZ_REF0001", "covered": 8, "overlap": 0, "genes_a": 2, "genes_b": 6,
        "overlap_fraction": 0.0, "verdict": "RECONSTRUCTION_SUPPORTED_COMPLEMENTARY",
        "ref_source": "synthetic reference"}


def _pair(n, products_a="halogenated"):
    a, b = f"BGC{n:03d}", f"BGC{n + 1:03d}"
    return {"pair": f"{a}+{b}", "bgc_a": a, "bgc_b": b, "contig_a": f"NODE_{n}", "contig_b": f"NODE_{n + 1}",
            "products_a": products_a, "products_b": "indole", "edge_a": "Edge", "edge_b": "Edge"}


def _lead(n, tiling, family_map=FMAP, cctt_a=("T43-HAL_halogenase",), products_a="halogenated"):
    return DR.assess_pair(_pair(n, products_a), list(cctt_a), ["T43-IDC_indolocarbazole"],
                          deep_tiling=tiling, kcb_a=KCB, kcb_b=KCB, family_map=family_map)


def _forward(tmp_path, leads):
    (tmp_path / "manifest.json").write_text(json.dumps({"strain_id": "TEST-STRAIN",
                                                        "bgc_counts": {"raw": 20}}), encoding="utf-8")
    (tmp_path / "TEST-STRAIN_4B_Diagnostic_Rescue_Leads.json").write_text(
        json.dumps({"strain": "TEST-STRAIN", "leads": leads}), encoding="utf-8")
    return open(PA.write_analysis_forward(str(tmp_path)), encoding="utf-8").read()


def _line_after(md, start):
    lines = md.splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith(start))
    return lines[i], (lines[i + 1] if i + 1 < len(lines) else "")


def test_valid_high_lists_its_passed_gates(tmp_path):
    lead = _lead(1, GOOD)
    assert lead["rescue_tier"] == HIGH
    md = _forward(tmp_path, [lead])
    assert "Diagnostic Rescue HIGH (concordant splits)" not in md
    _, gates = _line_after(md, "- **BGC001+BGC002**")
    assert "tiling RECONSTRUCTION_SUPPORTED_COMPLEMENTARY" in gates
    assert "class concordance concordant" in gates
    assert "reference genes 8 (floor 8)" in gates and "(per-arm floor 2)" in gates
    assert "halogenase arm trigger yes" in gates


def test_high_with_unrun_concordance_is_not_called_concordant(tmp_path):
    # a HIGH lead recorded with concordance not_evaluated (gate did not run)
    lead = dict(_lead(1, GOOD), rescue_tier=HIGH, kcb_concordance="not_evaluated")
    lead.pop("kcb_concordance_gate", None)
    md = _forward(tmp_path, [lead])
    _, gates = _line_after(md, "- **BGC001+BGC002**")
    assert "class concordance not_evaluated (gate not run)" in gates
    assert "concordant splits" not in md


def test_moderate_shared_scaffold_distant_geometry_states_the_failed_gate(tmp_path):
    distant = dict(GOOD, verdict="RECONSTRUCTION_NOT_SUPPORTED_DISTANT_LOCI")
    lead = _lead(3, distant)
    assert lead["rescue_tier"] == MODERATE
    md = _forward(tmp_path, [lead])
    assert "Geometry passes" not in md
    line, _ = _line_after(md, "- BGC003+BGC004")
    assert "tiling RECONSTRUCTION_NOT_SUPPORTED_DISTANT_LOCI" in line


def test_moderate_below_per_arm_floor_shows_counts(tmp_path):
    weak = dict(GOOD, genes_a=1, genes_b=7)
    lead = _lead(5, weak)
    assert lead["rescue_tier"] == MODERATE
    line, _ = _line_after(_forward(tmp_path, [lead]), "- BGC005+BGC006")
    assert "core 7 / arm 1 (per-arm floor 2)" in line


def test_moderate_indeterminate_and_saccharide_arm(tmp_path):
    ind = DR.assess_pair(_pair(7), ["T43-HAL_halogenase"], ["T43-IDC_indolocarbazole"], deep_tiling=GOOD,
                         kcb_a=KCB, kcb_b="no accession", family_map=FMAP)
    sac = _lead(9, GOOD, cctt_a=(), products_a="saccharide")
    assert ind["rescue_tier"] == MODERATE and sac["rescue_tier"] == MODERATE
    md = _forward(tmp_path, [ind, sac])
    line_i, _ = _line_after(md, "- BGC007+BGC008")
    line_s, _ = _line_after(md, "- BGC009+BGC010")
    assert "class concordance indeterminate (gate evaluated)" in line_i
    assert "halogenase arm trigger no" in line_s


def test_moderate_without_deep_tiling_says_so(tmp_path):
    pr = dict(_pair(11), best_sources="NZ_REF0002 (4 genes)")
    lead = DR.assess_pair(pr, ["T43-HAL_halogenase"], ["T43-IDC_indolocarbazole"], deep_tiling=None,
                          kcb_a=KCB, kcb_b=KCB, family_map=FMAP)
    assert lead["rescue_tier"] == MODERATE
    line, _ = _line_after(_forward(tmp_path, [lead]), "- BGC011+BGC012")
    assert "tiling not deep-tiled (RG-GMCI summary scaffold only)" in line
    assert "gene floors not applied (no deep tiling)" in line


def test_recorded_cap_reason_is_shown_and_missing_fields_stay_unknown():
    note = PA._rescue_gate_note({"kcb_concordance": "not_evaluated", "kcb_concordance_gate":
                                 "not_run_family_map_unavailable",
                                 "rescue_tier_cap_reason": "kcb_concordance_gate_not_run",
                                 "reference_genes_covered": 8})
    assert "(gate not_run_family_map_unavailable)" in note
    assert "tier capped: kcb_concordance_gate_not_run" in note
    # absent per-arm counts and halogenase flag are unknown, not zero / no
    assert "core — / arm —" in note and "halogenase arm trigger —" in note


def test_rest_of_directive_unchanged(tmp_path):
    md = _forward(tmp_path, [_lead(1, GOOD)])
    assert "## ★ Judge these first — Diagnostic Rescue HIGH\n" in md
    assert "Judge both fragments together." in md
    assert "## Priority worklist" in md
