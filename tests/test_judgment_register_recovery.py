"""Red/green coverage for bounded judgment-register recovery repairs.

The synthetic loci always carry complete four-component identities.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mamey import judgment_store


STRAIN = "TEST-001"
BGC = "BGC001"
BGC_2 = "BGC002"
FULL_NODE = "NODE_1_length_50000_cov_20.0"
FULL_NODE_2 = "NODE_2_length_40000_cov_18.0"
REGION = "region001"
REGION_2 = "region002"
IDENTITY = f"{STRAIN} / {FULL_NODE} / {REGION} / {BGC}"
IDENTITY_2 = f"{STRAIN} / {FULL_NODE_2} / {REGION_2} / {BGC_2}"


def _package(tmp_path: Path) -> Path:
    pkg = tmp_path / STRAIN / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(
        json.dumps({
            "strain_id": STRAIN,
            "bgcs": [{
                "strain": STRAIN,
                "full_node_or_contig": FULL_NODE,
                "region": REGION,
                "bgc_alias": BGC,
                "identity_display": IDENTITY,
            }, {
                "strain": STRAIN,
                "full_node_or_contig": FULL_NODE_2,
                "region": REGION_2,
                "bgc_alias": BGC_2,
                "identity_display": IDENTITY_2,
            }],
        }),
        encoding="utf-8",
    )
    return pkg


def test_init_register_recovers_last_good_instead_of_resetting_progress(tmp_path):
    pkg = _package(tmp_path)
    judgment_store.init_register(pkg, STRAIN, [BGC])
    judgment_store.record_batch_complete(pkg, "session-1", [BGC])
    reg_path = pkg / f"{STRAIN}_judgment_register.json"
    reg_path.write_text("{truncated", encoding="utf-8")

    recovered = judgment_store.init_register(pkg, STRAIN, [BGC, BGC_2])

    assert recovered["bgcs"][BGC]["status"] == "COMPLETE"
    assert recovered["bgcs"][BGC_2]["status"] == "PENDING"


def test_read_register_reports_failed_corrupt_backup(tmp_path, monkeypatch):
    pkg = _package(tmp_path)
    reg_path = pkg / f"{STRAIN}_judgment_register.json"
    reg_path.write_text("{truncated", encoding="utf-8")
    original_write_bytes = Path.write_bytes

    def fail_corrupt_backup(path: Path, data: bytes) -> int:
        if ".corrupt-" in path.name:
            raise PermissionError("synthetic read-only directory")
        return original_write_bytes(path, data)

    monkeypatch.setattr(Path, "write_bytes", fail_corrupt_backup)
    result = judgment_store.read_register(pkg)

    assert result["judgment_status"] == "CORRUPT"
    assert any(
        row["stage"] == "preserve_corrupt_register"
        and row["error_type"] == "PermissionError"
        for row in result["load_errors"]
    )


def test_read_register_reports_invalid_last_good_snapshot(tmp_path, monkeypatch):
    pkg = _package(tmp_path)
    reg_path = pkg / f"{STRAIN}_judgment_register.json"
    reg_path.write_text("{truncated", encoding="utf-8")
    last_good = Path(str(reg_path) + ".last-good")
    last_good.write_text("[not-an-object]", encoding="utf-8")
    monkeypatch.setattr(judgment_store, "_now", lambda: "2026-09-09T00:00:00Z")

    result = judgment_store.read_register(pkg)

    assert result["judgment_status"] == "CORRUPT"
    assert any(
        row["stage"] == "load_last_good" and row["error_type"] == "JSONDecodeError"
        for row in result["load_errors"]
    )
