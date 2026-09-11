"""Regression coverage for nonblocking judgment persistence diagnostics.

The synthetic locus is TEST-001 / NODE_1_length_50000_cov_20.0 /
region001 / BGC001 throughout.
"""
from __future__ import annotations

import json
from pathlib import Path

from mamey import judgment_store


STRAIN = "TEST-001"
BGC = "BGC001"
NODE = "NODE_1_length_50000_cov_20.0"
REGION = "region001"


def _package(tmp_path: Path) -> Path:
    pkg = tmp_path / STRAIN / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(
        json.dumps({
            "strain_id": STRAIN,
            "bgcs": [{
                "strain": STRAIN,
                "full_node_or_contig": NODE,
                "region": REGION,
                "bgc_alias": BGC,
                "identity_display": f"{STRAIN} / {NODE} / {REGION} / {BGC}",
            }],
        }),
        encoding="utf-8",
    )
    judgment_store.init_register(pkg, STRAIN, [BGC])
    return pkg


def test_last_good_snapshot_failure_is_returned_as_nonblocking_warning(tmp_path, monkeypatch):
    pkg = _package(tmp_path)
    original_write = judgment_store._atomic_write_text

    def fail_snapshot(path: Path, text: str) -> None:
        if path.name.endswith(".last-good"):
            raise PermissionError("synthetic snapshot failure")
        original_write(path, text)

    monkeypatch.setattr(judgment_store, "_atomic_write_text", fail_snapshot)
    result = judgment_store.record_batch_complete(pkg, "session-1", [BGC])

    assert result["judgment_status"] == "COMPLETE"
    assert result["persistence_warnings"] == [{
        "stage": "write_last_good_snapshot",
        "error_type": "PermissionError",
        "message": "synthetic snapshot failure",
    }]


def test_banner_sync_failure_is_returned_as_nonblocking_warning(tmp_path, monkeypatch):
    pkg = _package(tmp_path)
    start_here = pkg / "START_HERE.md"
    start_here.write_text(
        "# Start\n\n## ✅ EXTRACTION COMPLETE  ·  ⏳ JUDGMENT PENDING\n",
        encoding="utf-8",
    )
    original_write = judgment_store._atomic_write_text

    def fail_banner(path: Path, text: str) -> None:
        if path == start_here:
            raise PermissionError("synthetic banner failure")
        original_write(path, text)

    monkeypatch.setattr(judgment_store, "_atomic_write_text", fail_banner)
    result = judgment_store.record_batch_complete(pkg, "session-1", [BGC])

    assert result["judgment_status"] == "COMPLETE"
    assert result["persistence_warnings"] == [{
        "stage": "sync_judgment_banner",
        "error_type": "PermissionError",
        "message": "synthetic banner failure",
    }]


def test_successful_persistence_has_no_warning(tmp_path):
    pkg = _package(tmp_path)

    result = judgment_store.record_batch_complete(pkg, "session-1", [BGC])

    assert result["judgment_status"] == "COMPLETE"
    assert result.get("persistence_warnings", []) == []


def test_corrupt_recovery_state_cannot_become_complete_on_repeat_card_write(tmp_path):
    pkg = _package(tmp_path)
    register = pkg / f"{STRAIN}_judgment_register.json"
    last_good = Path(str(register) + ".last-good")
    if last_good.exists():
        last_good.unlink()
    register.write_text("{truncated", encoding="utf-8")
    card = f"# Mode B — {STRAIN} / {NODE} / {REGION} / {BGC}\n§1 content"

    judgment_store.record_mode_b(pkg, BGC, card)
    judgment_store.record_mode_b(pkg, BGC, card)
    recovered = judgment_store.read_register(pkg)

    assert recovered["judgment_status"] == "CORRUPT_RECOVERY_INCOMPLETE"
    ready, reason = judgment_store.compile_ready(pkg)
    assert ready is False
    assert "CORRUPT_RECOVERY_INCOMPLETE" in reason


def test_repeat_card_write_on_trustworthy_register_can_remain_complete(tmp_path):
    pkg = _package(tmp_path)
    card = f"# Mode B — {STRAIN} / {NODE} / {REGION} / {BGC}\n§1 content"

    judgment_store.record_mode_b(pkg, BGC, card)
    judgment_store.record_mode_b(pkg, BGC, card)

    assert judgment_store.read_register(pkg)["judgment_status"] == "COMPLETE"
