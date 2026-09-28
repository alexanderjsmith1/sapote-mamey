"""v9.7.444: `mamey phylo-run` must expose and forward every option of tools/run_planned_tree.py.

The CLI forwarded only genome-list, workdir, outgroup, hmm, threads, parallel, the ANI files, signoff and approved.
So a tree started through `mamey_run.py phylo-run` always ran IQ-TREE with -T 1 (the runner's --iqtree-threads
default) and could not set --seed, --tree-spec, --query-tips, --allow-reference-drop or --hmm-sha256.
"""
import importlib.util
import re
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
    for flag in ("--iqtree-threads", "--seed", "--tree-spec", "--query-tips", "--allow-reference-drop", "--hmm-sha256"):
        assert flag not in argv, flag


def test_cli_exposes_every_runner_option():
    runner = (ROOT / "tools" / "run_planned_tree.py").read_text()
    runner_opts = set(re.findall(r'add_argument\(\s*"(--[a-z0-9-]+)"', runner))
    sub = next(a for a in cli.build_parser()._subparsers._group_actions if "phylo-run" in a.choices)
    cli_opts = {o for act in sub.choices["phylo-run"]._actions for o in act.option_strings if o.startswith("--")}
    assert runner_opts, "no runner options found; the pattern no longer matches run_planned_tree.py"
    assert runner_opts - cli_opts == set(), sorted(runner_opts - cli_opts)
