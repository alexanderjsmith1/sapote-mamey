"""Synthetic consumer boundaries; no report, card or analysis is generated.

Toy label legend: toy-strain / toy-full-contig / region001 / BGC901.
Report validation is stubbed; gate, receipt read, discovery and availability
metadata writer remain real. Template/report positives stop before generators.
CLI callback is real but uses a small parser; no native-parser coverage here."""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from mamey import blastp_availability as availability
from mamey import blastp_gate as gate
from tests.test_452_identity_x34_quarantine_supported_path import _native_artifact_fixture, STRAIN, HELD_ALIAS


class AfterGateBoundary(RuntimeError):
    """Test-owned sentinel; proves arrival without creating a report or card."""


def _setup(tmp_path, monkeypatch):
    root = tmp_path / "NCBI_NR"
    root.mkdir()
    package, trove, quarantine, original, prior = _native_artifact_fixture(root, False)
    (package / "manifest.json").write_text(json.dumps({"strain_id": STRAIN}), encoding="utf-8")
    (package / (STRAIN + "_4_triage_board.csv")).write_text("BGC_ID\n", encoding="utf-8")
    monkeypatch.setenv("MAMEY_BLASTP_SCAN_ROOT", str(tmp_path))
    inputs = set(prior) | {quarantine} | {p for p in package.rglob("*") if p.is_file()}
    before = {p: p.read_bytes() for p in inputs}
    return package, quarantine, before


@pytest.mark.parametrize("door", ["availability", "template_single", "template_batch", "report", "cli_availability"])
@pytest.mark.parametrize("mode", ["refusal", "valid"])
def test_real_quarantine_gate_reaches_public_boundary_without_generation(tmp_path, monkeypatch, capsys, door, mode):
    package, quarantine, before = _setup(tmp_path, monkeypatch)
    output = tmp_path / "consumer-output"
    hits = []

    def stop_generator(*args, **kwargs):
        hits.append(door)
        raise AfterGateBoundary("verified gate reached declared generator boundary")

    args = SimpleNamespace(package=str(package), runs_dir=None, out=str(output))
    if door.startswith("template_"):
        from mamey import mode_b_receipt, modeb_template_emitter
        monkeypatch.setattr(modeb_template_emitter, "emit_card_template", stop_generator)
        monkeypatch.setattr(modeb_template_emitter, "emit_batch", stop_generator)
        args = SimpleNamespace(package=str(package), bgc=HELD_ALIAS if door.endswith("single") else None,
                               batch=door.endswith("batch"), blastp_waiver=None, out=str(output))
        call = lambda: mode_b_receipt.emit_modeb_template_command(args)
    elif door == "report":
        from mamey import compile_report, validate
        monkeypatch.setattr(compile_report, "build_report", stop_generator)
        monkeypatch.setattr(validate, "validate_package", lambda *a, **k: {
            "identity_binding": "PASS", "manifest_parse": "PASS", "checksum_integrity": "PASS"})
        args = SimpleNamespace(package_dir=str(package), out=str(output), pdf=False,
                               strict=False, no_figures=True, toc_depth=1, blastp_waiver=None)
        call = lambda: compile_report.compile_report_command(args)
    elif door == "cli_availability":
        from mamey import cli
        parser = argparse.ArgumentParser()
        parser.set_defaults(command="blastp-availability", func=availability.blastp_availability_command,
                            package=str(package), runs_dir=None, out=str(output))
        monkeypatch.setattr(cli, "build_parser", lambda: parser)
        call = lambda: cli.main([])
    else:
        call = lambda: availability.blastp_availability_command(args)

    native_open = Path.open
    refused = []
    def deny_quarantine(path, *a, **k):
        if path == quarantine:
            refused.append(True)
            raise PermissionError("synthetic quarantine source access refusal")
        return native_open(path, *a, **k)

    with monkeypatch.context() as fault:
        if mode == "refusal":
            fault.setattr(Path, "open", deny_quarantine)
            if door == "cli_availability":
                assert call() == 3
                err = capsys.readouterr().err
                assert "BLASTP_REKEY_RECEIPT_HOLD:" in err and "Traceback" not in err
            else:
                with pytest.raises(gate.BlastpDiscoveryError, match="^BLASTP_REKEY_RECEIPT_HOLD:"):
                    call()
            assert refused == [True] and hits == [] and not output.exists()
        elif door in {"report", "template_single", "template_batch"}:
            with pytest.raises(AfterGateBoundary, match="verified gate reached"):
                call()
            assert hits == [door] and not output.exists()
            assert "TYPED_HOLD_ONLY" in capsys.readouterr().err
        else:
            assert call() == 0 and hits == []
            data = json.loads((output / "BLASTP_AVAILABILITY.json").read_text(encoding="utf-8"))
            row, = data["strains"][0]["source_reconciliation"]
            assert row["held_current_bgcs"] == [HELD_ALIAS]
            assert row["source_hold_reasons"] == {"LEGACY_PROVENANCE_HOLD": 1}
            assert data["strains"][0]["gate_blocked"] is False
            assert (output / "BLASTP_AVAILABILITY.csv").is_file()
    assert all(p.read_bytes() == raw for p, raw in before.items())
