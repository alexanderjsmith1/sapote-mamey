"""Actual direct-archive harness, transactional summaries and package briefing."""
from pathlib import Path
import csv
import json
import sys
from types import SimpleNamespace
import pytest
try:
    from .test_captured_actual_run import inputs
    from .test_captured_batch_resume import batch_inputs
except ImportError:
    from test_captured_actual_run import inputs
    from test_captured_batch_resume import batch_inputs
from mamey import captured_harness, cli, source_context, captured_run
from mamey.intake_session import CapturedIntakeHold


def arguments(tmp_path, policy, source):
    out = tmp_path / "harness"
    return SimpleNamespace(inputs=[str(source)], outdir=str(out), registry=str(out / "registry.csv"),
        metrics=str(out / "metrics.csv"), batch_report=None, batch_label="fabricated", source="not verified",
        taxonomy_map=None, release="PRIVATE", mode="gold", bench=False, resume=False,
        capture_policy=str(policy), capture_batch_policy="all-or-nothing", capture_threads=1,
        capture_master=str(tmp_path / "master.xlsx"))


def test_actual_harness_transaction_csv_resume_and_raw_free_briefing(inputs, tmp_path, monkeypatch):
    import intake_harness
    one, _, policy = batch_inputs(tmp_path)
    args = arguments(tmp_path, policy, one)
    command = ["intake_harness.py", "--inputs", str(one), "--outdir", args.outdir,
        "--registry", args.registry, "--metrics", args.metrics, "--capture-policy", str(policy),
        "--capture-batch-policy", "all-or-nothing", "--capture-threads", "1", "--capture-master", args.capture_master]
    monkeypatch.setattr(sys, "argv", command)
    assert intake_harness.main() == 0
    with Path(args.registry).open() as stream:
        registry = list(csv.DictReader(stream))
    with Path(args.metrics).open() as stream:
        metrics = list(csv.DictReader(stream))
    assert len(registry) == len(metrics) == 1
    assert registry[0]["raw_bgcs"] == "1" and registry[0]["rescue_HIGH"] == ""
    assert metrics[0]["n_regions"] == "1" and metrics[0]["engine_peak_mb"] == ""
    completion = json.loads((Path(args.outdir) / "captured_completion.json").read_text())
    context = completion["binding"]["options"]["capture_harness_context"]
    assert context["engine"]["executed_harness_code_sha256"]
    assert context["input_profile"].startswith("direct captured")
    monkeypatch.setattr(sys, "argv", [*command, "--resume"])
    assert intake_harness.main() == 0
    one.unlink()
    from mamey.session_resume import build_resume
    package = next(Path(args.outdir).glob("*/package"))
    result = build_resume(package)
    assert result["captured_source"]["pin_origin"] == "PLANNED_CONSUMED_VERSION"
    assert result["captured_source"]["denominator"]["expected_biological_total"] is None
    assert "NOT_ESTABLISHED" in result["markdown"]
    assert intake_harness.main() == 2
    assert package.is_dir() and Path(args.registry).is_file()


@pytest.mark.parametrize("mutation", ["external_csv", "csv_collision", "no_policy_choice", "threads", "bench"])
def test_harness_unsupported_configuration_is_explicit(tmp_path, mutation):
    one, _, policy = batch_inputs(tmp_path)
    args = arguments(tmp_path, policy, one)
    if mutation == "external_csv": args.registry = str(tmp_path / "external.csv")
    elif mutation == "csv_collision": args.metrics = args.registry
    elif mutation == "no_policy_choice": args.capture_batch_policy = None
    elif mutation == "threads": args.capture_threads = 2
    else: args.bench = True
    with pytest.raises(CapturedIntakeHold):
        captured_harness.run(args, engine={"synthetic": True}, taxonomy_map={}, taxonomy_binding=None)
    assert not Path(args.outdir).exists()


def test_rggmci_explicit_none_stays_unavailable_under_capture(inputs, tmp_path):
    from mamey import rggmci
    source, policy_path = inputs
    policy = captured_run.load_policy(policy_path)
    args = SimpleNamespace(input_zip=str(source))
    session, genbank, aliases = captured_run.capture(args, policy)
    frame = captured_run.RunFrame(session, source, tmp_path / "stage", tmp_path / "out", None, None, aliases)
    source.unlink()
    with source_context.binding(frame):
        prepared = rggmci.prepare_archive_inputs(source, contigs=None, label="fabricated")
    assert prepared["contigs"] is None and prepared["sequence_context"]["available"] is False
    assert prepared["input"]["antismash_zip_sha256"] == session.snapshot.input_sha256


def test_capture_flags_require_capture_policy(inputs, tmp_path):
    source, _ = inputs
    assert cli.main(["run", "--input-zip", str(source), "--capture-resume", "--outdir", str(tmp_path / "out")]) == 2
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("failure", ["policy_missing", "policy_unreadable", "engine_binding"])
def test_actual_harness_capture_admission_errors_preserve_message_and_no_output(tmp_path, monkeypatch, capsys, failure):
    import intake_harness
    out = tmp_path / "not-created"
    argv = ["intake_harness.py", "--inputs", str(tmp_path / "absent.zip"),
            "--outdir", str(out), "--registry", str(out / "registry.csv"),
            "--metrics", str(out / "metrics.csv")]
    if failure == "policy_missing":
        argv += ["--capture-threads", "1"]
        expected = "CAPTURED_HARNESS_POLICY_REQUIRED"
    else:
        argv += ["--capture-policy", str(tmp_path / "absent-policy.json"),
                 "--capture-batch-policy", "all-or-nothing", "--capture-threads", "1"]
        expected = "REFUSED: CAPTURED_BATCH_HOLD: FileNotFoundError:"
        if failure == "engine_binding":
            def denied_binding():
                raise OSError("SELF_AUTHORED_ENGINE_BINDING_FAILURE")
            monkeypatch.setattr(intake_harness, "_engine_binding", denied_binding)
            expected = "CAPTURED_HARNESS_HOLD: SELF_AUTHORED_ENGINE_BINDING_FAILURE"
    monkeypatch.setattr(sys, "argv", argv)
    assert intake_harness.main() == 2
    output = capsys.readouterr()
    selected = output.err if failure == "policy_unreadable" else output.out
    assert selected.strip().startswith(expected)
    assert not out.exists()
