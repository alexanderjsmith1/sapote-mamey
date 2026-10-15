"""The pipeline forwards prep's required strictness policy instead of calling prep bare.

Prep refuses any call without --strictness or --allow-mixed. The pipeline's normal prep
path must therefore forward an operator-selected policy, refuse early when none is given,
and require a written justification for the mixed-input override.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "bigscape_pipeline_452", ROOT / "tools" / "bigscape_pipeline.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _argv(workdir, *extra):
    return ["--inputs", "synthetic.zip", "--pfam", "synthetic.hmm",
            "--workdir", str(workdir), "--skip-cluster", "--run-id", "42", *extra]


class _Stop(Exception):
    pass


def _record_prep(module, monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append([str(value) for value in cmd])
        raise _Stop()

    monkeypatch.setattr(module, "run", fake_run)
    return calls


def test_normal_prep_forwards_explicit_strictness(tmp_path, monkeypatch):
    module = _load()
    calls = _record_prep(module, monkeypatch)
    workdir = tmp_path / "run"
    with pytest.raises(_Stop):
        module.main(_argv(workdir, "--strictness", "loose"))
    prep = calls[0]
    assert prep[1].endswith("bigscape_prep.py")
    assert prep[prep.index("--strictness") + 1] == "loose"
    assert "--allow-mixed" not in prep
    policy = json.loads((workdir / "PREP_STRICTNESS_POLICY.json").read_text())
    assert policy["strictness"] == "loose" and policy["allow_mixed"] is False


def test_prep_without_policy_is_refused_before_staging(tmp_path, monkeypatch):
    module = _load()
    calls = _record_prep(module, monkeypatch)
    with pytest.raises(module.PipelineRunError, match="PREP_STRICTNESS_REQUIRED"):
        module.main(_argv(tmp_path / "run"))
    assert calls == []


def test_mixed_override_requires_justification(tmp_path, monkeypatch):
    module = _load()
    calls = _record_prep(module, monkeypatch)
    with pytest.raises(module.PipelineRunError, match="PREP_MIXED_JUSTIFICATION_REQUIRED"):
        module.main(_argv(tmp_path / "run", "--allow-mixed"))
    assert calls == []


def test_mixed_override_with_justification_is_forwarded_and_recorded(tmp_path, monkeypatch):
    module = _load()
    calls = _record_prep(module, monkeypatch)
    workdir = tmp_path / "run"
    with pytest.raises(_Stop):
        module.main(_argv(workdir, "--allow-mixed", "--mixed-justification", "checked by hand"))
    assert "--allow-mixed" in calls[0] and "--strictness" not in calls[0]
    policy = json.loads((workdir / "PREP_STRICTNESS_POLICY.json").read_text())
    assert policy["mixed_justification"] == "checked by hand"


def test_conflicting_policy_is_refused(tmp_path, monkeypatch):
    module = _load()
    _record_prep(module, monkeypatch)
    with pytest.raises(module.PipelineRunError, match="PREP_STRICTNESS_CONFLICT"):
        module.main(_argv(tmp_path / "run", "--strictness", "loose", "--allow-mixed",
                          "--mixed-justification", "x"))


def test_skip_prep_does_not_require_policy(tmp_path, monkeypatch):
    module = _load()
    calls = _record_prep(module, monkeypatch)
    # With no database the run binding refuses next; the point is that the strictness
    # policy is not demanded when prep is skipped.
    with pytest.raises(module.PipelineRunError, match="RUN_ID_NOT_PRESENT"):
        module.main(_argv(tmp_path / "run", "--skip-prep"))
    assert calls == []
