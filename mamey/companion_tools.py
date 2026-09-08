"""Companion-tools registry loader + presence probe (v9.7.331, AMBER).

External companion tools (antiSMASH upstream, BiG-SCAPE, clinker, cblaster, GECCO,
pyGenomeViz, pyCirclize, prodigal, MUSCLE, IQ-TREE, fastANI, GToTree, NCBI datasets,
skani, GTDB-Tk) are what the *analysis* workflow runs downstream of a sealed Mamey
package. They are **DETECTED, NOT BUNDLED**: the deterministic Mamey core installs and
runs offline with none of them present. This module reads the machine-readable registry
(mamey/data/companion_tools.json), and `probe_tools()` runs each tool's detection command
and reports present/missing + an install hint — WITHOUT ever failing when a tool is absent.

The registry data lives in mamey/data/companion_tools.json (the single source of truth).
mamey/cli.py::doctor_command consumes probe_tools(); tests/test_companion_tools_registry.py
guards the schema. A tool documented only in a chat session can be lost; a tool documented
here persists and transfers to a new user with both download AND usage instructions
(docs/companion_tools.md).
"""
from __future__ import annotations

import json
import pathlib
import platform
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import Optional

_REGISTRY_PATH = pathlib.Path(__file__).resolve().parent / "data" / "companion_tools.json"

# categories a well-formed entry may declare (mirrors the registry's `categories` list)
VALID_CATEGORIES = {
    "upstream-input", "BGC-detection", "GCF-clustering",
    "synteny", "figure", "phylogenomics",
}
VALID_REQUIREMENTS = {"REQUIRED-upstream", "optional", "on-request"}


@dataclass(frozen=True)
class CompanionTool:
    id: str
    name: str
    category: str
    requirement: str
    purpose: str
    consumes: str
    produces: str
    detection_command: str
    expected_version: str
    network_required: bool
    reference_db_required: bool
    install: tuple = field(default_factory=tuple)
    verify_flag: bool = False


@dataclass(frozen=True)
class ToolProbe:
    tool: CompanionTool
    present: bool
    detected_version: Optional[str]
    install_hint: str


def load_registry(path: pathlib.Path | None = None) -> list[CompanionTool]:
    """Load and validate the companion-tools registry. Raises on a malformed file so a
    typo can't silently drop a tool from `mamey doctor --companions`."""
    p = path or _REGISTRY_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("schema_version") != "1.0":
        raise ValueError(f"companion_tools.json: unexpected schema_version {data.get('schema_version')!r}")
    tools: list[CompanionTool] = []
    seen: set[str] = set()
    for t in data["tools"]:
        tid = t["id"]
        if tid in seen:
            raise ValueError(f"duplicate companion tool id in registry: {tid}")
        seen.add(tid)
        cat = t["category"]
        if cat not in VALID_CATEGORIES:
            raise ValueError(f"companion tool {tid}: unknown category {cat!r}")
        req = t["requirement"]
        if req not in VALID_REQUIREMENTS:
            raise ValueError(f"companion tool {tid}: unknown requirement {req!r}")
        det = t["detection"]
        tools.append(CompanionTool(
            id=tid,
            name=t["name"],
            category=cat,
            requirement=req,
            purpose=t["purpose"],
            consumes=t["consumes"],
            produces=t["produces"],
            detection_command=det["command"],
            expected_version=str(det.get("expected_version", "")),
            verify_flag=bool(det.get("verify_flag", False)),
            network_required=bool(t.get("network_required", False)),
            reference_db_required=bool(t.get("reference_db_required", False)),
            install=tuple(t.get("install", ())),
        ))
    return tools


def _current_platform() -> str:
    sysname = platform.system()
    if sysname == "Darwin":
        return "macos-arm64" if platform.machine() in ("arm64", "aarch64") else "macos"
    if sysname == "Linux":
        return "linux"
    if sysname == "Windows":
        return "windows"
    return sysname.lower()


def install_hint_for(tool: CompanionTool, plat: str | None = None) -> str:
    """Best-matching install command for the given platform (falls back to 'any')."""
    plat = plat or _current_platform()
    entries = list(tool.install)
    chosen = None
    for e in entries:
        if e.get("platform") == plat:
            chosen = e
            break
    if chosen is None:
        for e in entries:
            if e.get("platform") == "any":
                chosen = e
                break
    if chosen is None and entries:
        chosen = entries[0]
    if not chosen:
        return "(no install recipe recorded)"
    hint = chosen.get("command", "")
    if chosen.get("reference_db"):
        hint += f"   [DB: {chosen['reference_db']}]"
    return hint


def _run_detection(command: str, timeout: float = 8.0) -> tuple[bool, Optional[str]]:
    """Run a detection command; return (present, version_string_or_None). Never raises:
    a missing tool, non-zero exit, or timeout all resolve to (False, None) / best-effort."""
    try:
        proc = subprocess.run(
            shlex.split(command),
            capture_output=True, text=True, timeout=timeout,
        )
    except FileNotFoundError:
        return False, None
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return False, None
    out = ((proc.stdout or "") + " " + (proc.stderr or "")).strip()
    # Present if the command ran at all (exit 0), or printed a recognizable version line.
    present = proc.returncode == 0 or bool(out)
    version = out.splitlines()[0].strip() if out else None
    if not present:
        return False, None
    return True, version


def probe_tools(registry: list[CompanionTool] | None = None,
                run_detection: bool = True) -> list[ToolProbe]:
    """Probe every registered tool. Optional (`run_detection=False`) skips subprocess calls
    and just reports the registry with install hints — used by tests/offline contexts."""
    reg = registry if registry is not None else load_registry()
    plat = _current_platform()
    probes: list[ToolProbe] = []
    for tool in reg:
        if run_detection:
            present, version = _run_detection(tool.detection_command)
        else:
            present, version = False, None
        probes.append(ToolProbe(
            tool=tool,
            present=present,
            detected_version=version,
            install_hint=install_hint_for(tool, plat),
        ))
    return probes
