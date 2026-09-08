#!/usr/bin/env bash
# GUARDRAIL (installed 2026-08-04, after Claude Code overstepped and made an actual cut; tightened 2026-08-06):
# Claude Code NEVER RUNS the actual Sapote-Mamey seal scripts. The designated Patch Chat owns the seal
# (CUT_PROTOCOL rule 2). This PreToolUse Bash hook DENIES *executing* the seal scripts — but NOT merely
# reading/greping/ls-ing/documenting them (the old version blocked any mention, which broke audit work).
# Claude Code builds a CANDIDATE under the patches folder and hands off — nothing more.
# FAIL-CLOSED (v9.7.367 candidate, Indigo2 JOB-B): an internal error in a BLOCKING guardrail must
# DENY, not silently allow. Deny is a stdout JSON decision (exit 0), so plain `set -e` alone would
# still fail OPEN (nonzero without deny JSON = non-blocking error). Strict mode + ERR trap that
# EMITS the deny decision.
set -euo pipefail
_fail_closed() {
  printf '%s' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"GUARDRAIL INTERNAL ERROR in block_seal_commands.sh - failing CLOSED. The hook itself broke (python3 missing? grep error?), not your command. Fix the hook, then retry."}}'
  exit 0
}
trap _fail_closed ERR
# .402 jq-family port (ROSTER_402 seed #1): payload parse via python3 stdlib, not jq —
# with jq absent this fail-closed guard denied EVERY command with a misleading internal
# error. python3 is the bundle's own hard dependency; a malformed payload still exits
# nonzero -> ERR trap -> deny (unchanged fail direction).
input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
ti = d.get("tool_input") or {}
sys.stdout.write(ti.get("command") or "")')
[ -z "$cmd" ] && exit 0

# heredoc / file-write that merely CONTAINS the script name as text is not execution — allow.
printf '%s' "$cmd" | grep -qE '<<[-]?[A-Za-z_'"'"'"]' && exit 0

# EXECUTION patterns only:
#  (a) invoked via an interpreter:  bash|sh|zsh|source|exec|.  <path>release_cut.sh
#  (b) invoked as a command at a segment boundary (start, or after ; & | && ||):  ./release_cut.sh  / path/make_public_tier.sh
if printf '%s' "$cmd" | grep -qE '(^|[;&|]|\b(bash|sh|zsh|source|exec)\b)[[:space:]]*(\.?/?[A-Za-z0-9_./-]*)?(release_cut|make_public_tier)\.sh([[:space:]]|$|["'"'"'&;|])'; then
  printf '%s' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED by guardrail: Claude Code never RUNS the actual Sapote-Mamey seal. The designated Patch Chat owns the seal (CUT_PROTOCOL rule 2). Build a CANDIDATE under the patches folder and hand off. (Reading/greping the seal scripts is fine; executing release_cut.sh / make_public_tier.sh is not.) See memory: never-make-the-actual-cut."}}'
fi
exit 0
