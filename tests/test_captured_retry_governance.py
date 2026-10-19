"""Retained replay plans and invocation-local configured exclusions on tiny fixtures."""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import pytest
try:
    from .test_captured_batch_resume import parsed_batch, stub_pipeline
    from .test_captured_actual_run import inputs, run_args
except ImportError:
    from test_captured_batch_resume import parsed_batch, stub_pipeline
    from test_captured_actual_run import inputs, run_args
from mamey import cli, captured_run, captured_batch, capture_governance, exclusions, source_context
from mamey.intake_session import CapturedIntakeHold
from mamey.archive_snapshot import ArchiveSnapshot


@pytest.mark.parametrize("failed_index", [0, 1])
def test_plan_binding_exists_before_each_pinned_replay_and_unchanged_retry_succeeds(tmp_path, monkeypatch, failed_index):
    args, one, two, _ = parsed_batch(tmp_path)
    monkeypatch.setenv("MAMEY_BOUNDED_BUDGET_S", "0")
    original = captured_run.capture
    planned = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (one, two)}
    count = []
    def refused(selected, policy, expected=None):
        if expected is not None:
            saved = list(tmp_path.glob(".batch.captured-failure-*/BINDING.json"))
            assert saved
            identity = json.loads(saved[-1].read_text())
            assert {r["path"]: r["input_sha256"] for r in identity["inputs"]} == planned
            count.append(expected)
            if len(count) == failed_index + 1:
                raise OSError("fabricated replay refusal")
        return original(selected, policy, expected)
    monkeypatch.setattr(captured_run, "capture", refused)
    assert captured_batch.run_batch(args, stub_pipeline) == 2
    assert not Path(args.outdir).exists()
    states = [json.loads(p.read_text()) for p in tmp_path.glob(".batch.captured-failure-*/ATTEMPT.json")]
    assert states and states[-1]["state"] == "FAILED"
    monkeypatch.setattr(captured_run, "capture", original)
    args.capture_resume = True
    assert captured_batch.run_batch(args, stub_pipeline) == 0
    assert any(json.loads(p.read_text())["state"] == "COMMITTED"
               for p in tmp_path.glob(".batch.captured-failure-*/ATTEMPT.json"))


def test_active_accessor_consumes_captured_governance_without_reopening_changed_file(tmp_path, monkeypatch):
    official = tmp_path / "official";official.mkdir()
    path = official / "exclusions.json"
    original = b'{"hard_excluded":["SYNTHETIC_ORIGINAL"]}'
    path.write_bytes(original)
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(official))
    captured = capture_governance.capture(64000)
    path.write_text('{"hard_excluded":["SYNTHETIC_CHANGED"]}')
    assert exclusions.governed_excluded() == {"SYNTHETIC_CHANGED"}
    actual_open = Path.open
    def opened(selected, *args, **kwargs):
        assert selected != path, "captured governance locator reopened"
        return actual_open(selected, *args, **kwargs)
    monkeypatch.setattr(Path, "open", opened)
    # Explicit configuration-context adapter; no scientific capability is reconstructed.
    with source_context.binding(SimpleNamespace(governance=captured)):
        assert exclusions.governed_excluded() == {"SYNTHETIC_ORIGINAL"}
        first = exclusions.load_exclusions(strict=True)
        first["hard_excluded"].append("SYNTHETIC_MUTATION")
        assert exclusions.load_exclusions(strict=True)["hard_excluded"] == ["SYNTHETIC_ORIGINAL"]
    assert captured.binding()["selected"]["sha256"] == hashlib.sha256(original).hexdigest()


def test_configured_exclusion_resource_cap_refuses_before_archive_capture(inputs, tmp_path, monkeypatch):
    official = tmp_path / "oversized-official";official.mkdir()
    (official / "exclusions.json").write_text('{"hard_excluded":[],"pad":"' + "X" * 64001 + '"}')
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(official))
    monkeypatch.setattr(ArchiveSnapshot, "capture", lambda *a, **k: pytest.fail("oversized governance captured genome"))
    assert cli.main(run_args(inputs, tmp_path)) == 2
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("malformed", [False, True])
def test_missing_or_malformed_configured_source_keeps_explicit_fallback_state(tmp_path, monkeypatch, malformed):
    official = tmp_path / "official";official.mkdir()
    if malformed:
        (official / "exclusions.json").write_text("{")
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(official))
    captured = capture_governance.capture(64000)
    binding = captured.binding()
    assert binding["state"] == "MODULE_DEFAULT" and binding["selected"] is None
    assert binding["probes"][0]["state"] == ("PARSE_FAILED" if malformed else "MISSING")
    with pytest.raises(ValueError):
        captured.read(strict=True)
    with pytest.warns(RuntimeWarning):
        assert captured.read() == exclusions._DEFAULT
