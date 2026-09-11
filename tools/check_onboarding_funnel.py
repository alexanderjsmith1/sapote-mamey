#!/usr/bin/env python3
"""One-door onboarding-funnel guard (CLAUDE_409_onboarding_funnel_guard).

Deterministic, offline check that the onboarding funnel established by
`development/LLM_ONBOARDING_AUDIT.md` (and enforced by the CLAUDE_409_onboarding_one_door
lane) has not silently regressed. The audit's finding: an operating LLM meets many
"read me first / start here" doors at the bundle root and, with no first-glance arbiter,
opens none. The fix funnels every door to a single instruction -- run
``python mamey_run.py start`` -- and makes `AGENTS.md` the canonical contract. Nothing
guards that the funnel holds, so this asserts the one-door invariant:

  (1) every agent-facing root door (`*READ*ME*` / `*START*HERE*` / `AGENTS.md` /
      `CLAUDE.md` / `README*.md`) carries, near its top, either the canonical
      ``python mamey_run.py start`` directive or a redirect to `AGENTS.md`;
  (2) `AGENTS.md` and `CLAUDE.md` are byte-identical (one door, two names);
  (3) `python mamey_run.py start` exists and exits 0 (checked only with --run-start;
      the pytest wrapper covers this offline with `start --no-doctor`).

This is a static text check by default: no imports of `mamey`, no subprocess, no network.
It reads only root-level files inside the bundle it lives in.

Exit 0 = funnel intact; exit 1 = a door regressed (or the twin diverged).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The one instruction every door must deliver, verbatim (the runner that pins the local
# package -- `python -m mamey` can silently run a pip-cached install of another version).
DIRECTIVE = "python mamey_run.py start"
# A door may instead redirect to the canonical contract, which itself leads with DIRECTIVE.
REDIRECT = "AGENTS.md"

# "Near the top": an LLM opening the door must meet the funnel without scrolling.
HEAD_LINES = 12

# Root-only globs that discover an agent first-contact door. A NEW door added later that
# matches one of these is automatically pulled into the check (that is the anti-regression
# value) unless it is explicitly exempted below.
DOOR_GLOBS = ("*READ*ME*.md", "*START*HERE*.md", "AGENTS.md", "CLAUDE.md", "README*.md")

# Doors that are NOT agent first-contact onboarding entry points, with the reason.
# docs/FIGURES_START_HERE.md is the figures subsystem's door (it funnels into the figure-prompt
# workflow, not the run pipeline); the accepted one-door lane deliberately leaves it alone,
# so the guard must too, or it would fail-after and stop co-existing with that lane.
EXEMPT = {
    "docs/FIGURES_START_HERE.md": "figures subsystem door, not an agent run-pipeline entry point",
}

# A long project README legitimately leads with its banner; its agent funnel lives in a
# dedicated section (e.g. "Using with an AI assistant"), so scan the whole file, not the head.
WHOLE_FILE = {"README.md"}


def discover_doors(root: Path = ROOT):
    """Root-level door files matching DOOR_GLOBS, de-duplicated, sorted by name."""
    seen = {}
    for pat in DOOR_GLOBS:
        for p in root.glob(pat):
            if p.is_file():
                seen[p.name] = p
    return [seen[name] for name in sorted(seen)]


def door_ok(path: Path):
    """(ok, window_desc): does this door carry the directive or an AGENTS.md redirect?"""
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.name in WHOLE_FILE:
        window, where = text, "anywhere (long README)"
    else:
        window = "\n".join(text.splitlines()[:HEAD_LINES])
        where = f"first {HEAD_LINES} lines"
    ok = (DIRECTIVE in window) or (REDIRECT in window)
    return ok, where


def check_doors(root: Path = ROOT):
    """Return (failures, checked_names, exempt_names)."""
    failures = []
    checked = []
    exempt = []
    for p in discover_doors(root):
        if p.name in EXEMPT:
            exempt.append(p.name)
            continue
        checked.append(p.name)
        ok, where = door_ok(p)
        if not ok:
            failures.append(
                f"{p.name}: no `{DIRECTIVE}` and no `{REDIRECT}` redirect in its {where}"
            )
    return failures, checked, exempt


def check_twin(root: Path = ROOT):
    """AGENTS.md and CLAUDE.md must be byte-identical (invariant 2). Returns list of failures."""
    a, c = root / "AGENTS.md", root / "CLAUDE.md"
    if not a.exists() or not c.exists():
        return [f"missing canonical door: AGENTS.md exists={a.exists()} CLAUDE.md exists={c.exists()}"]
    if a.read_bytes() != c.read_bytes():
        return ["AGENTS.md and CLAUDE.md are not byte-identical (one door, two names)"]
    return []


def check_start_runs(root: Path = ROOT):
    """Optional: `mamey_run.py start --no-doctor` exists and exits 0 (invariant 3, offline)."""
    runner = root / "mamey_run.py"
    if not runner.exists():
        return ["mamey_run.py is missing (no runtime door for `start`)"]
    try:
        out = subprocess.run(
            [sys.executable, str(runner), "start", "--no-doctor"],
            cwd=str(root), capture_output=True, text=True, timeout=180,
        )
    except Exception as exc:  # pragma: no cover - environment dependent
        return [f"could not run `mamey_run.py start`: {exc!r}"]
    if out.returncode != 0:
        return [f"`mamey_run.py start` exited {out.returncode}: {out.stderr[-300:]}"]
    if DIRECTIVE.split(" start")[0] not in out.stdout:
        return ["`mamey_run.py start` output did not name the `python mamey_run.py` idiom"]
    return []


def run_checks(root: Path = ROOT, run_start: bool = False):
    door_failures, checked, exempt = check_doors(root)
    failures = list(door_failures) + check_twin(root)
    if run_start:
        failures += check_start_runs(root)
    return failures, checked, exempt


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="One-door onboarding-funnel guard.")
    ap.add_argument("--run-start", action="store_true",
                    help="also run `mamey_run.py start --no-doctor` and require exit 0")
    ap.add_argument("--root", default=str(ROOT), help="bundle root to check (default: this bundle)")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()

    failures, checked, exempt = run_checks(root, run_start=args.run_start)
    print(f"onboarding-funnel guard: {len(checked)} doors checked "
          f"({', '.join(checked)})")
    if exempt:
        print("  exempt: " + ", ".join(f"{n} ({EXEMPT[n]})" for n in exempt))
    if failures:
        print("FAIL — the one-door funnel has regressed:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("PASS — every root door funnels to `python mamey_run.py start` / AGENTS.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
