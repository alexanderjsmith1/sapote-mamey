#!/usr/bin/env python3
"""canonical_write_guard.py — refuse to silently overwrite a canonical dated deliverable.

WHY THIS EXISTS (a real incident, 2026-09-07). An auditing session ran `mamey surface-leads` once,
to see what the command did, against the real workspace. The command had no `--out`, so it rewrote
the canonical flagged-lead Markdown and its CSV companion in
place. Net damage was 3 bytes of byline text -- and only because that particular tool recomputes
deterministically from a frozen input. Nothing about the *command* made it safe; the determinism
did. A sweep then found the same shape elsewhere (`modeb-compile`, whose output is NOT
deterministic and whose canonical folder also holds PDFs it never regenerates).

The structural problem is not one missing flag. It is that a family of tools was written as one-off
scripts for one dated batch, later wired into the CLI as general commands, keeping hardcoded output
paths under `$MAMEY_DATA_ROOT/strain_data/` -- which is a SYMLINK to the canonical home. So "just
run it and see" writes into real deliverables, and per-command `--out` flags fix that one command
at a time while leaving the next one-off script free to repeat it.

WHAT THIS GUARDS, PRECISELY. It refuses to **overwrite an existing file** inside a canonical dated
deliverable folder. It does not stop:
  * creating a NEW file (a first-time generation in a fresh workspace is normal and allowed);
  * writing anywhere outside a dated deliverable folder;
  * an explicitly intended in-place refresh (`force=True`, wired to a `--force` / `--in-place`
    flag, or the MAMEY_ALLOW_CANONICAL_OVERWRITE=1 escape hatch for batch regeneration).

That is the narrowest rule that would have prevented the observed incident while breaking nothing
that legitimately regenerates a deliverable on purpose. A guard that fires on correct usage trains
people to disable it.

CLAIM SAFETY: this module moves no score, reads no biology, and makes no claim about any locus. It
is a filesystem-safety utility.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

#: A canonical deliverable folder is a dated one: `<something>_YYYY-MM-DD`. That trailing date is
#: the fingerprint of the one-off-batch tools this guard exists for (whole_bgc_majority_read_,
#: flagged_lead_surfacing_, modeb_compilation_, nr_vs_MIBiG_readout_, _AF_LEADS_ ...).
#: v9.7.416: the separator was hardcoded to "_", but this project's deliverable folders are named
#: with a SPACE or a HYPHEN just as often ("BGC Cohort Standout Roundups 2026-08-02",
#: "Geographic Study Figures 2026-07-26", "Gap Audit 2026-07-28"), and some are a bare date
#: ("TRANSCRIPT_BACKUPS/2026-08-15"). Measured over this workspace: 1,589 date-suffixed folders,
#: of which 25 were invisible to the underscore-only pattern -- 13 space-separated, 10 hyphen-
#: separated, 2 bare. This widens the SEPARATOR only: a leading name is still REQUIRED, so a bare
#: date stays out, deliberately. tests/test_canonical_write_guard_v97413.py pins that
#: ("2026-08-05", False) and it is right to -- both bare-date folders in this workspace are backup
#: dirs (TRANSCRIPT_BACKUPS/2026-08-15, 05_claude_recovered_sources/2026-07-26), not deliverables.
#: Anchored to the END, so "run-2026-06-09-scratch" is untouched.
DATED_DIR_RE = re.compile(r".*[ _-]\d{4}-\d{2}-\d{2}$")

#: Env escape hatch for a deliberate batch regeneration (CI, a full recut). Explicit and greppable.
ENV_ALLOW = "MAMEY_ALLOW_CANONICAL_OVERWRITE"


class CanonicalOverwriteRefused(RuntimeError):
    """Raised when a write would silently replace an existing canonical dated deliverable."""


def is_canonical_dated_path(path: str | os.PathLike) -> bool:
    """True if `path` sits inside a dated deliverable folder (`..._YYYY-MM-DD/`)."""
    p = Path(path).expanduser()
    return any(DATED_DIR_RE.match(parent.name) for parent in p.parents)


def guard_canonical_write(path: str | os.PathLike, *, force: bool = False,
                          hint: str = "--out DIR") -> None:
    """Refuse to overwrite an EXISTING file inside a dated canonical deliverable folder.

    No-ops when: the file does not exist yet, the path is not in a dated folder, `force=True`, or
    the env escape hatch is set. Raises `CanonicalOverwriteRefused` otherwise -- callers in the
    post-seal, non-blocking tool family should let it surface as a typed refusal, never a traceback.
    """
    if force or os.environ.get(ENV_ALLOW) == "1":
        return
    p = Path(path).expanduser()
    if not p.exists():
        return
    if not is_canonical_dated_path(p):
        return
    raise CanonicalOverwriteRefused(
        f"refusing to overwrite an existing canonical deliverable: {p}\n"
        f"  This file lives in a dated deliverable folder and something already wrote it.\n"
        f"  Write somewhere else with {hint}, or say so explicitly:\n"
        f"    --force / --in-place, or {ENV_ALLOW}=1 for a deliberate batch regeneration."
    )
