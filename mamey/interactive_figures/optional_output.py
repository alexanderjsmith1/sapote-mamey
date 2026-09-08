"""Small collision-safe output transaction for explicit optional figure tools."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


class OutputRefusal(ValueError):
    """Raised before output creation when a requested destination is unsafe."""


def logical_artifact_locator(root: Path, artifact_name: str) -> str:
    """Return a portable receipt locator for a published direct child artifact."""
    if not isinstance(artifact_name, str) or not artifact_name or Path(artifact_name).name != artifact_name:
        raise OutputRefusal("artifact name must be a simple filename")
    return f"{root.name}/{artifact_name}"


def _checked_output_root(output_dir: str | Path) -> tuple[Path, Path]:
    requested = Path(output_dir).expanduser()
    if requested.name in {"", ".", ".."}:
        raise OutputRefusal("output directory must name a new child directory")
    if requested.is_symlink():
        raise OutputRefusal("output directory must not be a symlink")
    if requested.exists():
        raise OutputRefusal("output directory already exists; refusing replacement")
    parent = requested.parent.resolve(strict=False)
    parent.mkdir(parents=True, exist_ok=True)
    root = (parent / requested.name).resolve(strict=False)
    if root.parent != parent:
        raise OutputRefusal("output directory escapes its resolved parent")
    return parent, root


def write_output_bundle(output_dir: str | Path, artifacts: Mapping[str, bytes]) -> Path:
    """Atomically publish named byte artifacts into a new output directory.

    The caller supplies an output directory that must not exist.  Artifacts are
    first written into a same-parent staging directory, then published through
    one atomic directory rename.  This makes a collision or write refusal leave
    no partial final output directory.
    """
    if not artifacts:
        raise OutputRefusal("refusing an empty output bundle")
    parent, root = _checked_output_root(output_dir)
    staging = parent / f".{root.name}.staging"
    if staging.exists() or staging.is_symlink():
        raise OutputRefusal("output staging directory already exists; refusing replacement")
    staging.mkdir()
    try:
        for name, payload in artifacts.items():
            if not isinstance(name, str) or not name or Path(name).name != name:
                raise OutputRefusal("artifact name must be a simple filename")
            if not isinstance(payload, bytes):
                raise OutputRefusal("artifact payload must be bytes")
            target = (staging / name).resolve(strict=False)
            if target.parent != staging:
                raise OutputRefusal("artifact path escapes output staging directory")
            target.write_bytes(payload)
        os.replace(staging, root)
    except Exception:
        for child in staging.iterdir() if staging.exists() else ():
            if child.is_file() or child.is_symlink():
                child.unlink()
        if staging.exists():
            staging.rmdir()
        raise
    return root
