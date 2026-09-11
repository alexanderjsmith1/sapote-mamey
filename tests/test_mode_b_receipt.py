"""Tests for mamey.mode_b_receipt — the Sapote Mode B persistence front door (P-D)."""

import json
from pathlib import Path

import pytest

from mamey.judgment_store import init_register, read_register
from mamey.mode_b_receipt import ingest_receipt, RECEIPT_SCHEMA_VERSION

from tests._modeb_card_fixtures import valid_modeb_card_stub


def _make_package(tmp_path: Path, strain="AS-TEST", bgc_ids=("BGC001", "BGC002", "BGC003")):
    """Create a minimal package dir with an initialised judgment register."""
    pkg = tmp_path / strain
    pkg.mkdir()
    # judgment_store resolves strain from a manifest.json or dir name; provide manifest.
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": strain}))
    init_register(pkg, strain_id=strain, bgc_ids=list(bgc_ids))
    return pkg


def _write_receipt(tmp_path: Path, cards, strain="AS-TEST", session="sess1"):
    rcpt = tmp_path / "mode_b_receipt.json"
    rcpt.write_text(json.dumps({
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "strain_id": strain,
        "session_id": session,
        "cards": cards,
    }))
    return rcpt


def test_ingest_records_known_bgcs(tmp_path):
    pkg = _make_package(tmp_path)
    rcpt = _write_receipt(tmp_path, [
        {"bgc_id": "BGC001", "mode_b_md": valid_modeb_card_stub("BGC001", strain_id="AS-TEST")},
        {"bgc_id": "BGC002", "mode_b_md": valid_modeb_card_stub("BGC002", strain_id="AS-TEST")},
    ])
    summary = ingest_receipt(pkg, rcpt)
    assert set(summary["recorded"]) == {"BGC001", "BGC002"}
    reg = read_register(pkg)
    assert reg["bgcs"]["BGC001"]["status"] == "COMPLETE"
    assert reg["bgcs"]["BGC002"]["status"] == "COMPLETE"
    assert reg["bgcs"]["BGC003"]["status"] == "PENDING"
    assert reg["complete_bgcs"] == 2
    # Card file actually written
    assert (pkg / "judgment" / "AS-TEST_BGC001_mode_b.md").exists()


def test_ingest_rejects_receipt_strain_conflict_before_any_card_write(tmp_path):
    pkg = _make_package(tmp_path, strain="REF-A", bgc_ids=("BGC001",))
    rcpt = _write_receipt(
        tmp_path,
        [{"bgc_id": "BGC001",
          "mode_b_md": valid_modeb_card_stub("BGC001", strain_id="REF-B")}],
        strain="REF-B",
    )
    with pytest.raises(ValueError, match="Receipt strain_id conflicts"):
        ingest_receipt(pkg, rcpt)
    assert read_register(pkg)["bgcs"]["BGC001"]["status"] == "PENDING"
    assert not (pkg / "judgment" / "REF-A_BGC001_mode_b.md").exists()


@pytest.mark.parametrize(
    ("header", "reason"),
    [
        ("<!-- MODE B: BGC002 | strain: REF-A | session: test -->",
         "CARD_BGC_MISMATCH"),
        ("<!-- MODE B TEMPLATE | bgc: BGC001 | node: NODE_1 | strain: REF-B | -->",
         "CARD_STRAIN_MISMATCH"),
    ],
)
def test_ingest_rejects_card_header_identity_conflict_even_with_override(
    tmp_path, header, reason
):
    pkg = _make_package(tmp_path, strain="REF-A", bgc_ids=("BGC001", "BGC002"))
    content = header + "\n\n" + valid_modeb_card_stub(
        "BGC001", node="NODE_1", strain_id="REF-A"
    )
    rcpt = _write_receipt(
        tmp_path,
        [{"bgc_id": "BGC001", "mode_b_md": content}],
        strain="REF-A",
    )
    summary = ingest_receipt(pkg, rcpt, force_structure=True)
    assert summary["recorded"] == []
    assert summary["recorded_with_structure_override"] == []
    assert summary["skipped_identity_mismatch"][0]["reason"] == reason
    assert read_register(pkg)["bgcs"]["BGC001"]["status"] == "PENDING"
    assert not (pkg / "judgment" / "REF-A_BGC001_mode_b.md").exists()


