"""Tests for mamey.cohort_leads_ledger (ADD-01 cohort priority-leads ledger).

Builds tiny synthetic sealed packages (triage board CSV + manifest.json) and
asserts the ledger unions the correct Exceptional/High rows, ranks them by
(tier, AF, AB), and emits the MIXED-ENGINE caution only when engines differ.
"""
import csv
import json
import os

import pytest

from mamey.cohort_leads_ledger import build_ledger, write_ledger, LEDGER_COLUMNS

TRIAGE_HEADER = [
    "Rank", "BGC_ID", "Node_ID", "antiSMASH_Region", "Assembly_Locator",
    "Arch_Capacity", "Lead_tier_auto", "AB_auto", "AF_auto", "KCB_top",
    "Misanchor_Flag",
]


def _write_package(runs_dir, strain, engine, triage_rows):
    pkg = os.path.join(runs_dir, strain, "package")
    os.makedirs(pkg, exist_ok=True)
    # triage board
    tb = os.path.join(pkg, f"{strain}_4_triage_board.csv")
    with open(tb, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=TRIAGE_HEADER)
        w.writeheader()
        for r in triage_rows:
            w.writerow(r)
    # manifest
    with open(os.path.join(pkg, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({"strain_id": strain, "workflow_version": engine}, fh)
    return pkg


def _row(bgc, node, region, cap, tier, ab, af, kcb="", mis=""):
    return {
        "Rank": "1", "BGC_ID": bgc, "Node_ID": node, "antiSMASH_Region": region,
        "Assembly_Locator": f"{node} {region} ({bgc})", "Arch_Capacity": cap,
        "Lead_tier_auto": tier, "AB_auto": ab, "AF_auto": af, "KCB_top": kcb,
        "Misanchor_Flag": mis,
    }


@pytest.fixture
def cohort_dir(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    # Strain A: 1 High, 1 Exceptional, 1 Medium (dropped), 1 Inventory (dropped)
    _write_package(
        str(runs), "AS-001", "Mamey v1.9.118",
        [
            _row("BGC001", "NODE_1", "region001", "PKS", "High", "50", "30", "kcbA1"),
            _row("BGC002", "NODE_2", "region001", "NRPS", "Exceptional", "80", "70", "kcbA2"),
            _row("BGC003", "NODE_3", "region001", "RiPP", "Medium", "40", "20"),
            _row("BGC004", "NODE_4", "region001", "terpene", "Inventory", "10", "5"),
        ],
    )
    # Strain B: 2 High with different AF for ranking, 1 High with misanchor
    _write_package(
        str(runs), "AS-002", "Mamey v1.9.118",
        [
            _row("BGC010", "NODE_9", "region001", "PKS", "High", "60", "55", "kcbB1"),
            _row("BGC011", "NODE_8", "region001", "NRPS", "High", "60", "40", "kcbB2", "MISANCHOR"),
        ],
    )
    return str(runs)


def test_union_counts_exceptional_and_high_only(cohort_dir):
    rows, meta = build_ledger(cohort_dir)
    # A: High+Exceptional = 2 ; B: 2 High = 2 ; total 4 (Medium/Inventory dropped)
    assert meta["n_leads"] == 4
    assert len(rows) == 4
    assert meta["n_strains"] == 2
    # no dropped/duplicated BGCs; each expected BGC present exactly once
    ids = sorted(r["BGC_ID"] for r in rows)
    assert ids == ["BGC001", "BGC002", "BGC010", "BGC011"]
    # Medium/Inventory never leaked in
    assert "BGC003" not in ids and "BGC004" not in ids


def test_ranking_tier_then_af_then_ab(cohort_dir):
    rows, _ = build_ledger(cohort_dir)
    order = [r["BGC_ID"] for r in rows]
    # Exceptional first (BGC002), then Highs ranked by AF desc:
    # BGC010 AF55 > BGC011 AF40? wait BGC001 AF30... High set: BGC010(55), BGC011(40), BGC001(30)
    assert order[0] == "BGC002"  # Exceptional outranks all High
    assert order[1] == "BGC010"  # highest-AF High
    assert order[2] == "BGC011"  # AF40
    assert order[3] == "BGC001"  # AF30
    # Cohort_rank is 1..N contiguous
    assert [r["Cohort_rank"] for r in rows] == [1, 2, 3, 4]


def test_columns_and_locator_and_misanchor(cohort_dir):
    rows, _ = build_ledger(cohort_dir)
    by_id = {r["BGC_ID"]: r for r in rows}
    # node_region built from Node_ID + antiSMASH_Region
    assert by_id["BGC002"]["node_region"] == "NODE_2 region001"
    # misanchor flag carried through
    assert by_id["BGC011"]["Misanchor_Flag"] == "MISANCHOR"
    # engine version stamped on every row
    assert all(r["engine_version"] == "Mamey v1.9.118" for r in rows)


def test_single_engine_note_no_mixed_warning(cohort_dir, tmp_path):
    rows, meta = build_ledger(cohort_dir)
    assert meta["mixed_engine"] is False
    out = tmp_path / "COHORT_PRIORITY_LEADS.csv"
    write_ledger(rows, meta, str(out))
    text = out.read_text()
    assert "MIXED ENGINE" not in text
    assert "single-engine cohort" in text
    # header row present and columns match
    lines = [ln for ln in text.splitlines() if not ln.startswith("#")]
    assert lines[0] == ",".join(LEDGER_COLUMNS)


def test_mixed_engine_emits_caution(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    _write_package(str(runs), "AS-100", "Mamey v1.9.118",
                   [_row("BGC001", "NODE_1", "region001", "PKS", "High", "50", "30")])
    _write_package(str(runs), "AS-101", "Mamey v1.9.114",
                   [_row("BGC002", "NODE_2", "region001", "NRPS", "High", "60", "40")])
    rows, meta = build_ledger(str(runs))
    assert meta["mixed_engine"] is True
    assert sorted(meta["engine_versions"]) == ["Mamey v1.9.114", "Mamey v1.9.118"]
    out = tmp_path / "led.csv"
    write_ledger(rows, meta, str(out))
    text = out.read_text()
    assert "MIXED ENGINE VERSIONS" in text
    assert "not strictly" in text.lower()
