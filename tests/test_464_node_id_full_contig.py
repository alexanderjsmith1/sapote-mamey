"""Ruling 479: Node_ID is the full contig from engine 1.9.180.

The old shortening stopped at the first dot, so a SPAdes coverage decimal was
dropped (NODE_5_length_8000_cov_3.25 -> NODE_5_length_8000_cov_3). New packages
keep the full contig. Stored packages and stored cards keep their legacy short form,
and only that exact form of the same contig is still accepted.
"""
from dataclasses import asdict

import pytest

import mamey.mode_b_receipt as receipt_mod
from mamey.crosswalk import (
    assembly_locator, enrich_bgc_crosswalk, infer_node_id, legacy_short_node_id,
)
from mamey.exact_identity import (
    ExactLocusIdentityError, exact_locus_from_native_inventory_row,
    exact_locus_from_native_manifest_bgc, validate_native_legacy_evidence_anchor,
)
from mamey.judgment_store import read_register
from mamey.models import BGCRecord
from mamey.modeb_template_emitter import _section_body
from tests._modeb_card_fixtures import valid_modeb_card_stub
from tests.test_auto_detect_ingest import _make_pkg_with_register, _write_card
from tests.test_mode_b_receipt import _make_package, _write_receipt

STRAIN = "SYN-1"
DECIMAL = "NODE_5_length_8000_cov_3.25"
DECIMAL_SHORT = "NODE_5_length_8000_cov_3"
INTEGER = "NODE_6_length_9000_cov_14"
WRONG_SHORT = "NODE_9_length_8000_cov_3"


def _record(contig):
    bgc = BGCRecord(bgc_id="BGC001", contig=contig, region_number=1, start=1, end=500,
                    contig_length=8000, products=["NRPS"])
    return enrich_bgc_crosswalk(bgc, "unused.region001.gbk")


def _manifest_row(contig, node_id):
    return {"contig": contig, "node_id": node_id, "antismash_region": "region001", "bgc_id": "BGC001"}


def _inventory(pkg, contig, node_id):
    rows = ("BGC_ID,Contig,Node_ID,antiSMASH_Region\n"
            f"BGC001,{contig},{node_id},region001\n")
    (pkg / f"{STRAIN}_2_inventory.csv").write_text(rows, encoding="utf-8")
    # The triage board carries the same locus; ingest binds the card header to it.
    (pkg / f"{STRAIN}_4_triage_board.csv").write_text(rows, encoding="utf-8")


def _card(node):
    return (f"<!-- MODE B TEMPLATE | bgc: BGC001 | node: {node} | region: region001 | "
            f"strain: {STRAIN} | products: NRPS -->\n\n"
            + valid_modeb_card_stub("BGC001", node=node, strain_id=STRAIN))


# ---- new packages -----------------------------------------------------------------

def test_decimal_coverage_contig_keeps_full_name_everywhere():
    bgc = _record(DECIMAL)
    row = bgc.crosswalk_dict()
    assert infer_node_id(DECIMAL, "") == DECIMAL
    assert bgc.node_id == DECIMAL
    assert row["node_id"] == DECIMAL
    assert assembly_locator(bgc).startswith(f"{DECIMAL} region001")
    assert bgc.user_label.startswith(DECIMAL)
    identity = exact_locus_from_native_manifest_bgc(STRAIN, row)
    assert identity.normalized_node_id == DECIMAL
    assert identity.exact_locus == f"{STRAIN} / {DECIMAL} / region001 / BGC001"


def test_legacy_function_is_the_frozen_old_shortening():
    assert legacy_short_node_id(DECIMAL) == DECIMAL_SHORT
    assert legacy_short_node_id("contig_1a") == "contig_1"
    assert legacy_short_node_id("CP000001.1") == "CP000001.1"
    assert infer_node_id("contig_1a", "") == "contig_1a"


