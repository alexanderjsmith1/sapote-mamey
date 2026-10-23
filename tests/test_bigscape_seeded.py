"""Synthetic launcher contract; external installation smoke is separately skipped."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/bigscape_seeded.py"

def test_route_exists():
    assert TOOL.is_file()

def run(tmp_path, args=(), seed="0", toy=True):
    env = os.environ.copy()
    env.pop("PYTHONHASHSEED", None)
    if seed is not None:
        env["PYTHONHASHSEED"] = seed
    if toy:
        pkg = tmp_path / "big_scape"
        pkg.mkdir(exist_ok=True)
        (pkg / "__init__.py").write_text("")
        (pkg / "__main__.py").write_text("import random, numpy\ndef main():\n print(random.random(), numpy.random.random())\n return 0\n")
        env["PYTHONPATH"] = str(tmp_path)
    return subprocess.run([sys.executable, str(TOOL), *args], env=env, capture_output=True, text=True)

def test_refuses_missing_hash(tmp_path):
    p = run(tmp_path, ["--receipt", str(tmp_path / "refused.json")], seed=None)
    assert p.returncode == 2
    assert "PYTHONHASHSEED" in p.stdout

def test_repeated_draws_and_receipt(tmp_path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    p = run(tmp_path, ["--receipt", str(a), "--numpy-seed", "7", "--random-seed", "9", "--", "cluster", "toy"])
    q = run(tmp_path, ["--receipt", str(b), "--numpy-seed", "7", "--random-seed", "9", "--", "cluster", "toy"])
    assert p.returncode == q.returncode == 0, p.stdout + p.stderr
    assert p.stdout == q.stdout
    receipt = json.loads(a.read_text())
    assert receipt["numpy_seed"] == 7 and receipt["random_seed"] == 9
    assert receipt["argv"] == ["cluster", "toy"]
    assert receipt["status"] == "EXITED" and receipt["exit_code"] == 0
    assert receipt["hash_seed"] == "0"

def test_override_is_receipted(tmp_path):
    receipt = tmp_path / "override.json"
    p = run(tmp_path, ["--allow-unseeded", "--receipt", str(receipt)], seed=None)
    assert p.returncode == 0, p.stdout + p.stderr
    assert json.loads(receipt.read_text())["allow_unseeded"] is True

def test_receipt_not_overwritten(tmp_path):
    receipt = tmp_path / "keep.json"
    receipt.write_text("original")
    assert run(tmp_path, ["--receipt", str(receipt)]).returncode != 0
    assert receipt.read_text() == "original"

def test_invalid_seed(tmp_path):
    assert run(tmp_path, ["--numpy-seed", "-1"]).returncode == 2

@pytest.mark.skipif(importlib.util.find_spec("big_scape") is None, reason="BiG-SCAPE absent; no installation permitted")
def test_external_help_smoke(tmp_path):
    p = run(tmp_path, ["--receipt", str(tmp_path / "help.json"), "--", "--help"], toy=False)
    assert p.returncode == 0
