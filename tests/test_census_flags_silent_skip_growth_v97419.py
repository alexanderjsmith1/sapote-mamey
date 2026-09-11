"""v9.7.419 — a census comparison must notice tests that stopped EXECUTING, not only ones removed.

`tools/suite_count_census.py` exists to keep collection, execution, skips and deselection distinct,
and its docstring is explicit that "skipped cases remain skips, not deselections". It preserves that
distinction in its OUTPUT and then never acts on it: `--against` compares selected nodeids and the
failure/error counts, so a run in which cases silently became skips has identical collection, no
failures, and returns `"status": "PASS"` with exit 0.

Why that gap matters here rather than in the abstract. Collection was measured as stable across two
extraction locations, but it is not stable across dependency availability: module-level
`pytest.importorskip` gates can remove every test in a module before execution. Execution can also
move when governed data are provisioned (`docs/EXTERNAL_DATA.md`). The census comparison therefore
needs to preserve both collection-process provisioning and imported JUnit outcome changes.

Skips are the only outcome class that can grow while everything stays green, which makes an
unwatched skip count the "a test can stop testing" shape at suite level.

Claim safety: measurement bookkeeping. No score moves and no biological claim is made or admitted.
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = pathlib.Path(os.environ.get(
    "CENSUS_TOOL_UNDER_TEST", ROOT / "tools" / "suite_count_census.py"))
SCOPE = "tests/test_seal_sweep_v97406.py"          # small, fast, always collectable

_CASES = '<testcase name="t{}"/>'
_SKIP = '<testcase name="t{}"><skipped/></testcase>'


def _junit(path, passed, skipped):
    body = "".join(_CASES.format(i) for i in range(passed))
    body += "".join(_SKIP.format(100 + i) for i in range(skipped))
    path.write_text(f'<testsuites><testsuite name="p">{body}</testsuite></testsuites>', encoding="utf-8")
    return path


def _census(tmp_path, junit, against=None, out=None):
    cmd = [sys.executable, str(TOOL), "--tests", SCOPE, "--junit", str(junit)]
    if against:
        cmd += ["--against", str(against)]
    if out:
        cmd += ["--write", "--out", str(out)]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))


def _census_scopes(scopes, junit, against=None, out=None, env=None):
    cmd = [sys.executable, str(TOOL), "--junit", str(junit)]
    for scope in scopes:
        cmd += ["--tests", str(scope)]
    if against:
        cmd += ["--against", str(against)]
    if out:
        cmd += ["--write", "--out", str(out)]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), env=env)


def _load():
    spec = importlib.util.spec_from_file_location("suite_count_census_under_test", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_a_run_where_cases_stopped_executing_is_not_a_pass(tmp_path):
    """The finding: 10 passed -> 5 passed + 5 skipped used to return PASS with exit 0."""
    base_json = tmp_path / "base.json"
    assert _census(tmp_path, _junit(tmp_path / "a.xml", 10, 0), out=base_json).returncode == 0
    out = _census(tmp_path, _junit(tmp_path / "b.xml", 5, 5), against=base_json)
    assert out.returncode != 0, (
        "five cases stopped executing between the two runs and the census reported PASS:\n" + out.stdout)
    payload = json.loads(out.stdout)
    assert payload["status"] == "REVIEW_REQUIRED"
    assert any("SKIPS_ROSE" in c for c in payload["concerns"]), payload["concerns"]


def test_an_unchanged_run_is_still_a_pass(tmp_path):
    """Control: the guard must not fire on a run that did not change."""
    base_json = tmp_path / "base.json"
    junit = _junit(tmp_path / "a.xml", 10, 0)
    assert _census(tmp_path, junit, out=base_json).returncode == 0
    out = _census(tmp_path, junit, against=base_json)
    assert out.returncode == 0, out.stdout
    assert json.loads(out.stdout)["status"] == "PASS"


def test_falling_skips_are_not_flagged(tmp_path):
    """Control: more tests executing than before is good news, not a concern."""
    base_json = tmp_path / "base.json"
    assert _census(tmp_path, _junit(tmp_path / "a.xml", 5, 5), out=base_json).returncode == 0
    out = _census(tmp_path, _junit(tmp_path / "b.xml", 10, 0), against=base_json)
    assert out.returncode == 0, out.stdout
    assert not [c for c in json.loads(out.stdout)["concerns"] if "SKIPS_ROSE" in c]


def test_environment_is_recorded_and_compared(tmp_path):
    """Two execution blocks measured under different provisioning are not comparable."""
    census = _load()
    env = census.environment_fingerprint()
    assert set(env) == {"official_data_reachable", "official_data_root",
                        "collection_gating_deps"}
    assert isinstance(env["official_data_reachable"], bool)

    base_json = tmp_path / "base.json"
    assert _census(tmp_path, _junit(tmp_path / "a.xml", 10, 0), out=base_json).returncode == 0
    doctored = json.loads(base_json.read_text())
    flipped = not doctored["environment"]["official_data_reachable"]
    doctored["environment"] = {"official_data_reachable": flipped, "official_data_root": None}
    base_json.write_text(json.dumps(doctored))
    out = _census(tmp_path, _junit(tmp_path / "b.xml", 10, 0), against=base_json)
    assert out.returncode != 0, "a baseline from a different provisioning was diffed silently"
    assert any("ENVIRONMENT_DIFFERS" in c for c in json.loads(out.stdout)["concerns"])


def test_collection_is_stable_across_location_which_is_all_that_was_measured():
    """The original evidence established location stability, not environment stability.

    Measured while writing it: the sealed v9.7.418 tree censused `collected: 10150` from inside the
    workspace and `10150` from a copy outside it. Dependency availability was not held to be equal.
    """
    census = _load()
    result = census.census([SCOPE])
    assert result["collected"] == result["selected"] + result["deselected"]
    assert result["collected"] > 0
    assert "environment" in result, "the fingerprint must travel with every census"


def test_requested_collection_records_the_import_gates_that_actually_ran():
    """The producer records exact gates from the same collection process and scope."""
    census = _load()
    result = census.census([SCOPE, "tests/test_compare_synthetic_ani.py"])
    deps = result["environment"]["collection_gating_deps"]
    assert "pyfastani" in deps
    collected = [nodeid for nodeid in result["selected_nodeids"]
                 if nodeid.startswith("tests/test_compare_synthetic_ani.py::")]
    assert bool(collected) is deps["pyfastani"]


def test_all_collection_skipped_scope_is_still_a_valid_census():
    """A gate can hide every case in a requested scope without making measurement fail."""
    census = _load()
    result = census.census(["tests/test_compare_synthetic_ani.py"])
    if result["environment"]["collection_gating_deps"]["pyfastani"]:
        pytest.skip("pyfastani is present, so this environment cannot exercise the empty scope")
    assert result["collected"] == 0
    assert result["selected_nodeids"] == []
    assert result["collection_skips"] == ["tests/test_compare_synthetic_ani.py"]


def test_collection_gate_capture_uses_the_test_modules_path_context():
    """A test-local sys.path addition is measured as collection sees it, not guessed outside it."""
    census = _load()
    result = census.census([SCOPE, "tests/test_zip_hygiene_allowlist_wiring.py"])
    assert result["environment"]["collection_gating_deps"]["preflight_zip_hygiene"] is True


def test_dependency_loss_is_attributed_to_collection_environment(tmp_path):
    """A real import gate changing from available to absent is not reported as deletion alone."""
    module_dir = tmp_path / "available"
    module_dir.mkdir()
    (module_dir / "optional_gate.py").write_text("VALUE = 1\n", encoding="utf-8")
    gated_test = tmp_path / "test_optional_gate.py"
    gated_test.write_text(
        "import pytest\n"
        "pytest.importorskip('optional_gate')\n"
        "def test_optional_gate_executes():\n"
        "    assert True\n",
        encoding="utf-8")
    scopes = [SCOPE, gated_test]
    junit = _junit(tmp_path / "run.xml", 1, 0)
    base_json = tmp_path / "base.json"
    with_dep = os.environ.copy()
    with_dep["PYTHONPATH"] = str(module_dir)
    assert _census_scopes(scopes, junit, out=base_json, env=with_dep).returncode == 0

    without_dep = os.environ.copy()
    without_dep.pop("PYTHONPATH", None)
    out = _census_scopes(scopes, junit, against=base_json, env=without_dep)
    assert out.returncode != 0
    payload = json.loads(out.stdout)
    assert payload["status"] == "REVIEW_REQUIRED"
    concern = next(c for c in payload["concerns"] if "ENVIRONMENT_DIFFERS" in c)
    assert "optional_gate" in concern
    assert "True" in concern and "False" in concern


def test_genuine_test_deletion_remains_a_nodeid_loss_under_same_environment(tmp_path):
    """Negative control: deletion is still detected without inventing an environment change."""
    changing_test = tmp_path / "test_changing.py"
    changing_test.write_text("def test_present():\n    assert True\n", encoding="utf-8")
    scopes = [SCOPE, changing_test]
    junit = _junit(tmp_path / "run.xml", 1, 0)
    base_json = tmp_path / "base.json"
    assert _census_scopes(scopes, junit, out=base_json).returncode == 0

    changing_test.write_text("# test removed\n", encoding="utf-8")
    current_json = tmp_path / "current.json"
    out = _census_scopes(scopes, junit, against=base_json, out=current_json)
    assert out.returncode != 0
    payload = json.loads(current_json.read_text(encoding="utf-8"))
    assert payload["removed_selected_nodeids"] == ["::test_present"]
    assert not any("ENVIRONMENT_DIFFERS" in c for c in payload["concerns"])
