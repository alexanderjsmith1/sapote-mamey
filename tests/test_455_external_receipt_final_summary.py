"""A later nonpassing terminal summary must invalidate a matching earlier pass."""
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "tools" / "verify_external_validation_receipt.py"


def _fixture(tmp_path, log_text):
    spec = importlib.util.spec_from_file_location("receipt_final_summary", HELPER_PATH)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    root = tmp_path / "source"
    root.mkdir()
    (root / "module.py").write_text("VALUE = 1\n")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    contents = {"pytest.log": log_text, "nodeids.txt": "tests/test_one.py::test_one\n",
                "outcomes.tsv": "nodeid\toutcome\ntests/test_one.py::test_one\tpassed\n"}
    for name, text in contents.items():
        (evidence / name).write_text(text, encoding="utf-8")
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    payload = {
        "schema": helper.SCHEMA, "status": "PASS",
        "source": {"tree_sha256": helper.source_tree_sha256(root)},
        "execution": {"profile": helper.PROFILE, "argv": [sys.executable, *helper.COMMAND_TAIL],
                      "cwd": ".", "exit_code": 0, "python_version": sys.version.split()[0],
                      "pytest_version": pytest.__version__, "platform": sys.platform,
                      "started_utc": (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
                      "completed_utc": now.isoformat().replace("+00:00", "Z")},
        "artifacts": {key: {"path": name, "sha256": sha(evidence / name)} for key, name in
                      (("pytest_log", "pytest.log"), ("test_identity", "nodeids.txt"),
                       ("test_results", "outcomes.tsv"))},
        "results": {name: int(name == "passed") for name in helper.OUTCOMES},
    }
    payload["artifacts"]["test_identity"]["count"] = 1
    payload["results"]["total"] = 1
    receipt = evidence / "receipt.json"
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    return helper, root, receipt, sha(receipt), now


@pytest.mark.parametrize("later", [
    "1 error in 0.02s", "2 errors in 0.02s", "1 failed in 0.02s",
    "1 skipped in 0.02s", "no tests ran in 0.02s", "1 xfailed in 0.02s", "1 warning in 0.02s",
])
def test_later_nonpassing_summary_refuses_receipt(tmp_path, later):
    helper, root, receipt, digest, now = _fixture(tmp_path, "1 passed in 0.01s\n" + later + "\n")
    with pytest.raises(helper.ReceiptRefused, match="summary does not match"):
        helper.verify_receipt(receipt, root, digest, now=now)


@pytest.mark.parametrize("log_text", [
    "1 passed in 0.01s\n",
    "======================= 1 passed in 0.01s =======================\n",
    "1 passed in 0.01s\ntrailing diagnostic without a test summary\n",
    "1 passed in 0.01s\nreport saved in 0.02s\n",
    "1 error in 0.01s\n1 passed in 0.02s\n",
])
def test_final_passing_summary_still_admitted(tmp_path, log_text):
    helper, root, receipt, digest, now = _fixture(tmp_path, log_text)
    assert helper.verify_receipt(receipt, root, digest, now=now) == receipt.parent / "pytest.log"
