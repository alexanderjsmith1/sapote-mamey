"""Synthetic local inventory controls; no installed companion, network or genome needed."""
import ast
import dataclasses
import importlib.util
import json
import pathlib
import shlex
import subprocess
import sys
from types import SimpleNamespace

import pytest

import mamey.companion_tools as C

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _tool(**changes):
    base = C.CompanionTool(
        id="invented", name="InventedTool", category="figure", requirement="optional",
        purpose="synthetic probe", consumes="nothing", produces="inventory only",
        detection_command="invented --version", expected_version="1.2.3",
        network_required=False, reference_db_required=False,
        install=({"platform": "any", "command": "operator selected install"},),
    )
    return dataclasses.replace(base, **changes)


def _answer(monkeypatch, *, stdout="InventedTool 1.2.3", stderr="", code=0):
    calls = []
    monkeypatch.setattr(C.shutil, "which", lambda name: "/synthetic/bin/" + name)
    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=code, stdout=stdout, stderr=stderr)
    monkeypatch.setattr(C.subprocess, "run", fake_run)
    return calls


@pytest.mark.parametrize("stdout,stderr", [
    ("InventedTool 1.2.3", ""), ("", "InventedTool 1.2.3"),
    ("InventedTool 1.2.3", "InventedTool 1.2.3"),
])
def test_nonzero_version_output_is_not_presence(monkeypatch, stdout, stderr):
    _answer(monkeypatch, stdout=stdout, stderr=stderr, code=2)
    probe = C.probe_tools([_tool()])[0]
    assert probe.present is False and probe.detected_version is None
    assert probe.probe_status == "PROBE_NONZERO_EXIT" and probe.probe_returncode == 2
    assert probe.version_status == "NOT_CHECKED"


@pytest.mark.parametrize("output,status", [
    ("Traceback (most recent call last):\nImportError: invented 1.2.3", "PROBE_DIAGNOSTIC_OUTPUT"),
    ("ModuleNotFoundError: invented 1.2.3", "PROBE_DIAGNOSTIC_OUTPUT"),
    ("wrapper: ImportError: invented 1.2.3", "PROBE_DIAGNOSTIC_OUTPUT"),
    ("WEB_SERVICE_OR_MANUAL_INSTALL 1.2.3", "PROBE_DIAGNOSTIC_OUTPUT"),
    ("NOT_PROBED 1.2.3", "PROBE_DIAGNOSTIC_OUTPUT"),
    ("", "NO_VERSION_EVIDENCE"),
    ("usage: invented --version", "NO_VERSION_EVIDENCE"),
    ("Invented 1.2.3\nInvented 2.0.0", "AMBIGUOUS_VERSION"),
    ("Invented 1.2.3rc1", "NO_VERSION_EVIDENCE"),
    ("1.2.3 " * 12000, "PROBE_TEXT_LIMIT"),
])
def test_zero_exit_untrusted_output_cannot_become_green(monkeypatch, output, status):
    _answer(monkeypatch, stdout=output)
    probe = C.probe_tools([_tool()])[0]
    assert probe.present is False and probe.detected_version is None
    assert probe.probe_status == status
    text = "\n".join(C.probe_display_lines(probe))
    assert "✅" not in text and "local detection not established" in text


@pytest.mark.parametrize("kind,status", [("manual", "MANUAL_NOT_PROBED"),
                                           ("web-or-manual", "WEB_OR_MANUAL_NOT_PROBED")])
def test_manual_web_entries_never_launch_or_infer_absent_install(monkeypatch, kind, status):
    def forbidden(*args, **kwargs):
        raise AssertionError("manual/web entry cannot invoke or resolve a command")
    monkeypatch.setattr(C.subprocess, "run", forbidden)
    monkeypatch.setattr(C.shutil, "which", forbidden)
    probe = C.probe_tools([_tool(detection_kind=kind)])[0]
    assert probe.present is False and probe.probe_status == status
    assert probe.probe_executable is None and probe.probe_returncode is None
    text = "\n".join(C.probe_display_lines(probe))
    assert "local installation NOT_ASSESSED" in text and "not found" not in text
    assert "install:" not in text


