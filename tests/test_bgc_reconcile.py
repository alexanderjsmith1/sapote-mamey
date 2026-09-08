"""bgc_reconcile: pre-authoring cross-channel evidence reconciliation ledger. Hermetic.

Matches the reclass_check test convention (importlib-loaded tool, synthetic tempdir
fixtures, assertions on the pure reconcile() return). No private strain data.

Covers: each triage-driven contradiction detector, the clean-BGC path, the BLOCK/WATCH
counts that drive --strict, and the property that the rendered ledger passes the bundle's
OWN claim-safety linter (a tool that enforces claim discipline must model it).
"""
import csv
import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_s = importlib.util.spec_from_file_location("bgc_reconcile", ROOT / "tools" / "bgc_reconcile.py")
br = importlib.util.module_from_spec(_s)
_s.loader.exec_module(br)

_HDR = ["Rank", "BGC_ID", "Contig", "Node_ID", "antiSMASH_Region", "Products", "Boundary",
        "Arch", "Class_Conf", "AB_auto", "AF_auto", "Novelty_auto", "KCB_top", "KCB_score",
        "Primary_metab_flag", "Misanchor_Flag", "Two_Pathway_Flag", "Two_Model_Flag", "Concordance"]


def _row(**k):
    r = {h: "" for h in _HDR}
    r.update(k)
    return r


