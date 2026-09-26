"""`outgroup_registry.py get-16s` prints a next-step command that phylo_refset.py can parse.

The hint used to say `phylo_refset.py --add-outgroup <genus>`. phylo_refset.py has no such
option; its grammar is `add-outgroup <refs.fasta> --genus <genus> --out <refs_final.fasta>`.
The printed command is parsed with `--help` appended, so nothing is read or written.
"""
import argparse
import importlib.util
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(monkeypatch, tmp_path):
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    spec = importlib.util.spec_from_file_location("outgroup_registry_hint_v97443",
                                                  ROOT / "tools" / "outgroup_registry.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _hint(monkeypatch, tmp_path, capsys, genus="Streptomyces"):
    mod = _load(monkeypatch, tmp_path)
    monkeypatch.setattr(mod, "get_16s", lambda *a, **k: str(tmp_path / "og.fasta"))
    mod.cmd_get16s(argparse.Namespace(genus=genus, scope="genus", out=None, force=False))
    out = capsys.readouterr().out
    line = next(l for l in out.splitlines() if "phylo_refset.py" in l)
    return shlex.split(line[line.index("phylo_refset.py"):])[1:]


def _parses(args):
    proc = subprocess.run([sys.executable, str(ROOT / "tools" / "phylo_refset.py"), *args, "--help"],
                          capture_output=True, text=True, cwd=str(ROOT), env=dict(os.environ))
    return proc.returncode, proc.stderr


def test_printed_add_outgroup_command_parses(monkeypatch, tmp_path, capsys):
    args = _hint(monkeypatch, tmp_path, capsys)
    assert args[0] == "add-outgroup"
    assert "--genus" in args and args[args.index("--genus") + 1] == "Streptomyces"
    rc, err = _parses(args)
    assert rc == 0, err


def test_old_hint_form_is_rejected_by_the_parser():
    rc, _ = _parses(["--add-outgroup", "Streptomyces"])
    assert rc != 0