def test_offline_mode_has_no_detection_or_resolution(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline inventory cannot spawn or resolve commands")
    monkeypatch.setattr(C.subprocess, "run", forbidden)
    monkeypatch.setattr(C.shutil, "which", forbidden)
    probes = C.probe_tools([_tool(), _tool(detection_kind="manual")], run_detection=False)
    assert [p.probe_status for p in probes] == ["NOT_PROBED", "NOT_PROBED"]
    assert all(not p.present and p.detected_version is None for p in probes)


@pytest.mark.parametrize("observed,expected,status", [
    ("1.2.3", "1.2.3", "MATCH"), ("1.2.4", "1.2.3", "MISMATCH"),
    ("0.11.9", "0.11.x", "MATCH"), ("2.0.1", "2.x", "MATCH"),
    ("5.2", "5.2", "MATCH"), ("1.8.19", "1.8.19 or 2.0.x", "MATCH"),
    ("2.0.88", "1.8.19 or 2.0.x", "MATCH"), ("1.8.16", "1.8.19 or 2.0.x", "MISMATCH"),
    ("2.1.0", "1.8.19 or 2.0.x", "MISMATCH"), ("3.0.0", "", "NOT_SPECIFIED"),
    ("1.2.3", ">=1.0; arbitrary prose", "UNRECOGNIZED_POLICY"),
])
def test_successful_inventory_preserves_version_policy_and_readiness_limits(monkeypatch, observed, expected, status):
    calls = _answer(monkeypatch, stdout="InventedTool " + observed)
    probe = C.probe_tools([_tool(expected_version=expected)])[0]
    assert probe.present is True and probe.detected_version == observed
    assert probe.version_status == status and probe.probe_status == "DETECTED"
    assert probe.probe_executable == "/synthetic/bin/invented"
    assert calls[0][1]["stdin"] == subprocess.DEVNULL
    text = "\n".join(C.probe_display_lines(probe))
    assert "version " + status in text and "workflow NOT_ASSESSED" in text
    assert "✅" not in text


def test_zero_exit_stderr_version_is_successful_local_detection(monkeypatch):
    _answer(monkeypatch, stdout="", stderr="InventedTool 1.2.3")
    probe = C.probe_tools([_tool()])[0]
    assert probe.present and probe.detected_version == "1.2.3"
    assert probe.version_status == "MATCH"


def test_verify_flag_is_visible_even_when_numeric_version_matches(monkeypatch):
    _answer(monkeypatch, stdout="InventedTool 1.2.3")
    probe = C.probe_tools([_tool(verify_flag=True)])[0]
    assert probe.present and probe.version_status == "MATCH" and probe.review_required
    assert "REVIEW_REQUIRED" in "\n".join(C.probe_display_lines(probe))


def test_selected_native_failure_does_not_fallthrough_to_other_candidate(monkeypatch):
    calls = _answer(monkeypatch, stdout="GToTree v2.0.0", code=2)
    probe = C.probe_tools([_tool(detection_command="GToTree -v",
                                 executable_candidates=("GToTree", "gtotree"))])[0]
    assert not probe.present and probe.probe_status == "PROBE_NONZERO_EXIT"
    assert len(calls) == 1 and calls[0][0] == ["/synthetic/bin/GToTree", "-v"]


def test_lowercase_gtotree_candidate_is_detectable(monkeypatch):
    calls = _answer(monkeypatch, stdout="GToTree v2.0.0")
    monkeypatch.setattr(C.shutil, "which", lambda name: "/synthetic/bin/gtotree" if name == "gtotree" else None)
    tool = next(t for t in C.load_registry() if t.id == "gtotree")
    probe = C.probe_tools([tool])[0]
    assert probe.present and probe.detected_version == "2.0.0" and probe.version_status == "MATCH"
    assert calls[0][0] == ["/synthetic/bin/gtotree", "-v"]


@pytest.mark.parametrize("error,status", [(FileNotFoundError(), "MISSING_EXECUTABLE"),
                                           (subprocess.TimeoutExpired("invented", 8), "PROBE_TIMEOUT"),
                                           (OSError("synthetic OS refusal"), "PROBE_FAILED")])
def test_probe_failures_stay_explicit(monkeypatch, error, status):
    monkeypatch.setattr(C.shutil, "which", lambda name: "/synthetic/bin/invented")
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(C.subprocess, "run", fail)
    probe = C.probe_tools([_tool()])[0]
    assert not probe.present and probe.probe_status == status


def test_missing_binary_and_invalid_command_are_not_success(monkeypatch):
    monkeypatch.setattr(C.shutil, "which", lambda name: None)
    assert C.probe_tools([_tool()])[0].probe_status == "MISSING_EXECUTABLE"
    assert C.probe_tools([_tool(detection_command="'")])[0].probe_status == "PROBE_FAILED"
    assert C.probe_tools([_tool(detection_command="")])[0].probe_status == "INVALID_COMMAND"


def test_actual_child_uses_exact_running_python_instead_of_poisoned_path(tmp_path, monkeypatch):
    # Real child, invented scalar only. A PATH Python would leave a marker and fail.
    marker = tmp_path / "wrong-python-used"
    fake = tmp_path / "python"
    fake.write_text("#!/bin/sh\nprintf wrong > " + shlex.quote(str(marker)) + "\nexit 7\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    tool = _tool(detection_command="python -c " + shlex.quote("print('1.2.3')"))
    probe = C.probe_tools([tool])[0]
    assert probe.present and probe.detected_version == "1.2.3"
    assert probe.probe_executable == str(pathlib.Path(sys.executable).absolute())
    assert probe.version_status == "MATCH" and not marker.exists()


def test_actual_failed_import_child_is_not_installed():
    tool = _tool(detection_command="python -c " + shlex.quote("raise ImportError('invented 1.2.3')"))
    probe = C.probe_tools([tool])[0]
    assert not probe.present and probe.detected_version is None
    assert probe.probe_status == "PROBE_NONZERO_EXIT" and probe.probe_returncode != 0


def test_registry_gtotree_policy_agrees_with_existing_shared_owner():
    spec = importlib.util.spec_from_file_location("companion_shared_policy", ROOT / "tools/_gtotree_versions.py")
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    tool = next(t for t in C.load_registry() if t.id == "gtotree")
    assert tool.expected_version == " or ".join(shared.ACCEPTED_GTOTREE_VERSIONS_TEXT)
    assert tool.executable_candidates == shared.GTOTREE_BINS
    for version in ["1.8.16", "1.8.19", "1.8.190", "2.0.0", "2.0.9", "2.1.0", "3.0.0"]:
        assert (C._version_status(version, tool.expected_version) == "MATCH") is shared.accepted(version)
    assert tool.verify_flag is False


def test_declared_kinds_loaded_and_malformed_kinds_refused(tmp_path):
    registry = json.loads((ROOT / "mamey/data/companion_tools.json").read_text())
    tools = {t.id: t for t in C.load_registry()}
    assert tools["prism"].detection_kind == tools["gnps_masst"].detection_kind == "web-or-manual"
    assert tools["corason"].detection_kind == "manual"
    for invalid in ["unsupported", [], None]:
        changed = json.loads(json.dumps(registry))
        changed["tools"][0]["detection"]["kind"] = invalid
        path = tmp_path / "bad-kind.json"
        path.write_text(json.dumps(changed))
        with pytest.raises(ValueError, match="unknown detection kind"):
            C.load_registry(path)


@pytest.mark.parametrize("candidates", ["GToTree", ["../GToTree"], ["bad name"], [None]])
def test_malformed_executable_candidates_are_refused(tmp_path, candidates):
    registry = json.loads((ROOT / "mamey/data/companion_tools.json").read_text())
    registry["tools"][0]["detection"]["executable_candidates"] = candidates
    path = tmp_path / "bad-candidates.json"
    path.write_text(json.dumps(registry))
    with pytest.raises(ValueError, match="malformed executable candidates"):
        C.load_registry(path)


def test_malformed_review_flag_cannot_silently_become_true(tmp_path):
    registry = json.loads((ROOT / "mamey/data/companion_tools.json").read_text())
    registry["tools"][0]["detection"]["verify_flag"] = "false"
    path = tmp_path / "bad-review-flag.json"
    path.write_text(json.dumps(registry))
    with pytest.raises(ValueError, match="review metadata"):
        C.load_registry(path)


def test_doctor_consumes_the_typed_display_owner_without_green_presence_shortcut():
    tree = ast.parse((ROOT / "mamey/cli.py").read_text())
    doctor = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "doctor_command")
    calls = [n for n in ast.walk(doctor) if isinstance(n, ast.Call)]
    assert any(isinstance(n.func, ast.Name) and n.func.id == "probe_display_lines" for n in calls)


def test_docs_keep_version_specific_argv_and_governed_admission_limits():
    doc = (ROOT / "docs/companion_tools.md").read_text()
    protocol = (ROOT / "docs/LLM_COMPANION_TOOL_PROTOCOL.md").read_text()
    assert "GToTree -j 1 -n 1 -M 1 -N" in doc
    assert "omits `-n` for 2.0.x" in doc
    assert "planner still requires/emits" not in doc
    for text in [doc, protocol]:
        assert "max(2 * jobs, jobs * muscle_threads)" in text
        assert "at least two" in text
        assert "does not expose" in text and "tools/run_planned_tree.py" in text
    assert "`RUN_STATE.json` has `approved=true`" in protocol
    assert "legacy v1" in protocol and "--plan-dir" in protocol
