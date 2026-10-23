"""Only well-formed identities, rows and integer result metadata are admitted."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "tools/verify_external_validation_receipt.py"


def _case(tmp_path):
    # Reuse the shipped producer-shaped fixture in place, with the selected tool.
    spec = importlib.util.spec_from_file_location(
        "existing_receipt_fixture", ROOT / "tests/test_release_external_validation_receipt_sol10.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    fixture.HELPER_PATH = HELPER_PATH
    helper, source, evidence, receipt, payload, now = fixture._receipt_fixture(tmp_path)
    # A single exact node makes JSON true/1 and false/0 equality visible.
    (evidence / "nodeids.txt").write_text("tests/test_alpha.py::test_alpha\n")
    (evidence / "outcomes.tsv").write_text("nodeid\toutcome\ntests/test_alpha.py::test_alpha\tpassed\n")
    (evidence / "pytest.log").write_text("1 passed in 0.01s\n")
    payload["artifacts"]["test_identity"]["count"] = 1
    payload["results"] = {key: int(key == "passed") for key in helper.OUTCOMES}
    payload["results"]["total"] = 1
    return helper, source, evidence, receipt, payload, now


def _verify(case):
    helper, source, evidence, receipt, payload, now = case
    for block in payload["artifacts"].values():
        path = evidence / block["path"]
        block["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    receipt.write_text(json.dumps(payload))
    return helper.verify_receipt(receipt, source, hashlib.sha256(receipt.read_bytes()).hexdigest(), now=now)


@pytest.mark.parametrize("field,value", [
    ("identity_count", True), ("exit_code", False), ("exit_code", 0.0),
    ("passed", True), ("passed", 1.0), ("skipped", False), ("skipped", 0.0),
    ("total", True), ("total", 1.0),
])
def test_non_integer_receipt_metadata_is_refused(tmp_path, field, value):
    case = _case(tmp_path)
    payload = case[4]
    if field == "identity_count":
        payload["artifacts"]["test_identity"]["count"] = value
    elif field == "exit_code":
        payload["execution"]["exit_code"] = value
    else:
        payload["results"][field] = value
    with pytest.raises(case[0].ReceiptRefused):
        _verify(case)


@pytest.mark.parametrize("nodeid", ["   ", "\t", "\u2003"])
def test_whitespace_only_identities_are_refused(tmp_path, nodeid):
    case = _case(tmp_path)
    evidence = case[2]
    (evidence / "nodeids.txt").write_text(nodeid + "\n")
    with (evidence / "outcomes.tsv").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["nodeid", "outcome"])
        writer.writerow([nodeid, "passed"])
    with pytest.raises(case[0].ReceiptRefused, match="blank node ID"):
        _verify(case)


@pytest.mark.parametrize("extra", ["\textra", "\t", "\tfailed"])
def test_extra_result_cells_are_refused(tmp_path, extra):
    case = _case(tmp_path)
    path = case[2] / "outcomes.tsv"
    path.write_text("nodeid\toutcome\ntests/test_alpha.py::test_alpha\tpassed" + extra + "\n")
    with pytest.raises(case[0].ReceiptRefused, match="exactly two cells"):
        _verify(case)


def test_missing_result_cell_is_refused(tmp_path):
    case = _case(tmp_path)
    (case[2] / "outcomes.tsv").write_text("nodeid\toutcome\ntests/test_alpha.py::test_alpha\n")
    with pytest.raises(case[0].ReceiptRefused):
        _verify(case)


def test_valid_identity_with_spaces_inside_a_parameter_is_preserved(tmp_path):
    case = _case(tmp_path)
    nodeid = "tests/test_alpha.py::test_alpha[value with spaces]"
    (case[2] / "nodeids.txt").write_text(nodeid + "\n")
    (case[2] / "outcomes.tsv").write_text("nodeid\toutcome\n" + nodeid + "\tpassed\n")
    assert _verify(case) == case[2] / "pytest.log"
