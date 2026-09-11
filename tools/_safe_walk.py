"""_safe_walk.py — shared directory-walk helper that surfaces permission errors instead of
silently swallowing them.

`Path.rglob()` (and plain `os.walk()` without `onerror`) silently swallows a per-directory
`OSError`: if a subdirectory cannot be read, the walk simply yields nothing for that subtree --
no exception, no warning, no signal that part of the tree was never examined. For a validation
gate, that is a silent coverage gap in the gate's own scan, indistinguishable downstream from
"this subtree legitimately has nothing interesting in it."

v9.7.400: found and independently fixed in three release/CI-hygiene gates this round --
`check_no_brace_paths.py`, `check_duplicate_dict_keys.py`, `public_release_audit.py` -- the
same shape each time (reproduced live against each real pristine script: a genuine finding
sitting inside a permission-locked directory silently reported PASS). Consolidated here per
Alex's direction after the third instance turned up, so a future walk-based gate gets the
guarantee for free and a future fix to this shape needs one change instead of N -- the same
"stop writing the Nth independent resolver" lesson already applied to the hooks' shared
`deliverable_hub_root()` reuse this round.
"""
from __future__ import annotations
import os
from pathlib import Path


def safe_walk_files(
    root: Path,
    *,
    suffix: str | None = None,
    skip_dirs: frozenset[str] | None = None,
    include_dirs: bool = False,
) -> tuple[list[Path], list[str]]:
    """Every file under `root`, plus any directory this walk could not descend into.

    Returns `(paths, unreadable_dirs)`: `paths` is every file path found (sorted), filtered by
    `suffix` if given (e.g. `".py"` -- exact suffix match via `str.endswith`, case-sensitive).
    `unreadable_dirs` is the path string of every directory `os.walk` called `onerror` for --
    empty on a fully-readable tree. A caller whose whole job is a validation gate should treat
    ANY non-empty `unreadable_dirs` as its own finding (the scan is incomplete, so the gate
    cannot honestly report PASS) rather than silently proceeding with a partial file list.

    A missing top path (root does not exist at all) returns `([], [])` -- matching
    `Path.rglob()`'s own silent-empty behavior for a missing path, NOT "unreadable directory."
    This distinction must be made explicitly: unlike `rglob()`, `os.walk(..., onerror=...)`
    calls `onerror` even for a missing top path (`FileNotFoundError`) -- without this check, a
    tree simply lacking some legitimately-optional subdirectory (e.g. no `mamey/data/`) would
    falsely report as "unreadable" rather than "not present."

    `skip_dirs`, if given, is a set of directory *names* (not paths) pruned from the walk at
    every depth -- e.g. `{"__pycache__", ".git"}` -- so a skipped directory is never descended
    into at all (more efficient than filtering results afterward, and means it can never
    generate a spurious `unreadable_dirs` entry either, since the walk never touches it).

    `include_dirs`, if true, also includes each directory's own path in `paths` (not just its
    files) -- for a caller checking a property of the PATH itself (e.g. "does any path,
    directory or file, contain a brace character") rather than file contents.
    """
    if not root.exists():
        return [], []

    paths: list[Path] = []
    unreadable_dirs: list[str] = []

    def _onerror(exc: OSError) -> None:
        unreadable_dirs.append(getattr(exc, "filename", None) or str(exc))

    for dirpath, dirnames, filenames in os.walk(root, onerror=_onerror):
        if skip_dirs:
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        names = (dirnames + filenames) if include_dirs else filenames
        for name in names:
            if suffix is not None and not name.endswith(suffix):
                continue
            paths.append(Path(dirpath) / name)
    return sorted(paths), unreadable_dirs
