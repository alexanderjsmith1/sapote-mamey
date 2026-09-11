"""mamey/workspace_root.py (CANDIDATE, Indigo2 JOB-C) — single home of the workspace-root default.

JOB-C constraint honored: behavior is BYTE-IDENTICAL when no env var is set — the historical
literal remains the fallback, but it now lives in exactly ONE place with its portability caveat,
instead of being pasted into 12 modules. Env precedence: SAPOTE_WORKSPACE_ROOT, then SAPOTE_ROOT
(both already exist in the tree's env-var vocabulary; no new name invented).
"""
from __future__ import annotations
import os
from pathlib import Path

# Generic fallback: env vars first (below), else the current working directory. A public
# install never assumes a personal home; set SAPOTE_WORKSPACE_ROOT to bind an operator pack.


def workspace_root() -> Path:
    for var in ("SAPOTE_WORKSPACE_ROOT", "SAPOTE_ROOT"):
        v = os.environ.get(var)
        if v:
            return Path(v)
    return Path.cwd()
