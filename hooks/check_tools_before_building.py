#!/usr/bin/env python3
"""check_tools_before_building.py — PreToolUse advisory: before a Write creates a brand-new
`.py` file outside this bundle's own `tools/`/`mamey/`, surface any shipped tool whose name
shares a concept token with the new file, so a script isn't independently re-derived when the
engine already ships one.

ROSTER_401_SEEDS.md item 2 (Alex-assigned to BC2, from VGP's 2026-09-02 self-audit, "audit
control #1, the highest-value change"): VGP independently re-derived `rggmci.py`,
`rggmci_cohort_rollup.py`, `build_reconstruction.py`, and `cohort_leads_ledger.py` — all four
already ship in the sealed bundle (confirmed: `mamey/rggmci.py`, `tools/rggmci_cohort_rollup.py`,
`tools/build_reconstruction.py`, `mamey/cohort_leads_ledger.py`) — apparently without checking
first. Same "check before create" house rule this project already states behaviorally
(memory: check-before-create, check-local-assets-before-download), mechanized here as an
advisory hook rather than left purely to memory/habit.

Design notes:
  * Advisory ONLY — never denies. `permissionDecision: "allow"` with `permissionDecisionReason`
    set to the reminder text; the Write always proceeds. Denying would fight legitimate new
    work, which the roster seed explicitly rules out ("deny would fight legitimate new work").
  * Scoped to Write only (not Edit/MultiEdit): those tools require an already-existing file by
    construction, so they can never create the brand-new file this hook cares about.
  * "New" is checked directly against the filesystem (target path does not yet exist) —
    PreToolUse timing is what makes this check trivial and race-free; a PostToolUse hook would
    have to infer "was this newly created" after the fact, which is fragile.
  * Fires only when the target is OUTSIDE this bundle's own `tools/`/`mamey/` — a new module
    added directly inside those directories is already covered by
    `tools/check_module_accretion.py` (mamey/) and ordinary code review (tools/); the gap this
    hook closes is specifically standalone analysis scripts built elsewhere (a workspace-level
    folder, a patch card, a scratch dir) that duplicate bundle functionality nobody checked for.
  * The tool count and concept-token index are computed live from the real `tools/`/`mamey/`
    listing every run — never hardcoded, so this reminder can't itself go stale the way a
    hardcoded "N tools" count would (this round's own recurring lesson about generated-vs-
    hardcoded counts).
  * This is the FIRST advisory (non-deny) PreToolUse hook in this bundle's hook set — every
    existing PreToolUse hook here (`overclaim_guard.py`, `block_sealed_tree_edits.sh`, etc.)
    only ever emits `deny` or stays silent. `permissionDecision: "allow"` with a
    `permissionDecisionReason` is a real, documented Claude Code hook capability, but its
    end-to-end visual rendering could not be verified against the live harness from inside this
    audit lane — only the JSON shape and the underlying matching logic are directly testable
    here. Worth a real end-to-end smoke test by whoever applies this card.

Fails OPEN: any parse error / unexpected shape exits 0 silently (matches this bundle's other
guardrail hooks' stated contract).
"""
from __future__ import annotations
import sys, json, re
from pathlib import Path

BUNDLE_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = BUNDLE_ROOT / "tools"
MAMEY_DIR = BUNDLE_ROOT / "mamey"

_MIN_TOKEN_LEN = 3


def _concept_tokens(stem: str) -> list[str]:
    """Split a filename stem into lowercase word tokens for a fuzzy concept match --
    'cohort_leads_ledger' -> ['cohort', 'leads', 'ledger']. Tokens shorter than
    _MIN_TOKEN_LEN are dropped (too noisy to be a meaningful concept signal on their own:
    'id', 'to', 'a', 'v2', ...)."""
    parts = re.split(r"[_\-]+", stem.lower())
    return [p for p in parts if len(p) >= _MIN_TOKEN_LEN]


def _existing_py_stems() -> list[str]:
    """Discover existing module names recursively for duplicate warnings."""
    stems: list[str] = []
    for d in (TOOLS_DIR, MAMEY_DIR):
        if d.is_dir():
            for p in d.rglob("*.py"):
                if any(part.startswith(".") or part == "__pycache__" for part in p.relative_to(d).parts):
                    continue
                stems.append(p.stem)
    return stems


def _concept_matches(new_stem: str, existing: list[str]) -> list[str]:
    """Existing stems sharing a concept token with `new_stem`, ranked most-relevant first.

    Caught live against the real bundle before staging: a plain alphabetical sort buried the
    single most relevant hit -- 'cohort_leads_ledger' (the real E1 near-duplicate) fell past
    the 8-item preview truncation behind generic 'cohort_*'/'build_*' matches that only share
    one weak token. Ranked by (exact stem match, then number of matching tokens, then name for
    determinism) so the closest match is always visible even when the preview is capped.
    """
    tokens = _concept_tokens(new_stem)
    if not tokens:
        return []
    new_low = new_stem.lower()
    scored = []
    for name in existing:
        low = name.lower()
        overlap = sum(1 for tok in tokens if tok in low)
        if overlap == 0:
            continue
        exact = 1 if low == new_low else 0
        scored.append((exact, overlap, name))
    scored.sort(key=lambda t: (-t[0], -t[1], t[2]))
    seen: set[str] = set()
    ranked: list[str] = []
    for _, _, name in scored:
        if name not in seen:
            seen.add(name)
            ranked.append(name)
    return ranked


def _new_py_target_outside_bundle_dirs(path_str: str) -> Path | None:
    """The resolved Path if `path_str` is a brand-new .py file outside tools/ and mamey/;
    None if it doesn't qualify (wrong extension, already exists, or is itself inside one of
    those two directories)."""
    if not path_str or not path_str.lower().endswith(".py"):
        return None
    p = Path(path_str)
    if not p.is_absolute():
        p = Path.cwd() / p
    try:
        resolved = p.resolve()
    except OSError:
        return None
    if resolved.exists():
        return None  # an edit/overwrite of something already there, not a new file
    try:
        tools_resolved = TOOLS_DIR.resolve()
        mamey_resolved = MAMEY_DIR.resolve()
    except OSError:
        return None
    parents = resolved.parents
    if tools_resolved in parents or mamey_resolved in parents:
        return None
    return resolved


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # fail open
    if data.get("tool_name") != "Write":
        return 0
    ti = data.get("tool_input", {}) or {}
    target = _new_py_target_outside_bundle_dirs(ti.get("file_path", "") or "")
    if target is None:
        return 0
    try:
        existing = _existing_py_stems()
    except OSError:
        return 0
    if not existing:
        return 0
    hits = _concept_matches(target.stem, existing)
    if not hits:
        return 0
    preview = ", ".join(hits[:8])
    suffix = " …" if len(hits) > 8 else ""
    reason = (
        f"CHECK BEFORE BUILDING: this bundle ships {len(existing)} scripts in tools/+mamey/. "
        f"{len(hits)} shipped file(s) share a name concept with '{target.name}': "
        f"{preview}{suffix}. Before continuing, check whether one of these already does what "
        f"you're building -- grep its docstring or run "
        f"`ls tools/ mamey/ | grep -i <keyword>`. Not blocking; proceeding anyway is fine if "
        f"this is genuinely new work."
    )
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": "allow",
                                             "permissionDecisionReason": reason}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
