"""Record optional suite tools without executing them or assuming a local install."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil


OPTIONAL_TOOLS = ("node", "pdfinfo", "Rscript", "hmmbuild", "diamond", "blastp")
TOOL_DIRECTORY_VARIABLE = "SAPOTE_SUITE_TOOL_DIR"


def declared_environment(environment: dict[str, str]) -> dict[str, str]:
    """Prepend only an explicitly supplied absolute directory; preserve the caller."""
    result = dict(environment)
    directory = result.get(TOOL_DIRECTORY_VARIABLE)
    if directory is not None:
        path = Path(directory)
        if not path.is_absolute() or not path.is_dir():
            raise ValueError("SAPOTE_SUITE_TOOL_DIR must name an existing absolute directory")
        directory = str(path.resolve(strict=True))
        result[TOOL_DIRECTORY_VARIABLE] = directory
        entries = result.get("PATH", os.defpath).split(os.pathsep)
        result["PATH"] = os.pathsep.join([directory, *(p for p in entries if p != directory)])
    return result


def suite_tool_header(environment: dict[str, str], cwd: Path) -> dict:
    """Measure PATH resolution and binary bytes only; missing tools stay explicit."""
    path = environment.get("PATH", os.defpath)
    # Relative and empty PATH entries refer to the child's cwd, not this process.
    search = os.pathsep.join(str((cwd / entry).resolve()) if not Path(entry).is_absolute()
                             else entry for entry in path.split(os.pathsep))
    tools = []
    for name in OPTIONAL_TOOLS:
        located = shutil.which(name, path=search)
        row = {"name": name, "status": "MISSING", "path": None, "target": None,
               "sha256": None}
        if located is not None:
            target = Path(located).resolve(strict=True)
            digest = hashlib.sha256()
            with target.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            row.update(status="PRESENT", path=located, target=str(target), sha256=digest.hexdigest())
        tools.append(row)
    return {"schema": "sapote-mamey.suite-tool-environment.v1", "cwd": str(cwd),
            "path": path, "declared_tool_directory": environment.get(TOOL_DIRECTORY_VARIABLE),
            "tools": tools, "missing_optional_tools": [r["name"] for r in tools if r["status"] == "MISSING"],
            "scope": "PATH resolution and content hashes; binary versions and runtime behavior untested"}
