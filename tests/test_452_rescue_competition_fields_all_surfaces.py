"""P300-115: the competition fields the 4B JSON carries reach the CSV, Markdown, D4 sheet and
analysis-forward. Synthetic leads only; the fields come from build_leads, never recomputed."""
import csv
import json

import pytest

from mamey import diagnostic_rescue as DR
from mamey import package_addons as PA

HIGH = "DIAGNOSTIC_RESCUE_HIGH_CONFIDENCE"
FMAP = {"by_accession": {"BGC0000809": "indolocarbazole"}, "compatible_pairs": []}
TILING = {"best_scaffold": "NZ_REF0001", "covered": 8, "overlap": 0, "genes_a": 4, "genes_b": 4,
          "overlap_fraction": 0.0, "verdict": "RECONSTRUCTION_SUPPORTED_COMPLEMENTARY",
          "ref_source": "synthetic reference"}


def _pair(a, b, contig_a, contig_b):
    return {"pair": f"{a}+{b}", "bgc_a": a, "bgc_b": b, "contig_a": contig_a, "contig_b": contig_b,
            "products_a": "halogenated", "products_b": "indole", "edge_a": "Edge", "edge_b": "Edge",
            "rggmci_confidence": "LOW_SHARED_REFERENCE_SIGNAL", "acceptance_gate": "DEMOTED_TO_LOW"}


def _leads():
    # BGC001 (arm) pairs HIGH with two different cores -> two competing hypotheses;
    # BGC004+BGC005 is an independent HIGH pair; BGC006+BGC007 is MODERATE (saccharide arm).
    pairs = [_pair("BGC001", "BGC002", "NODE_1", "NODE_2"), _pair("BGC001", "BGC003", "NODE_1", "NODE_3"),
             _pair("BGC004", "BGC005", "NODE_4", "NODE_5"),
             dict(_pair("BGC006", "BGC007", "NODE_6", "NODE_7"), products_a="saccharide")]
    cctt = {"BGC001": ["T43-HAL_halogenase"], "BGC004": ["T43-HAL_halogenase"], "BGC006": [],
            "BGC002": ["T43-IDC_indolocarbazole"], "BGC003": ["T43-IDC_indolocarbazole"],
            "BGC005": ["T43-IDC_indolocarbazole"], "BGC007": ["T43-IDC_indolocarbazole"]}
    kcb = {b: "BGC0000809.3 | AT2433-A1" for b in cctt}
    leads = DR.build_leads({"ranked_pairs": pairs}, cctt, deep_tiling_fn=lambda a, b: dict(TILING),
                           kcb_per_bgc=kcb, family_map=FMAP)
    by = {l["pair"]: l for l in leads}
    assert [by[p]["rescue_tier"] for p in ("BGC001+BGC002", "BGC001+BGC003", "BGC004+BGC005")] == [HIGH] * 3
    assert by["BGC006+BGC007"]["rescue_tier"] != HIGH
    return leads, by


def test_csv_carries_competition_fields(tmp_path):
    leads, by = _leads()
    PA._write_4b(str(tmp_path), "TEST-STRAIN", leads, deep=True)
    with open(tmp_path / "TEST-STRAIN_4B_Diagnostic_Rescue_Leads.csv", encoding="utf-8") as f:
        rows = {r["pair"]: r for r in csv.DictReader(f)}
    assert rows["BGC001+BGC002"]["competing_hypothesis_count"] == "1"
    assert rows["BGC001+BGC002"]["mutually_exclusive_best"] == "False"
    assert rows["BGC004+BGC005"]["competing_hypothesis_count"] == "0"
    assert rows["BGC004+BGC005"]["mutually_exclusive_best"] == "True"
    # not computed for non-HIGH leads: blank, never coerced to 0 / False
    assert rows["BGC006+BGC007"]["competing_hypothesis_count"] == ""
    assert rows["BGC006+BGC007"]["mutually_exclusive_best"] == ""


