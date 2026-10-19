"""Precompiled references must retain the old escaped-regex and word-boundary contract."""
import importlib.util
import os
from pathlib import Path
import re
import sys

import pytest

ROOT = Path(os.environ.get("ATLAS_TEST_SOURCE_ROOT", Path(__file__).resolve().parents[1]))


def load_atlas(path):
    spec = importlib.util.spec_from_file_location("atlas_patterns_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def fixture_root(tmp_path):
    stems = ["alpha", "a+b", "core.v2", "dash-tool", "[core]", "name(1)", "^anchor$", "café", "under_score"]
    for stem in stems:
        write(tmp_path / "tools" / (stem + ".py"), f'"""Declared source purpose for {stem}."""\nVALUE = 1\n')
    write(tmp_path / "mamey/alpha.py", '"""Second source sharing the same stem."""\nfrom . import under_score\n')
    write(tmp_path / "mamey/cli.py", '"""Synthetic CLI source."""\nDECLARED = \'sub.add_parser("alpha")\'\n')
    text = ("alpha (alpha) alpha_suffix prefixalpha alpha0 αalpha alphaβ\n"
            "a+b aab core.v2 coreXv2 name(1) aname(1)b ^anchor$ x^anchor$y\n"
            "[core] x[core]y dash-tool xdash-tool under_score café xcafé caféx\n")
    write(tmp_path / "tests/test_boundary.py", text)
    write(tmp_path / "tests/test_other.py", "prefixalpha alpha_suffix aab coreXv2\n")
    write(tmp_path / "tasks/run.sh", "python alpha.py\nalpha --flag\n  under_score --indented\ncore.v2 --flag\n")
    write(tmp_path / "registry/gate_registry.tsv", "a+b\tgate\nunder_score\tgate\nx[core]y.py\tgate\n")
    write(tmp_path / "_vendor/ignored.sh", "under_score.py\n")
    return tmp_path


def legacy_refs(root, stems):
    tests = {stem: set() for stem in stems}
    shells = {stem: set() for stem in stems}
    for path in (root / "tests").rglob("test_*.py"):
        text = path.read_text()
        for stem in stems:
            if re.search(rf"\b{re.escape(stem)}\b", text):
                tests[stem].add(path.name)
    for path in list(root.rglob("*.sh")) + list(root.rglob("gate_registry.tsv")):
        if any(part in {"__pycache__", "_vendor", "data"} for part in path.parts):
            continue
        text = path.read_text()
        for stem in stems:
            if re.search(rf"\b{re.escape(stem)}\.py\b", text) or re.search(rf"^{re.escape(stem)}\b", text, re.M):
                shells[stem].add(path.name)
    return tests, shells


def test_reference_fields_match_legacy_expressions_exactly(fixture_root, monkeypatch):
    atlas = load_atlas(ROOT / "tools/file_atlas.py")
    monkeypatch.setattr(atlas, "ROOT", fixture_root)
    rows = atlas.build()
    stems = {Path(row["path"]).stem for row in rows}
    tests, shells = legacy_refs(fixture_root, stems)
    for row in rows:
        stem = Path(row["path"]).stem
        assert row["n_tests"] == len(tests[stem])
        assert row["test_refs"] == ";".join(sorted(tests[stem])[:4])
        assert row["shell_refs"] == ";".join(sorted(shells[stem]))
    # Two physical modules with the same stem still share reference membership.
    alpha = [row for row in rows if Path(row["path"]).stem == "alpha"]
    assert len(alpha) == 2
    assert alpha[0]["test_refs"] == alpha[1]["test_refs"]
    assert alpha[0]["shell_refs"] == alpha[1]["shell_refs"]


def test_three_patterns_are_compiled_once_per_unique_stem(fixture_root, monkeypatch):
    atlas = load_atlas(ROOT / "tools/file_atlas.py")
    monkeypatch.setattr(atlas, "ROOT", fixture_root)
    unique = {path.stem for path in atlas._py_files()}
    class Spy:
        M = re.M
        def __init__(self):
            self.compiled = []
            self.dynamic_searches = 0
        def compile(self, pattern, flags=0):
            self.compiled.append((pattern, flags))
            return re.compile(pattern, flags)
        def search(self, *args, **kwargs):
            self.dynamic_searches += 1
            return re.search(*args, **kwargs)
        escape = staticmethod(re.escape)
        findall = staticmethod(re.findall)
    spy = Spy()
    monkeypatch.setattr(atlas, "re", spy)
    atlas.build()
    assert len(spy.compiled) == 3 * len(unique)
    assert len(set(spy.compiled)) == len(spy.compiled)
    assert spy.dynamic_searches == 0
    assert set(spy.compiled) == {
        (pattern, flags)
        for stem in unique
        for pattern, flags in [(rf"\b{re.escape(stem)}\b", 0),
                               (rf"\b{re.escape(stem)}\.py\b", 0),
                               (rf"^{re.escape(stem)}\b", re.M)]
    }


@pytest.mark.parametrize("text,hit", [("alpha", True), ("(alpha)", True),
                                       ("prefixalpha", False), ("alpha_suffix", False),
                                       ("αalpha", False), ("alphaβ", False)])
def test_unicode_and_identifier_word_boundaries_are_preserved(tmp_path, monkeypatch, text, hit):
    atlas = load_atlas(ROOT / "tools/file_atlas.py")
    write(tmp_path / "tools/alpha.py", '"""Only a source description."""\n')
    write(tmp_path / "tests/test_one.py", text)
    monkeypatch.setattr(atlas, "ROOT", tmp_path)
    row, = atlas.build()
    assert row["n_tests"] == int(hit)
    assert row["test_refs"] == ("test_one.py" if hit else "")
