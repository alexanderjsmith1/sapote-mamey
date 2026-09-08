"""test_mode_b_fixture.py — mode-b subcommand fixture tests (v9.7.81).

Acceptance criteria (P1 item 4):
  - mode-b produces _Mode_B_Top_Leads.md and .csv from a sealed package.
  - The BGC with higher combined AB+AF score ranks above the lower-scored one.
  - Safe-claim ceiling is present in every output row.
  - Excludes standing-rule and primary-metab BGCs from ranking.
"""
import csv
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mamey.chatgpt_commands import mode_b_command


@pytest.fixture()
def scored_package(tmp_path):
    """Synthetic package where BGC035 outranks BGC028 by combined AB+AF score."""
    import csv as _csv

    pkg = tmp_path / "NOCARDIA" / "package"
    pkg.mkdir(parents=True)

    (pkg / "manifest.json").write_text(json.dumps({
        "strain": {"strain_id": "NOCARDIA"},
        "bgcs": [
            {"bgc_id": "BGC035", "contig": "NODE_35", "products": ["NRPS"],
             "antismash_region": "region001", "edge_status": "Interior",
             "architecture_confidence": "A", "architecture_class_confidence": "high",
             "kcb_top": "indolocarbazole", "kcb_cumulative": 45000, "kcb_protein_hits": 12,
             "length_kb": 35.0, "cctt_triggers": ["T43-IDC"]},
            {"bgc_id": "BGC028", "contig": "NODE_28", "products": ["T1PKS"],
             "antismash_region": "region001", "edge_status": "Edge",
             "architecture_confidence": "C", "architecture_class_confidence": "medium",
             "kcb_top": "nystatin", "kcb_cumulative": 80268, "kcb_protein_hits": 5,
             "length_kb": 60.7, "cctt_triggers": []},
            {"bgc_id": "BGC099", "contig": "NODE_99", "products": ["saccharide"],
             "antismash_region": "region001", "edge_status": "Full-contig",
             "architecture_confidence": "E", "architecture_class_confidence": "low",
             "kcb_top": "", "kcb_cumulative": 0, "kcb_protein_hits": 0,
             "length_kb": 5.0, "cctt_triggers": []},
        ],
        "source_scans": {
            "blda_tta": {"per_bgc": {
                "BGC035": {"bldA_tier": "T1", "tta_codons": 0},
                "BGC028": {"bldA_tier": "T1", "tta_codons": 0},
            }},
            "resistance_tiers": {"per_bgc": {
                "BGC035": {"tier": "T3"},
                "BGC028": {"tier": "none"},
            }},
        },
    }), encoding="utf-8")

    # Triage board: BGC035 has higher AB+AF than BGC028; BGC099 is standing-rule
    tb = pkg / "NOCARDIA_4_triage_board.csv"
    rows = [
        {"BGC_ID": "BGC035", "Contig": "NODE_35", "Products": "NRPS",
         "Standing_rule": "", "Primary_metab_flag": "",
         "AB_auto": "65", "AF_auto": "40", "Novelty_auto": "45",
         "Arch": "A", "Boundary": "Interior", "Depth_floor": "full_mode_b",
         "CCTT_triggers": "T43-IDC", "KCB_top": "indolocarbazole", "KCB_score": "45000"},
        {"BGC_ID": "BGC028", "Contig": "NODE_28", "Products": "T1PKS",
         "Standing_rule": "", "Primary_metab_flag": "",
         "AB_auto": "30", "AF_auto": "50", "Novelty_auto": "35",
         "Arch": "C", "Boundary": "Edge", "Depth_floor": "full_mode_b",
         "CCTT_triggers": "", "KCB_top": "nystatin", "KCB_score": "80268"},
        {"BGC_ID": "BGC099", "Contig": "NODE_99", "Products": "saccharide",
         "Standing_rule": "saccharide-exclusion", "Primary_metab_flag": "",
         "AB_auto": "90", "AF_auto": "90", "Novelty_auto": "90",  # high but excluded
         "Arch": "E", "Boundary": "Full-contig", "Depth_floor": "abbrev_ledger",
         "CCTT_triggers": "", "KCB_top": "", "KCB_score": ""},
    ]
    fields = list(rows[0].keys())
    with open(tb, "w", newline="", encoding="utf-8") as fh:
        w = _csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # Empty RGGMCI pairs file
    rggmci = pkg / "NOCARDIA_4A_RGGMCI_ranked_pairs.csv"
    rggmci.write_text("bgc_a,bgc_b,rggmci_confidence,Score\n", encoding="utf-8")

    return pkg


