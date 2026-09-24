"""Resolve an operator workspace without assuming a personal home directory.

Explicit SAPOTE_WORKSPACE_ROOT takes precedence over SAPOTE_ROOT. Otherwise walk
from the current directory to the nearest workspace asset marker; if none exists,
retain the current directory as the generic fallback.
"""
from __future__ import annotations
import os
from pathlib import Path

# A public install never assumes a personal home. Explicit environment overrides
# bind an operator pack; marker discovery supports bundles nested inside that pack.


def workspace_root() -> Path:
    for var in ("SAPOTE_WORKSPACE_ROOT", "SAPOTE_ROOT"):
        v = os.environ.get(var)
        if v:
            return Path(v)
    return _walk_to_workspace_marker(Path.cwd())


# Markers that only a WORKSPACE (never a CODE bundle) contains. NOT OFFICIAL_DATA: the bundle ships
# its own OFFICIAL_DATA/ (outgroup cache, registries), so that name cannot tell the two apart.
# A bundle nested inside its own workspace is the normal layout, so when the cwd is the bundle we
# climb until one of these appears; if none does, the historical behaviour (cwd) is kept byte-identical.
WORKSPACE_MARKERS = ("miniconda3", "blast_dbs", "Tools/databases")


def _walk_to_workspace_marker(start: Path) -> Path:
    here = start.resolve()
    for candidate in (here, *here.parents):
        if any((candidate / m).is_dir() for m in WORKSPACE_MARKERS):
            return candidate
    return start
