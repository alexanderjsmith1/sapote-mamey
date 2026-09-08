#!/usr/bin/env python3
"""
check_duplicate_dict_keys.py — fail closed on NEW duplicate dict-literal keys.

WHY
---
A duplicate key in a Python dict literal is silent data loss: the last binding wins, the
earlier entries vanish, and there is no error, no warning, and no test failure.

v9.7.235 carries three such collisions, all from one cause — the AS_SCRUB anonymiser rewrote
distinct real strain IDs into the same placeholder token (`AS-XXX`, `SID-XXX`), collapsing
what had been distinct keys. Measured on the live tree:

  mamey/master_figure_atlas.py    label_positions  10 written ->  1 survives  (9 lost)
  tools/build_thesis_vignettes.py CAUSEMAP          3 written ->  1 survives  (2 lost)
  tests/test_ptm_af_scoring.py    SURVEY            5 written ->  4 survive   (1 lost)

Runtime effect, not cosmetics: every strain label in the master figure atlas resolves to the
single surviving position, and every thesis vignette resolves to `causemap_rejections.png`.

Those three are ALLOWLISTED rather than fixed. De-colliding them needs the real
strain -> entry mapping, which the source comments explicitly decline to guess and which the
code cannot infer. The bundle already pins their current (broken) state with regression tests
(`test_label_positions_dict_documents_the_known_duplicate_key_collision`,
`test_causemap_dict_documents_the_known_duplicate_key_collision`), so a silent RE-collision
fails loudly. This gate is the missing half: it stops a FOURTH site appearing.

The allowlist is a ratchet. Remove an entry the moment the real IDs are restored; never add
one without a comment saying why the collision is intentional.

Note: the AS cohort became public on 2026-07-06 (PI decision), so the editorial input these
three sites were waiting on — the real strain IDs — is now available.

USAGE
  python tools/check_duplicate_dict_keys.py            # gate: exit 1 on any NEW collision
  python tools/check_duplicate_dict_keys.py --list     # report every collision, allowlisted or not
  python tools/check_duplicate_dict_keys.py --strict   # ignore allowlist; any collision fails
  python tools/check_duplicate_dict_keys.py --json
  python tools/check_duplicate_dict_keys.py --root mamey tools
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import ast
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _safe_walk import safe_walk_files  # v9.7.400: shared unreadable-dir-aware walk

# path -> why this collision is tolerated. This list must only ever SHRINK.
# v9.7.308: fully paid down. The three AS_SCRUB placeholder collisions were de-collided:
#   mamey/master_figure_atlas.py  (label_positions -> LABEL_POSITION_OVERRIDES, empty real-keyed map)
#   tools/build_thesis_vignettes.py (CAUSEMAP -> empty real-keyed map; authored routes preserved)
#   tests/test_ptm_af_scoring.py   (SURVEY -> distinct synthetic SURVEY-N keys)
# The gate now runs with an empty allowlist: any collision, anywhere, fails.
ALLOWLIST: dict[str, str] = {}

SKIP_PARTS = {"__pycache__", "_vendor", ".git", "node_modules", "build", "dist"}


def _const_key(node):
    """Comparable key for a constant dict key; None for computed keys / ** expansion.

    v9.7.374: returns the raw constant value itself, not a (type_name, value) tuple. The old
    tuple form made e.g. 1 (int), True (bool), and 1.0 (float) compare as three DIFFERENT keys
    here, even though Python's real dict-literal semantics treat them as the SAME key (they all
    hash and compare equal: `{1: "a", True: "b", 1.0: "c"}` really does collapse to one entry,
    silently discarding two of three bindings -- exactly the class of bug this whole gate exists
    to catch). Returning the raw value lets Python's own hash/eq decide collisions, matching
    what actually happens at runtime.

    v9.7.395: evaluates via ast.literal_eval with a hashability guard instead of accepting only
    bare scalar ast.Constant nodes. The old isinstance test silently skipped constant TUPLE keys
    (`{("AS-1","BGC001"): x, ("AS-1","BGC001"): y}` — an ast.Tuple, not ast.Constant) and
    negative-number keys (`-1` parses as UnaryOp) — both are real runtime collisions (last
    binding wins, earlier entries vanish) that this gate reported nothing for. literal_eval
    covers every literal form with Python's own semantics; anything non-literal or unhashable
    (a genuinely computed key) still returns the None sentinel and is skipped as before.
    Known residual: a literal `None` key still conflates with the sentinel and is not tracked.
    """
    if node is None:  # ** expansion
        return None
    try:
        v = ast.literal_eval(node)
        hash(v)
    except Exception:
        return None
    if v is None:
        return None
    return v


def scan_file(path: Path):
    """Yield dicts describing each offending dict literal in `path`."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        const = [k for k in (_const_key(k) for k in node.keys) if k is not None]
        if not const:
            continue
        counts = collections.Counter(const)
        dups = sorted(str(k) for k, c in counts.items() if c > 1)
        if dups:
            yield {"line": node.lineno, "duplicate_keys": dups,
                   "entries_written": len(const), "entries_surviving": len(set(const)),
                   "entries_lost": len(const) - len(set(const))}


