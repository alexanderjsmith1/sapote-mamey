"""--genus-color is the main flag (--genus-colour stays as a hidden alias); help and caption text use American spelling."""
import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BRITISH = re.compile(r"colou?r(?<!color)|\bgrey\b|labelling|labelled", re.I)


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class _Stop(Exception):
    pass


_REAL_PARSE_ARGS = argparse.ArgumentParser.parse_args


def _parsed(monkeypatch, main, argv):
    """Run main(argv) only as far as its parse_args call and return the Namespace."""
    box = {}

    def grab(self, args=None, namespace=None):
        box["ns"] = _REAL_PARSE_ARGS(self, args, namespace)
        raise _Stop

    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", grab)
    with pytest.raises(_Stop):
        main(argv)
    return box["ns"]


def _help(tool, *prefix):
    out = subprocess.run([sys.executable, str(ROOT / "tools" / tool), *prefix, "--help"],
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-400:]
    return out.stdout


def test_blastp_identity_both_flag_spellings_set_the_same_value(monkeypatch):
    pytest.importorskip("matplotlib")
    mod = _load("bif_459", "tools/blastp_identity_figures.py")
    base = ["--root", "/x", "--out", "/y", "--genomes", "/z", "--store", "/s"]
    new = _parsed(monkeypatch, mod.main, base + ["--genus-color", "Streptomyces=#112233", "--genus-color", "Kribbella=#445566"])
    old = _parsed(monkeypatch, mod.main, base + ["--genus-colour", "Streptomyces=#112233", "--genus-colour", "Kribbella=#445566"])
    assert new.genus_colour == old.genus_colour == ["Streptomyces=#112233", "Kribbella=#445566"]


def test_max4_render_both_flag_spellings_set_the_same_value(monkeypatch):
    mod = _load("m4_459", "tools/max4_tree_figure.py")
    base = ["render", "--tree", "t", "--metadata", "m", "--out", "o"]
    new = _parsed(monkeypatch, mod.main, base + ["--genus-color", "Streptomyces=0f4c5c"])
    old = _parsed(monkeypatch, mod.main, base + ["--genus-colour", "Streptomyces=0f4c5c"])
    assert new.genus_colour == old.genus_colour == ["Streptomyces=0f4c5c"]


def test_old_spelling_is_hidden_and_new_spelling_is_listed():
    for tool, prefix in (("blastp_identity_figures.py", ()), ("max4_tree_figure.py", ("render",))):
        text = _help(tool, *prefix)
        assert "--genus-color" in text, tool
        assert "--genus-colour" not in text, tool


def test_help_text_of_the_named_tools_is_american():
    for tool in ("taxonomy_T05_figures.py", "novel_and_active_figure.py", "figure_render_qc.py"):
        text = _help(tool)
        assert not BRITISH.findall(text), (tool, BRITISH.findall(text))
    assert "labeling rule" in _help("figure_render_qc.py")
    for tool, prefix in (("blastp_identity_figures.py", ()), ("max4_tree_figure.py", ("render",))):
        for line in _help(tool, *prefix).splitlines():
            if "genus-color" in line or "per-paper" in line:
                assert not BRITISH.findall(line), (tool, line)


def test_cohort_captions_are_american():
    pytest.importorskip("matplotlib")
    src = (ROOT / "mamey" / "cohort_figures.py").read_text(encoding="utf-8")
    import tokenize
    import io
    bad = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.STRING and not tok.string.startswith(('"""', "'''")) and BRITISH.search(tok.string):
            bad.append((tok.start[0], tok.string[:70]))
    assert not bad, bad
