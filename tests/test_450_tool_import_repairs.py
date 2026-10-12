"""Offline import/entry tests and frozen original-AST compatibility controls.

No real bank pipeline or plotting is needed. Child help/import probes use stdlib
only; wrapper outcome tests replace workbook/plot execution with synthetic seams.
"""
from __future__ import annotations

import argparse
import ast
import builtins
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "tools" / "build_master.py"
PLOT = ROOT / "tools" / "plot_examples.py"
EXPORT = ROOT / "tools" / "cohort_tailoring" / "export_evidence_index.py"
# Original pinned source: build_master fdbbee719f7f18c0b0eb80e85166d0eb22c0b1d39e45d7208b8f7dd0716de886,
# plot_examples 292e424ae4c5165ec8247539a7970de967b429f12eda14f85060352ab9f4d3e5,
# evidence exporter 166559543cfc62e0efa42346edb6aa10525127fc7f73a342097e47c403898b22.
WORKBOOK_AST = 'eaa8d5c53baf5cd26c00291c0907588fd39700aee4cd5818744e1fc63b6b0cf7'
HELPERS_AST = 'df97659038375d67f475b0c0f5c55b8ebacd36de052367fc2f05d88b872eac02'
CLI_AST = '10159d88ecc66244ddcdd1ae5198f9f98d032a7a57107922cf16854a3b0c36ff'
PLOT_AST = '041762527e2d8e46fc876732ec5089a0c04e76436ad87db1854ab90289952afa'
EXPORT_AST = '5e0312ac13dc2bcc066cf040b28901e27ebe8f8b4fe233f9a73985485fc52d30'


def _canonical_ast(node):
    if isinstance(node, ast.AST):
        return {
            "node": type(node).__name__,
            "fields": {
                key: _canonical_ast(value) for key, value in ast.iter_fields(node)
                if not (key == "type_params" and not value)
            },
        }
    if isinstance(node, list):
        return [_canonical_ast(value) for value in node]
    return node


