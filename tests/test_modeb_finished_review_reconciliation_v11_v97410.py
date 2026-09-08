"""Request-v1.9 coupling for the prospective §28 specificity gate."""
from __future__ import annotations

import json

from mamey.mode_b_receipt import validate_finished_review_request
from tests.test_modeb_finished_review_request_v97410 import (
    _fixture,
    _sha,
    _snapshot,
    _upgrade_to_v10,
    _write_json,
)


PROFILE = (
    "SUBSTANTIVE_V2_PLUS_SEMANTIC_SECTIONS_V3_PLUS_SEMANTIC_COMPARATORS_V4_PLUS_"
    "SEMANTIC_SECTIONS_V5_PLUS_SEMANTIC_DECISION_CHAINS_V6_PLUS_"
    "SEMANTIC_CLAIM_MODELS_V7_PLUS_INVENTORY_RECONCILIATION_V8_PLUS_"
    "SELECTION_PROCESS_V9_PLUS_FIGURE_SPEC_V10_PLUS_RECONCILIATION_SPECIFICITY_V11"
)


TOKENS = (
    "amber birch cedar dahlia elm fir ginger hazel iris juniper kelp lilac maple nutmeg "
    "olive pine quince rose sage thyme umber violet willow xenia yarrow zinnia acorn basil "
    "clover dogwood eucalyptus fennel gardenia heather indigo jasmine kumquat lavender "
    "magnolia nectarine orchid papaya quinoa rosemary saffron tulip verbena walnut"
).split()


def _upgrade_to_v11(pkg, root, request_path, request, *, distinct_card=True):
    _upgrade_to_v10(pkg, root, request_path, request)
    card_path = root / request["card"]["locator"]
    if distinct_card:
        card = card_path.read_text()
        for section, token in enumerate(TOKENS, 1):
            card = card.replace(
                f"| §{section} | SUBSTANTIVE | named source | RETAIN | reconciled |",
                f"| §{section} | SUBSTANTIVE | {token} assay receipt | RETAIN | "
                f"{token} evidence retained after conflict review |",
            )
        card_path.write_text(card)
        request["card"]["sha256"] = _sha(card_path)
    request["schema_version"] = "mode-b-finished-review-request-1.9"
    request["quality_profile"] = PROFILE
    common = {
        "exact_identity": request["identity"]["display"],
        "card_sha256": request["card"]["sha256"],
        "package_manifest_sha256": request["package_manifest_sha256"],
        "query_roster_sha256": request["roster"]["query_roster_sha256"],
        "quality_profile": PROFILE,
    }
    for spec in request["verification_receipts"].values():
        path = root / spec["locator"]
        receipt = json.loads(path.read_text())
        receipt.update(common)
        path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
        spec["sha256"] = _sha(path)
    request["verification_receipts"]["reconciliation_specificity_v11"] = _write_json(
        root / "receipts" / "reconciliation_v11.json",
        {**common, "status": "PASS", "reconciliation_specificity_v11": True},
    )
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")


def test_v19_profile_is_bound_rerun_and_read_only(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v11(pkg, root, request_path, request)
    before = _snapshot(tmp_path)
    result = validate_finished_review_request(pkg, request_path, root)
    assert result["status"] == "READY_FOR_OWNER_REVIEW"
    assert result["schema_version"] == "mode-b-finished-review-request-1.9"
    assert result["mutation_performed"] is False
    assert _snapshot(tmp_path) == before


def test_v19_fake_pass_cannot_replace_live_reconciliation_gate(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v11(pkg, root, request_path, request, distinct_card=False)
    result = validate_finished_review_request(pkg, request_path, root)
    assert "REVIEW_LIVE_FINISHED_GATE_NOT_PASS" in result["finding_codes"]


def test_v19_requires_exact_profile_and_true_receipt(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v11(pkg, root, request_path, request)
    request["quality_profile"] = "RECONCILIATION_SPECIFICITY_V11"
    spec = request["verification_receipts"]["reconciliation_specificity_v11"]
    path = root / spec["locator"]
    receipt = json.loads(path.read_text())
    receipt["reconciliation_specificity_v11"] = False
    path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    spec["sha256"] = _sha(path)
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert "REVIEW_REQUEST_QUALITY_PROFILE_MISMATCH" in codes
    assert "REVIEW_RECONCILIATION_V11_RECEIPT_NOT_PASS" in codes


def test_v18_rejects_stray_v11_receipt(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v10(pkg, root, request_path, request)
    request["verification_receipts"]["reconciliation_specificity_v11"] = {
        "locator": "receipts/none.json", "sha256": "0" * 64}
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert "REVIEW_VERIFICATION_RECEIPT_SET_MISMATCH" in codes


def test_v19_receipt_must_bind_exact_card_and_profile(tmp_path):
    pkg, root, request_path, request = _fixture(tmp_path)
    _upgrade_to_v11(pkg, root, request_path, request)
    spec = request["verification_receipts"]["reconciliation_specificity_v11"]
    path = root / spec["locator"]
    receipt = json.loads(path.read_text())
    receipt["card_sha256"] = "0" * 64
    receipt["quality_profile"] = "wrong"
    path.write_text(json.dumps(receipt, sort_keys=True) + "\n")
    spec["sha256"] = _sha(path)
    request_path.write_text(json.dumps(request, sort_keys=True) + "\n")
    codes = validate_finished_review_request(pkg, request_path, root)["finding_codes"]
    assert "REVIEW_RECEIPT_BINDING_MISMATCH" in codes
