"""v9.7.405 — the generated command catalog must be current and must list every CLI subcommand."""
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "gen_command_catalog.py"
DOC = ROOT / "docs" / "COMMAND_CATALOG.generated.md"


def _load():
    spec = importlib.util.spec_from_file_location("gen_command_catalog", TOOL)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def test_catalog_is_current():
    r = subprocess.run([sys.executable, str(TOOL), "--check"], capture_output=True, text=True,
                       env={"PYTHONDONTWRITEBYTECODE": "1"})
    assert r.returncode == 0, r.stderr


def test_every_subcommand_is_catalogued_and_grouped():
    mod = _load()
    from mamey import cli
    subs = None
    for action in cli.build_parser()._actions:
        if isinstance(action, argparse._SubParsersAction):
            subs = set(action.choices)
    assert subs
    text = DOC.read_text(encoding="utf-8")
    missing = [n for n in subs if f"| `{n}` |" not in text]
    assert not missing, f"subcommands absent from catalog: {missing}"
    grouped = {n for _, _, names in mod.GROUPS for n in names}
    ungrouped = sorted(subs - grouped)
    assert not ungrouped, f"add these to GROUPS in tools/gen_command_catalog.py: {ungrouped}"


def test_mode_b_row_says_not_a_finished_card():
    text = DOC.read_text(encoding="utf-8")
    row = [l for l in text.splitlines() if l.startswith("| `mode-b` |")][0]
    assert "NOT a finished 48-section" in row
