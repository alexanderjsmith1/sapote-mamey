from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "audit_documents_wheelhouse.py"
SPEC = importlib.util.spec_from_file_location("audit_documents_wheelhouse", TOOL)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_documents_profile_names_every_direct_runtime() -> None:
    requirements = MODULE.read_profile(ROOT / "sapote_addons" / "profiles" / "documents.txt")
    names = {MODULE.requirement_name(requirement) for requirement in requirements}
    assert names == {"python-docx", "lxml", "pyyaml", "reportlab", "pypdf", "pillow"}


def test_interpreter_path_preserves_venv_symlink(tmp_path: Path) -> None:
    target = tmp_path / "base-python"
    target.write_text("placeholder\n", encoding="utf-8")
    venv_python = tmp_path / "venv-python"
    venv_python.symlink_to(target)
    observed = MODULE.interpreter_path(str(venv_python))
    assert observed == venv_python.absolute()
    assert observed != target.resolve()


def test_audit_reports_every_missing_requirement_without_network(tmp_path: Path) -> None:
    python = tmp_path / "python"
    python.write_text("placeholder\n", encoding="utf-8")
    wheelhouse = tmp_path / "wheels"
    wheelhouse.mkdir()
    commands: list[list[str]] = []

    def fake_runner(command, **kwargs):
        commands.append(command)
        requirement = command[-1]
        returncode = 1 if requirement.startswith(("python-docx", "lxml")) else 0
        message = "No matching distribution" if returncode else "Would install"
        return SimpleNamespace(returncode=returncode, stdout=message, stderr="")

    report = MODULE.audit_requirements(
        python=python,
        wheelhouse=wheelhouse,
        requirements=["python-docx>=1.2,<2.0", "lxml>=5.0,<7.0", "pypdf>=5.0,<7.0"],
        runner=fake_runner,
    )
    assert report["status"] == "FAIL"
    assert report["failed_resolution"] == ["python-docx", "lxml"]
    assert len(commands) == 3
    assert all("--no-index" in command for command in commands)
    assert all("--only-binary=:all:" in command for command in commands)
