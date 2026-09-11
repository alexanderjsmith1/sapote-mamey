#!/usr/bin/env python3
"""patch_queue_composition_audit.py — advisory pre-composition audit of a patch queue.

WHY THIS EXISTS (v9.7.412, ordered composition audit)
A patch card can hand the composer either a unified DIFF or a whole-FILE DROP. A diff states
its intent: the composer sees exactly which lines move, and `patch --fuzz=0` refuses if the
base moved underneath it. A file drop states nothing. If the sealed tree gained content in a
cut the card's author never saw, copying their file over it REVERTS that content silently --
no conflict, no reject, no signal.

Measured on the real v9.7.412 queue against sealed v9.7.411: two cards shipped whole-file
replacements of `tools/ggtree_placement.R` and `tools/ggtree_rect_heatmap.R`, each dropping
lines that exist in sealed .411 (which had just landed "ggtree producer + methods footer").
One turned out to be a deliberate re-tune; the other swapped a figure's colour-key vocabulary
outright. Both may well be correct -- the defect is that the composer could not TELL, because
a file drop carries no statement of intent.

This tool makes the invisible case visible. It is ADVISORY: it always exits 0, it never edits
anything, and a WARN is a request to look, not a verdict that the card is wrong.

Usage:
    python tools/patch_queue_composition_audit.py <queue-dir> --base <sealed-tree-root> [--json]
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import sys
from pathlib import Path

DIFF_SUFFIXES = {".patch", ".diff"}
# Bundle-relative roots a payload file may mirror. A payload path is matched against the base
# tree by its longest suffix that starts with one of these, so both
# `CARD/tools/x.py` and `CARD/payload/tools/x.py` resolve to `<base>/tools/x.py`.
BUNDLE_ROOTS = ("tools", "mamey", "tests", "deliverable_tools", "sapote_hooks", "docs", "scripts")

CODE_DIFF = "DIFF"
CODE_NEW = "FILE_DROP_NEW_FILE"
CODE_REVERT = "FILE_DROP_REMOVES_SEALED_CONTENT"
CODE_SAME = "FILE_DROP_IDENTICAL"
CODE_ADDONLY = "FILE_DROP_ADDS_ONLY"
CODE_WORKTREE = "AUDIT_WORKING_TREE_SKIPPED"
CODE_DEBRIS = "PAYLOAD_BUILD_DEBRIS"
CODE_COLLISION = "CROSS_CARD_DROP_COLLISION"

# Compiled/binary artefacts are never a meaningful line-diff target: decoding them with
# errors="replace" invents "removed lines" that mean nothing. They are ALSO a real hygiene
# problem when they sit in a payload directory -- a file-drop composition can copy them into
# the tree -- so they are reported as debris under their own code rather than suppressed.
BINARY_SUFFIXES = {".pyc", ".pyo", ".so", ".dylib", ".png", ".jpg", ".jpeg", ".gif", ".pdf",
                   ".zip", ".gz", ".whl", ".xlsx", ".docx", ".ico", ".treefile"}
DEBRIS_NAMES = {".DS_Store", "Thumbs.db"}
DEBRIS_PARTS = {"__pycache__", ".pytest_cache"}


def is_debris(path: Path) -> bool:
    return (path.suffix in {".pyc", ".pyo"} or path.name in DEBRIS_NAMES
            or any(part in DEBRIS_PARTS for part in path.parts))


def bundle_relpath(payload: Path, item_root: Path, base: Path | None = None) -> Path | None:
    """Map a payload file to its bundle-relative path, or None if it mirrors no bundle root.

    Two shapes are handled. Cards that mirror the tree (`CARD/tools/x.py`) resolve by path
    component. Cards that drop a bare file at the card root (`CARD/test_x.py`) -- a very common
    shape in this queue -- resolve by BASENAME LOOKUP against the sealed tree, because their
    payload carries no directory to key on. Without the fallback these files are invisible to
    the audit, which is how a same-filename collision between two cards went undetected.
    """
    parts = payload.relative_to(item_root).parts
    for i, part in enumerate(parts):
        if part in BUNDLE_ROOTS:
            return Path(*parts[i:])
    if base is not None and len(parts) == 1:
        for root in BUNDLE_ROOTS:
            if (base / root / payload.name).is_file():
                return Path(root) / payload.name
    return None


def _lines(path: Path) -> list[str] | None:
    try:
        return path.read_bytes().decode("utf-8").splitlines(keepends=True)
    except (OSError, UnicodeError):
        return None


def classify_drop(sealed: Path, dropped: Path) -> tuple[str, list[str]]:
    """Return (code, lines_present_in_sealed_but_absent_from_drop)."""
    if not sealed.exists():
        return CODE_NEW, []
    a, b = _lines(sealed), _lines(dropped)
    if a is None or b is None:
        return CODE_REVERT, []          # unreadable -> fail loud, never silently pass
    if a == b:
        return CODE_SAME, []
    # Preserve order, repeated occurrences, blank lines and line endings. Set membership
    # incorrectly calls reordered code or a deleted repeated statement "adds only".
    missing = [ln for tag, i, j, _k, _l in
               difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes()
               if tag in {"delete", "replace"} for ln in a[i:j]]
    return (CODE_REVERT, missing) if missing else (CODE_ADDONLY, [])


# An item that carries a bundle identity file (or a very large mirrored payload) is an audit
# WORKING TREE, not a set of payload files. Reporting each of its thousands of copied files
# would bury the signal -- and a guard that emits thousands of INFO rows is one people learn to
# skip, which is worse than no guard. Such items are named once and not walked.
WORKING_TREE_MARKERS = ("BUILD_STAMP.txt", "TIER_MANIFEST.txt", "MODULE_MANIFEST.txt")
WORKING_TREE_FILE_BUDGET = 200

# `diffbuild/` (and a/ b/ pre/post image pairs) is SCAFFOLDING used to GENERATE a unified diff --
# the card's real payload is the .patch it produced. Treating those pre/post images as file drops
# reports the diff's own intended removals as if they were silent reverts, which is a false
# positive on a card that did exactly the right thing. Excluded by directory name.
SCAFFOLD_PARTS = {"diffbuild", "diff_build", ".diffbuild", "_diffbuild"}


def is_scaffold(path: Path) -> bool:
    return any(part in SCAFFOLD_PARTS for part in path.parts)


def looks_like_working_tree(item: Path) -> bool:
    if any((item / m).exists() or list(item.glob(f"*/{m}")) for m in WORKING_TREE_MARKERS):
        return True
    n = 0
    for _ in item.rglob("*"):
        n += 1
        if n > WORKING_TREE_FILE_BUDGET:
            return True
    return False


def audit_queue(queue: Path, base: Path) -> list[dict]:
    findings: list[dict] = []
    for item in sorted(p for p in queue.iterdir() if p.is_dir()):
        if looks_like_working_tree(item):
            findings.append({"item": item.name, "path": "(whole tree)", "code": CODE_WORKTREE,
                             "severity": "INFO", "removed": 0})
            continue
        for payload in sorted(p for p in item.rglob("*") if p.is_file()):
            if payload.suffix in DIFF_SUFFIXES:
                findings.append({"item": item.name, "path": payload.name,
                                 "code": CODE_DIFF, "severity": "OK", "removed": 0})
                continue
            if is_scaffold(payload.relative_to(item)):
                continue                 # diff-generation scaffolding, not payload
            if is_debris(payload):
                findings.append({"item": item.name, "path": payload.name, "code": CODE_DEBRIS,
                                 "severity": "WARN", "removed": 0,
                                 "sample": ["build artefact in a payload directory"]})
                continue
            rel = bundle_relpath(payload, item, base)
            if rel is None:
                continue                 # card prose, receipts, notes -- not a payload
            if payload.suffix in BINARY_SUFFIXES:
                continue                 # binary: no meaningful line comparison
            code, missing = classify_drop(base / rel, payload)
            try:
                digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            except OSError:
                digest = ""
            findings.append({
                "_rel": str(rel), "_sha": digest,
                "item": item.name, "path": str(rel), "code": code,
                "severity": "WARN" if code == CODE_REVERT else "INFO",
                "removed": len(missing), "sample": [m.strip()[:110] for m in missing[:3]],
            })
    findings.extend(_collisions(findings))
    return findings


def _collisions(findings: list[dict]) -> list[dict]:
    """Two cards dropping the SAME target with DIFFERENT content: whichever the composer copies
    second silently overwrites the first. No patch is involved, so nothing else detects it."""
    by_target: dict[str, list[dict]] = {}
    for f in findings:
        if f.get("_rel") and f.get("_sha"):
            by_target.setdefault(f["_rel"], []).append(f)
    out = []
    for rel, rows in sorted(by_target.items()):
        cards = {r["item"]: r["_sha"] for r in rows}
        if len(cards) > 1 and len(set(cards.values())) > 1:
            out.append({"item": " + ".join(sorted(cards)), "path": rel, "code": CODE_COLLISION,
                        "severity": "WARN", "removed": 0,
                        "sample": [f"{len(cards)} cards drop this target with differing content"]})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("queue", type=Path)
    ap.add_argument("--base", type=Path, required=True, help="sealed tree root to compare against")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    for label, path in (("queue", args.queue), ("base", args.base)):
        if not path.is_dir():
            sys.stderr.write(f"REFUSED: {label} is not a directory: {path}\n")
            return 2

    findings = audit_queue(args.queue, args.base)
    if args.json:
        sys.stdout.write(json.dumps({"queue": str(args.queue), "base": str(args.base),
                                     "findings": findings}, indent=2) + "\n")
        return 0

    warns = [f for f in findings if f["severity"] == "WARN"]
    out = [f"patch-queue composition audit: {args.queue.name} vs {args.base.name}",
           f"  payload entries: {len(findings)}   diffs: {sum(1 for f in findings if f['code'] == CODE_DIFF)}"
           f"   file-drops: {sum(1 for f in findings if f['code'] not in (CODE_DIFF, CODE_SAME, CODE_WORKTREE))}"
           f"   identical(hidden): {sum(1 for f in findings if f['code'] == CODE_SAME)}"
           f"   WARN: {len(warns)}"]
    for f in findings:
        # IDENTICAL carries no composition risk: a byte-for-byte copy changes nothing.
        if f["code"] in (CODE_DIFF, CODE_SAME):
            continue
        out.append(f"  [{f['severity']}] {f['code']}: {f['item']} -> {f['path']}"
                   + (f" ({f['removed']} sealed lines absent)" if f["removed"] else ""))
        for s in f.get("sample", []):
            out.append(f"        - {s}")
    if warns:
        out.append("  NOTE: REMOVES_SEALED_CONTENT means the drop omits lines the sealed tree has -- that may")
        out.append("        be a deliberate rewrite; ask the lane owner for a diff so intent is legible.")
        out.append("        PAYLOAD_BUILD_DEBRIS means a build artefact sits in a payload dir; strip before handoff.")
    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
