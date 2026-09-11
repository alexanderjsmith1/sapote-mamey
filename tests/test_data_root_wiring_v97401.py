"""Regression tests for governed phylogeny data-root resolution.

All fixtures are synthetic. The tests exercise real shell sourcing and fresh Python subprocesses,
including directories with spaces and an inherited test-process environment.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


TOOLS = Path(__file__).resolve().parents[1] / "tools"
REL = Path("strain_data/_ANTISMASH_CANONICAL/STRAIN_METADATA_CONSOLIDATED.tsv")


def _clean_env(**updates: str) -> dict[str, str]:
    env = dict(os.environ)
    env.pop("MAMEY_DATA_ROOT", None)
    env.update(updates)
    return env


def _source_env(cwd: Path, project_root: Path, env_root: Path | None = None) -> dict[str, str]:
    env = _clean_env(PROJECT_ROOT=str(project_root))
    if env_root is not None:
        env["MAMEY_DATA_ROOT"] = str(env_root)
    proc = subprocess.run(
        ["bash", "-c", 'source "$1" >/dev/null 2>&1; env -0', "bash", str(TOOLS / "gtotree_env.sh")],
        cwd=cwd,
        env=env,
        capture_output=True,
        check=True,
    )
    return {
        key.decode(): value.decode()
        for item in proc.stdout.split(b"\0")
        if item
        for key, value in [item.split(b"=", 1)]
    }


def _module_root(module: str, cwd: Path, env: dict[str, str]) -> str:
    code = (
        f"import sys; sys.path.insert(0, {str(TOOLS)!r}); "
        f"import {module} as target; print(target.ROOT)"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _write_table(root: Path) -> None:
    table = root / REL
    table.parent.mkdir(parents=True)
    table.write_text("strain\ttaxonomy\tsource\nSYN-001\tStreptomyces sp.\tsynthetic\n", encoding="utf-8")


def test_operator_override_with_spaces_wins_and_is_exported(tmp_path: Path) -> None:
    launch = tmp_path / "launch"
    project = tmp_path / "portable code"
    override = tmp_path / "governed data override"
    launch.mkdir()
    project.mkdir()
    override.mkdir()
    _write_table(launch)
    sourced = _source_env(launch, project, override)
    assert sourced["MAMEY_DATA_ROOT"] == str(override)


def test_valid_launch_root_drives_both_downstream_tools(tmp_path: Path) -> None:
    launch = tmp_path / "workspace with spaces"
    project = tmp_path / "portable code without data"
    launch.mkdir()
    project.mkdir()
    _write_table(launch)
    sourced = _source_env(launch, project)
    assert sourced["MAMEY_DATA_ROOT"] == str(launch)
    for module in ("phylo_preflight", "phylo_postflight"):
        assert _module_root(module, launch, sourced) == str(launch)


def test_project_root_is_used_only_when_its_table_exists(tmp_path: Path) -> None:
    launch = tmp_path / "bare launch"
    project = tmp_path / "portable code with governed data"
    launch.mkdir()
    project.mkdir()
    _write_table(project)
    sourced = _source_env(launch, project)
    assert sourced["MAMEY_DATA_ROOT"] == str(project)


def test_invalid_default_is_not_exported_or_allowed_to_mask_fallback(tmp_path: Path) -> None:
    launch = tmp_path / "bare launch"
    project = tmp_path / "portable code without data"
    launch.mkdir()
    project.mkdir()
    sourced = _source_env(launch, project)
    assert "MAMEY_DATA_ROOT" not in sourced
    for module in ("phylo_preflight", "phylo_postflight"):
        assert _module_root(module, launch, sourced) == str(TOOLS.parent)


def test_resolution_does_not_search_above_the_current_directory(tmp_path: Path) -> None:
    parent = tmp_path / "parent with unrelated table"
    child = parent / "nested launch"
    project = tmp_path / "portable code"
    child.mkdir(parents=True)
    project.mkdir()
    _write_table(parent)
    sourced = _source_env(child, project)
    assert "MAMEY_DATA_ROOT" not in sourced
    for module in ("phylo_preflight", "phylo_postflight"):
        assert _module_root(module, child, sourced) == str(TOOLS.parent)
