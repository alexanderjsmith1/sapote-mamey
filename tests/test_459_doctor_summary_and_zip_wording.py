"""doctor wording: the summary names a missing core dependency, and the no-ZIP warning points at real options.

Before: a missing ijson (a core dependency in pyproject.toml) was summarized as "optional items only", and the
no-ZIP warning told the user to supply `--input-zip`, which `doctor` does not have. Severity and exit code are
unchanged; this card only fixes the words.
"""
import argparse
import importlib.util
import tomllib
from pathlib import Path

import pytest

from mamey import cli

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def synthetic_bundle(tmp_path, monkeypatch):
    root = tmp_path / "SYNTHETIC_DOCTOR_OUTPUT"
    root.mkdir()
    monkeypatch.setattr(cli, "BUNDLE_ROOT", root)
    monkeypatch.chdir(root)
    return root


def _absent(monkeypatch, *names):
    real = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda n, *a, **k: None if n.split(".")[0] in names else real(n, *a, **k))


def _doctor(capsys):
    status = cli.doctor_command(argparse.Namespace())
    return status, capsys.readouterr().out


def _summary(out):
    return next(line for line in out.splitlines() if line.startswith("DOCTOR:"))


def test_missing_ijson_is_not_called_optional(synthetic_bundle, monkeypatch, capsys):
    _absent(monkeypatch, "ijson")
    status, out = _doctor(capsys)
    summary = _summary(out)
    assert "ijson absent" in out
    assert "optional items only" not in summary
    assert "core dependency" in summary and "ijson" in summary
    assert "pyproject.toml" in summary
    assert status == 0                      # severity unchanged: the line is still a warning, not a failure


def test_only_optional_items_missing_keeps_the_old_wording(synthetic_bundle, monkeypatch, capsys):
    _absent(monkeypatch, "matplotlib")      # an optional extra; ijson and reportlab stay as the environment has them
    if importlib.util.find_spec("ijson") is None or importlib.util.find_spec("reportlab") is None:
        pytest.skip("needs ijson and reportlab installed")
    status, out = _doctor(capsys)
    summary = _summary(out)
    assert "optional items only" in summary and "core dependency" not in summary
    assert status == 0


def test_the_core_names_doctor_flags_are_core_in_pyproject():
    deps = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"]
    core = {d.split(">")[0].split("<")[0].split("=")[0].strip().lower() for d in deps}
    assert {"ijson", "reportlab"} <= core


def test_no_zip_warning_does_not_offer_a_flag_doctor_lacks(synthetic_bundle, capsys):
    _, out = _doctor(capsys)
    line = next(l for l in out.splitlines() if "no antiSMASH ZIPs found" in l)
    assert "--input-zip" not in line.split("mamey run")[0]      # doctor's own advice never names it
    assert "mamey inspect <zip>" in line and "mamey run --input-zip <zip>" in line
    doctor_flags = {a.option_strings[0] for a in _doctor_parser()._actions if a.option_strings}
    assert "--input-zip" not in doctor_flags


def _doctor_parser():
    sub = next(a for a in cli.build_parser()._actions if a.dest == "command")
    return sub.choices["doctor"]
