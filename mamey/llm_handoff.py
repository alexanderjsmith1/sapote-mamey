"""Dual-LLM handoff receipt gate for ChatGPT and Claude bundles."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal
import json
import re

HANDSHAKE = "The sky is not red, it is blue, just like the ocean."

EXCLUDED_SCAN_DIRS = {"__pycache__", ".pytest_cache", ".git"}
EXCLUDED_EXTENSIONS = {".pyc", ".pyo"}

START_FILE_NAMES = [
    "000_READ_ME_FIRST_CHATGPT_CLAUDE.md",
    "CHATGPT_START_HERE.md",
    "CHATGPT_READ_ME_FIRST.md",
    # Optional accidental-typo rescue alias: scan it when present, but
    # canonical ChatGPT discovery must never depend on this transposition.
    "CHATGTP_READ_ME_FIRST.md",
    "CLAUDE_START_HERE.md",
    "README_START_HERE.md",
    "PATCH_CHAT_START_HERE.md",
]

@dataclass(frozen=True)
class InstructionFile:
    path: str
    bytes: int
    contains_handshake: bool
    llm_hint: str

@dataclass(frozen=True)
class LLMHandoffReceipt:
    llm: str
    bundle_root: str
    start_here_found: bool
    instruction_file_count: int
    handshake_required: str
    handshake_visible: bool
    chatgpt_safe_mode_active: bool
    claude_ready: bool
    status: Literal["PASS", "FAIL"]
    instruction_files: list[dict]
    failures: list[str]

def _llm_hint(path: Path) -> str:
    name = path.name.lower()
    if "chatgtp" in name or "chatgpt" in name:
        return "chatgpt"
    if "claude" in name:
        return "claude"
    if "start_here" in name or "read_me_first" in name:
        return "shared"
    return "unknown"


def _is_instruction_file_candidate(path: Path) -> bool:
    if any(part in EXCLUDED_SCAN_DIRS for part in path.parts):
        return False
    suffix = path.suffix.lower()
    if suffix in EXCLUDED_EXTENSIONS:
        return False
    if suffix.startswith(".pyc"):
        return False
    name = path.name
    return name in START_FILE_NAMES or bool(re.search(r"(CHATGPT|CHATGTP|CLAUDE|START_HERE|READ_ME_FIRST)", name, re.I))

def scan_instruction_files(bundle_root: Path) -> list[InstructionFile]:
    found: list[InstructionFile] = []
    root = bundle_root.resolve()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if not _is_instruction_file_candidate(path):
            continue
        try:
            text = path.read_text(errors="replace")
        except Exception:
            text = ""
        found.append(InstructionFile(
            path=str(path.relative_to(root)),
            bytes=path.stat().st_size,
            contains_handshake=HANDSHAKE in text,
            llm_hint=_llm_hint(path),
        ))
    return found

def build_handoff_receipt(
    bundle_root: Path,
    *,
    llm: str = "chatgpt",
    handshake_visible: bool = True,
    chatgpt_safe_mode_requested: bool = False,
) -> LLMHandoffReceipt:
    files = scan_instruction_files(bundle_root)
    start_here_found = any(path.name in START_FILE_NAMES for path in [bundle_root / f.path for f in files])
    has_chatgpt = any(f.llm_hint == "chatgpt" for f in files)
    has_claude = any(f.llm_hint == "claude" for f in files)
    has_handshake = any(f.contains_handshake for f in files)

    failures: list[str] = []
    if not files:
        failures.append("no instruction/start-here files found")
    if llm.lower() == "chatgpt" and not has_chatgpt:
        failures.append("no ChatGPT-specific instruction file found")
    if llm.lower() == "claude" and not has_claude:
        failures.append("no Claude-specific instruction file found")
    if llm.lower() == "chatgpt" and not has_handshake:
        failures.append("ChatGPT handshake marker not found in instruction files")
    if chatgpt_safe_mode_requested and not start_here_found:
        failures.append("cannot activate ChatGPT-safe mode without start-here file")
    if chatgpt_safe_mode_requested and not handshake_visible:
        failures.append("cannot activate ChatGPT-safe mode without visible handshake")

    status: Literal["PASS", "FAIL"] = "PASS" if not failures else "FAIL"
    return LLMHandoffReceipt(
        llm=llm,
        bundle_root=str(bundle_root),
        start_here_found=start_here_found,
        instruction_file_count=len(files),
        handshake_required=HANDSHAKE,
        handshake_visible=handshake_visible,
        chatgpt_safe_mode_active=(chatgpt_safe_mode_requested and status == "PASS"),
        claude_ready=has_claude,
        status=status,
        instruction_files=[asdict(f) for f in files],
        failures=failures,
    )

def write_handoff_receipt(path: Path, receipt: LLMHandoffReceipt) -> Path:
    if receipt.chatgpt_safe_mode_active and not receipt.start_here_found:
        raise ValueError("Cannot activate ChatGPT-safe mode without start-here file.")
    path.parent.mkdir(parents=True, exist_ok=True)
    _tmp = path.with_name(path.name + ".tmp")
    _tmp.write_text(json.dumps(asdict(receipt), indent=2), encoding="utf-8")
    _tmp.replace(path)
    return path

def write_handoff_outputs(
    bundle_root: Path,
    out_dir: Path,
    *,
    llm: str = "chatgpt",
    handshake_visible: bool = True,
    chatgpt_safe_mode_requested: bool = False,
) -> dict[str, str | int | list[str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    receipt = build_handoff_receipt(
        bundle_root,
        llm=llm,
        handshake_visible=handshake_visible,
        chatgpt_safe_mode_requested=chatgpt_safe_mode_requested,
    )
    json_path = out_dir / "LLM_HANDOFF_RECEIPT.json"
    write_handoff_receipt(json_path, receipt)

    md_path = out_dir / "LLM_HANDOFF_RECEIPT.md"
    lines = [
        "# Dual-LLM Handoff Receipt",
        "",
        f"Status: **{receipt.status}**",
        f"LLM: `{receipt.llm}`",
        f"Instruction files found: {receipt.instruction_file_count}",
        f"Handshake visible: {receipt.handshake_visible}",
        f"ChatGPT-safe mode active: {receipt.chatgpt_safe_mode_active}",
        "",
        "## Instruction files",
        "",
    ]
    for item in receipt.instruction_files:
        lines.append(f"- `{item['path']}` · {item['bytes']} bytes · hint={item['llm_hint']} · handshake={item['contains_handshake']}")
    if receipt.failures:
        lines += ["", "## Failures", ""]
        for failure in receipt.failures:
            lines.append(f"- {failure}")
    _md_tmp = md_path.with_name(md_path.name + ".tmp")
    _md_tmp.write_text("\n".join(lines), encoding="utf-8")
    _md_tmp.replace(md_path)

    return {
        "receipt_json": str(json_path),
        "receipt_md": str(md_path),
        "status": receipt.status,
        "failure_count": len(receipt.failures),
        "failures": receipt.failures,
    }
