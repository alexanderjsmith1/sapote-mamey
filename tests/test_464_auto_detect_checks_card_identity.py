"""ingest-receipts --auto-detect checks a card's identity, not just its file name."""
from tests._modeb_card_fixtures import valid_modeb_card_stub
from tests.test_auto_detect_ingest import _make_pkg_with_register, _write_card


def _header(bgc, node, strain="STRAINX"):
    return f"<!-- MODE B TEMPLATE | bgc: {bgc} | node: {node} | strain: {strain} | products: NRPS -->\n"


def test_header_naming_another_bgc_is_not_recorded(tmp_path):
    from mamey.mode_b_receipt import auto_detect_ingest
    pkg = _make_pkg_with_register(tmp_path, "STRAINX")
    _write_card(pkg, "STRAINX", "BGC001", _header("BGC002", "NODE_1") + valid_modeb_card_stub("BGC001", strain_id="STRAINX"))
    summary = auto_detect_ingest(pkg)
    assert summary["recorded"] == []
    assert summary["skipped_identity_mismatch"][0]["card"] == "STRAINX_BGC001_mode_b.md"


def test_header_node_that_differs_from_the_package_is_not_recorded(tmp_path):
    from mamey.mode_b_receipt import auto_detect_ingest
    pkg = _make_pkg_with_register(tmp_path, "STRAINX")
    (pkg / "STRAINX_2_inventory.csv").write_text(
        "BGC_ID,Contig,Node_ID,antiSMASH_Region\nBGC001,NODE_9_length_100_cov_5.5,NODE_9_length_100_cov_5,region001\n")
    _write_card(pkg, "STRAINX", "BGC001", _header("BGC001", "NODE_1") + valid_modeb_card_stub("BGC001", strain_id="STRAINX"))
    summary = auto_detect_ingest(pkg)
    assert summary["recorded"] == []
    assert "NODE_9_length_100_cov_5.5" in summary["skipped_identity_mismatch"][0]["expected"]


def test_matching_header_is_still_recorded(tmp_path):
    from mamey.mode_b_receipt import auto_detect_ingest
    pkg = _make_pkg_with_register(tmp_path, "STRAINX")
    (pkg / "STRAINX_2_inventory.csv").write_text(
        "BGC_ID,Contig,Node_ID,antiSMASH_Region\nBGC001,NODE_9_length_100_cov_5.5,NODE_9_length_100_cov_5,region001\n")
    _write_card(pkg, "STRAINX", "BGC001",
                _header("BGC001", "NODE_9_length_100_cov_5.5") + valid_modeb_card_stub("BGC001", strain_id="STRAINX"))
    assert auto_detect_ingest(pkg)["recorded"] == ["BGC001"]
