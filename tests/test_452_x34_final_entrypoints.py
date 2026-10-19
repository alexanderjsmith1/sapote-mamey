"""Synthetic metadata controls for public availability and report-reader boundaries.

TOY-A / toy-full-contig-A / region001 / BGC901 and TOY-B / toy-full-contig-B /
region001 / BGC902 are fixture labels, not validated biological loci.
No search, resolver, analysis, figure, card or report builder is run.
The seal-marker fixture is not a validated scientific package.
Only native-CLI cases create a sequential child; they do not start pytest."""
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = Path(__file__).with_name("x34_final_entrypoint_fixtures.json")
PAYLOAD_SHA256 = "b6dfd5f5415e1227f10479c969335d06a5081586ef96291408ddf81691c42297"


class StopBeforeReport(RuntimeError):
    """Test-owned positive boundary; never a generated report or successful report exit."""


def _metadata(workspace, strain, *, sealed=False, missing_quarantine=False):
    raw = PAYLOAD.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PAYLOAD_SHA256
    spec = json.loads(raw)["variants"][strain]
    package = workspace / "runs" / strain / "package"
    package.mkdir(parents=True)
    payloads = dict(spec["package_utf8"])
    if sealed:
        payloads["seal_status.json"] = spec["seal_marker_utf8"]
    for relative, text in payloads.items():
        if missing_quarantine and relative == "blastp_quarantine/toy.csv":
            continue  # missing file is a declared toy refusal premise, not deleted evidence
        target = package / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))
    source = workspace / "NCBI_NR" / spec["source_relative_to_trove"]
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(spec["source_utf8"].encode("utf-8"))
    quarantine = package / "blastp_quarantine" / "toy.csv"
    if sealed:
        assert len(_files(package)) == 6
        assert sum(len(value) for value in _files(package).values()) == 1130
    return package, quarantine, spec


