"""Tree launchers refuse thread budgets above the project limit of four, before any tool starts."""
import argparse
import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILD_TREE = ROOT / "tools" / "build_tree.sh"


def _build_tree(tmp_path, *args, **env):
    full_env = {**os.environ, **env}
    return subprocess.run(["bash", str(BUILD_TREE), str(tmp_path), *args],
                          capture_output=True, text=True, env=full_env, timeout=60)


@pytest.mark.parametrize("var,value", [("BUILD_TREE_JOBS", "8"), ("BUILD_TREE_THREADS", "16"),
                                       ("BUILD_TREE_JOBS", "0"), ("BUILD_TREE_THREADS", "four")])
def test_build_tree_refuses_out_of_range_budgets(tmp_path, var, value):
    result = _build_tree(tmp_path, **{var: value})
    assert result.returncode == 2
    assert f"TREE_RESOURCE_REFUSED: {var} must be 1, 2, 3 or 4" in result.stderr


@pytest.mark.parametrize("flag", ["-j", "-n", "-M", "-T"])
def test_build_tree_refuses_thread_flags_passed_to_gtotree(tmp_path, flag):
    result = _build_tree(tmp_path, flag, "8")
    assert result.returncode == 2
    assert "TREE_RESOURCE_REFUSED" in result.stderr


def _phylo_place():
    spec = importlib.util.spec_from_file_location("_phylo_place_caps", ROOT / "tools" / "phylo_place.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("value", ["1", "4"])
def test_placement_accepts_one_to_four_threads(value):
    assert _phylo_place()._positive_threads(value) == int(value)


@pytest.mark.parametrize("value", ["5", "64"])
def test_placement_refuses_more_than_four_threads(value):
    with pytest.raises(argparse.ArgumentTypeError, match="at most 4"):
        _phylo_place()._positive_threads(value)
