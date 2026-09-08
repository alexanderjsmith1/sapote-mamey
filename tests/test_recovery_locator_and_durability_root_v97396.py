from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

import mamey.report_from_spec as rfs
from mamey.evidence_roots import EvidenceRootError, logical_locator


def _load_checklist():
    path = Path(__file__).parents[1] / "tools" / "session_checklist.py"
    spec = importlib.util.spec_from_file_location("portable_session_checklist", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _stub_report_pipeline(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    manifest_path = tmp_path / "manifest.json"
    spec_path = tmp_path / "spec.json"
    for path in (config_path, manifest_path, spec_path):
        path.write_text("{}", encoding="utf-8")
    spec = {
        "schema_version": rfs.SPEC_SCHEMA,
        "strain": "FIXTURE-STRAIN",
        "source_ids": {"identity_db": "id_db"},
        "output": {"root_id": "outputs", "relative_path": "reports/result"},
        "source_discovery_preflight": {
            "catalog_source_id": "catalog",
            "decisions_source_id": "decisions",
        },
    }
    durable = tmp_path / "durable"
    monkeypatch.setattr(rfs, "load_json", lambda path: spec if path == spec_path else {})
    monkeypatch.setattr(rfs, "resolve_roots", lambda *args, **kwargs: {"outputs": durable})
    resolved = {
        "id_db": tmp_path / "identity.json",
        "catalog": tmp_path / "catalog.json",
        "decisions": tmp_path / "decisions.json",
    }
    monkeypatch.setattr(
        rfs, "resolve_sources", lambda *args, **kwargs: (resolved, {"status": "PASS_PREFLIGHT"})
    )
    monkeypatch.setattr(
        rfs,
        "require_source_discovery_preflight",
        lambda **kwargs: {
            "catalog_sha256": "a" * 64,
            "decisions_sha256": "b" * 64,
            "required_collection_types": ["fixture"],
        },
    )
    monkeypatch.setattr(
        rfs, "resolve_output", lambda *args, **kwargs: durable / "reports" / "result"
    )

    def build(args):
        args.out_root.mkdir(parents=True)
        (args.out_root / "report.md").write_text("complete", encoding="utf-8")
        return {"status": "complete"}

    monkeypatch.setattr(rfs.report_builder, "build", build)
    return config_path, manifest_path, spec_path, durable


def test_publication_failure_preserves_bytes_and_emits_redacted_typed_receipt(
    tmp_path, monkeypatch
):
    config, manifest, spec, durable = _stub_report_pipeline(monkeypatch, tmp_path)
    monkeypatch.setattr(
        rfs.os,
        "replace",
        lambda src, dst: (_ for _ in ()).throw(OSError(18, f"host leak {tmp_path}")),
    )
    with pytest.raises(rfs.ReportPublicationError) as caught:
        rfs.run(config, manifest, spec, {})
    receipt = caught.value.receipt
    staging = list((durable / "reports").glob(".result.staging-*"))
    assert len(staging) == 1 and (staging[0] / "report.md").is_file()
    receipt_path = staging[0] / rfs.RECOVERY_RECEIPT_NAME
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt
    assert receipt["status"] == "RECOVERY_REQUIRED_PUBLICATION_FAILED"
    assert receipt["recovery_locator"].startswith("evidence://outputs/reports/.result.staging-")
    assert receipt["target_locator"] == "evidence://outputs/reports/result"
    serialized = json.dumps(receipt, sort_keys=True)
    assert str(tmp_path) not in serialized
    assert "host leak" not in serialized


def test_staging_root_escape_is_refused_before_build(tmp_path, monkeypatch):
    config, manifest, spec, durable = _stub_report_pipeline(monkeypatch, tmp_path)
    monkeypatch.setattr(rfs, "resolve_output", lambda *args, **kwargs: durable)
    with pytest.raises(EvidenceRootError, match="Staging path escapes"):
        rfs.run(config, manifest, spec, {})


def _portable_fixture(root: Path):
    outputs = root / "outputs" / "current"
    outputs.mkdir(parents=True)
    (outputs / "fixture_Complete_Package.zip").write_bytes(b"fixture")
    config = root / "roots.json"
    config.write_text(
        json.dumps({
            "schema_version": "sapote_evidence_root_config_v1",
            "roots": {"session_outputs": {"path": "outputs"}},
        }),
        encoding="utf-8",
    )
    return config, outputs


def test_clean_copy_relocation_keeps_logical_receipt_and_redacts_host_paths(
    tmp_path, capsys
):
    checklist = _load_checklist()
    receipts = []
    for name in ("copy_a", "copy_b"):
        config, _outputs = _portable_fixture(tmp_path / name)
        receipt_path = tmp_path / name / "outputs" / "receipts" / "close.json"
        assert checklist.main([
            "--durable-root-config", str(config),
            "--durable-root-id", "session_outputs",
            "--scan-relative", "current",
            "--receipt-relative", "receipts/close.json",
        ]) is None
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        serialized = json.dumps(receipt, sort_keys=True)
        assert str(tmp_path) not in serialized
        receipts.append(receipt)
    assert receipts[0] == receipts[1]
    console = capsys.readouterr().out
    assert str(tmp_path) not in console
    assert "evidence://session_outputs/current" in console


def test_traversal_absolute_and_symlink_escape_are_refused(tmp_path):
    checklist = _load_checklist()
    config, _outputs = _portable_fixture(tmp_path / "bundle")
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "bundle" / "outputs" / "escape").symlink_to(
        outside, target_is_directory=True
    )
    for unsafe in ("../outside", str(outside), "escape"):
        with pytest.raises(EvidenceRootError):
            checklist._resolve_governed_scan(config, "session_outputs", unsafe, {})


def test_missing_stale_relative_root_fails_closed_after_relocation(tmp_path):
    checklist = _load_checklist()
    root = tmp_path / "moved_bundle"
    root.mkdir()
    config = root / "roots.json"
    config.write_text(
        json.dumps({
            "schema_version": "sapote_evidence_root_config_v1",
            "roots": {"session_outputs": {"path": "missing_outputs"}},
        }),
        encoding="utf-8",
    )
    with pytest.raises(EvidenceRootError, match="unavailable"):
        checklist._resolve_governed_scan(config, "session_outputs", ".", {})


def test_receipt_and_markdown_targets_refuse_outside_root_without_creation(tmp_path):
    checklist = _load_checklist()
    config, _outputs = _portable_fixture(tmp_path / "bundle")
    outside = tmp_path / "outside.json"
    with pytest.raises(EvidenceRootError):
        checklist.main([
            "--durable-root-config", str(config),
            "--durable-root-id", "session_outputs",
            "--scan-relative", "current",
            "--receipt-relative", "../outside.json",
        ])
    assert not outside.exists()


def test_logical_locator_never_accepts_traversal_or_absolute_paths():
    assert logical_locator("session_outputs", ".") == "evidence://session_outputs"
    with pytest.raises(EvidenceRootError):
        logical_locator("session_outputs", "../outside")
    with pytest.raises(EvidenceRootError):
        logical_locator("session_outputs", "/outside")