def _digest(nodes):
    # Canonical fields avoid ast.dump formatting differences between Python versions;
    # an empty type_params field was added in 3.12 and has no legacy body semantics.
    tree = ast.Module(body=nodes, type_ignores=[])
    raw = json.dumps(_canonical_ast(tree), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _tree_and_main(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    return tree, main


def _namespace(path, tree=None):
    namespace = {"__name__": "offline_import_fixture", "__file__": str(path)}
    code = compile(tree if tree is not None else path.read_text(encoding="utf-8"), str(path), "exec")
    exec(code, namespace)
    return namespace


def _child(args, cwd):
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    return subprocess.run(
        [sys.executable, "-B", "-S", *args], cwd=cwd, env=environment,
        text=True, capture_output=True, timeout=30,
    )


@pytest.mark.parametrize("path", [BUILD, PLOT])
def test_import_does_not_parse_argv_change_paths_or_start_work(tmp_path, monkeypatch, capsys, path):
    # Compile before installing the operation seams: loading source bytes is allowed.
    code = compile(path.read_text(encoding="utf-8"), str(path), "exec")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["unrelated-host", "--unrecognized-host-argument"])
    before_path = list(sys.path)
    before_modules = set(sys.modules)
    def refused(*args, **kwargs):
        pytest.fail("import must not start command, filesystem or process work")
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", refused)
    monkeypatch.setattr(os, "chdir", refused)
    monkeypatch.setattr(subprocess, "Popen", refused)
    monkeypatch.setattr(builtins, "open", refused)
    namespace = {"__name__": "offline_import_fixture", "__file__": str(path)}
    exec(code, namespace)
    assert callable(namespace["main"])
    assert sys.path == before_path
    assert set(sys.modules) == before_modules
    assert list(tmp_path.iterdir()) == []
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


def test_workbook_help_needs_no_optional_dependency_or_bank(tmp_path):
    result = _child([str(BUILD), "--help"], tmp_path)
    assert result.returncode == 0, result.stderr
    assert "--banked-dir" in result.stdout
    assert "--out" in result.stdout
    assert "[DEPRECATED] tools/build_master.py" in result.stderr
    assert "NOT the canonical builder" in result.stderr
    assert list(tmp_path.iterdir()) == []


def test_original_workbook_body_helpers_and_cli_are_mechanically_preserved():
    tree, main = _tree_and_main(BUILD)
    assert [type(node).__name__ for node in tree.body] == ["Expr", "FunctionDef", "If"]
    run = next(node for node in main.body if isinstance(node, ast.Try))
    # The first four try statements admit bank, preserve absolute output resolution,
    # change cwd, then lazily load atomic_save. Every legacy workbook statement follows.
    assert isinstance(run.body[3], ast.ImportFrom) and run.body[3].module == "_wbio"
    assert len(run.body[4:]) == 205
    assert _digest(run.body[4:]) == WORKBOOK_AST
    helpers = [node for node in main.body if isinstance(node, ast.FunctionDef)]
    assert _digest(helpers) == HELPERS_AST
    banner_index = next(i for i, node in enumerate(main.body) if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "emit")
    parse_index = next(i for i, node in enumerate(main.body) if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "_a")
    cli = copy.deepcopy(main.body[banner_index:parse_index + 1])
    assert isinstance(cli[-1].value, ast.Call)
    assert ast.dump(cli[-1].value.args[0], include_attributes=False) == "Name(id='argv', ctx=Load())"
    cli[-1].value.args = []  # sole intended CLI change: injectable argv with the same default.
    assert _digest(cli) == CLI_AST
    assert ast.dump(run.finalbody[0], include_attributes=False) == ast.dump(
        ast.parse("_os_.chdir(_previous_cwd)").body[0], include_attributes=False,
    )


def _stub_bank_and_atomic_save(monkeypatch, calls):
    guard = types.ModuleType("mamey.bank_transaction")
    monkeypatch.setattr(guard, "hold_reader", lambda bank: calls.append(("reader", bank)), raising=False)
    monkeypatch.setitem(sys.modules, "mamey.bank_transaction", guard)
    writer = types.ModuleType("_wbio")
    monkeypatch.setattr(writer, "atomic_save", lambda *args, **kwargs: pytest.fail("real workbook pipeline must not run"), raising=False)
    monkeypatch.setitem(sys.modules, "_wbio", writer)
    monkeypatch.setattr(sys, "path", list(sys.path))


def test_workbook_cwd_restored_after_fake_dependency_failure(tmp_path, monkeypatch):
    namespace = _namespace(BUILD)
    bank = tmp_path / "bank"
    bank.mkdir()
    caller = tmp_path / "caller"
    caller.mkdir()
    monkeypatch.chdir(caller)
    calls = []
    _stub_bank_and_atomic_save(monkeypatch, calls)
    original_import = builtins.__import__
    def failing_import(name, *args, **kwargs):
        if name == "openpyxl":
            assert Path.cwd() == bank
            raise RuntimeError("synthetic-workbook-dependency-failure")
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", failing_import)
    with pytest.raises(RuntimeError, match="synthetic-workbook-dependency-failure"):
        namespace["main"](["--banked-dir", str(bank), "--out", "legacy.xlsx"])
    assert Path.cwd() == caller
    assert calls == [("reader", str(bank))]
    assert not (caller / "legacy.xlsx").exists()
    assert list(bank.iterdir()) == []


def test_workbook_success_wrapper_restores_cwd_and_uses_caller_relative_output(tmp_path, monkeypatch):
    # Synthetic control-flow seam replaces only the fingerprinted workbook block.
    # It exercises the actual admission/parse/cwd/finally wrapper without running a bank pipeline.
    tree, main = _tree_and_main(BUILD)
    run = next(node for node in main.body if isinstance(node, ast.Try))
    assert _digest(run.body[4:]) == WORKBOOK_AST
    run.body[4:] = ast.parse("events.append((_os_.getcwd(), _OUT))\nreturn 0").body
    ast.fix_missing_locations(tree)
    namespace = _namespace(BUILD, tree)
    namespace["events"] = []
    bank = tmp_path / "bank"
    bank.mkdir()
    caller = tmp_path / "caller"
    caller.mkdir()
    monkeypatch.chdir(caller)
    calls = []
    _stub_bank_and_atomic_save(monkeypatch, calls)
    assert namespace["main"](["--banked-dir", str(bank), "--out", "legacy.xlsx"]) == 0
    assert namespace["events"] == [(str(bank), str(caller / "legacy.xlsx"))]
    assert Path.cwd() == caller
    assert list(bank.iterdir()) == []
    assert list(caller.iterdir()) == []


def test_original_plot_body_and_export_function_are_mechanically_preserved():
    tree, main = _tree_and_main(PLOT)
    assert [type(node).__name__ for node in tree.body] == ["Expr", "FunctionDef", "If"]
    load_index = next(i for i, node in enumerate(main.body) if isinstance(node, ast.FunctionDef) and node.name == "load")
    assert _digest(main.body[load_index:-1]) == PLOT_AST
    assert isinstance(main.body[-1], ast.Return) and main.body[-1].value.value == 0
    export_tree = ast.parse(EXPORT.read_text(encoding="utf-8"))
    export = next(node for node in export_tree.body if isinstance(node, ast.FunctionDef) and node.name == "export")
    assert _digest([export]) == EXPORT_AST


@pytest.mark.parametrize("argv,host_args,expected", [
    ([], ["host", "ignored"], "figure_ready"),
    (["selected", "extra-ignored"], ["host"], "selected"),
    (None, ["host"], "figure_ready"),
    (None, ["host", "positional", "extra-ignored"], "positional"),
])
def test_plot_wrapper_retains_legacy_positional_default_with_fake_dependencies(monkeypatch, argv, host_args, expected):
    tree, main = _tree_and_main(PLOT)
    load_index = next(i for i, node in enumerate(main.body) if isinstance(node, ast.FunctionDef) and node.name == "load")
    assert _digest(main.body[load_index:-1]) == PLOT_AST
    main.body[load_index:] = ast.parse("return d").body  # input-selection seam; no figures are rendered.
    ast.fix_missing_locations(tree)
    namespace = _namespace(PLOT, tree)
    backend_calls = []
    mpl = types.ModuleType("matplotlib")
    mpl.__path__ = []
    monkeypatch.setattr(mpl, "use", lambda backend: backend_calls.append(backend), raising=False)
    plt = types.ModuleType("matplotlib.pyplot")
    mpl.pyplot = plt
    monkeypatch.setitem(sys.modules, "matplotlib", mpl)
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", plt)
    monkeypatch.setattr(sys, "argv", host_args)
    monkeypatch.setattr(sys, "path", list(sys.path))
    assert namespace["main"](argv) == expected
    assert backend_calls == ["Agg"]


def test_exporter_package_import_in_clean_stdlib_child(tmp_path):
    code = "import sys; sys.path.insert(0, " + repr(str(ROOT)) + "); import tools.cohort_tailoring.export_evidence_index as module; assert callable(module.export)"
    result = _child(["-c", code], tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout == result.stderr == ""
    assert list(tmp_path.iterdir()) == []


def test_exporter_bare_script_help_from_unrelated_cwd(tmp_path):
    result = _child([str(EXPORT), "--help"], tmp_path)
    assert result.returncode == 0, result.stderr
    assert "--data" in result.stdout and "--sha256" in result.stdout
    assert "--locus" in result.stdout and "--output" in result.stdout
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("package,level", [("tools.cohort_tailoring", 1), (None, 0)])
def test_exporter_does_not_mask_nested_sibling_importerror(monkeypatch, package, level):
    code = compile(EXPORT.read_text(encoding="utf-8"), str(EXPORT), "exec")
    original_import = builtins.__import__
    attempts = []
    def nested_failure(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "build_atlas":
            attempts.append((name, level))
            raise ImportError("synthetic-nested-sibling-import-error")
        return original_import(name, globals, locals, fromlist, level)
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr(builtins, "__import__", nested_failure)
    namespace = {"__name__": "offline_import_fixture", "__package__": package, "__file__": str(EXPORT)}
    with pytest.raises(ImportError, match="synthetic-nested-sibling-import-error"):
        exec(code, namespace)
    assert attempts == [("build_atlas", level)]
