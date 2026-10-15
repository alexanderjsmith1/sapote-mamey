"""P300-063: a Diagnostic Rescue lead cannot stay HIGH when the KCB-class concordance gate did not run.

Synthetic inputs only. Covers the direct assess_pair path, build_leads, and the emit_rescue_4b production
wiring (family map loaded by package_addons, deep tiling from clusterblast text files).
"""
import json

from mamey import diagnostic_rescue as DR
from mamey import package_addons as PA

HIGH = "DIAGNOSTIC_RESCUE_HIGH_CONFIDENCE"
MODERATE = "DIAGNOSTIC_RESCUE_MODERATE"
LOW = "DIAGNOSTIC_RESCUE_LOW"


def _pair():
    return {"pair": "BGC001+BGC013", "bgc_a": "BGC001", "bgc_b": "BGC013",
            "contig_a": "NODE_105", "contig_b": "NODE_182",
            "products_a": "halogenated; saccharide", "products_b": "indole",
            "edge_a": "Edge", "edge_b": "Full-contig",
            "rggmci_confidence": "LOW_SHARED_REFERENCE_SIGNAL", "acceptance_gate": "DEMOTED_TO_LOW"}


CCTT_A = ["T43-HAL_halogenase"]
CCTT_B = ["T43-IDC_indolocarbazole"]
TILING = {"best_scaffold": "NZ_REF0001", "covered": 8, "overlap": 0, "genes_a": 2, "genes_b": 6,
          "overlap_fraction": 0.0, "verdict": "RECONSTRUCTION_SUPPORTED_COMPLEMENTARY",
          "ref_source": "synthetic reference"}
FMAP = {"by_accession": {"BGC0000809": "indolocarbazole", "BGC0002460": "indolocarbazole",
                         "BGC0002381": "tambjamine"}, "compatible_pairs": []}
KCB_A = "BGC0002460.3 | loonamycin"
KCB_B = "BGC0000809.3 | AT2433-A1"


def _assess(family_map, kcb_b=KCB_B, tiling=TILING):
    return DR.assess_pair(_pair(), CCTT_A, CCTT_B, deep_tiling=tiling,
                          kcb_a=KCB_A, kcb_b=kcb_b, family_map=family_map)


# --- the defect: every "gate did not run" state used to leave HIGH -----------------------------------
def test_absent_map_caps_high_at_moderate():
    lead = _assess(None)
    assert lead["rescue_tier"] == MODERATE
    assert lead["kcb_concordance"] == "not_evaluated"
    assert lead["kcb_concordance_gate"] == "not_run_family_map_absent"
    assert lead["rescue_tier_cap_reason"] == "kcb_concordance_gate_not_run"
    assert lead["promoted_over_rggmci"] is False


def test_empty_map_caps_high_at_moderate():
    lead = _assess({})
    assert lead["rescue_tier"] == MODERATE
    assert lead["kcb_concordance_gate"] == "not_run_family_map_absent"
    assert lead["rescue_tier_cap_reason"] == "kcb_concordance_gate_not_run"


def test_skipped_map_caps_high_at_moderate():
    lead = _assess({"_skipped": True})
    assert lead["rescue_tier"] == MODERATE
    assert lead["kcb_concordance"] == "not_evaluated"
    assert lead["kcb_concordance_gate"] == "not_run_family_map_unavailable"
    assert lead["rescue_tier_cap_reason"] == "kcb_concordance_gate_not_run"


def test_missing_map_file_through_loader_caps_high(tmp_path):
    fmap = DR.load_family_map(str(tmp_path / "no_such_map.json"))
    assert fmap.get("_skipped") is True
    lead = _assess(fmap)
    assert lead["rescue_tier"] == MODERATE
    assert lead["kcb_concordance_gate"] == "not_run_family_map_unavailable"


def test_build_leads_without_map_has_no_high():
    leads = DR.build_leads({"ranked_pairs": [_pair()]},
                           {"BGC001": CCTT_A, "BGC013": CCTT_B},
                           deep_tiling_fn=lambda a, b: dict(TILING),
                           kcb_per_bgc={"BGC001": KCB_A, "BGC013": KCB_B}, family_map=None)
    assert [l["rescue_tier"] for l in leads] == [MODERATE]
    # competition annotations are only computed among HIGH leads; a capped lead does not carry them
    assert "competing_hypothesis_count" not in leads[0]


# --- unchanged behaviour once the gate has run -------------------------------------------------------
def test_evaluated_concordant_stays_high():
    lead = _assess(FMAP)
    assert lead["rescue_tier"] == HIGH
    assert lead["kcb_concordance"] == "concordant"
    assert lead["kcb_concordance_gate"] == "evaluated"
    assert lead["rescue_tier_cap_reason"] is None


