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


def scan(root: Path, counts: dict | None = None) -> list[dict[str, str]]:
    """Collect drift hits. `counts`, when given, receives the TARGET tally.

    v9.7.438: the caller needs to know how many files were actually examined. Without it the
    verdict `1 if hits else 0` cannot distinguish "43 high-risk files checked and clean" from
    "zero files were in scope" — and both printed the same PASS line.
    """
    hits: list[dict[str, str]] = []
    n_considered = n_selected = 0
    if not root.is_dir():
        raise ValueError("audit root must be an existing directory")
    # Do not follow symlinked files or directories from supplied trees.
    for base, dirs, names in _os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d != ".git" and not (Path(base) / d).is_symlink())
        for name in sorted(names):
            path = Path(base) / name
            if path.is_symlink() or path.suffix.lower() not in {".md", ".txt", ".json"}:
                continue
            n_considered += 1
            rel = path.relative_to(root).as_posix()
            if not high_risk(rel):
                continue
            n_selected += 1
            text = path.read_text(encoding="utf-8")
            for idx, line in enumerate(text.splitlines(), 1):
                for rule, pattern in RULES.items():
                    if pattern.search(line):
                        hits.append({"path": rel, "line": str(idx), "rule": rule,
                                     "snippet": line.strip()[:240]})
    if counts is not None:
        counts["considered"] = n_considered
        counts["selected"] = n_selected
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    counts: dict[str, int] = {}
    hits = scan(root, counts)
    n_sel = counts.get("selected", 0)
    # v9.7.438: refuse rather than pass when nothing was in scope. A gate that reports PASS on an
    # empty target set keeps reporting PASS after a refactor moves the files it watches, which is
    # the failure that let a workspace doc sit four cuts stale while its check passed every cut.
    if not hits and n_sel == 0:
        msg = (f"CHATGPT_NEXTPATHS_DRIFT_AUDIT: REFUSED — 0 high-risk file(s) in scope under "
               f"{root} ({counts.get('considered', 0)} .md/.txt/.json file(s) considered). "
               f"Nothing was audited; this is not a PASS.")
        if ns.json:
            import json
            msg = json.dumps({"status": "REFUSED", "reason": "no high-risk targets in scope",
                              "considered": counts.get("considered", 0), "selected": 0}, indent=2)
        emit(msg)
        return 2
    if ns.json:
        import json
        emit(json.dumps({"status": "PASS" if not hits else "FAIL", "high_risk_hits": hits,
                         "considered": counts.get("considered", 0), "selected": n_sel}, indent=2))
    else:
        if hits:
            emit("CHATGPT_NEXTPATHS_DRIFT_AUDIT: FAIL")
            for hit in hits:
                emit(f"- {hit['path']}:{hit['line']}: {hit['snippet']}")
        else:
            emit(f"CHATGPT_NEXTPATHS_DRIFT_AUDIT: PASS ({n_sel} high-risk file(s) checked, "
                 f"{counts.get('considered', 0)} considered)")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