def test_integer_coverage_contig_has_one_form_and_loads():
    assert infer_node_id(INTEGER, "") == INTEGER
    assert legacy_short_node_id(INTEGER) == INTEGER
    identity = exact_locus_from_native_manifest_bgc(STRAIN, asdict(_record(INTEGER)))
    assert identity.normalized_node_id == INTEGER
    # A pattern guard would have treated this whole-number coverage name as a short form.
    assert identity.exact_locus == f"{STRAIN} / {INTEGER} / region001 / BGC001"


def test_template_section_line_names_full_contig_for_a_stored_short_node_id():
    facts = {"bgc_id": "BGC001", "node": DECIMAL_SHORT, "contig": DECIMAL, "region": "region001"}
    assert f"**Node / contig:** {DECIMAL}\n" in _section_body(1, facts, {})


# ---- stored packages --------------------------------------------------------------

def test_stored_package_with_legacy_short_node_id_still_loads():
    identity = exact_locus_from_native_manifest_bgc(STRAIN, _manifest_row(DECIMAL, DECIMAL_SHORT))
    assert identity.full_contig == DECIMAL
    assert identity.normalized_node_id == DECIMAL_SHORT
    assert identity.exact_locus == f"{STRAIN} / {DECIMAL} / region001 / BGC001"
    board = exact_locus_from_native_inventory_row(
        STRAIN, {"Contig": DECIMAL, "Node_ID": DECIMAL_SHORT,
                 "antiSMASH_Region": "region001", "BGC_ID": "BGC001"})
    assert board.exact_locus == identity.exact_locus


@pytest.mark.parametrize("anchor_contig", [DECIMAL_SHORT, DECIMAL])
@pytest.mark.parametrize("board_node", [DECIMAL_SHORT, DECIMAL])
def test_legacy_evidence_anchor_binds_on_either_form(anchor_contig, board_node):
    board = exact_locus_from_native_manifest_bgc(STRAIN, _manifest_row(DECIMAL, board_node))
    anchor = {"strain": STRAIN, "contig": anchor_contig, "region": "region001", "bgc_id": "BGC001"}
    binding = validate_native_legacy_evidence_anchor(STRAIN, anchor, board)
    assert binding.board_identity is board


@pytest.mark.parametrize("node_id", [WRONG_SHORT, "NODE_5_length_8000_cov_32", "NODE_5", "NODE_5_length_8000"])
def test_node_id_that_is_neither_form_is_refused(node_id):
    with pytest.raises(ExactLocusIdentityError, match="neither the full contig nor its legacy short form"):
        exact_locus_from_native_manifest_bgc(STRAIN, _manifest_row(DECIMAL, node_id))
    board = exact_locus_from_native_manifest_bgc(STRAIN, _manifest_row(DECIMAL, DECIMAL))
    anchor = {"strain": STRAIN, "contig": node_id, "region": "region001", "bgc_id": "BGC001"}
    with pytest.raises(ExactLocusIdentityError):
        validate_native_legacy_evidence_anchor(STRAIN, anchor, board)


# ---- stored cards -----------------------------------------------------------------

def _receipt_ingest(tmp_path, node, *, package_node_id=DECIMAL_SHORT):
    pkg = _make_package(tmp_path, strain=STRAIN, bgc_ids=("BGC001",))
    _inventory(pkg, DECIMAL, package_node_id)
    rcpt = _write_receipt(tmp_path, [{"bgc_id": "BGC001", "mode_b_md": _card(node)}], strain=STRAIN)
    return pkg, receipt_mod.ingest_receipt(pkg, rcpt, force_structure=True)


def _auto_ingest(tmp_path, node, *, package_node_id=DECIMAL_SHORT):
    pkg = _make_pkg_with_register(tmp_path, STRAIN, bgc_states={"BGC001": "PENDING"})
    _inventory(pkg, DECIMAL, package_node_id)
    _write_card(pkg, STRAIN, "BGC001", _card(node))
    return pkg, receipt_mod.auto_detect_ingest(pkg, force_structure=True)


