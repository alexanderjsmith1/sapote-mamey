"""Offline dependency selectors; no pip install, network, or figure-library import.

The shell controls use a synthetic interpreter which logs argv/stdin and never runs pip
or the embedded import diagnostic. They establish routing/selection, not installation.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import re
import subprocess
import tomllib

import pytest
from ._python_fixture_launcher import write_python_fixture

ROOT = Path(__file__).resolve().parents[1]
PLOTTING = {"dna-features-viewer", "pycirclize"}
RENDER_REQUIREMENTS = PLOTTING | {"biopython"}


def _name(requirement):
    return re.split(r"[<>=!~;\[\s]", requirement, maxsplit=1)[0].lower().replace("_", "-")


def _selection_errors(project):
    groups = project["optional-dependencies"]
    errors = []
    for group in ("figures", "all"):
        missing = RENDER_REQUIREMENTS - {_name(item) for item in groups[group]}
        if missing:
            errors.append((group, "missing", missing))
    leaked = PLOTTING & {_name(item) for item in project["dependencies"]}
    if leaked:
        errors.append(("core", "optional plotting leak", leaked))
    return errors


def test_renderer_requirements_selected_by_figures_and_all_without_core_promotion():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert _selection_errors(project) == []
    groups = project["optional-dependencies"]
    assert set(groups["bio"]) <= set(groups["figures"])
    assert "pyskani" not in {_name(item) for item in groups["figures"]}
    assert "logomaker" not in {_name(item) for item in groups["figures"]}


@pytest.mark.parametrize("mutation", ("missing-figures", "missing-all", "core-leak"))
def test_selector_controls_detect_real_missing_extra_and_core_promotion(mutation):
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    if mutation == "core-leak":
        project["dependencies"].append("dna-features-viewer")
    else:
        group = mutation.removeprefix("missing-")
        project["optional-dependencies"][group] = [
            item for item in project["optional-dependencies"][group]
            if _name(item) != "pycirclize"
        ]
    assert _selection_errors(project), "control must expose selector drift"


def test_direct_figure_imports_remain_function_local():
    # Static direct-owner boundary only, not a claim about all transitive imports.
    for rel in ("mamey/bgc_figures.py", "tools/bgc_figures.py"):
        tree = ast.parse((ROOT / rel).read_text())
        parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
        hits = []
        for node in ast.walk(tree):
            names = ([node.module] if isinstance(node, ast.ImportFrom)
                     else [alias.name for alias in node.names] if isinstance(node, ast.Import) else [])
            if not any(name and name.split(".")[0] in {"dna_features_viewer", "pycirclize"} for name in names):
                continue
            hits.append(node)
            owner = parents.get(node)
            while owner is not None and not isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                owner = parents.get(owner)
            assert owner is not None, f"{rel}:{node.lineno} promoted an optional figure import"
        assert hits, f"expected direct optional figure import in {rel}"


def test_addon_diagnostic_reports_both_optional_figure_imports():
    script = (ROOT / "bundle_support/install_sapote_addons.sh").read_text()
    payload = script.split('"$PY" - <<\'PY\'\n', 1)[1].split('\nPY\n', 1)[0]
    tree = ast.parse(payload)
    optional_loops = [node for node in tree.body if isinstance(node, ast.For)
                      and isinstance(node.iter, ast.List)]
    rows = [ast.literal_eval(node.iter) for node in optional_loops]
    modules = {row[0] for group in rows for row in group}
    assert {"dna_features_viewer", "pycirclize"} <= modules
    for node in optional_loops:
        # Optional import failures are reported, not promoted to core failure.
        assert not any(isinstance(item, ast.Raise) for item in ast.walk(node))


@pytest.mark.parametrize("figure_failure", (False, True))
def test_offline_installer_selects_both_libraries_and_keeps_figures_best_effort(tmp_path, figure_failure):
    repo = tmp_path / "isolated repo"
    (repo / "bundle_support").mkdir(parents=True)
    script = (ROOT / "bundle_support/install_sapote_addons.sh").read_text()
    # Constrain only fixture discovery; retain actual installation/fallback/verification owners.
    start = script.index('SEARCH_ROOTS+=(\n')
    end = script.index('\n)\n', start) + 3
    script = script[:start] + 'SEARCH_ROOTS+=("$HERE")\n' + script[end:]
    target = repo / "bundle_support/install_sapote_addons.sh"
    target.write_text(script)
    (repo / "synthetic.whl").write_text("not a usable wheel: synthetic interpreter only")
    log = tmp_path / "calls.jsonl"
    fake = write_python_fixture(tmp_path / "fake selected python", r'''import json, os, sys
from pathlib import Path
if sys.argv[1:2] == ["-c"]:
    print(1)  # synthetic virtual-environment reply
    raise SystemExit(0)
record = {"argv": sys.argv[1:]}
if sys.argv[1:] == ["-"]:
    record["stdin"] = sys.stdin.read()
with Path(os.environ["FAKE_LOG"]).open("a") as stream:
    stream.write(json.dumps(record) + "\n")
if sys.argv[1:3] == ["-m", "pip"] and "pycirclize" in sys.argv and os.environ["FIGURE_FAILURE"] == "1":
    print("synthetic invalid wheel archive", file=sys.stderr)
    raise SystemExit(1)
''')
    env = dict(os.environ, PYTHON=str(fake), FAKE_LOG=str(log), FIGURE_FAILURE=str(int(figure_failure)))
    result = subprocess.run(["bash", str(target)], cwd=repo, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    pip = [call["argv"] for call in calls if call["argv"][:2] == ["-m", "pip"]]
    assert len(pip) == 2
    assert all("--no-index" in call for call in pip)
    assert not (PLOTTING & {_name(item) for item in pip[0]})
    assert PLOTTING <= {_name(item) for item in pip[1]}
    assert len([call for call in calls if call["argv"] == ["-"]]) == 1
    if figure_failure:
        assert "optional figure stack unavailable; core imports still verified below" in result.stdout
    else:
        assert "figure stack installed" in result.stdout
