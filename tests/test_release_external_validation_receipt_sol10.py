"""Release external-validation receipts must bind exact source, command, identity, and results."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "tools" / "verify_external_validation_receipt.py"
BUILDER = ROOT / "tools" / "make_public_tier.sh"


def _load_helper():
    spec = importlib.util.spec_from_file_location("external_receipt", HELPER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _receipt_fixture(tmp_path: Path):
    helper = _load_helper()
    root = tmp_path / "exact source"
    root.mkdir()
    (root / "module.py").write_text("VALUE = 1\n", encoding="utf-8")

    evidence = tmp_path / "external evidence"
    evidence.mkdir()
    log = evidence / "pytest.log"
    log.write_text("1 passed, 1 skipped in 0.01s\n", encoding="utf-8")
    identity = evidence / "nodeids.txt"
    identity.write_text(
        "tests/test_alpha.py::test_alpha\n"
        "tests/test_beta.py::test_beta\n",
        encoding="utf-8",
    )
    outcomes = evidence / "outcomes.tsv"
    outcomes.write_text(
        "nodeid\toutcome\n"
        "tests/test_alpha.py::test_alpha\tpassed\n"
        "tests/test_beta.py::test_beta\tskipped\n",
        encoding="utf-8",
    )
    now = datetime.now(timezone.utc).replace(microsecond=0)
    receipt = evidence / "receipt.json"
    payload = {
        "schema": helper.SCHEMA,
        "status": "PASS",
        "source": {"tree_sha256": helper.source_tree_sha256(root)},
        "execution": {
            "profile": helper.PROFILE,
            "argv": [sys.executable, *helper.COMMAND_TAIL],
            "cwd": ".",
            "exit_code": 0,
            "started_utc": (now - timedelta(minutes=2)).isoformat().replace("+00:00", "Z"),
            "completed_utc": now.isoformat().replace("+00:00", "Z"),
            "python_version": sys.version.split()[0],
            "pytest_version": pytest.__version__,
            "platform": sys.platform,
        },
        "artifacts": {
            "pytest_log": {"path": log.name, "sha256": _sha(log)},
            "test_identity": {
                "path": identity.name,
                "sha256": _sha(identity),
                "count": 2,
            },
            "test_results": {"path": outcomes.name, "sha256": _sha(outcomes)},
        },
        "results": {
            "passed": 1,
            "skipped": 1,
            "xfailed": 0,
            "xpassed": 0,
            "failed": 0,
            "errors": 0,
            "total": 2,
        },
    }
    receipt.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return helper, root, evidence, receipt, payload, now


def _rewrite(receipt: Path, payload: dict) -> str:
    receipt.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return _sha(receipt)


def test_valid_exact_source_receipt_returns_verified_log(tmp_path: Path):
    helper, root, evidence, receipt, _payload, now = _receipt_fixture(tmp_path)
    result = helper.verify_receipt(receipt, root, _sha(receipt), now=now)
    assert result == (evidence / "pytest.log").resolve()


def test_free_text_log_is_not_a_receipt(tmp_path: Path):
    helper, root, evidence, _receipt, _payload, now = _receipt_fixture(tmp_path)
    log = evidence / "pytest.log"
    with pytest.raises(helper.ReceiptRefused, match="valid JSON"):
        helper.verify_receipt(log, root, _sha(log), now=now)


def test_receipt_hash_must_be_pinned_out_of_band(tmp_path: Path):
    helper, root, _evidence, receipt, _payload, now = _receipt_fixture(tmp_path)
    with pytest.raises(helper.ReceiptRefused, match="receipt SHA-256 mismatch"):
        helper.verify_receipt(receipt, root, "0" * 64, now=now)


def test_source_tree_drift_refuses_receipt(tmp_path: Path):
    helper, root, _evidence, receipt, _payload, now = _receipt_fixture(tmp_path)
    expected = _sha(receipt)
    (root / "module.py").write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(helper.ReceiptRefused, match="source tree SHA-256 mismatch"):
        helper.verify_receipt(receipt, root, expected, now=now)


def test_declared_counts_must_match_exact_per_node_outcomes(tmp_path: Path):
    helper, root, _evidence, receipt, payload, now = _receipt_fixture(tmp_path)
    payload["results"]["passed"] = 2
    with pytest.raises(helper.ReceiptRefused, match=r"results\.passed"):
        helper.verify_receipt(receipt, root, _rewrite(receipt, payload), now=now)


def test_stale_receipt_refuses_external_validation(tmp_path: Path):
    helper, root, _evidence, receipt, payload, now = _receipt_fixture(tmp_path)
    stale = now - timedelta(days=2)
    payload["execution"]["started_utc"] = (stale - timedelta(minutes=2)).isoformat().replace("+00:00", "Z")
    payload["execution"]["completed_utc"] = stale.isoformat().replace("+00:00", "Z")
    with pytest.raises(helper.ReceiptRefused, match="older than 24 hours"):
        helper.verify_receipt(receipt, root, _rewrite(receipt, payload), now=now)


def test_selecting_a_subset_is_not_the_configured_full_suite(tmp_path: Path):
    helper, root, _evidence, receipt, payload, now = _receipt_fixture(tmp_path)
    payload["execution"]["argv"].append("tests/test_alpha.py")
    with pytest.raises(helper.ReceiptRefused, match="exact configured full-suite command"):
        helper.verify_receipt(receipt, root, _rewrite(receipt, payload), now=now)


def test_default_partition_cannot_claim_full_suite(tmp_path: Path):
    helper, root, _evidence, receipt, payload, now = _receipt_fixture(tmp_path)
    payload["execution"]["argv"] = [
        sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"
    ]
    with pytest.raises(helper.ReceiptRefused, match="exact configured full-suite command"):
        helper.verify_receipt(receipt, root, _rewrite(receipt, payload), now=now)


def test_release_entrypoints_verify_receipt_before_honoring_skip():
    cut = (ROOT / "tools" / "release_cut.sh").read_text(encoding="utf-8")
    release = (ROOT / "tools" / "release.sh").read_text(encoding="utf-8")
    for text in (cut, release):
        assert "PYTEST_RECEIPT" in text
        assert "PYTEST_RECEIPT_SHA256" in text
        assert "verify_external_validation_receipt.py" in text
        assert "--print-log-path" in text
    assert "--skip-tests requires PYTEST_LOG=" not in cut
    assert cut.index("verify_external_validation_receipt.py") < cut.index(
        'export BUILD_STAMP="$STAMP" SKIP_INTIER_PYTEST=1'
    )
    assert release.index("verify_external_validation_receipt.py") < release.index(
        'for TIER in "${TIERS[@]}"'
    )


def _generic_source(tmp_path: Path) -> Path:
    stamp = "20260902v00000a"
    source = tmp_path / "generic source"
    (source / "mamey").mkdir(parents=True)
    (source / "tools").mkdir()
    (source / "mamey" / "__init__.py").write_text('__version__ = "0.0.0"\n', encoding="utf-8")
    (source / "BUILD_STAMP.txt").write_text(
        f"version=0.0.0\nbuild={stamp}\nengine=0.0.0\ntier=merged\n",
        encoding="utf-8",
    )
    (source / "CITATION.cff").write_text("version: 0.0.0\n", encoding="utf-8")
    (source / "generic_payload.txt").write_text("generic payload\n", encoding="utf-8")
    for name in ("tracked_file_policy.py", "check_release_manifest.py"):
        shutil.copy2(ROOT / "tools" / name, source / "tools" / name)
    return source


@pytest.mark.skipif(not shutil.which("bash") or not shutil.which("zip"), reason="bash/zip unavailable")
def test_explicit_intier_pytest_skip_remains_loud_and_builds_only_an_unsealed_candidate(tmp_path: Path):
    source = _generic_source(tmp_path)
    output = tmp_path / "engineering builds"
    env = {
        **os.environ,
        "BUILD_STAMP": "20260902v00000a",
        "SKIP_INTIER_PYTEST": "1",
        "PYTHON": sys.executable,
    }
    result = subprocess.run(
        ["bash", str(BUILDER), "merged", str(source), str(output)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "pytest gate: SKIPPED via SKIP_INTIER_PYTEST=1" in result.stderr
    archives = list(output.glob("*.zip"))
    assert len(archives) == 1
    assert "sealed" not in (result.stdout + result.stderr).lower()