def test_evaluated_indeterminate_and_discordant_unchanged():
    ind = _assess(FMAP, kcb_b="no accession here")
    assert (ind["rescue_tier"], ind["kcb_concordance"]) == (MODERATE, "indeterminate")
    assert ind["rescue_tier_cap_reason"] is None
    dis = _assess(FMAP, kcb_b="BGC0002381.3 | tambjamine")
    assert (dis["rescue_tier"], dis["kcb_concordance"]) == (LOW, "discordant")
    assert dis["rescue_tier_cap_reason"] is None


def test_non_high_tier_without_map_is_not_marked_capped():
    weak = dict(TILING, covered=4, genes_a=2, genes_b=2)  # below the covered floor -> MODERATE already
    lead = _assess(None, tiling=weak)
    assert lead["rescue_tier"] == MODERATE
    assert lead["rescue_tier_cap_reason"] is None
    assert lead["kcb_concordance_gate"] == "not_run_family_map_absent"


# --- production wiring: emit_rescue_4b loads the shipped map and builds deep tiling ----------------
def _cb_text(acc, hits):
    rows = "\n".join(f"{q}\t{s}\t60\t400\t90\t1e-50" for q, s in hits)
    return ("ClusterBlast scores\n\n>>\n1. %s\nSource: synthetic reference\nType: other\n"
            "Cumulative BLAST score: 2000\n\nTable of Blast hits (query gene, subject gene, %%identity, "
            "blast score, %%coverage, e-value):\n%s\n" % (acc, rows))


def _package(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    man = {"strain_id": "TEST-STRAIN",
           "bgcs": [{"bgc_id": "BGC001", "contig": "NODE_105", "region_number": 1},
                    {"bgc_id": "BGC013", "contig": "NODE_182", "region_number": 1}],
           "source_scans": {"cctt": {"per_bgc": {"BGC001": CCTT_A, "BGC013": CCTT_B}}}}
    (pkg / "manifest.json").write_text(json.dumps(man), encoding="utf-8")
    (pkg / "TEST-STRAIN_4A_RGGMCI_full.json").write_text(json.dumps({"ranked_pairs": [_pair()]}),
                                                          encoding="utf-8")
    (pkg / "TEST-STRAIN_records.json").write_text(json.dumps({"records": [
        {"bgc_id": "BGC001", "kcb_top": KCB_A}, {"bgc_id": "BGC013", "kcb_top": KCB_B}]}),
        encoding="utf-8")
    cb = tmp_path / "clusterblast"
    cb.mkdir()
    (cb / "NODE_105_c1.txt").write_text(_cb_text("NZ_REF0001", [
        ("ctgA_1", "REF_RS00070"), ("ctgA_2", "REF_RS00080")]), encoding="utf-8")
    (cb / "NODE_182_c1.txt").write_text(_cb_text("NZ_REF0001", [
        ("ctgB_%d" % i, "REF_RS%05d" % (10 * i)) for i in range(1, 7)]), encoding="utf-8")
    return pkg, cb


def test_emit_rescue_4b_with_shipped_map_keeps_high(tmp_path):
    pkg, cb = _package(tmp_path)
    leads = PA.emit_rescue_4b(str(pkg), clusterblast_dir=str(cb))
    assert [l["rescue_tier"] for l in leads] == [HIGH]
    assert leads[0]["kcb_concordance_gate"] == "evaluated"


def test_emit_rescue_4b_with_unavailable_map_caps_high(tmp_path, monkeypatch):
    pkg, cb = _package(tmp_path)
    monkeypatch.setattr(DR, "_FAMILY_MAP_PATH", str(tmp_path / "missing_family_map.json"))
    leads = PA.emit_rescue_4b(str(pkg), clusterblast_dir=str(cb))
    assert [l["rescue_tier"] for l in leads] == [MODERATE]
    assert leads[0]["rescue_tier_cap_reason"] == "kcb_concordance_gate_not_run"
    saved = json.loads((pkg / "TEST-STRAIN_4B_Diagnostic_Rescue_Leads.json").read_text(encoding="utf-8"))
    assert saved["leads"][0]["kcb_concordance_gate"] == "not_run_family_map_unavailable"


def test_emit_rescue_4b_concordance_disabled_caps_high(tmp_path):
    pkg, cb = _package(tmp_path)
    leads = PA.emit_rescue_4b(str(pkg), clusterblast_dir=str(cb), enable_concordance=False)
    assert [l["rescue_tier"] for l in leads] == [MODERATE]
    assert leads[0]["kcb_concordance_gate"] == "not_run_family_map_absent"
