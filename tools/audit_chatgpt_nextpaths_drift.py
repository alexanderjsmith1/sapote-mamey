#!/usr/bin/env python3
"""Audit high-risk ChatGPT/Mamey instruction surfaces for next-path drift.

This repository uses a strict handback contract for ChatGPT/Mamey:
exactly 8 unique numbered next paths. Older "3-10 next paths" wording is allowed
only in explicitly historical/archive/Claude exploratory contexts, not in active
Mamey/ChatGPT prompts or deliverable modules.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

from pathlib import Path
import argparse
import re
import sys

# v9.7.374 fix (AUDIT_374): only one of the ChatGPT-tier prompts living directly in
# prompts/ was covered here. docs/CHATGPT_EXECUTION_SLICE_v97147.md is the CURRENT canonical
# ChatGPT/Sapote entrypoint per prompts/FULL_RUN_PROFILE.md's own text ("new ChatGPT/Sapote
# sessions load docs/CHATGPT_EXECUTION_SLICE_v97147.md") -- the single most load-bearing
# ChatGPT-facing file in the bundle -- and was entirely outside this gate's scan scope (it sits
# directly under docs/, not docs/modules/). prompts/MAMEY_CHATGPT_EXECUTION_PROMPT.md,
# prompts/CHATGPT_TASK_BRIEF_TEMPLATE.md, prompts/RUN_DIAGNOSIS_PROMPT.md ("ChatGPT prompt" per
# its own header), and prompts/FULL_RUN_PROFILE.md are all explicitly ChatGPT-tier prompts at
# the same directory level as the one file that WAS covered, with no principled reason to
# exclude them. All five currently already carry the correct "exactly 8" wording (confirmed live
# against the .373b source), so adding them does not flip today's PASS to FAIL -- it closes the
# blind spot so a future regression in any of them is actually caught, matching this gate's own
# stated purpose of protecting "active Mamey/ChatGPT prompts."
HIGH_RISK_EXACT = {
    "SESSION_START_MANIFEST.md",
    "prompts/SAPOTE_MAMEY_CO_EXECUTION_PROMPT.md",
    "docs/CHATGPT_EXECUTION_SLICE_v97147.md",
    "prompts/MAMEY_CHATGPT_EXECUTION_PROMPT.md",
    "prompts/CHATGPT_TASK_BRIEF_TEMPLATE.md",
    "prompts/RUN_DIAGNOSIS_PROMPT.md",
    "prompts/FULL_RUN_PROFILE.md",
}
HIGH_RISK_PREFIXES = (
    "prompts/reuse/",
    "docs/modules/",
)
ALLOW_LOW_RISK_PREFIXES = (
    "docs/archive/",
    "docs/patch_notes/",
)
RANGE_RE = re.compile(r"3\s*[–-]\s*10|3\s+to\s+10|three\s+to\s+ten", re.I)
NEXT_RE = re.compile(r"next[- ]paths?|next[- ]step\s+paths?|next\s+steps", re.I)


def high_risk(path: str) -> bool:
    return path in HIGH_RISK_EXACT or any(path.startswith(prefix) for prefix in HIGH_RISK_PREFIXES)


def low_risk_allowed(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in ALLOW_LOW_RISK_PREFIXES)


def scan(root: Path) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".json", ".py"}:
            continue
        rel = path.relative_to(root).as_posix()
        if low_risk_allowed(rel):
            continue
        if not high_risk(rel):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for idx, line in enumerate(text.splitlines(), 1):
            if RANGE_RE.search(line) and NEXT_RE.search(line):
                hits.append({"path": rel, "line": str(idx), "snippet": line.strip()[:240]})
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
