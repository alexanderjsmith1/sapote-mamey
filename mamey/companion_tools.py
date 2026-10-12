"""Companion-tools registry loader + presence probe (v9.7.331, AMBER).

External companion tools (antiSMASH upstream, BiG-SCAPE, clinker, cblaster, GECCO,
pyGenomeViz, pyCirclize, prodigal, MUSCLE, IQ-TREE, fastANI, GToTree, NCBI datasets,
skani, GTDB-Tk) are what the *analysis* workflow runs downstream of a sealed Mamey
package. They are **DETECTED, NOT BUNDLED**: the deterministic Mamey core installs and
runs offline with none of them present. This module reads the machine-readable registry
(mamey/data/companion_tools.json), and `probe_tools()` runs each tool's detection command
and reports local detection, expected-version comparison and review state with an install hint.
None of those states proves workflow execution, model readiness or scientific validation.
Missing companions never fail the offline core.

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
import re
import shutil
import sys
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import Optional

_REGISTRY_PATH = pathlib.Path(__file__).resolve().parent / "data" / "companion_tools.json"

# categories a well-formed entry may declare (mirrors the registry's `categories` list)
VALID_CATEGORIES = {
    "upstream-input", "BGC-detection", "GCF-clustering",
    "synteny", "figure", "phylogenomics", "metabolomics",
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
    detection_kind: str = "local"
    executable_candidates: tuple = field(default_factory=tuple)


@dataclass(frozen=True)
class ToolProbe:
    tool: CompanionTool
    present: bool
    detected_version: Optional[str]
    install_hint: str
    probe_status: str = "NOT_PROBED"
    version_status: str = "NOT_CHECKED"
    review_required: bool = False
    probe_executable: Optional[str] = None
    probe_returncode: Optional[int] = None


@dataclass(frozen=True)
class _Detection:
    status: str
    version: Optional[str] = None
    executable: Optional[str] = None
    returncode: Optional[int] = None


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
        if not isinstance(det, dict) or not isinstance(det.get("verify_flag", False), bool):
            raise ValueError(f"companion tool {tid}: malformed detection/review metadata")
        kind = det.get("kind", "local")
        if not isinstance(kind, str) or kind not in {"local", "manual", "web-or-manual"}:
            raise ValueError(f"companion tool {tid}: unknown detection kind {kind!r}")
        candidates = det.get("executable_candidates", [])
        if (not isinstance(candidates, list) or any(
                not isinstance(x, str) or not x or pathlib.Path(x).name != x
                or any(ch.isspace() or ch in "\\/" for ch in x) for x in candidates)):
            raise ValueError(f"companion tool {tid}: malformed executable candidates")
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
            detection_kind=kind,
            executable_candidates=tuple(candidates),
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


# Conservative best-effort inventory, not a tool-specific interface/runtime gate.
_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_VERSION = re.compile(r"(?<![\w.])v?(\d+\.\d+(?:\.\d+)?)(?!\w|\.\d)")
_DIAGNOSTIC = re.compile(
    r"(?im)\bTraceback\b|\b(?:ModuleNotFoundError|ImportError|SyntaxError|"
    r"RuntimeError|ValueError|OSError|FileNotFoundError):|^\s*(?:ERROR\b|FATAL\b)"
    r"|\b(?:NOT_PROBED|WEB_SERVICE(?:_OR_MANUAL_INSTALL)?)\b"
)
_PROBE_TEXT_LIMIT = 65536


def _detect_command(command: str, timeout: float = 8.0,
                    executable_candidates: tuple = ()) -> _Detection:
    """A zero-exit, unambiguous numeric version is local detection evidence only.

    Bare Python probes use this process's exact invocation executable, preserving
    venv semantics. Native candidates follow their declared order, with no fallback
    after a selected executable fails. Output is not a historical run receipt.
    """
    if not isinstance(command, str) or not command.strip():
        return _Detection("INVALID_COMMAND")
    try:
        argv = shlex.split(command)
        if not argv:
            return _Detection("INVALID_COMMAND")
        if re.fullmatch(r"python(?:\d+(?:\.\d+)?)?", argv[0]):
            executable = sys.executable
        else:
            names = executable_candidates or (argv[0],)
            executable = next((p for name in names if (p := shutil.which(name))), None)
        if not executable:
            return _Detection("MISSING_EXECUTABLE")
        # Do not resolve symlinks: that can change a Python venv invocation.
        executable = str(pathlib.Path(executable).absolute())
        argv[0] = executable
        proc = subprocess.run(argv, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=timeout, check=False)
    except FileNotFoundError:
        return _Detection("MISSING_EXECUTABLE")
    except subprocess.TimeoutExpired:
        return _Detection("PROBE_TIMEOUT")
    except (OSError, ValueError, UnicodeError):
        return _Detection("PROBE_FAILED")
    if proc.returncode != 0:
        return _Detection("PROBE_NONZERO_EXIT", executable=executable, returncode=proc.returncode)
    out = _ANSI.sub("", (proc.stdout or "") + "\n" + (proc.stderr or ""))
    if len(out) > _PROBE_TEXT_LIMIT:
        return _Detection("PROBE_TEXT_LIMIT", executable=executable, returncode=0)
    if _DIAGNOSTIC.search(out):
        return _Detection("PROBE_DIAGNOSTIC_OUTPUT", executable=executable, returncode=0)
    versions = set(_VERSION.findall(out))
    if len(versions) != 1:
        status = "AMBIGUOUS_VERSION" if versions else "NO_VERSION_EVIDENCE"
        return _Detection(status, executable=executable, returncode=0)
    return _Detection("DETECTED", versions.pop(), executable, 0)


def _run_detection(command: str, timeout: float = 8.0) -> tuple[bool, Optional[str]]:
    """Compatibility tuple; richer status is available through probe_tools()."""
    result = _detect_command(command, timeout)
    return result.status == "DETECTED", result.version


def _version_status(version: str | None, expected: str) -> str:
    """Compare registry numeric exact/x families; never eval a policy expression.

    Registry alternatives use `or`. Unrecognized policies stay unverified rather
    than silently admitting arbitrary versions. This is not native compatibility.
    """
    if version is None:
        return "NOT_CHECKED"
    if not expected.strip():
        return "NOT_SPECIFIED"
    alternatives = re.split(r"\s+or\s+", expected.strip())
    parsed = []
    for item in alternatives:
        if not re.fullmatch(r"\d+(?:\.(?:\d+|x)){1,2}", item):
            return "UNRECOGNIZED_POLICY"
        components = item.split(".")
        if "x" in components[:-1]:
            return "UNRECOGNIZED_POLICY"
        parsed.append(components)
    observed = version.split(".")
    for parts in parsed:
        if parts[-1] == "x":
            if len(observed) >= len(parts) and observed[:len(parts)-1] == parts[:-1]:
                return "MATCH"
        elif observed == parts:
            return "MATCH"
    return "MISMATCH"


def probe_tools(registry: list[CompanionTool] | None = None,
                run_detection: bool = True) -> list[ToolProbe]:
    """Local inventory only; web/manual entries never launch a subprocess.

    `present` means a successful local numeric-version probe. Expected-version
    comparison and verify_flag review requirements remain separate and visible.
    No probe authorizes native execution or clears a model/resource/approval gate.
    """
    reg = registry if registry is not None else load_registry()
    plat = _current_platform()
    probes: list[ToolProbe] = []
    for tool in reg:
        if not run_detection:
            result = _Detection("NOT_PROBED")
        elif tool.detection_kind != "local":
            result = _Detection("MANUAL_NOT_PROBED" if tool.detection_kind == "manual"
                                else "WEB_OR_MANUAL_NOT_PROBED")
        else:
            result = _detect_command(tool.detection_command,
                                     executable_candidates=tool.executable_candidates)
        probes.append(ToolProbe(
            tool=tool,
            present=result.status == "DETECTED",
            detected_version=result.version,
            install_hint=install_hint_for(tool, plat),
            probe_status=result.status,
            version_status=_version_status(result.version, tool.expected_version),
            review_required=tool.verify_flag,
            probe_executable=result.executable,
            probe_returncode=result.returncode,
        ))
    return probes


def probe_display_lines(probe: ToolProbe, tag: str = "") -> tuple[str, ...]:
    """One doctor row: inventory, version policy and review do not imply readiness."""
    tool = probe.tool
    if probe.present:
        review = "; REVIEW_REQUIRED" if probe.review_required else ""
        return (f"    ⓘ   {tool.name}{tag}: detected {probe.detected_version}; "
                f"expected {tool.expected_version or 'not specified'}; "
                f"version {probe.version_status}{review}; workflow NOT_ASSESSED",)
    if probe.probe_status in {"MANUAL_NOT_PROBED", "WEB_OR_MANUAL_NOT_PROBED", "NOT_PROBED"}:
        return (f"    ⬚   {tool.name}{tag}: {probe.probe_status}; local installation NOT_ASSESSED",)
    return (f"    ⬚   {tool.name}{tag}: {probe.probe_status}; local detection not established",
            f"         install: {probe.install_hint}")