def _files(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


def _inputs(workspace):
    return {prefix + "/" + rel: value
            for prefix in ("runs", "NCBI_NR")
            for rel, value in _files(workspace / prefix).items()}


def _assert_row(record, spec):
    row, = record["source_reconciliation"]
    assert row["state"] == "REKEYED_SOURCE_WITH_TYPED_HOLDS_ONLY"
    assert row["held_current_bgcs"] == [spec["held_alias"]]
    assert row["admitted_current_bgcs"] == []
    assert row["source_hold_reasons"] == {spec["reason"]: 1}
    assert row["receipt"] == "toy-receipt.json"
    assert row["source_sha256"] == spec["source_sha256"]
    assert record["gate_blocked"] is False


@pytest.mark.parametrize("mode", ["refusal", "valid"])
def test_two_package_availability_keeps_each_receipt_or_refuses_before_publication(tmp_path, monkeypatch, mode):
    from mamey import blastp_availability as availability
    workspace = tmp_path / "project"
    first, _, first_spec = _metadata(workspace, "TOY-A")
    second, quarantine, second_spec = _metadata(workspace, "TOY-B")
    before = _inputs(workspace)
    monkeypatch.setenv("MAMEY_BLASTP_SCAN_ROOT", str(workspace))
    output = workspace / "availability"
    native_strain = availability.strain_availability
    visits = []
    def trace_package(package, strain, **kwargs):
        visits.append(strain)
        return native_strain(package, strain, **kwargs)
    monkeypatch.setattr(availability, "strain_availability", trace_package)
    args = SimpleNamespace(package=None, runs_dir=str(workspace / "runs"), out=str(output))
    from mamey.blastp_gate import BlastpDiscoveryError
    native_open = Path.open
    denied = []
    def refuse_second_quarantine(path, *args, **kwargs):
        if path == quarantine:
            denied.append(True)
            raise PermissionError("synthetic second-package quarantine refusal")
        return native_open(path, *args, **kwargs)
    with monkeypatch.context() as fault:
        if mode == "refusal":
            fault.setattr(Path, "open", refuse_second_quarantine)
            with pytest.raises(BlastpDiscoveryError, match="^BLASTP_REKEY_RECEIPT_HOLD:"):
                availability.blastp_availability_command(args)
            assert denied == [True] and not output.exists()
        else:
            assert availability.blastp_availability_command(args) == 0
            data = json.loads((output / "BLASTP_AVAILABILITY.json").read_bytes())
            assert data["meta"]["strains"] == 2
            records = {r["strain"]: r for r in data["strains"]}
            assert set(records) == {"TOY-A", "TOY-B"}
            _assert_row(records["TOY-A"], first_spec)
            _assert_row(records["TOY-B"], second_spec)
            with (output / "BLASTP_AVAILABILITY.csv").open(newline="", encoding="utf-8") as handle:
                assert {r["strain"] for r in csv.DictReader(handle)} == {"TOY-A", "TOY-B"}
    assert visits == ["TOY-A", "TOY-B"]
    assert _inputs(workspace) == before


@pytest.mark.parametrize("mode", ["refusal", "valid"])
def test_sealed_reader_snapshots_tiny_metadata_then_real_gate_stops_before_report(tmp_path, monkeypatch, mode):
    from mamey import compile_report, blastp_gate, validate
    workspace = tmp_path / "project"
    package, quarantine, spec = _metadata(workspace, "TOY-A", sealed=True)
    before = _inputs(workspace)
    package_before = _files(package)
    monkeypatch.setenv("MAMEY_BLASTP_SCAN_ROOT", str(workspace))
    # Scientific/package validation is outside this control, never invoked.
    monkeypatch.setattr(validate, "validate_package", lambda *a, **k: {
        "identity_binding": "PASS", "manifest_parse": "PASS", "checksum_integrity": "PASS"})
    output = workspace / "reader" / "report.md"
    gate_calls, builder_calls, reader_calls, denied = [], [], [], []
    native_gate, native_open = blastp_gate.gate, Path.open

    def forbidden_builder(view, **kwargs):
        builder_calls.append(Path(view))
        pytest.fail("build_report must remain unreachable in this control")
    monkeypatch.setattr(compile_report, "build_report", forbidden_builder)
    native_reader = compile_report._compile_report_from_reader_view
    def trace_reader(args):
        reader_calls.append((Path(args.package_dir), Path(args._postseal_source_package), args.no_figures))
        return native_reader(args)
    monkeypatch.setattr(compile_report, "_compile_report_from_reader_view", trace_reader)

    def source_gate_after_snapshot(source, strain, **kwargs):
        gate_calls.append((Path(source), strain))
        assert Path(source) == package and strain == "TOY-A"
        snapshots = list(output.parent.glob(".reader_view_*/package"))
        assert len(snapshots) == 1 and _files(snapshots[0]) == package_before
        # Arm only here: the real native snapshot/hash path must finish first.
        def refuse_original_quarantine(path, *args, **kwargs):
            if path == quarantine:
                denied.append(True)
                raise PermissionError("synthetic quarantine refusal after snapshot")
            return native_open(path, *args, **kwargs)
        with monkeypatch.context() as fault:
            if mode == "refusal":
                fault.setattr(Path, "open", refuse_original_quarantine)
            result = native_gate(source, strain, **kwargs)
        row, = result["source_reconciliation"]
        assert row["held_current_bgcs"] == [spec["held_alias"]]
        assert row["source_hold_reasons"] == {spec["reason"]: 1}
        assert row["source_sha256"] == spec["source_sha256"]
        assert result["ok"] is True and result["blocked"] is False
        raise StopBeforeReport("real gate returned valid metadata; no report generated")
    monkeypatch.setattr(blastp_gate, "gate", source_gate_after_snapshot)
    args = SimpleNamespace(package_dir=str(package), out=str(output), no_figures=True,
                           pdf=False, strict=False, toc_depth=1, blastp_waiver=None)
    if mode == "refusal":
        with pytest.raises(blastp_gate.BlastpDiscoveryError, match="^BLASTP_REKEY_RECEIPT_HOLD:"):
            compile_report.compile_report_command(args)
        assert denied == [True] and builder_calls == []
    else:
        with pytest.raises(StopBeforeReport, match="no report generated"):
            compile_report.compile_report_command(args)
        assert denied == [] and builder_calls == []
    assert gate_calls == [(package, "TOY-A")]
    snapshots = list(output.parent.glob(".reader_view_*/package"))
    assert len(snapshots) == 1 and _files(snapshots[0]) == package_before
    assert reader_calls == [(snapshots[0], package, True)]
    assert builder_calls == []
    assert not output.exists() and not output.with_suffix(".pdf").exists()
    assert not output.with_suffix(".source_receipt.json").exists()
    assert _inputs(workspace) == before


@pytest.mark.parametrize("mode", ["refusal", "valid"])
def test_native_availability_runner_parser_keeps_metadata_or_returns_receipt_hold(tmp_path, mode):
    workspace = tmp_path / "project"
    package, quarantine, spec = _metadata(workspace, "TOY-A", missing_quarantine=mode == "refusal")
    before = _inputs(workspace)
    output = workspace / "availability"
    env = dict(os.environ)
    env.pop("MAMEY_TREE", None)
    env.pop("PYTHONPYCACHEPREFIX", None)
    env.update(PYTHONDONTWRITEBYTECODE="1", MAMEY_BLASTP_SCAN_ROOT=str(workspace))
    child_tmp = workspace / "child_tmp"
    child_tmp.mkdir()
    env["TMPDIR"] = str(child_tmp)
    # Avoid inheriting a real evidence reservoir into lazy CLI imports.
    for key, name in (("MAMEY_OFFICIAL_DATA", "empty_official"), ("MAMEY_DATA_ROOT", "empty_data")):
        empty = workspace / name
        empty.mkdir()
        env[key] = str(empty)
    assert (ROOT / "mamey_run.py").is_file()
    command = [sys.executable, "-B", str(ROOT / "mamey_run.py"),
               "blastp-availability", "--package", str(package), "--out", str(output)]
    # One native metadata-only CLI child; no nested pytest.
    process = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                             text=True, timeout=40, check=False)
    assert "Traceback" not in process.stdout + process.stderr
    if mode == "refusal":
        assert not quarantine.exists()
        assert process.returncode == 3
        assert "BLASTP_REKEY_RECEIPT_HOLD:" in process.stderr
        assert not output.exists()
    else:
        assert process.returncode == 0, process.stdout + process.stderr
        data = json.loads((output / "BLASTP_AVAILABILITY.json").read_bytes())
        assert data["meta"]["strains"] == 1
        _assert_row(data["strains"][0], spec)
        with (output / "BLASTP_AVAILABILITY.csv").open(newline="", encoding="utf-8") as handle:
            assert [r["strain"] for r in csv.DictReader(handle)] == ["TOY-A"]
    assert _inputs(workspace) == before
