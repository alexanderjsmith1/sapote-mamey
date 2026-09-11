#!/usr/bin/env bash
# GUARDRAIL (2026-08-06, after F04/F05): a candidate handoff zip must be gated on a FRESH FULL-suite
# green run — not just a card's focused tests. F04/F05 passed its 18 focused tests but regressed 13
# seal/package tests that only the full suite caught. This PreToolUse(Bash) hook DENIES zipping a
# `candidate_cut_*` handoff unless a marker `<candidate>/_CANDIDATE_NOTES/.fullsuite_green` exists AND
# is newer than the newest *.py in the candidate tree (any source edit since the last green run
# invalidates it). The builder writes the marker after a green `pytest tests/ -q`.
# .402 jq-family port (ROSTER_402 seed #1): payload parse via python3 stdlib, not jq —
# jq is absent in clean/container shells and the silent-empty form disarmed this hook
# there. Same repair shape as bgc_node_name_guard (.401 seal-gate repair).
input=$(cat 2>/dev/null) || input=""
cmd=$(printf '%s' "$input" | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = d.get("tool_input") or {}
sys.stdout.write(ti.get("command") or "")' 2>/dev/null || true)
[ -z "$cmd" ] && exit 0

# NARROWED 2026-08-07 (the review lane): only gate a real ARCHIVE-CREATION command, not any command that merely
# CONTAINS the substring "zip"/"tar" (e.g. a card named gov_zip_allowlist, or a `rm *.zip`, or a heredoc that
# says "re-zip"). This was false-blocking read-only listings + rm + doc writes. Fix mirrors the other hooks.
# 1) skip heredocs + file-writes (mention != action)
printf '%s' "$cmd" | grep -qE '<<[-]?[A-Za-z_'"'"'"]|(^|[^a-zA-Z])(cat|tee|printf|echo)[[:space:]]+.*(>>?|\|)' && exit 0
# 2) require zip/ditto/tar as a COMMAND at command position (start, or after ; & | && then), not a substring
printf '%s' "$cmd" | grep -qE '(^|[;&|]|&&|\bthen)[[:space:]]*(zip|ditto|tar)[[:space:]]' || exit 0
# 3) skip extraction/read (unzip, tar -x) — only creation gates
printf '%s' "$cmd" | grep -qE '(^|[^a-z])(unzip)([^a-z]|$)|(^|[;&|]|&&|\bthen)[[:space:]]*tar[[:space:]]+[^|]*-[a-z]*x' && exit 0
# 4) must target a candidate_cut_* tree
printf '%s' "$cmd" | grep -qE 'candidate_cut_' || exit 0

name=$(printf '%s' "$cmd" | grep -oE 'candidate_cut_[A-Za-z0-9._-]+' | head -1)
[ -z "$name" ] && exit 0

root="${SAPOTE_WORKSPACE_ROOT:-${CLAUDE_PROJECT_DIR:-$PWD}}"
# locate the candidate dir under any "Patches for next cut ..." queue (absolute; cwd-independent)
cand=$(find "$root" -maxdepth 3 -type d -name "$name" 2>/dev/null | head -1)
[ -z "$cand" ] && exit 0   # can't resolve → don't block (fail-open on locate)

# --- guardrail-hook integrity gate (VGP .371) -------------------------------------------------------
# Before a candidate bundle is zipped, verify its OWN hook set is complete + portable: every
# bundle-scoped hook in its HOOKS_MANIFEST.tsv ships in hooks/, none hardcode the workspace root without
# an env-var fallback, no cruft. Self-contained (`verify --tree`), so no dependency on the live .claude.
# Fail-open if the tool/manifest isn't in the candidate (older candidates predate the hook system).
htool="$cand/sapote_hooks/sapote_hooks.py"
if [ -f "$htool" ] && [ -f "$cand/sapote_hooks/HOOKS_MANIFEST.tsv" ]; then
  if ! hg=$(python3 "$htool" verify --tree "$cand" --gate 2>&1); then
    hreason="BLOCKED before packaging: guardrail-hook integrity gate FAILED for $name.

$hg

Every bundle-scoped hook in HOOKS_MANIFEST.tsv must ship in hooks/ and be portable. Resolve each finding
(ship the missing hook into hooks/, or re-scope it to 'workspace' in the manifest; fix any NON-PORTABLE
hardcoded root), then re-zip. (Workspace cruft is advisory and does not fail this gate.)"
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":%s}}' "$(printf '%s' "$hreason" | python3 -c 'import json,sys; sys.stdout.write(json.dumps(sys.stdin.read()))')"
    exit 0
  fi
fi
# --------------------------------------------------------------------------------------------------

marker="$cand/_CANDIDATE_NOTES/.fullsuite_green"
newest_py=$(find "$cand" -name '*.py' -not -path '*/__pycache__/*' -newer "$marker" 2>/dev/null | head -1)

# PASS only if the marker exists and no .py is newer than it
if [ -f "$marker" ] && [ -z "$newest_py" ]; then
  exit 0
fi

reason="BLOCKED by guardrail: package a candidate ONLY after a FRESH FULL-suite green run (not just a card's focused tests — F04/F05 passed its focused suite but regressed 13 tests the full suite caught). "
if [ ! -f "$marker" ]; then
  reason+="No green marker found. "
else
  reason+="A source file changed after the last green run (marker is stale). "
fi
reason+="Run: cd '$cand' && Tools/bin/python3 -m pytest tests/ -q  (expect 0 failed), then: touch '$marker'  — then re-zip."
printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":%s}}' "$(printf '%s' "$reason" | python3 -c 'import json,sys; sys.stdout.write(json.dumps(sys.stdin.read()))')"
exit 0
