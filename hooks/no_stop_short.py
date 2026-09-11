#!/usr/bin/env python3
import hashlib
import json
import os
import re
import sys
import tempfile
import time

def _project_root():
    return os.environ.get("SAPOTE_WORKSPACE_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

CONTRACT = os.path.join(_project_root(), ".claude", "state", "TASK_CONTRACT.md")
STALE_SECONDS = 12 * 3600
MAX_REPEAT = 6

OPEN_RE = re.compile(r"^\s*[-*]\s*\[\s\]\s*(.+?)\s*$")
DEFER_RE = re.compile(r"^\s*[-*]\s*\[[~\-]\]\s*(.+?)\s*$")


def _fail_open():
    sys.exit(0)


def main():
    try:
        _ = sys.stdin.read()  # drain stdin (Stop hook JSON); we key off the contract file
    except Exception:
        pass
    try:
        if not os.path.isfile(CONTRACT):
            _fail_open()
        if (time.time() - os.path.getmtime(CONTRACT)) > STALE_SECONDS:
            _fail_open()  # abandoned contract; do not trap the session
        text = open(CONTRACT, encoding="utf-8", errors="replace").read()
    except Exception:
        _fail_open()

    open_items, undocumented_defers = [], []
    for line in text.splitlines():
        m = OPEN_RE.match(line)
        if m:
            open_items.append(m.group(1).strip())
            continue
        d = DEFER_RE.match(line)
        if d and not re.search(r"\b(DEFERRED|WON'?T|SKIP)\b", d.group(1), re.I):
            undocumented_defers.append(d.group(1).strip())

    blocking = open_items + undocumented_defers
    if not blocking:
        _fail_open()

    try:
        h = hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
        stem = os.path.join(tempfile.gettempdir(), f"no_stop_short_{h}")
        sf, rf = stem + ".count", stem + ".released"

        # The release must PERSIST for this exact contract text. Deleting the counter on release
        # re-armed the block on the very next Stop, so an unchanged contract produced a permanent
        # MAX_REPEAT-1 blocks / 1 release cycle rather than the advertised escape hatch.
        # Any real edit changes the contract text, changes `h`, and re-arms the block by itself.
        if os.path.isfile(rf):
            try:
                fresh = (time.time() - os.path.getmtime(rf)) <= STALE_SECONDS
            except OSError:
                fresh = False
            if fresh:
                sys.exit(0)
            try:
                os.remove(rf)
            except OSError:
                pass

        n = 0
        if os.path.isfile(sf):
            try:
                n = int(open(sf).read().strip() or "0")
            except Exception:
                n = 0
        n += 1
        open(sf, "w").write(str(n))
        if n >= MAX_REPEAT:
            try:
                os.remove(sf)
            except OSError:
                pass
            open(rf, "w").close()
            sys.stderr.write(
                "[no_stop_short] WARNING: task contract still has OPEN items after "
                f"{MAX_REPEAT} blocks with no edit. Releasing the stop to avoid a hard lock, "
                "but the work is NOT complete:\n  - " + "\n  - ".join(blocking) + "\n"
                f"Contract: {CONTRACT}\n"
            )
            sys.exit(0)
    except Exception:
        pass  # backstop is best-effort; fall through to block

    msg = [
        "[no_stop_short] DO NOT STOP — the declared task is not finished.",
        f"Open items in {CONTRACT}:",
    ]
    for it in open_items:
        msg.append(f"  - [ ] {it}")
    for it in undocumented_defers:
        msg.append(f"  - [~] {it}   (deferred box with NO reason — add 'DEFERRED: <why>' or finish it)")
    msg += [
        "",
        "Finish each item (mark it '- [x]'), or consciously defer it with",
        "'- [~] <item> — DEFERRED: <reason>'. Do not end the turn with silent unfinished work.",
        "When the whole task is done, delete the contract file.",
    ]
    sys.stderr.write("\n".join(msg) + "\n")
    sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
