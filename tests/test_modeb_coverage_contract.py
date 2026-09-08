import json
from pathlib import Path
from types import SimpleNamespace

from mamey.chatgpt_commands import mode_b_command


def _write_pkg(tmp_path: Path):
    pkg = tmp_path / "AS_XXX" / "package"
    pkg.mkdir(parents=True)
    manifest = {
        "strain": {"strain_id": "AS-XXX"},
        "bgcs": [{"bgc_id": f"BGC{i:03d}", "products": ["T1PKS"], "edge_status": "Interior"} for i in range(1, 6)],
        "source_scans": {"blda_tta": {"per_bgc": {}}, "resistance_tiers": {"per_bgc": {}}},
    }
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    triage = pkg / "AS-XXX_4_triage_board.csv"
    triage.write_text(
        "BGC_ID,Contig,Products,AB_auto,AF_auto,Novelty_auto,Standing_rule,Primary_metab_flag,Boundary,Arch,Class_Conf,KCB_top,KCB_score,CCTT_triggers\n"
        "BGC001,NODE_1,T1PKS,90,10,5,,,Interior,A,HIGH,BGC0000001,1000,\n"
        "BGC002,NODE_2,T1PKS,80,10,5,,,Interior,A,HIGH,BGC0000002,900,\n"
        "BGC003,NODE_3,T1PKS,70,10,5,,,Interior,A,HIGH,BGC0000003,800,\n",
        encoding="utf-8",
    )
    return pkg


def test_modeb_coverage_receipt_reports_partial_native_coverage(tmp_path):
    pkg = _write_pkg(tmp_path)
    args = SimpleNamespace(package=str(pkg), top_n=5, outdir=None, node_first=True, with_domain_level=False, strict_all=False)
    rc = mode_b_command(args)
    assert rc == 0
    receipt = json.loads((pkg / "mode_b" / "Mode_B_Coverage_Receipt.json").read_text())
    assert receipt["requested_top_n"] == 5
    assert receipt["inventory_bgc_count"] == 5
    assert receipt["emitted_card_count"] == 3
    assert receipt["coverage_status"] == "PARTIAL_NATIVE_MODEB_COVERAGE"
    assert receipt["missing_bgc_ids"] == ["BGC004", "BGC005"]


def test_modeb_strict_all_exits_nonzero_on_partial_full_request(tmp_path):
    pkg = _write_pkg(tmp_path)
    args = SimpleNamespace(package=str(pkg), top_n=5, outdir=None, node_first=True, with_domain_level=False, strict_all=True)
    rc = mode_b_command(args)
    assert rc == 2


def test_modeb_topn_request_is_not_full_inventory_contract(tmp_path):
    pkg = _write_pkg(tmp_path)
    args = SimpleNamespace(package=str(pkg), top_n=2, outdir=None, node_first=True, with_domain_level=False, strict_all=True)
    rc = mode_b_command(args)
    assert rc == 0
    receipt = json.loads((pkg / "mode_b" / "Mode_B_Coverage_Receipt.json").read_text())
    assert receipt["coverage_status"] == "TOPN_NATIVE_MODEB_COVERAGE"
    assert receipt["missing_bgc_ids"] == []


def test_modeb_refuses_ambiguous_triage_board_before_writing_output(tmp_path):
    pkg = _write_pkg(tmp_path)
    (pkg / "ARCHIVE_4_triage_board.csv").write_text("BGC_ID\nBGC999\n", encoding="utf-8")
    args = SimpleNamespace(package=str(pkg), top_n=2, outdir=None, node_first=True,
                           with_domain_level=False, strict_all=False)
    assert mode_b_command(args) == 1
    assert not (pkg / "mode_b").exists()


def test_modeb_refuses_missing_manifest_strain_identity_before_writing_output(tmp_path):
    pkg = _write_pkg(tmp_path)
    manifest_path = pkg / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("strain", None)
    manifest.pop("strain_id", None)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (pkg / "AS-XXX_4_triage_board.csv").rename(pkg / "AS_XXX_4_triage_board.csv")
    args = SimpleNamespace(package=str(pkg), top_n=2, outdir=None, node_first=True,
                           with_domain_level=False, strict_all=False)
    assert mode_b_command(args) == 1
    assert not (pkg / "mode_b").exists()


def test_modeb_refuses_conflicting_manifest_strain_identities_before_writing_output(tmp_path):
    pkg = _write_pkg(tmp_path)
    manifest_path = pkg / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["strain_id"] = "OTHER-STRAIN"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    args = SimpleNamespace(package=str(pkg), top_n=2, outdir=None, node_first=True,
                           with_domain_level=False, strict_all=False)
    assert mode_b_command(args) == 1
    assert not (pkg / "mode_b").exists()