def test_csv_existing_columns_unchanged(tmp_path):
    leads, _ = _leads()
    PA._write_4b(str(tmp_path), "TEST-STRAIN", leads, deep=True)
    with open(tmp_path / "TEST-STRAIN_4B_Diagnostic_Rescue_Leads.csv", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header[:21] == ["pair", "rescue_tier", "kcb_concordance", "core_bgc", "core_node", "core_triggers",
                           "core_kcb_family", "arm_bgc", "arm_node", "arm_roles", "arm_kcb_family",
                           "shared_scaffold", "reference_genes_covered", "reference_gene_overlap",
                           "overlap_fraction", "tiling_verdict", "rggmci_confidence", "rggmci_gate",
                           "promoted_over_rggmci", "claim_ceiling", "safe_claim"]
    assert header[21:] == ["competing_hypothesis_count", "mutually_exclusive_best"]


def test_markdown_carries_competition_fields(tmp_path):
    leads, _ = _leads()
    PA._write_4b(str(tmp_path), "TEST-STRAIN", leads, deep=True)
    md = (tmp_path / "TEST-STRAIN_4B_Diagnostic_Rescue_Leads.md").read_text(encoding="utf-8")
    assert "| Competing HIGH | Exclusive best |" in md
    rows = {line.split(" | ")[2]: line for line in md.splitlines() if line.startswith("| DIAGNOSTIC")}
    assert rows["BGC001+BGC002"].endswith("| 1 | no |")
    assert rows["BGC004+BGC005"].endswith("| 0 | yes |")
    assert rows["BGC006+BGC007"].endswith("| — | — |")


def test_json_lead_object_is_the_source(tmp_path):
    leads, by = _leads()
    PA._write_4b(str(tmp_path), "TEST-STRAIN", leads, deep=True)
    saved = json.loads((tmp_path / "TEST-STRAIN_4B_Diagnostic_Rescue_Leads.json").read_text(encoding="utf-8"))
    for l in saved["leads"]:
        assert l.get("competing_hypothesis_count") == by[l["pair"]].get("competing_hypothesis_count")


def test_d4_sheet_carries_competition_fields(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    leads, _ = _leads()
    wb_path = tmp_path / "TEST-STRAIN_5_workbook.xlsx"
    wb = openpyxl.Workbook()
    wb.save(wb_path)
    assert PA.add_d4_sheet(str(wb_path), leads)
    ws = openpyxl.load_workbook(wb_path)["D4_Diagnostic_Rescues"]
    rows = list(ws.iter_rows(values_only=True))
    hdr = list(rows[0])
    assert hdr[-2:] == ["competing_hypothesis_count", "mutually_exclusive_best"]
    data = {r[0]: r for r in rows[1:]}
    assert data["BGC001+BGC003"][-2:] == (1, False)
    assert data["BGC004+BGC005"][-2:] == (0, True)
    assert data["BGC006+BGC007"][-2:] == (None, None)


def test_analysis_forward_names_competition(tmp_path):
    leads, _ = _leads()
    (tmp_path / "manifest.json").write_text(json.dumps({"strain_id": "TEST-STRAIN",
                                                        "bgc_counts": {"raw": 7}}), encoding="utf-8")
    PA._write_4b(str(tmp_path), "TEST-STRAIN", leads, deep=True)
    md = open(PA.write_analysis_forward(str(tmp_path)), encoding="utf-8").read()
    lines = {l.split("**")[1]: l for l in md.splitlines() if l.startswith("- **BGC")}
    assert "Competing HIGH hypotheses: 1 (mutually exclusive best: no)." in lines["BGC001+BGC002"]
    assert "Competing HIGH hypotheses: 0 (mutually exclusive best: yes)." in lines["BGC004+BGC005"]


def test_analysis_forward_without_fields_is_unchanged(tmp_path):
    # an older 4B JSON without the fields renders the bullet as before
    leads, _ = _leads()
    for l in leads:
        l.pop("competing_hypothesis_count", None)
        l.pop("mutually_exclusive_best", None)
    (tmp_path / "manifest.json").write_text(json.dumps({"strain_id": "TEST-STRAIN",
                                                        "bgc_counts": {"raw": 7}}), encoding="utf-8")
    PA._write_4b(str(tmp_path), "TEST-STRAIN", leads, deep=True)
    md = open(PA.write_analysis_forward(str(tmp_path)), encoding="utf-8").read()
    bullet = [l for l in md.splitlines() if l.startswith("- **BGC004+BGC005**")][0]
    assert bullet.endswith("Judge both fragments together.")
