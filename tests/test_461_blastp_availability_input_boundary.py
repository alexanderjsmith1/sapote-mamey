"""Unavailable paths must not become apparently clear BLASTp availability reports."""
from argparse import Namespace
from pathlib import Path
import pytest
from mamey import blastp_availability as ba


@pytest.mark.parametrize("kind", ["absent", "file"])
def test_unavailable_package_refused_before_discovery(tmp_path, monkeypatch, kind):
    package = tmp_path / "package input"
    if kind == "file": package.write_text("not a directory\n")
    monkeypatch.setattr(ba._g, "discover_trove_roots", lambda *args: pytest.fail("unavailable input must not be scanned"))
    with pytest.raises(ValueError, match="BLASTP_PACKAGE_UNAVAILABLE"):
        ba.scan(package=package)


def test_cli_refusal_does_not_write_report(tmp_path, capsys):
    out = tmp_path / "availability output"
    args = Namespace(package=str(tmp_path / "missing"), runs_dir=None, out=str(out))
    assert ba.blastp_availability_command(args) == 2
    assert "BLASTP_PACKAGE_UNAVAILABLE" in capsys.readouterr().err
    assert not out.exists()


@pytest.mark.parametrize("kind", ["absent", "file"])
def test_unavailable_runs_root_has_typed_refusal(tmp_path, kind):
    root = tmp_path / "runs input"
    if kind == "file": root.write_text("not a directory\n")
    with pytest.raises(ValueError, match="BLASTP_RUNS_UNAVAILABLE"):
        ba.scan(runs_dir=root)
