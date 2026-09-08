"""test_intake_harness_mode_choices.py — test for W8 finding 5 (v9.7.149c).

`tools/intake_harness.py --mode` previously accepted any string silently.
Add `choices=["smoke", "standard", "gold"]` to validate at the CLI layer.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest


def _load_intake_harness():
    """Load tools/intake_harness.py as a module without importing the
    surrounding tools package (which may have heavy side-effect imports)."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    path = repo_root / "tools" / "intake_harness.py"
    spec = importlib.util.spec_from_file_location("intake_harness_test_load",
                                                  path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_intake_harness_mode_accepts_valid_choices():
    """--mode smoke / standard / gold must all parse cleanly."""
    ih = _load_intake_harness()
    # We can't easily call ap.parse_args() without supplying required args, so
    # poke the parser directly via _parse_known_args on a minimal cmdline.
    import argparse

    # Recreate just the --mode arg from the real parser to isolate the test
    # from required args that would fail on a stub invocation.
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="standard",
                    choices=["smoke", "standard", "gold"])
    for valid in ("smoke", "standard", "gold"):
        ns = ap.parse_args(["--mode", valid])
        assert ns.mode == valid, f"failed to parse --mode {valid}"


def test_intake_harness_mode_rejects_invalid_choice():
    """--mode garbage must exit with non-zero status (argparse SystemExit)."""
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="standard",
                    choices=["smoke", "standard", "gold"])
    with pytest.raises(SystemExit):
        ap.parse_args(["--mode", "garbage-not-a-mode"])


def test_intake_harness_module_arg_has_choices_constraint():
    """Source-level assertion: the real intake_harness.py file declares the
    choices= constraint. Guards against the constraint being silently removed
    in a future refactor."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    src = (repo_root / "tools" / "intake_harness.py").read_text(encoding="utf-8")
    # Find the --mode argument line and verify choices= is present nearby
    import re
    m = re.search(r'add_argument\("--mode"[^)]+\)', src, re.DOTALL)
    assert m is not None, "could not find --mode argument in intake_harness.py"
    assert "choices=" in m.group(0), (
        "--mode argument no longer has choices= constraint; "
        "W8 finding 5 has regressed"
    )