@pytest.mark.parametrize("package_node_id", [DECIMAL_SHORT, DECIMAL])
def test_legacy_short_header_is_accepted_with_note_on_receipt_ingest(tmp_path, package_node_id):
    pkg, summary = _receipt_ingest(tmp_path, DECIMAL_SHORT, package_node_id=package_node_id)
    assert summary["skipped_identity_mismatch"] == []
    assert summary["recorded"] + summary["recorded_with_structure_override"] == ["BGC001"]
    (note,) = summary["identity_notes"]
    assert note["code"] == "LEGACY_SHORT_NODE"
    assert (note["bgc_id"], note["card_node"], note["package_contig"]) == ("BGC001", DECIMAL_SHORT, DECIMAL)
    assert read_register(pkg)["bgcs"]["BGC001"]["status"] == "COMPLETE"


def test_legacy_short_header_is_accepted_with_note_on_auto_detect(tmp_path):
    pkg, summary = _auto_ingest(tmp_path, DECIMAL_SHORT)
    assert summary["skipped_identity_mismatch"] == []
    assert summary["recorded"] + summary["recorded_with_structure_override"] == ["BGC001"]
    (note,) = summary["identity_notes"]
    assert note["code"] == "LEGACY_SHORT_NODE" and note["package_contig"] == DECIMAL
    card = pkg / "judgment" / f"{STRAIN}_BGC001_mode_b.md"
    # The stored card keeps its short header: ingest adds only its usual record header above it.
    assert card.read_text(encoding="utf-8").endswith(_card(DECIMAL_SHORT))


def test_legacy_short_header_is_accepted_with_note_on_single_card_ingest(tmp_path):
    pkg = _make_package(tmp_path, strain=STRAIN, bgc_ids=("BGC001",))
    _inventory(pkg, DECIMAL, DECIMAL_SHORT)
    path = tmp_path / "card.md"
    path.write_text(_card(DECIMAL_SHORT), encoding="utf-8")
    summary = receipt_mod.ingest_one_card(pkg, path, force_structure=True)
    assert summary["status"] != "SKIPPED_IDENTITY_MISMATCH"
    assert [n["code"] for n in summary["identity_notes"]] == ["LEGACY_SHORT_NODE"]


def test_full_header_needs_no_note(tmp_path):
    _pkg, summary = _receipt_ingest(tmp_path, DECIMAL)
    assert summary["skipped_identity_mismatch"] == []
    assert summary["identity_notes"] == []


@pytest.mark.parametrize("flow", ["receipt", "auto"])
def test_wrong_short_header_is_still_refused(tmp_path, flow):
    ingest = _receipt_ingest if flow == "receipt" else _auto_ingest
    pkg, summary = ingest(tmp_path, WRONG_SHORT)
    assert summary["recorded"] == [] and summary["recorded_with_structure_override"] == []
    assert len(summary["skipped_identity_mismatch"]) == 1
    assert summary["identity_notes"] == []
    assert read_register(pkg)["bgcs"]["BGC001"]["status"] == "PENDING"


def test_acceptance_ends_at_the_named_cut(tmp_path, monkeypatch):
    assert receipt_mod.LEGACY_SHORT_NODE_ACCEPTANCE_ENDS_AT_CUT is None
    assert receipt_mod.legacy_short_node_accepted("9.7.900", "9.7.899")
    assert not receipt_mod.legacy_short_node_accepted("9.7.900", "9.7.900")
    assert not receipt_mod.legacy_short_node_accepted("not a cut", "9.7.1")
    monkeypatch.setattr(receipt_mod, "LEGACY_SHORT_NODE_ACCEPTANCE_ENDS_AT_CUT", "1.0.0")
    _pkg, summary = _receipt_ingest(tmp_path, DECIMAL_SHORT)
    assert summary["skipped_identity_mismatch"][0]["reason"] == "CARD_PACKAGE_LOCUS_MISMATCH"
    assert summary["identity_notes"] == []
