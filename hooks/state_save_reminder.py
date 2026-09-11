#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import time

WARN_MINUTES = 120        # the user's "once per hour or two hours" outer bound
DORMANT_MINUTES = 1440    # >24h = finished/parked, reported separately, not a nag
UNCONFIGURED_REPEAT_SECONDS = 12 * 3600   # say it once, not on every Stop


def _warn_unconfigured(root: str) -> None:
    """Say once that the resolved state root does not exist.

    A missing root used to return 0 with no output, so an operator who installed this hook and never
    set SAPOTE_TASK_STATE_ROOT got permanent silence and read it as "everyone is current". The
    generic default `task_state/` matches nothing in a workspace that names the directory anything
    else, which is the normal case, so silence here is a misconfiguration, not a clean bill.
    """
    try:
        h = hashlib.sha1(root.encode("utf-8", "replace")).hexdigest()[:16]
        marker = os.path.join(tempfile.gettempdir(), f".state_save_root_missing_{h}")
        if os.path.isfile(marker) and (time.time() - os.path.getmtime(marker)) < UNCONFIGURED_REPEAT_SECONDS:
            return
        open(marker, "w").close()
    except Exception:
        pass  # a debounce failure must not cost the operator the warning
    print(f"\nSTATE-SAVE CADENCE: no state root at {root} — this check is doing nothing.",
          file=sys.stderr)
    print("Point SAPOTE_TASK_STATE_ROOT at the directory holding <name>/STATE.md, or uninstall the hook.",
          file=sys.stderr)
    print("", file=sys.stderr)


def main() -> int:
    try:
        base = os.environ.get("SAPOTE_WORKSPACE_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        colours = os.environ.get("SAPOTE_TASK_STATE_ROOT") or os.path.join(base, "task_state")
        if not os.path.isdir(colours):
            _warn_unconfigured(colours)
            return 0

        ignore: set[str] = set()
        ig = os.path.join(colours, ".state_save_ignore")
        if os.path.isfile(ig):
            with open(ig, encoding="utf-8") as fh:
                ignore = {ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")}

        now = time.time()
        stale: list[tuple[str, int]] = []
        dormant: list[tuple[str, int]] = []
        for name in sorted(os.listdir(colours)):
            if name in ignore or name.startswith("."):
                continue
            p = os.path.join(colours, name, "STATE.md")
            if not os.path.isfile(p):
                continue
            age = int((now - os.path.getmtime(p)) / 60)
            if age >= DORMANT_MINUTES:
                dormant.append((name, age))
            elif age >= WARN_MINUTES:
                stale.append((name, age))

        if not stale:
            return 0  # silent when everyone is current — the normal case

        print("\nSTATE-SAVE CADENCE (advisory): these chats' STATE.md are past the 2-hour mark.",
              file=sys.stderr)
        print("If one of them is you, save state before this session compacts or ends.",
              file=sys.stderr)
        for name, age in stale:
            h, m = divmod(age, 60)
            print(f"  - {name}: {h}h {m}m since last STATE.md write", file=sys.stderr)
        if dormant:
            names = ", ".join(f"{n} ({a // 1440}d)" for n, a in dormant)
            print(f"  (dormant, expected — not a nag: {names})", file=sys.stderr)
        print("", file=sys.stderr)
    except Exception:
        return 0  # fail open — a reminder must never wedge a Stop
    return 0


if __name__ == "__main__":
    sys.exit(main())
