"""Released-v1 CLI forwarding, with explicit deferred governed-v2 controls.

The shared runner remains the admission/execution owner. Its governed-v2 options
are intentionally unavailable here while unreleased integration is deferred.
"""
import ast
import importlib.util
import subprocess
import sys

import pytest
from pathlib import Path
from types import SimpleNamespace

from mamey import cli

ROOT = Path(__file__).resolve().parents[1]
BASE = ["phylo-run", "--genome-list", "/abs/g.txt", "--workdir", "/abs/w", "--outgroup", "OG"]


def _forwarded(monkeypatch, extra):
    captured = {}
    monkeypatch.setattr(importlib.util, "spec_from_file_location",
                        lambda name, path: SimpleNamespace(loader=SimpleNamespace(exec_module=lambda m: None)))
    monkeypatch.setattr(importlib.util, "module_from_spec",
                        lambda spec: SimpleNamespace(main=lambda argv: captured.setdefault("argv", argv) and 0))
    args = cli.build_parser().parse_args(BASE + extra)
    assert args.func(args) == 0
    return captured["argv"]


def test_runner_options_reach_the_runner(monkeypatch):
    argv = _forwarded(monkeypatch, ["--iqtree-threads", "4", "--seed", "7", "--tree-spec", "/abs/spec.json",
                                    "--query-tips", "A,B", "--allow-reference-drop", "--hmm-sha256", "ab12", "--approved"])
    pairs = dict(zip(argv, argv[1:]))
    assert pairs["--iqtree-threads"] == "4"
    assert pairs["--seed"] == "7"
    assert pairs["--tree-spec"] == "/abs/spec.json"
    assert pairs["--query-tips"] == "A,B"
    assert pairs["--hmm-sha256"] == "ab12"
    assert "--allow-reference-drop" in argv and "--approved" in argv


def test_unset_options_leave_the_runner_defaults_alone(monkeypatch):
    argv = _forwarded(monkeypatch, ["--approved"])
    for flag in ("--iqtree-threads", "--seed", "--tree-spec", "--query-tips", "--allow-reference-drop", "--hmm-sha256",
                 "--gtotree-bin", "--iqtree-bin", "--mapping-file"):
        assert flag not in argv, flag


# This exact deferral is a reviewed product-scope decision, not a catch-all
# `--gtotree-*` exception: any newly added runner option must receive review.
DEFERRED_GOVERNED_V2_OPTIONS = {
    "--plan-dir",
    "--gtotree-runtime-manifest", "--gtotree-runtime-environment",
    "--gtotree-runtime-source", "--gtotree-runtime-probe-dir",
    "--gtotree-rss-limit", "--gtotree-min-disk", "--gtotree-timeout",
    "--gtotree-cpu-budget",
}


def _source_options(relative_path, function):
    tree = ast.parse((ROOT / relative_path).read_text())
    owner = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function)
    return {
        argument.value
        for node in ast.walk(owner)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_argument"
        for argument in node.args
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str)
        and argument.value.startswith("--")
    }


def _cli_phylo_options():
    sub = next(a for a in cli.build_parser()._subparsers._group_actions if "phylo-run" in a.choices)
    return {o for act in sub.choices["phylo-run"]._actions for o in act.option_strings
            if o.startswith("--") and o != "--help"}


def _option_gaps(runner_options, cli_options):
    admitted = runner_options - DEFERRED_GOVERNED_V2_OPTIONS
    return admitted - cli_options, cli_options - admitted


def test_cli_exposes_every_released_runner_option_and_no_governed_v2_controls():
    # Include helper-created options that the old quote-specific regex missed.
    runner_options = (_source_options("tools/run_planned_tree.py", "main")
                      | _source_options("tools/_gtotree_runtime.py", "add_runtime_arguments"))
    assert DEFERRED_GOVERNED_V2_OPTIONS <= runner_options
    assert {"--gtotree-bin", "--iqtree-bin", "--mapping-file"} <= _cli_phylo_options()
    assert _option_gaps(runner_options, _cli_phylo_options()) == (set(), set())


def test_option_contract_detects_new_unreviewed_runner_option_and_missing_released_selector():
    runner_options = (_source_options("tools/run_planned_tree.py", "main")
                      | _source_options("tools/_gtotree_runtime.py", "add_runtime_arguments"))
    assert _option_gaps(runner_options | {"--new-unreviewed-option"}, _cli_phylo_options())[0] == {"--new-unreviewed-option"}
    assert _option_gaps(runner_options, _cli_phylo_options() - {"--mapping-file"})[0] == {"--mapping-file"}
    assert _option_gaps(runner_options, _cli_phylo_options() | {"--plan-dir"})[1] == {"--plan-dir"}


def test_selected_released_binaries_and_mapping_reach_existing_runner_exactly(monkeypatch):
    # Paths are argv elements, never shell expressions. Full mapped labels stay
    # in the selected TSV; the front door does not rewrite or infer identities.
    selected = {
        "--gtotree-bin": "/abs/selected tools/GToTree",
        "--iqtree-bin": "/abs/selected tools/iqtree2",
        "--mapping-file": "/abs/selected maps/exact labels.tsv",
    }
    extra = [item for pair in selected.items() for item in pair] + ["--approved"]
    argv = _forwarded(monkeypatch, extra)
    for flag, value in selected.items():
        assert argv.count(flag) == 1
        assert argv[argv.index(flag) + 1] == value
    assert not (DEFERRED_GOVERNED_V2_OPTIONS & set(argv))


@pytest.mark.parametrize("flag", sorted(DEFERRED_GOVERNED_V2_OPTIONS))
def test_governed_v2_controls_refuse_at_cli_parse_before_runner_load(monkeypatch, flag):
    monkeypatch.setattr(importlib.util, "spec_from_file_location",
                        lambda *a, **k: pytest.fail("runner loaded before CLI parse refusal"))
    with pytest.raises(SystemExit) as refused:
        cli.build_parser().parse_args(BASE + [flag, "unselected"])
    assert refused.value.code == 2


def test_real_cli_to_runner_still_refuses_without_explicit_approval(tmp_path):
    # The actual shared runner checks approval before paths/probes/output. No
    # external software is present or invoked by this negative integration case.
    out = tmp_path / "absent"
    command = [sys.executable, str(ROOT / "mamey_run.py"), "phylo-run",
               "--genome-list", str(tmp_path / "missing-genomes.txt"),
               "--workdir", str(out), "--outgroup", "OG",
               "--gtotree-bin", str(tmp_path / "missing-GToTree"),
               "--iqtree-bin", str(tmp_path / "missing-iqtree"),
               "--mapping-file", str(tmp_path / "missing-mapping.tsv")]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=20)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "requires explicit human approval" in result.stderr
    assert not out.exists()


@pytest.mark.parametrize("flag", ("--gtotree-bin", "--iqtree-bin", "--mapping-file"))
@pytest.mark.parametrize("value", ("", "   "))
def test_explicit_empty_selection_refuses_before_runner_load(monkeypatch, flag, value):
    monkeypatch.setattr(importlib.util, "spec_from_file_location",
                        lambda *a, **k: pytest.fail("runner loaded before invalid-selection refusal"))
    args = cli.build_parser().parse_args(BASE + [flag, value, "--approved"])
    assert args.func(args) == 2
