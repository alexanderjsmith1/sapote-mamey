#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import sys
import glob

_SCOPE_GLOBS = ("tools/*.py", "tools/*.sh", "tools/*/*.py", "tools/*/*.sh")
_DRIFT_DIR = "SAPOTE_CONTROL/tool_drift"


def _project_dir() -> str:
    return os.environ.get("SAPOTE_WORKSPACE_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def _session_id() -> str:
    try:
        data = json.load(sys.stdin)
        sid = str(data.get("session_id") or "").strip()
        return sid or "_shared"
    except Exception:
        return "_shared"


def _hash_scope(base: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for pat in _SCOPE_GLOBS:
        for p in glob.glob(os.path.join(base, pat)):
            try:
                with open(p, "rb") as fh:
                    out[os.path.relpath(p, base)] = hashlib.sha256(fh.read()).hexdigest()
            except Exception:
                continue  # unreadable file is not this hook's problem
    return out


def _baseline_path(base: str, sid: str, create: bool = False) -> str:
    d = os.path.join(base, _DRIFT_DIR)
    if create:
        os.makedirs(d, exist_ok=True)  # only the snapshot writer may create state in the project
    safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in sid)[:64]
    return os.path.join(d, f"baseline_{safe}.json")


def main() -> int:
    try:
        mode = "check"
        if "--mode" in sys.argv:
            mode = sys.argv[sys.argv.index("--mode") + 1]
        base = _project_dir()
        sid = _session_id()
        bpath = _baseline_path(base, sid, create=(mode == "baseline"))

        if mode == "baseline":
            with open(bpath, "w", encoding="utf-8") as fh:
                json.dump(_hash_scope(base), fh)
            return 0  # silent snapshot

        if not os.path.isfile(bpath):
            # Fail open, but SAY SO when other sessions did snapshot: the Stop payload carrying no
            # session_id (or a different one than SessionStart saw) sends the check at
            # `baseline__shared.json`, which never exists, and every real tools/ modification is then
            # passed over in silence. An unarmed detector must not look like a clean one.
            try:
                d = os.path.join(base, _DRIFT_DIR)
                others = [f for f in os.listdir(d)
                          if f.startswith("baseline_") and f.endswith(".json")] if os.path.isdir(d) else []
            except OSError:
                others = []
            if others:
                print(f"\nC10 TOOL-DRIFT: unarmed for this session — no {os.path.basename(bpath)} "
                      f"({len(others)} baseline(s) from other session id(s) present).", file=sys.stderr)
                print("Pass the same session_id to the SessionStart --mode baseline and the Stop "
                      "--mode check, or this check reports nothing.", file=sys.stderr)
                print("", file=sys.stderr)
            return 0  # no baseline (e.g. session predates the hook) — nothing to compare, fail open
        with open(bpath, encoding="utf-8") as fh:
            before = json.load(fh)
        after = _hash_scope(base)

        modified = sorted(k for k in after if k in before and after[k] != before[k])
        removed = sorted(k for k in before if k not in after)
        added = sorted(k for k in after if k not in before)

        if modified or removed:
            print("\nC10 TOOL-DRIFT (advisory): this session changed EXISTING workspace tool(s) in place.",
                  file=sys.stderr)
            print("Modifying a shared tools/ file is a PATCH action — it should ship as a candidate under",
                  file=sys.stderr)
            print("a review patch with an explicit baseline and owner disposition.",
                  file=sys.stderr)
            for k in modified:
                print(f"  - MODIFIED: {k}", file=sys.stderr)
            for k in removed:
                print(f"  - REMOVED:  {k}", file=sys.stderr)
            if added:
                print(f"  ({len(added)} new file(s) created — allowed, not flagged.)", file=sys.stderr)
            print("", file=sys.stderr)
        return 0
    except Exception:
        return 0  # fail open — a detector must never wedge a hook


if __name__ == "__main__":
    sys.exit(main())