def test_mode_b_produces_md_and_csv(scored_package, tmp_path):
    """mode-b must produce both MD and CSV output files."""
    outdir = tmp_path / "mb_out"
    args = SimpleNamespace(package=str(scored_package), top_n=5,
                           outdir=str(outdir), node_first=True)
    rc = mode_b_command(args)
    assert rc == 0
    assert (outdir / "NOCARDIA_Mode_B_Top_Leads.md").exists()
    assert (outdir / "NOCARDIA_Mode_B_Top_Leads.csv").exists()


def test_bgc035_outranks_bgc028(scored_package, tmp_path):
    """BGC035 (AB=65+AF=40=105) must rank above BGC028 (AB=30+AF=50=80)."""
    outdir = tmp_path / "mb_rank"
    args = SimpleNamespace(package=str(scored_package), top_n=5,
                           outdir=str(outdir), node_first=True)
    mode_b_command(args)
    rows = list(csv.DictReader(open(outdir / "NOCARDIA_Mode_B_Top_Leads.csv")))
    assert len(rows) >= 2
    rank1 = next((r for r in rows if r["BGC_ID"] == "BGC035"), None)
    rank2 = next((r for r in rows if r["BGC_ID"] == "BGC028"), None)
    assert rank1 is not None, "BGC035 not in mode-b output"
    assert rank2 is not None, "BGC028 not in mode-b output"
    assert int(rank1["Rank"]) < int(rank2["Rank"]), (
        f"BGC035 (rank {rank1['Rank']}) should outrank BGC028 (rank {rank2['Rank']})"
    )


def test_standing_rule_bgc_excluded(scored_package, tmp_path):
    """BGC099 (saccharide-exclusion) must NOT appear in mode-b output."""
    outdir = tmp_path / "mb_exc"
    args = SimpleNamespace(package=str(scored_package), top_n=5,
                           outdir=str(outdir), node_first=True)
    mode_b_command(args)
    rows = list(csv.DictReader(open(outdir / "NOCARDIA_Mode_B_Top_Leads.csv")))
    bgc_ids = [r["BGC_ID"] for r in rows]
    assert "BGC099" not in bgc_ids, "Standing-rule BGC099 must be excluded"


def test_safe_claim_ceiling_present(scored_package, tmp_path):
    """Every row must have a non-empty Safe_claim_ceiling."""
    outdir = tmp_path / "mb_ceil"
    args = SimpleNamespace(package=str(scored_package), top_n=5,
                           outdir=str(outdir), node_first=True)
    mode_b_command(args)
    rows = list(csv.DictReader(open(outdir / "NOCARDIA_Mode_B_Top_Leads.csv")))
    for row in rows:
        assert row.get("Safe_claim_ceiling", "").strip(), (
            f"BGC {row.get('BGC_ID')} is missing Safe_claim_ceiling"
        )


def test_md_contains_claim_safety_header(scored_package, tmp_path):
    """The MD output must contain the claim-safety reminder block."""
    outdir = tmp_path / "mb_md"
    args = SimpleNamespace(package=str(scored_package), top_n=5,
                           outdir=str(outdir), node_first=True)
    mode_b_command(args)
    md = (outdir / "NOCARDIA_Mode_B_Top_Leads.md").read_text(encoding="utf-8")
    assert "claim-safety" in md.lower() or "Claim-safety" in md


def test_node_first_label_in_md(scored_package, tmp_path):
    """With node_first=True the MD rank heading should contain the node name."""
    outdir = tmp_path / "mb_nf"
    args = SimpleNamespace(package=str(scored_package), top_n=5,
                           outdir=str(outdir), node_first=True)
    mode_b_command(args)
    md = (outdir / "NOCARDIA_Mode_B_Top_Leads.md").read_text(encoding="utf-8")
    # BGC035 is on NODE_35 — that should appear in the rank-1 heading
    assert "NODE_35" in md, "node-first label must include contig node name"
