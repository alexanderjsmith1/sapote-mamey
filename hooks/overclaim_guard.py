#!/usr/bin/env python3
"""PreToolUse guardrail — BLOCK a Write/Edit that ships an UNQUALIFIED product-identity overclaim.

Tiered guardrails, the "teeth" layer. Narrow by design: it blocks ONLY the two egregious constructions
  * KNOWN -> <compound> / KNOWN: <compound>   (a per-gene MIBiG anchor written as the product)
  * produces/synthesizes <compound>           (biosynthesis asserted as fact)
when the offending line carries NO claim-safety qualifier AND the file has no override token. Everything
else passes. Scoped to REPORT artefacts (.md/.csv/.txt/.docx) under the canonical deliverable-
report home -- 'strain_data/', or the structurally-discovered / $SAPOTE_DELIVERABLE_ROOT root,
see in_report_scope() below; patch cards, scratchpad, code, and docs that quote a defect are
exempt (they legitimately contain the pattern).

Override: put `CLAIM_SAFETY_OVERRIDE` anywhere in the file (e.g. when documenting a defect as an example).

Fails OPEN: any parse error / unexpected shape exits 0 (never break a write because the hook hiccuped).
Block mechanism: emits the PreToolUse `permissionDecision: deny` JSON (matching block_sealed_tree_edits.sh).
"""
import sys, json, re, os

# Reuse link_check.py's portable deliverable-hub-root discovery (same directory, same
# convention: $SAPOTE_DELIVERABLE_ROOT override, else the single workspace subdirectory that
# owns WHERE_THINGS_LIVE.md, else legacy strain_data/) instead of a second, independent
# reimplementation of "find the canonical report home" -- this hook's own docstring already
# names strain_data/ as one such home, and duplicating discovery logic across sibling hooks is
# exactly the bug family this round already found and fixed five times over (see the
# save_transcript.py / block_subagent_spawn.py / session_cost_ledger.py cards). Imported
# defensively: this hook's own contract is "fail OPEN on any parse error / unexpected shape",
# so a missing or renamed sibling file must not crash it -- it degrades to the bare
# 'strain_data' path-component check instead.
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from link_check import deliverable_hub_root
except Exception:
    deliverable_hub_root = None

WORKSPACE = os.environ.get("SAPOTE_WORKSPACE_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

QUALIFIER = re.compile(r"family|resembl|anchor|class[- ]level|candidate|putative|not a product call|"
                       r"capacity|similar|~|≈|convergen|hypothes|weak|minority|promiscuous|flagged|"
                       r"predicted", re.I)
COMPOUND = r"[A-Z]?[A-Za-z][A-Za-z0-9'\-]{3,}"
KNOWN_ARROW = re.compile(r"\bKNOWN(?:_ANCHORED)?\b\s*(?:->|→|:)\s*(%s)" % COMPOUND)
PRODUCES = re.compile(r"\b(?:produces|synthesi[sz]es|biosynthesi[sz]es)\s+(%s)" % COMPOUND, re.I)
NEG = re.compile(r"\b(?:not|no|does not|doesn't|cannot|can't|without|rather than|no evidence)\b", re.I)
REPORT_EXT = (".md", ".csv", ".txt", ".docx")


def _path_components(path):
    """Lowercased path segments, independent of separator style (posix or windows) -- so a
    scope check can test real path components instead of raw substring containment (a marker
    like 'strain_data' should mean the directory segment, not any string that happens to embed
    those characters)."""
    return [seg for seg in path.replace("\\", "/").lower().split("/") if seg]


def in_report_scope(path):
    """Is this an in-scope report artefact -- one under the canonical deliverable-report home?

    v9.7.400 REDESIGN (Codex pool review): the prior scope check hardcoded this specific
    deployment's private folder name ('as strain master') as a raw substring test, alongside a
    second raw substring test for 'strain_data'. Neither generalizes to a differently-named or
    differently-laid-out workspace, and substring containment can match inside an unrelated,
    longer path segment rather than a genuine directory component. Replaced with: the engine's
    own documented, portable 'strain_data' directory-name convention, checked as an exact path
    component; OR the structurally-discovered deliverable-hub root (same resolver link_check.py
    uses, so one $SAPOTE_DELIVERABLE_ROOT setting configures both hooks), also checked as an
    exact path component. Verified live: on the current real workspace this resolves to the
    same root the old literal named, reached structurally rather than by a hardcoded name --
    no live coverage regression.

    $SAPOTE_DELIVERABLE_ROOT is checked directly here, not only through the imported helper:
    this hook's own card may be applied independently of link_check.py's (they are separate,
    independently-appliable patch cards), and confirmed by direct verification that the
    import-only path leaves the env-var override non-functional when link_check.py hasn't
    also been redesigned yet. Checking it here too means this hook's scope is fully
    functional on its own; the imported structural fallback is pure upside when both cards
    are applied together, never a hard dependency.
    """
    if not path.lower().endswith(REPORT_EXT):
        return False
    parts = _path_components(path)
    if "strain_data" in parts:
        return True
    env = os.environ.get("SAPOTE_DELIVERABLE_ROOT")
    if env:
        root_name = os.path.basename(env.rstrip("/\\")).lower()
        return bool(root_name) and root_name in parts
    if deliverable_hub_root is not None:
        try:
            root = deliverable_hub_root(WORKSPACE)
        except Exception:
            root = None
        if root:
            root_name = os.path.basename(root.rstrip("/\\")).lower()
            if root_name and root_name in parts:
                return True
    return False


def egregious_lines(content):
    out = []
    for i, line in enumerate(content.splitlines(), 1):
        s = line.strip()
        if not s or QUALIFIER.search(s) or NEG.search(s):
            continue
        m = KNOWN_ARROW.search(s) or PRODUCES.search(s)
        if m:
            out.append((i, m.group(0)))
    return out


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # fail open
    tool = data.get("tool_name", "")
    if tool not in ("Write", "Edit", "MultiEdit"):
        return 0
    ti = data.get("tool_input", {}) or {}
    path = ti.get("file_path", "") or ""
    if not in_report_scope(path):
        return 0
    low = path.lower()
    if any(x in low for x in ("patches for next cut", "/scratchpad", "_provenance", "guardrail",
                              "claim_safety", "flagged_lead_surfacing", "readme_and_bgc059")):
        return 0
    # gather the pending content
    if tool == "Write":
        content = ti.get("content", "") or ""
    elif tool == "Edit":
        content = ti.get("new_string", "") or ""
    else:  # MultiEdit
        content = "\n".join(e.get("new_string", "") for e in (ti.get("edits", []) or []))
    if "CLAIM_SAFETY_OVERRIDE" in content:
        return 0
    bad = egregious_lines(content)
    if not bad:
        return 0
    reason = ("BLOCKED by claim-safety guardrail: unqualified product-identity overclaim in a report ("
              + "; ".join(f"line {ln}: {txt}" for ln, txt in bad[:4])
              + "). A per-gene MIBiG anchor is a class-level SIMILARITY, never a product identity. "
                "Rewrite as '<compound> family (n/total genes); not a product call', OR add the token "
                "CLAIM_SAFETY_OVERRIDE to the file if you are deliberately quoting the defect as an example.")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
