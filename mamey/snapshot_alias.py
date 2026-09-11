"""snapshot_alias.py — load a Project_Memory_Snapshot, following the v9.7.400 alias stub.

Before v9.7.400 the per-strain ``{sid}_Project_Memory_Snapshot.json`` was a VERBATIM re-dump of
``manifest.json`` — every package shipped its entire ``source_scans`` blob twice (measured on a
96-BGC strain: 20,882,853 identical bytes in each file, ~40% of the sealed package). The writer
now emits a small stub::

    {"schema": "project_memory_snapshot_alias_v1", "alias_of": "manifest.json", ...}

and readers resolve the stub to the manifest in the same directory. ``load_snapshot`` is the one
loader that handles BOTH generations: a pre-.400 full snapshot is returned as-is; a stub is
transparently replaced by the manifest content (which is exactly what the full snapshot used to
be). Claim-safety: packaging/provenance mechanics only — no scientific content changes.
"""
from __future__ import annotations

import json
import os

__all__ = ["load_snapshot", "resolve_alias"]


def resolve_alias(data: dict, snapshot_path: str) -> dict:
    """If *data* is an alias stub, return the referenced manifest's content; else *data*.

    Fail-open: when the stub's target is missing/unreadable the stub itself is returned —
    an honest degraded read, never an exception a caller didn't have before.
    """
    if isinstance(data, dict) and data.get("alias_of") and "source_scans" not in data:
        target = os.path.join(os.path.dirname(str(snapshot_path)) or ".", str(data["alias_of"]))
        if os.path.isfile(target):
            try:
                with open(target, encoding="utf-8") as fh:
                    return json.load(fh)
            except Exception:
                return data
    return data


def load_snapshot(path: str) -> dict:
    """Load a Project_Memory_Snapshot JSON, following an alias stub to manifest.json."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return resolve_alias(data, path)