def test_ingest_accepts_matching_card_header_identity(tmp_path):
    pkg = _make_package(tmp_path, strain="REF-A", bgc_ids=("BGC001",))
    content = (
        "<!-- MODE B: BGC001 | strain: REF-A | session: test -->\n\n"
        + valid_modeb_card_stub("BGC001", node="NODE_1", strain_id="REF-A")
    )
    rcpt = _write_receipt(
        tmp_path,
        [{"bgc_id": "BGC001", "mode_b_md": content}],
        strain="REF-A",
    )
    summary = ingest_receipt(pkg, rcpt)
    assert summary["recorded"] == ["BGC001"]
    assert summary["skipped_identity_mismatch"] == []


def _write_exact_inventory(pkg, *, full_node="NODE_7_length_12345_cov_20.500000",
                           node_id="NODE_7_length_12345_cov_20", region="region001"):
    (pkg / "AS-TEST_2_inventory.csv").write_text(
        "BGC_ID,Contig,Node_ID,antiSMASH_Region\n"
        f"BGC001,{full_node},{node_id},{region}\n"
    )


def _card_with_exact_header(*, node, region="region001"):
    return (
        f"<!-- MODE B TEMPLATE | bgc: BGC001 | node: {node} | "
        f"region: {region} | strain: AS-TEST | -->\n\n"
        + valid_modeb_card_stub("BGC001", node=node, strain_id="AS-TEST")
    )


def test_batch_ingest_rejects_package_node_mismatch_even_with_override(tmp_path):
    pkg = _make_package(tmp_path, strain="AS-TEST", bgc_ids=("BGC001",))
    _write_exact_inventory(pkg)
    content = _card_with_exact_header(node="NODE_8_length_12345_cov_20.500000")
    rcpt = _write_receipt(
        tmp_path, [{"bgc_id": "BGC001", "mode_b_md": content}], strain="AS-TEST"
    )
    summary = ingest_receipt(pkg, rcpt, force_structure=True)
    assert summary["recorded"] == []
    assert summary["recorded_with_structure_override"] == []
    assert summary["skipped_identity_mismatch"][0]["reason"] == "CARD_PACKAGE_LOCUS_MISMATCH"
    assert "NODE_7_length_12345_cov_20.500000" in summary["skipped_identity_mismatch"][0]["expected_locus"]
    assert read_register(pkg)["bgcs"]["BGC001"]["status"] == "PENDING"


def test_batch_ingest_prefers_full_contig_over_shortened_node_id(tmp_path):
    pkg = _make_package(tmp_path, strain="AS-TEST", bgc_ids=("BGC001",))
    full_node = "NODE_7_length_12345_cov_20.500000"
    _write_exact_inventory(pkg, full_node=full_node)
    rcpt = _write_receipt(
        tmp_path,
        [{"bgc_id": "BGC001", "mode_b_md": _card_with_exact_header(node=full_node)}],
        strain="AS-TEST",
    )
    summary = ingest_receipt(pkg, rcpt, force_structure=True)
    assert summary["skipped_identity_mismatch"] == []
    assert summary["recorded"] + summary["recorded_with_structure_override"] == ["BGC001"]


def test_batch_ingest_rejects_package_region_mismatch_even_with_override(tmp_path):
    pkg = _make_package(tmp_path, strain="AS-TEST", bgc_ids=("BGC001",))
    full_node = "NODE_7_length_12345_cov_20.500000"
    _write_exact_inventory(pkg, full_node=full_node, region="region001")
    rcpt = _write_receipt(
        tmp_path,
        [{"bgc_id": "BGC001", "mode_b_md": _card_with_exact_header(node=full_node, region="region002")}],
        strain="AS-TEST",
    )
    summary = ingest_receipt(pkg, rcpt, force_structure=True)
    assert summary["recorded"] == []
    assert summary["recorded_with_structure_override"] == []
    assert summary["skipped_identity_mismatch"][0]["reason"] == "CARD_PACKAGE_LOCUS_MISMATCH"
    assert summary["skipped_identity_mismatch"][0]["expected_locus"].endswith("in region001")
    assert read_register(pkg)["bgcs"]["BGC001"]["status"] == "PENDING"


