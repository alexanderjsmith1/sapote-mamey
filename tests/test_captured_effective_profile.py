"""Effective timeout/capped profile and downstream source identity guards."""
from pathlib import Path
import json
import pytest
try:
    from .test_captured_actual_run import inputs, run_args
except ImportError:
    from test_captured_actual_run import inputs, run_args
from mamey import cli, captured_run, source_context
from mamey.archive_snapshot import ArchiveSnapshot


def test_resolved_timeout_is_used_after_environment_changes(inputs, tmp_path, monkeypatch):
    monkeypatch.setenv("MAMEY_BOUNDED_BUDGET_S", "0")
    execute = captured_run.execute_stage
    parsed = cli._parse_evidence_with_budget
    observed = []
    def changed(args, legacy, frame):
        monkeypatch.setenv("MAMEY_BOUNDED_BUDGET_S", "1")
        return execute(args, legacy, frame)
    def parsing(source, mode, budget, stage):
        observed.append(budget)
        return parsed(source, mode, budget, stage)
    monkeypatch.setattr(captured_run, "execute_stage", changed)
    monkeypatch.setattr(cli, "_parse_evidence_with_budget", parsing)
    assert cli.main(run_args(inputs, tmp_path, "--json-evidence", "bounded")) == 0
    assert observed == [0]
    package = tmp_path / "out/SYNTHETIC-CAPTURED-RUN/package"
    manifest = json.loads((package / "manifest.json").read_text())
    evidence = json.loads(next(package.glob("*_AntiSMASH_Evidence_Parse.json")).read_text())
    receipt = json.loads((tmp_path / "out/captured_completion.json").read_text())
    assert evidence["json_parse_budget"]["seconds"] == 0
    assert manifest["captured_source"]["execution_options"]["status_budget_seconds"] == 0
    assert receipt["binding"]["execution_options"]["status_budget_seconds"] == 0


def test_capped_profile_resolves_documented_defaults_before_admission(inputs, tmp_path, monkeypatch):
    monkeypatch.delenv("MAMEY_ZIP_COMPRESSION", raising=False)
    args = cli.build_parser().parse_args(["run", "--input-zip", str(inputs[0]), "--capped-session",
        "--capture-policy", str(inputs[1]), "--reference-completion", "off"])
    assert args.brief == "standard" and args.locus_maps == "auto"
    resolved = captured_run.resolve_execution(args)
    captured_run.require_profile(resolved)
    assert resolved.brief == "none" and resolved.locus_maps == "off" and resolved.json_evidence == "off"
    assert resolved.require_workbook is True and args.brief == "standard"
    assert resolved._capture_execution["requested"]["brief"] == "standard"
    assert resolved._capture_execution["effective"]["brief"] == "none"
    assert __import__("os").environ["MAMEY_ZIP_COMPRESSION"] == "stored"


@pytest.mark.parametrize("budget", ["-1", "invalid"])
def test_invalid_timeout_refuses_before_capture(inputs, tmp_path, monkeypatch, budget):
    monkeypatch.setenv("MAMEY_BOUNDED_BUDGET_S", budget)
    monkeypatch.setattr(ArchiveSnapshot, "capture", lambda *a, **k: pytest.fail("invalid budget captured input"))
    assert cli.main(run_args(inputs, tmp_path)) == 2
    assert not (tmp_path / "out").exists()


def test_wrong_downstream_rg_digest_is_not_annotated_as_bound(inputs, tmp_path, monkeypatch):
    from openpyxl import Workbook
    master = tmp_path / "master.xlsx"
    book = Workbook();book.save(master);book.close()
    before = master.read_bytes()
    actual = cli.run_archive
    observed = []
    def mismatched(source, **kwargs):
        frame = source_context.active()
        assert source_context.bound_source(source) is frame.session.snapshot
        result = actual(source, **kwargs)
        observed.append(result["input"]["antismash_zip_sha256"])
        result["input"]["antismash_zip_sha256"] = "0" * 64
        return result
    monkeypatch.setattr(cli, "run_archive", mismatched)
    assert cli.main(run_args(inputs, tmp_path)) == 2
    assert observed and master.read_bytes() == before and not (tmp_path / "out").exists()
    rows = [json.loads(line) for p in tmp_path.glob(".out.captured-failure-*/**/run_phase_receipts.jsonl")
            for line in p.read_text().splitlines()]
    assert any(r["phase"] == "rggmci" and r["status"] == "ERROR" and
        "RG_SOURCE_BINDING_MISMATCH" in r.get("reason", "") for r in rows)
