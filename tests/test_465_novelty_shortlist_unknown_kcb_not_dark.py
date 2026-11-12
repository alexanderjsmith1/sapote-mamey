"""The novelty shortlist must not score missing evidence as a novelty signal.

A blank KCB_top with KCB_evidence_state UNKNOWN_KCB means the comparison is not in the package,
not that KnownClusterBlast found nothing. A package with no convergence table has no per-gene
recognizability to be low.
"""
import csv
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import build_novelty_shortlist as N  # noqa: E402


def _write(path, fields, rows):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _pkg(tmp_path, inv_fields, inv, conv=None):
    d = tmp_path / "S1" / "package"
    d.mkdir(parents=True)
    _write(d / "S1_2_inventory.csv", inv_fields, inv)
    _write(d / "S1_4_triage_board.csv", ["BGC_ID", "Novelty_auto", "Lead_tier_auto", "RGGMCI_support"],
           [{"BGC_ID": r["BGC_ID"], "Novelty_auto": "0", "Lead_tier_auto": "", "RGGMCI_support": ""} for r in inv])
    if conv is not None:
        _write(d / "S1_3_mibig_convergence.csv", ["bgc_id", "recognizable_gene_share"], conv)
    return str(d)


FIELDS = ["BGC_ID", "Products", "Length_kb", "KCB_top", "KCB_evidence_state"]


def _row(bid, state, top=""):
    return {"BGC_ID": bid, "Products": "T1PKS", "Length_kb": "40", "KCB_top": top, "KCB_evidence_state": state}


def test_only_a_reported_no_hit_is_kcb_dark(tmp_path):
    inv = [_row("BGC001", "UNKNOWN_KCB"), _row("BGC002", "KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED"),
           _row("BGC003", "CLUSTERBLAST_FALLBACK_OBSERVED"), _row("BGC004", "KNOWNCLUSTERBLAST_OBSERVED", "x cluster")]
    conv = [{"bgc_id": b, "recognizable_gene_share": "0.9"} for b in ("BGC001", "BGC002", "BGC003", "BGC004")]
    rows = {r["bgc_id"]: r for r in N.build([_pkg(tmp_path, FIELDS, inv, conv)])}
    assert [rows[b]["kcb_dark"] for b in ("BGC001", "BGC002", "BGC003", "BGC004")] == [0, 1, 0, 0]
    assert rows["BGC001"]["kcb_evidence_state"] == "UNKNOWN_KCB"
    assert rows["BGC001"]["novelty_score"] == 0.0
    assert rows["BGC002"]["novelty_score"] == 2.0


def test_older_inventory_without_state_column_keeps_its_rule_and_says_so(tmp_path):
    inv = [{"BGC_ID": "BGC001", "Products": "NRPS", "Length_kb": "30", "KCB_top": ""}]
    rows = N.build([_pkg(tmp_path, ["BGC_ID", "Products", "Length_kb", "KCB_top"], inv, [])])
    assert rows[0]["kcb_dark"] == 1
    assert rows[0]["kcb_evidence_state"] == N.KCB_STATE_NOT_RECORDED


def test_missing_convergence_table_scores_no_low_recognizability(tmp_path):
    rows = N.build([_pkg(tmp_path, FIELDS, [_row("BGC001", "KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED")], None)])
    assert rows[0]["low_recognizability"] == 0
    assert rows[0]["recognizability_source"] == "NO_CONVERGENCE_TABLE"
    assert rows[0]["novelty_score"] == 2.0


def test_no_row_in_a_present_convergence_table_still_counts_as_low(tmp_path):
    rows = N.build([_pkg(tmp_path, FIELDS, [_row("BGC001", "KNOWNCLUSTERBLAST_OBSERVED", "x")], [])])
    assert rows[0]["low_recognizability"] == 1
    assert rows[0]["recognizability_source"] == "NO_ROW_FOR_BGC"


def test_markdown_marks_unknown_signals(tmp_path):
    pkg = _pkg(tmp_path, FIELDS, [_row("BGC001", "UNKNOWN_KCB")], None)
    out = tmp_path / "out"
    assert N.main(["--package", pkg, "--out", str(out)]) == 0
    md = (out / "novelty_shortlist.md").read_text()
    assert "| ? | ? |" in md
    header = (out / "novelty_shortlist.csv").read_text().splitlines()[0]
    assert header.endswith("kcb_evidence_state,recognizability_source")
