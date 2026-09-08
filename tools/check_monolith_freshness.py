#!/usr/bin/env python3
"""check_monolith_freshness.py — the monolith is the parent design controller; keep its anchor honest.

v9.7.243. `docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md` is referenced by 20 files, including
`prompts/CLAUDE_SYSTEM_PROMPT.md` and at least one test. It is deliberately NOT bumped every patch —
its content is reviewed at checkpoints. That convention is sound. What is not sound is the anchor
line drifting silently: at v9.7.242 the monolith still said

    "vetted against bundle v9.7.6 (last full read-through 2026-06-13)"
    "current bundle 9.7.57 / engine 1.9.64"

185 cuts of drift, with no signal. This gate does not demand a re-read. It demands that the monolith
state, truthfully, how far behind it is.

Checks
  1. the monolith exists and names a `vetted against` bundle version
  2. the `current bundle X / engine Y` parenthetical, if present, matches the live pyproject/BUILD_STAMP
  3. the drift (live bundle patch - vetted patch) is reported, and fails above --max-drift
  4. no retired doctrine is present (assembly tiers 66/50/33, per-BGC BSL-2 flagging, AS_SCRUB,
     the PUBLIC/PRIVATE figure divider) — these are the decisions the project has explicitly reversed

Exit 0 = fresh enough and doctrinally current. Exit 1 = stale anchor or retired doctrine. Exit 2 = missing.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
MONOLITH = ROOT / "docs" / "SAPOTE_MAMEY_BUNDLE_MONOLITH.md"

# Doctrine the project has explicitly retired. Presence in the parent design doc is a real defect:
# a fresh chat reads the monolith first.
RETIRED = {
    r"\b66%": "assembly tier thresholds 66/50/33 (retired; now GOOD>=70 / MODERATE>=45 / POOR>=20)",
    r"\b33%": "assembly tier thresholds 66/50/33 (retired)",
    r"BSL-?2": "per-BGC enediyne BSL-2 flagging (retired; engine emits a neutral [E-signal])",
    r"AS_SCRUB": "AS-series scrub (retired 2026-07-06: the AS cohort is public)",
    r"PRIVATE \(AS-": "AS- as a private identifier (retired: release-tier and figure-tier both public)",
}


def _live_bundle() -> str:
    m = re.search(r'bundle_version\s*=\s*"([0-9.]+)"', (ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return m.group(1) if m else ""


def _patch(v: str) -> int:
    try:
        return int(v.split(".")[-1])
    except (ValueError, IndexError):
        return -1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-drift", type=int, default=60,
                    help="fail when the monolith's vetted bundle trails the live bundle by more than N patches")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    if not MONOLITH.is_file():
        emit("check_monolith_freshness: docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md is missing", file=sys.stderr)
        return 2

    text = MONOLITH.read_text(encoding="utf-8")
    live = _live_bundle()
    problems: list[str] = []

    # Two anchors are honest, and they mean different things:
    #   "vetted against bundle vX"      -> a full read-through (expensive; done at checkpoints)
    #   "spot-vetted against bundle vX" -> a targeted check (doctrine + anchor + dangling refs)
    # Drift is measured from whichever is newer. A spot-vet does not pretend to be a read-through.
    m_full = re.search(r"(?<!spot-)vetted against bundle v([0-9.]+)", text)
    m_spot = re.search(r"spot-vetted against bundle v([0-9.]+)", text)
    if not (m_full or m_spot):
        problems.append("no `vetted against bundle vX.Y.Z` anchor line — the monolith must say what it was read against")
        vetted = ""
    else:
        cands = [x.group(1) for x in (m_full, m_spot) if x]
        vetted = max(cands, key=_patch)

    # the parenthetical "current bundle X / engine Y" must not lie
    m2 = re.search(r"current bundle ([0-9.]+)\s*/\s*engine ([0-9.]+)", text)
    if m2 and m2.group(1) != live:
        problems.append(f"anchor claims `current bundle {m2.group(1)}` but the live bundle is {live} "
                        f"— either update the line or delete it (pyproject.toml is authoritative)")

    drift = _patch(live) - _patch(vetted) if vetted else -1
    if vetted and drift > a.max_drift:
        problems.append(f"vetted against v{vetted}, live is v{live} — {drift} patches of drift "
                        f"(max {a.max_drift}). Re-read, or restate the anchor honestly.")

    # v9.7.243: negation-aware, the same lesson as the novelty lint's denial guard. A sentence that
    # DENIES a retired doctrine ("no AS_SCRUB", "BSL-2 flagging retired") is the correct state, not a
    # violation. Look only at the local window before the match. My first version flagged its own
    # freshly-written "no per-BGC BSL-2 flagging" line.
    _DENY = re.compile(r"\b(no|not|never|without|retired|removed|dropped|superseded)\b", re.I)
    # BC2-CMF-01 (v9.7.396): RETIRED's patterns were matched via bare re.finditer(pat, text) with
    # no re.I, unlike _DENY right above (already re.I). This monolith is explicitly "hand-
    # maintained" and "reviewed at checkpoints" (this module's own docstring) -- casual prose
    # referencing a retired flag or phrase in a different case (e.g. "as_scrub is still checked"
    # instead of "AS_SCRUB") is a genuinely plausible authoring variance in a large human-edited
    # doc, unlike a machine-emitted identifier with fixed casing. Reproduced: a monolith positively
    # asserting "as_scrub is still checked before every cut" (a real, un-negated retired-doctrine
    # statement, lowercase) reported a clean PASS on pristine .395 -- exactly the "anchor drifting
    # silently... with no signal" failure class this tool's own docstring says it exists to
    # prevent, just for case instead of version staleness.
    for pat, why in RETIRED.items():
        for m3 in re.finditer(pat, text, re.I):
            window = text[max(0, m3.start() - 60):m3.start()]
            # v9.7.374: a fixed 60-char blind lookback can cross a sentence boundary and pick up
            # a negation word that denies something else entirely -- e.g. "We never rely on manual
            # triage today. Assembly tiers are still 66% ..." has "never" inside the 60-char window
            # but it negates the FIRST sentence, not the doctrine assertion in the second. Trim the
            # window back to the start of its own sentence/clause so only a same-sentence negation
            # can count as a denial.
            boundary = max(window.rfind("."), window.rfind("!"), window.rfind("?"), window.rfind("\n"))
            if boundary != -1:
                window = window[boundary + 1:]
            if _DENY.search(window):
                continue                       # a denial, not an assertion
            problems.append(f"retired doctrine present ({pat}): {why}")
            break

    if not a.quiet:
        emit(f"monolith: vetted v{vetted or '?'} | live v{live} | drift {drift if drift >= 0 else '?'} patches "
              f"| {len(text):,} chars")
    if problems:
        emit("check_monolith_freshness: FAIL")
        for p in problems:
            emit(f"  - {p}")
        return 1
    if not a.quiet:
        emit("check_monolith_freshness: PASS (anchor honest, no retired doctrine)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
