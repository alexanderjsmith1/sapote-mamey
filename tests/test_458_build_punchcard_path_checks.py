"""build_punchcard refuses an --out inside a package it reads, and a --gbk-dirs list that does not pair
one-to-one with --packages.

Before: --out could replace a package's manifest.json, and a short --gbk-dirs list silently paired the
wrong folders with the wrong packages.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "build_punchcard.py"


def _pkg(tmp_path, name):
    p = tmp_path / name
    p.mkdir()
    (p / "manifest.json").write_text(json.dumps({"strain": name, "bgcs": []}))
    return p


def _run(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True)


def test_out_inside_a_package_is_refused_and_the_manifest_kept(tmp_path):
    a = _pkg(tmp_path, "S1")
    before = (a / "manifest.json").read_bytes()
    r = _run("--packages", a, "--out", a / "manifest.json")
    assert r.returncode != 0 and "outside the packages" in r.stderr
    assert (a / "manifest.json").read_bytes() == before


def test_short_gbk_dirs_list_is_refused(tmp_path):
    a, b = _pkg(tmp_path, "S1"), _pkg(tmp_path, "S2")
    r = _run("--packages", a, b, "--gbk-dirs", tmp_path, "--out", tmp_path / "card.md")
    assert r.returncode != 0 and "one per package" in r.stderr
    assert not (tmp_path / "card.md").exists()
