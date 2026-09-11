#!/usr/bin/env python3
"""Check ChatGPT handbacks for exactly 8 unique next paths.

Usage:
  python tools/check_chatgpt_next_paths.py HANDOFF.md

Exit codes:
  0 = pass
  1 = fail
  2 = bad input (handback file missing)
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, re, sys
from pathlib import Path

GENERIC = {"continue", "do", "run", "make", "create", "work", "analyze", "execute", "perform", "build", "implement", "handle"}

def extract_numbered_items(text: str):
    # Grab the final numbered-list-looking block with items 1. ...
    lines = text.splitlines()
    blocks, cur = [], []
    for line in lines:
        if re.match(r"^\s*\d+\.\s+\S", line):
            cur.append(line.strip())
        else:
            if cur:
                blocks.append(cur); cur=[]
    if cur: blocks.append(cur)
    return blocks[-1] if blocks else []

def normalize_item(item: str) -> str:
    item = re.sub(r"^\d+\.\s*", "", item).strip().lower()
    item = re.sub(r"[`*_#()\[\],:;]+", " ", item)
    item = re.sub(r"\s+", " ", item).strip()
    # uniqueness by leading verb + object-ish first 6 tokens, after removing filler
    toks = [t for t in item.split() if t not in {"the", "a", "an", "to", "for", "with", "and", "or", "this"}]
    return " ".join(toks[:6])

def main(path: str) -> int:
    handoff = Path(path)
    if not handoff.is_file():
        emit(f"INPUT_NOT_FOUND: {path}", file=sys.stderr)
        return 2
    text = handoff.read_text(encoding="utf-8", errors="replace")
    items = extract_numbered_items(text)
    errors = []
    if len(items) != 8:
        errors.append(f"expected exactly 8 numbered next paths; found {len(items)}")
    nums = [int(re.match(r"^\s*(\d+)\.", x).group(1)) for x in items if re.match(r"^\s*(\d+)\.", x)]
    if nums != list(range(1,9)):
        errors.append(f"expected numbering 1..8; found {nums}")
    norms = [normalize_item(x) for x in items]
    if len(set(norms)) != len(norms):
        errors.append("duplicate/near-duplicate next paths detected by leading action/object")
    too_generic = [x for x,n in zip(items,norms) if n.split()[0:1] and n.split()[0] in GENERIC and len(n.split()) < 4]
    if too_generic:
        errors.append("generic/filler-looking paths: " + " | ".join(too_generic[:3]))
    if errors:
        emit("NEXT_PATHS_CHECK: FAIL")
        for e in errors: emit("-", e)
        return 1
    emit("NEXT_PATHS_CHECK: PASS")
    return 0

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("handoff", help="path to the ChatGPT handback markdown to check")
    sys.exit(main(ap.parse_args().handoff))
