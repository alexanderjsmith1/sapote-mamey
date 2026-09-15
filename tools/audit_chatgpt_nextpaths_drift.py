#!/usr/bin/env python3
"""Audit selected current assistant surfaces for superseded unconditional rules.

The command name is retained for compatibility. This is a lexical regression check,
not a proof of instruction consistency or assistant behavior. Historical documents
and the explicitly selected legacy eight-item checker are outside its scope.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

from pathlib import Path
import argparse
import re
import sys

# Explicitly scoped: extend this list when a current contract adds a new dependency.
HIGH_RISK_EXACT = {
    "AGENTS.md", "CLAUDE.md", "skills/sapote-mamey/SKILL.md",
    "docs/DELIVERABLE_CONTRACT.md", "docs/SAPOTE_WORKFLOW_CONTRACT.md",
    "docs/CHATGPT_EXECUTION_SLICE_v97147.md",
    "prompts/SAPOTE_MAMEY_CO_EXECUTION_PROMPT.md",
    "prompts/MAMEY_CHATGPT_EXECUTION_PROMPT.md",
    "prompts/CHATGPT_TASK_BRIEF_TEMPLATE.md", "prompts/RUN_DIAGNOSIS_PROMPT.md",
    "prompts/CLAUDE_SYSTEM_PROMPT.md",
}
HIGH_RISK_PREFIXES = ("prompts/reuse/", "docs/modules/")
RULES = {
    "fixed_handback_quota": re.compile(r"exactly[ -]+(?:8|eight).*next[ -]|3\s*[–-]\s*10.*next[ -]", re.I),
    "task_authority_override": re.compile(r"override any conflicting task instruction", re.I),
    "audit_design_immunity": re.compile(r"do\s+(?:\*\*)?not(?:\*\*)?\s+flag intentional designs", re.I),
    "system_python_override": re.compile(r"(?:^|`|\s)(?:pip(?:3)?|python[^\n]*?-m pip)\s+install[^\n]*--break-system-packages", re.I),
}


def high_risk(path: str) -> bool:
    return path in HIGH_RISK_EXACT or any(path.startswith(prefix) for prefix in HIGH_RISK_PREFIXES)


def scan(root: Path) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    if not root.is_dir():
        raise ValueError("audit root must be an existing directory")
    # Do not follow symlinked files or directories from supplied trees.
    for base, dirs, names in _os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d != ".git" and not (Path(base) / d).is_symlink())
        for name in sorted(names):
            path = Path(base) / name
            if path.is_symlink() or path.suffix.lower() not in {".md", ".txt", ".json"}:
                continue
            rel = path.relative_to(root).as_posix()
            if not high_risk(rel):
                continue
            text = path.read_text(encoding="utf-8")
            for idx, line in enumerate(text.splitlines(), 1):
                for rule, pattern in RULES.items():
                    if pattern.search(line):
                        hits.append({"path": rel, "line": str(idx), "rule": rule,
                                     "snippet": line.strip()[:240]})
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    hits = scan(root)
    if ns.json:
        import json
        emit(json.dumps({"status": "PASS" if not hits else "FAIL", "high_risk_hits": hits}, indent=2))
    else:
        if hits:
            emit("CHATGPT_NEXTPATHS_DRIFT_AUDIT: FAIL")
            for hit in hits:
                emit(f"- {hit['path']}:{hit['line']}: {hit['snippet']}")
        else:
            emit("CHATGPT_NEXTPATHS_DRIFT_AUDIT: PASS")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
