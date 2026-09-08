#!/usr/bin/env python3
"""_widget_paths.py — shared, de-duplicated default-path resolution for the graduated
Sapote-Mamey analysis/widget deliverable tools (v9.7.349x candidate).

The over-merge inspector, RG-GMCI widget, assembly-line widget, AF lead-board and the
protocluster split-card QC-fixer all keyed off the same hardcoded workspace root and a
handful of derived locations (the `strain_data/` deliverables workspace, the
gene-layer runs dir, the BLASTp Repository). Those constants are collected here so the
five tools share one source of truth instead of re-declaring them.

Nothing here reads or writes anything; it only builds paths. Every tool accepts a
`--root` (or more specific) override on the command line, so the defaults below are just
the documented locations — override them for any other workspace. The default root can
also be set with the ``SAPOTE_WORKSPACE_ROOT`` environment variable.

Stdlib-only. No engine imports, no scoring, no side effects.
"""
from __future__ import annotations
import os

# Documented default deliverables-workspace root (the top-level sapote_workspace folder,
# per the project CLAUDE.md). Override with --root on any tool or SAPOTE_WORKSPACE_ROOT.
ROOT_DEFAULT = os.environ.get(
    "SAPOTE_WORKSPACE_ROOT", os.getcwd())


def master_dir(root: str = ROOT_DEFAULT) -> str:
    """The `strain_data/` deliverables workspace under the given root."""
    return os.path.join(root, "strain_data")


def runs_root(root: str = ROOT_DEFAULT) -> str:
    """The gene-layer working runs directory (sealed per-strain packages)."""
    return os.path.join(master_dir(root), "gene_layer_working_2026-07-31", "runs")


def blastp_repo(root: str = ROOT_DEFAULT) -> str:
    """The BLASTp Repository (per-strain/per-BGC nr top-hit CSVs)."""
    return os.path.join(root, "BLASTp Repository")


def module_dir(name: str, root: str = ROOT_DEFAULT) -> str:
    """A named `_*_MODULE` folder under strain_data (default output home)."""
    return os.path.join(master_dir(root), name)