def collect(roots, stats=None, unreadable_out=None):
    # v9.7.400: file discovery now goes through the shared safe_walk_files() (tools/
    # _safe_walk.py) instead of a local `rp.rglob("*.py")` -- rglob silently swallows a
    # per-directory OSError, so a real collision sitting inside an unscannable directory
    # reported PASS. SKIP_PARTS is pruned during the walk (via `skip_dirs`), not just
    # filtered from the result afterward, so a skipped directory is never descended into.
    for root in roots:
        rp = Path(root)
        if rp.is_file():
            files = [rp]
        else:
            files, unreadable = safe_walk_files(rp, suffix=".py", skip_dirs=SKIP_PARTS)
            if unreadable_out is not None:
                unreadable_out.extend(unreadable)
        for f in files:
            if any(part in SKIP_PARTS for part in f.parts):
                continue
            if stats is not None:
                stats["files"] = stats.get("files", 0) + 1
            for rec in scan_file(f):
                rec["file"] = f.as_posix()
                yield rec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", nargs="*", default=["mamey", "tools", "tests"])
    ap.add_argument("--strict", action="store_true", help="ignore the allowlist")
    ap.add_argument("--list", action="store_true", help="report every collision found")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    # v9.7.395: a gate run that scans NOTHING must not report PASS. Pre-fix, a missing root —
    # e.g. running from any cwd other than the bundle root, or a typo'd --root — made
    # rglob() yield zero files and the gate print "PASS ... 0 new" (exit 0) having checked
    # nothing. Reproduced live from an empty directory. Missing roots and an empty scan are
    # now hard errors (exit 2, the argparse-style usage-error code), and the PASS line
    # self-reports how many files it actually scanned.
    missing = [r for r in a.root if not Path(r).exists()]
    if missing:
        sys.stderr.write(f"duplicate-dict-key gate: ERROR — root(s) do not exist: "
                         f"{missing} (wrong working directory?)\n")
        return 2

    stats = {"files": 0}
    unreadable: list[str] = []
    new, known = [], []
    for rec in collect(a.root, stats, unreadable):
        if not a.strict and rec["file"] in ALLOWLIST:
            rec["allowlisted"] = ALLOWLIST[rec["file"]]
            known.append(rec)
        else:
            new.append(rec)

    # v9.7.400: a run that scanned MOST of the tree but silently skipped an unreadable
    # subdirectory must not report PASS either -- same principle as the v9.7.395 zero-files
    # guard below, for the partial-coverage case that guard doesn't catch (stats["files"] is
    # still nonzero whenever at least one OTHER directory was readable). Reproduced live: a
    # real duplicate-key collision inside a permission-locked subdirectory, alongside one
    # ordinary readable file elsewhere, reported "PASS ... 1 file(s) scanned" pre-fix.
    if unreadable:
        uniq = sorted(set(unreadable))
        sys.stderr.write(f"duplicate-dict-key gate: ERROR — {len(uniq)} director"
                         f"{'y' if len(uniq) == 1 else 'ies'} could not be scanned (unreadable), "
                         f"so this run is NOT a complete scan and cannot report PASS: {uniq}\n")
        return 2

    if stats["files"] == 0:
        sys.stderr.write(f"duplicate-dict-key gate: ERROR — 0 python files found under "
                         f"root(s) {a.root}; refusing to PASS on an empty scan\n")
        return 2

    if a.json:
        emit(json.dumps({"new": new, "allowlisted": known,
                          "files_scanned": stats["files"]}, indent=2))
        return 1 if new else 0

    if a.list or known:
        for r in known:
            emit(f"  known  {r['file']}:{r['line']}  {r['entries_written']} written -> "
                  f"{r['entries_surviving']} survive ({r['entries_lost']} lost)")
    for r in new:
        emit(f"  NEW    {r['file']}:{r['line']}  keys={r['duplicate_keys']}  "
              f"{r['entries_written']} written -> {r['entries_surviving']} survive "
              f"({r['entries_lost']} SILENTLY DISCARDED)", file=sys.stderr)

    if new:
        emit(f"\nduplicate-dict-key gate: FAIL ({len(new)} new site(s)). "
              f"Python keeps only the last binding — this is silent data loss.", file=sys.stderr)
        return 1
    emit(f"\nduplicate-dict-key gate: PASS ({len(known)} known collision(s) allowlisted, 0 new; "
          f"{stats['files']} file(s) scanned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