def _pkg(tmp, rows):
    pkg = Path(tmp) / "package"
    pkg.mkdir(parents=True, exist_ok=True)
    with open(pkg / "SYN_4_triage_board.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_HDR)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return str(pkg)


def _codes(entry):
    return {c["code"] for c in entry["contradictions"]}


def test_clean_bgc_has_no_contradictions():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = _pkg(tmp, [_row(Rank=1, BGC_ID="BGC001", Node_ID="NODE_3", antiSMASH_Region="region001",
                              Products="lanthipeptide", Boundary="Interior", Arch="A", Class_Conf="HIGH")])
        ledger, summary = br.reconcile(pkg, cmap=None)
        assert summary["n_bgc"] == 1
        assert ledger[0]["contradictions"] == []
        assert summary["n_with_block"] == 0


def test_two_pathway_and_two_model_are_block():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = _pkg(tmp, [_row(Rank=1, BGC_ID="BGC002", Node_ID="NODE_5", antiSMASH_Region="region002",
                              Products="NRPS,T1PKS", Boundary="Interior", Class_Conf="MED",
                              Two_Pathway_Flag="TWO_PATHWAY:PKS+NRPS (2 lines)",
                              Two_Model_Flag="TWO_MODEL_STRONG:PKS+NRPS (5,000bp) [KCB_DISCONNECT]")])
        ledger, summary = br.reconcile(pkg, cmap=None)
        e = ledger[0]
        assert "TWO_PATHWAY" in _codes(e)
        assert "TWO_MODEL" in _codes(e)
        assert e["n_block"] >= 2
        assert summary["n_with_block"] == 1


def test_low_class_conf_and_edge_and_misanchor_and_primary_metab():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = _pkg(tmp, [_row(Rank=1, BGC_ID="BGC003", Node_ID="NODE_9", antiSMASH_Region="region003",
                              Products="terpene", Boundary="Edge", Class_Conf="LOW",
                              KCB_top="geosmin biosynthetic gene cluster", KCB_score="100",
                              Primary_metab_flag="SUF_operon", Misanchor_Flag="ANCHOR_SHIFT_2kb",
                              Concordance="LOW")])
        e = br.reconcile(pkg, cmap=None)[0][0]
        codes = _codes(e)
        assert "LOW_CLASS_CONFIDENCE" in codes
        assert "TRUNCATED_NO_STRUCTURE" in codes
        assert "MISANCHOR" in codes
        assert "PRIMARY_METABOLISM" in codes
        assert "LOW_CONCORDANCE" in codes
        # KCB anchor present but no strain-dir → tier unverified, forces the front-page read
        assert "KCB_TIER_UNVERIFIED" in codes


def test_kcb_dark_is_not_a_contradiction_but_sets_ceiling():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = _pkg(tmp, [_row(Rank=1, BGC_ID="BGC004", Node_ID="NODE_1", antiSMASH_Region="region001",
                              Products="NRPS", Boundary="Interior", Class_Conf="HIGH")])
        e = br.reconcile(pkg, cmap=None)[0][0]
        assert all(c["code"].startswith("KCB") is False for c in e["contradictions"])
        assert any("identity is not established" in cc for cc in e["claim_ceiling"])


def test_missing_triage_board_errors_cleanly():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "empty"
        pkg.mkdir()
        ledger, summary = br.reconcile(str(pkg), cmap=None)
        assert ledger == []
        assert "error" in summary


def test_verify_card_catches_ignored_block_contradiction():
    """A card that silently ignores an OVER_MERGE flag must be caught (the failure lint_card
    can't see: structurally fine, but authored one product over a merged region)."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = _pkg(tmp, [
            _row(Rank=1, BGC_ID="BGC018", Node_ID="rec1", Contig="rec1",
                 antiSMASH_Region="region018", Products="NRPS;RiPP", Boundary="Interior",
                 Class_Conf="HIGH"),
        ])
        with open(Path(pkg) / "SYN_predicted_polymers.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["record_id", "region_number", "n_protoclusters", "candidate_kind", "over_merge_flag"])
            w.writerow(["rec1", "18", "3", "neighbouring", "YES (split before product claims)"])
        card = "# BGC018\n## §6\nThe product is a single NRPS siderophore.\n"
        report, summary = br.verify_card(pkg, "BGC018", card, cmap=None)
        om = next(r for r in report if r["code"] == "OVER_MERGE")
        assert om["status"] == "UNADDRESSED"
        assert summary["n_unaddressed_block"] >= 1


def test_verify_card_passes_when_acknowledged():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = _pkg(tmp, [
            _row(Rank=1, BGC_ID="BGC018", Node_ID="rec1", Contig="rec1",
                 antiSMASH_Region="region018", Products="NRPS;RiPP", Boundary="Interior",
                 Class_Conf="HIGH"),
        ])
        with open(Path(pkg) / "SYN_predicted_polymers.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["record_id", "region_number", "n_protoclusters", "candidate_kind", "over_merge_flag"])
            w.writerow(["rec1", "18", "3", "neighbouring", "YES (split before product claims)"])
        card = ("# BGC018\nregion018 is over-merged; per scope_cluster only the NRPS protocluster "
                "was kept, the other protoclusters authored separately.\n")
        report, summary = br.verify_card(pkg, "BGC018", card, cmap=None)
        assert summary["n_unaddressed_block"] == 0
        assert all(r["status"] == "ADDRESSED" for r in report if r["severity"] == "BLOCK")


def test_verify_card_unknown_bgc_errors():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = _pkg(tmp, [_row(Rank=1, BGC_ID="BGC001", Node_ID="n", antiSMASH_Region="region001",
                              Products="NRPS", Boundary="Interior", Class_Conf="HIGH")])
        report, summary = br.verify_card(pkg, "BGC999", "# card\n", cmap=None)
        assert report == []
        assert "error" in summary


def test_next_action_names_the_real_tool():
    """Each contradiction must carry a runnable action naming the real resolution tool:
    OVER_MERGE -> scope_cluster; CLASS_DISCREPANCY -> hmm-adjudicate (v9.7.303 chain)."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = _pkg(tmp, [
            _row(Rank=1, BGC_ID="BGC018", Node_ID="rec1", Contig="rec1",
                 antiSMASH_Region="region018", Products="NRPS;RiPP;other",
                 Boundary="Interior", Class_Conf="HIGH"),
        ])
        with open(Path(pkg) / "SYN_predicted_polymers.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["record_id", "region_number", "n_protoclusters", "candidate_kind", "over_merge_flag"])
            w.writerow(["rec1", "18", "3", "neighbouring", "YES (split before product claims)"])
        e = br.reconcile(pkg, cmap=None)[0][0]
        om = next(c for c in e["contradictions"] if c["code"] == "OVER_MERGE")
        assert "scope_cluster.py" in (om.get("action") or "")
        assert "--category" in om["action"]


def test_over_merge_from_predicted_polymers():
    """The antiSMASH '>=2 BGCs' signal lives in predicted_polymers.csv, not the triage board.
    reconcile() must join it by region number and BLOCK a composite region (real BGC018 case)."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = _pkg(tmp, [
            _row(Rank=1, BGC_ID="BGC018", Node_ID="NODE_1", antiSMASH_Region="region018",
                 Products="NRP-metallophore;NRPS;RiPP", Boundary="Interior", Class_Conf="HIGH"),
            _row(Rank=2, BGC_ID="BGC001", Node_ID="NODE_2", antiSMASH_Region="region001",
                 Products="terpene", Boundary="Interior", Class_Conf="HIGH"),
        ])
        # sidecar the engine emits; region 18 = 4-protocluster chemical hybrid, region 1 = single
        with open(Path(pkg) / "SYN_predicted_polymers.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["record_id", "region_number", "sc_number", "n_protoclusters",
                        "candidate_kind", "over_merge_flag"])
            w.writerow(["rec1", "18", "23", "4", "chemical_hybrid|neighbouring|single",
                        "YES (region likely >=2 BGCs; split before product claims)"])
            w.writerow(["rec1", "1", "1", "1", "single", "no"])
        ledger, _ = br.reconcile(pkg, cmap=None)
        by_id = {e["bgc_id"]: e for e in ledger}
        assert "OVER_MERGE" in _codes(by_id["BGC018"])
        assert by_id["BGC018"]["n_block"] >= 1
        assert "4 protoclusters" in next(c["evidence"] for c in by_id["BGC018"]["contradictions"]
                                         if c["code"] == "OVER_MERGE")
        # a single-protocluster region must NOT be flagged
        assert "OVER_MERGE" not in _codes(by_id["BGC001"])


def test_over_merge_absent_without_sidecar():
    """No predicted_polymers.csv → no OVER_MERGE (graceful, not an error)."""
    with tempfile.TemporaryDirectory() as tmp:
        pkg = _pkg(tmp, [_row(Rank=1, BGC_ID="BGC001", Node_ID="NODE_1",
                              antiSMASH_Region="region018", Products="NRPS",
                              Boundary="Interior", Class_Conf="HIGH")])
        e = br.reconcile(pkg, cmap=None)[0][0]
        assert "OVER_MERGE" not in _codes(e)


def test_norm_compound_joins_frontpage_to_triage():
    """The KCB tier join must survive the 'BGC0000116.5 | name | known 78%' triage layout
    and match the frontpage's bare compound name (real Ae150A-Ps1 failure: r1c1/region007)."""
    board = br._norm_compound("BGC0000116.5 | nystatin-like Pseudonocardia polyene A1 | knownclusterblast #1")
    front = br._norm_compound("nystatin-like Pseudonocardia polyene A1")
    assert board and board == front
    # accession-only / metadata-only fields do not become the key
    assert br._norm_compound("BGC0000392.5 | mirubactin | known 42%") == br._norm_compound("mirubactin")
    assert br._norm_compound("") == ""


def test_rendered_ledger_passes_claim_safety_linter():
    """A tool that enforces claim discipline must model it: its own prose must be lint-clean."""
    from claim_safety_linter import lint_claim_safety
    with tempfile.TemporaryDirectory() as tmp:
        pkg = _pkg(tmp, [
            _row(Rank=1, BGC_ID="BGC001", Node_ID="NODE_3", antiSMASH_Region="region001",
                 Products="lanthipeptide", Boundary="Edge", Class_Conf="LOW",
                 KCB_top="mycotrienin I", KCB_score="50", Primary_metab_flag="SUF_operon",
                 Misanchor_Flag="SHIFT", Two_Pathway_Flag="TWO_PATHWAY:PKS+NRPS", Concordance="LOW"),
        ])
        md = br.render_md(*br.reconcile(pkg, cmap=None), pkg)
        assert lint_claim_safety(md) == []
