#!/usr/bin/env python3
"""Phantom-command guard (patch 46).

Fails if any doc or source references a backticked ``mamey <token>`` where <token> is not a
live CLI subcommand. This is the gate that would have caught F-01 (`mamey crosswalk`) and
F-02 (`mamey render-brief`): both were documented command invocations pointing at nothing.

Scope: backticked ``mamey <token>`` only (a command-invocation signal), so prose like
"the mamey engine" or "a mamey package" does not false-positive.

v9.7.401 HARDENING (BC2): the scan previously used a plain `os.walk()` (no `onerror`) and a
bare `except Exception: continue` around each file read -- both silently drop coverage with no
signal. Reproduced live against the real pristine script: a genuine phantom command reference
hidden inside either an unreadable directory OR an unreadable individual file is completely
invisible to the scan, which then reports "OK" -- a false PASS on the exact defect class this
gate exists to catch. Both now collect what they could not scan and refuse to report OK/PASS
when anything was skipped, matching this round's `os.walk(..., onerror=...)` pattern already
applied to `check_no_brace_paths.py` / `check_duplicate_dict_keys.py` / `check_module_
accretion.py` (a local implementation here, not yet the shared `tools/_safe_walk.py` helper --
that consolidation has not folded into this baseline; migrating this file to it once it does is
a natural, low-risk follow-up, not urgent enough to gate this fix on).
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PAT = re.compile(r"`mamey ([a-zA-Z][\w-]*)")
EXTS = (".md", ".txt", ".py", ".html", ".rst")
# words that legitimately follow `mamey ` without being subcommands
NON_CMD_ALLOWED = {"--version", "-V", "--help", "-h", "run", "doctor"}  # run/doctor are real too


def live_subcommands():
    from mamey.cli import build_parser
    p = build_parser()
    cmds = set()
    subparsers = getattr(p, "_subparsers", None)
    if subparsers:
        for a in subparsers._group_actions:
            if hasattr(a, "choices") and a.choices:
                cmds.update(a.choices.keys())
    return cmds


def scan(allowed):
    bad = []
    unscanned: list[str] = []

    def _onerror(exc: OSError) -> None:
        unscanned.append(getattr(exc, "filename", None) or str(exc))

    for dp, dirs, files in os.walk(ROOT, onerror=_onerror):
        if "/.git" in dp or "__pycache__" in dp:
            continue
        for fn in files:
            if not fn.endswith(EXTS):
                continue
            fp = Path(dp) / fn
            # skip this guard's own source and any file that is defining the allow-set
            if fp.name == "check_command_pointers.py":
                continue
            try:
                text = fp.read_text(encoding="utf-8", errors="ignore")
            except Exception as exc:  # noqa: BLE001 - report, don't silently drop the file
                unscanned.append(f"{fp.relative_to(ROOT)} ({type(exc).__name__})")
                continue
            for m in PAT.finditer(text):
                tok = m.group(1)
                if tok not in allowed:
                    ln = text[: m.start()].count("\n") + 1
                    bad.append((str(fp.relative_to(ROOT)), ln, tok))
    return bad, unscanned


def main():
    real = live_subcommands()
    allowed = real | NON_CMD_ALLOWED
    bad, unscanned = scan(allowed)
    failed = False
    if unscanned:
        failed = True
        # v9.7.401 (per independent pool review): report/refusal prints belong on stderr,
        # matching the .400-round print-ratchet convention (delta-d / safe-walk precedent) --
        # this bundle's print_calls ceiling has zero headroom, and a refusal/error message is
        # not the kind of output that should count toward it anyway.
        sys.stderr.write(f"COULD NOT FULLY SCAN — {len(unscanned)} path(s) unreadable, so this "
                         f"run is NOT a complete scan and cannot report OK:\n")
        for u in unscanned:
            sys.stderr.write(f"  {u}\n")
    if bad:
        failed = True
        emit(f"PHANTOM COMMAND POINTERS: {len(bad)} (against {len(real)} live subcommands)")
        for f, ln, tok in sorted(set(bad)):
            emit(f"  {f}:{ln} -> `mamey {tok}` is not a subcommand")
    if failed:
        return 1
    emit(f"OK: no phantom `mamey <cmd>` pointers ({len(real)} live subcommands)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