def test_ingest_fail_closed_on_unknown_bgc(tmp_path):
    """An unknown BGC must be skipped and reported, never invented into the register."""
    pkg = _make_package(tmp_path)
    rcpt = _write_receipt(tmp_path, [
        {"bgc_id": "BGC001", "mode_b_md": valid_modeb_card_stub("BGC001", strain_id="AS-TEST")},
        {"bgc_id": "BGC999", "mode_b_md": valid_modeb_card_stub("BGC999", strain_id="AS-TEST")},
    ])
    summary = ingest_receipt(pkg, rcpt)
    assert summary["recorded"] == ["BGC001"]
    assert summary["skipped_unknown"] == ["BGC999"]
    reg = read_register(pkg)
    assert "BGC999" not in reg["bgcs"]


def test_ingest_skips_empty_content(tmp_path):
    pkg = _make_package(tmp_path)
    rcpt = _write_receipt(tmp_path, [
        {"bgc_id": "BGC001", "mode_b_md": valid_modeb_card_stub("BGC001", strain_id="AS-TEST")},
        {"bgc_id": "BGC002", "mode_b_md": "   "},  # intentionally whitespace-only (negative test)
    ])
    summary = ingest_receipt(pkg, rcpt)
    assert summary["recorded"] == ["BGC001"]
    assert summary["skipped_no_content"] == ["BGC002"]
    assert read_register(pkg)["bgcs"]["BGC002"]["status"] == "PENDING"


def test_ingest_idempotent(tmp_path):
    """Re-ingesting the same receipt does not change the complete count."""
    pkg = _make_package(tmp_path)
    rcpt = _write_receipt(tmp_path, [{"bgc_id": "BGC001", "mode_b_md": valid_modeb_card_stub("BGC001", strain_id="AS-TEST")}])
    ingest_receipt(pkg, rcpt)
    first = read_register(pkg)["complete_bgcs"]
    ingest_receipt(pkg, rcpt)
    second = read_register(pkg)["complete_bgcs"]
    assert first == second == 1


def test_ingest_records_layperson_and_fermentation(tmp_path):
    pkg = _make_package(tmp_path)
    rcpt = _write_receipt(tmp_path, [
        {"bgc_id": "BGC001", "mode_b_md": valid_modeb_card_stub("BGC001", strain_id="AS-TEST"),
         "layperson_paragraph": "plain words here",
         "fermentation_note": "SAX fractionation note"},
    ])
    ingest_receipt(pkg, rcpt)
    lay = (pkg / "judgment" / "AS-TEST_laypersons_section.md").read_text()
    ferm = (pkg / "judgment" / "AS-TEST_fermentation_section.md").read_text()
    assert "plain words here" in lay
    assert "SAX fractionation note" in ferm


def test_ingest_raises_on_uninitialised_register(tmp_path):
    pkg = tmp_path / "AS-NONE"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "AS-NONE"}))
    rcpt = _write_receipt(tmp_path, [{"bgc_id": "BGC001", "mode_b_md": valid_modeb_card_stub("BGC001", strain_id="AS-NONE")}], strain="AS-NONE")
    with pytest.raises(ValueError, match="NOT_INITIALISED"):
        ingest_receipt(pkg, rcpt)


def test_ingest_bad_receipt_json(tmp_path):
    pkg = _make_package(tmp_path)
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json")
    with pytest.raises(ValueError, match="not valid JSON"):
        ingest_receipt(pkg, bad)


def test_ingest_missing_cards_array(tmp_path):
    pkg = _make_package(tmp_path)
    bad = tmp_path / "nocards.json"
    bad.write_text(json.dumps({"schema_version": RECEIPT_SCHEMA_VERSION, "strain_id": "AS-TEST"}))
    with pytest.raises(ValueError, match="cards"):
        ingest_receipt(pkg, bad)
