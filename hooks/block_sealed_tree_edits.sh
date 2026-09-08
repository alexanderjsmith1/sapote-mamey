#!/usr/bin/env bash
# GUARDRAIL (a contributor lane, 2026-08-05): a SEALED cut tree is immutable. This PreToolUse hook
# (matcher: Write|Edit|MultiEdit|NotebookEdit) DENIES any file write whose target lives inside a
# sealed `sapote-mamey-vX.Y.Z-CODE-<build>` tree. Sealed trees are integrity-tracked by
# SOURCE_CHECKSUMS; editing one in place silently breaks the checksum manifest and the audit trail.
# The correct workflow is: copy the tree to a working dir (rsync) OR verify a change with
# cut_audit.py rebase-verify, and stage the change as a patch card under "Patches for next cut ...".
#
# Deliberately NOT blocked (these are working/staging areas, not the sealed cut):
#   * anything under a "Patches for next cut ..." folder (incl. candidate_cut_* assembly)
#   * scratchpad / build* working copies, and /tmp / /private/tmp
#   * the .zip itself (not an editable path)
# FAIL-CLOSED (v9.7.367 candidate, Indigo2 JOB-B): an internal error in a BLOCKING guardrail must
# DENY, not silently allow. Deny is a stdout JSON decision (exit 0), so plain `set -e` alone would
# still fail OPEN (nonzero without deny JSON = non-blocking error). Strict mode + ERR trap that
# EMITS the deny decision.
set -euo pipefail
_fail_closed() {
  printf '%s' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"GUARDRAIL INTERNAL ERROR in block_sealed_tree_edits.sh - failing CLOSED. The hook itself broke (python3 missing? grep error?), not your command. Fix the hook, then retry."}}'
  exit 0
}
trap _fail_closed ERR
# .402 jq-family port (ROSTER_402 seed #1): payload parse via python3 stdlib, not jq —
# with jq absent this fail-closed guard denied EVERY command with a misleading internal
# error. python3 is the bundle's own hard dependency; a malformed payload still exits
# nonzero -> ERR trap -> deny (unchanged fail direction).
input=$(cat)
path=$(printf '%s' "$input" | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
ti = d.get("tool_input") or {}
sys.stdout.write(ti.get("file_path") or "")')
[ -z "$path" ] && exit 0

# is the target inside a sealed CODE tree?  (build stamp form: -CODE-2026....)
if printf '%s' "$path" | grep -qE 'sapote-mamey-v[0-9.]+-CODE-[0-9]'; then
  # ...but allow working/staging locations
  if printf '%s' "$path" | grep -qiE 'Patches for next cut|candidate_cut|/scratchpad/|/build[0-9]|/tmp/|/private/tmp/|\.orig$'; then
    exit 0
  fi
  printf '%s' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED by guardrail: that path is inside a SEALED cut tree (sapote-mamey-vX.Y.Z-CODE-...). Sealed trees are immutable — editing in place breaks SOURCE_CHECKSUMS and the audit trail. Copy the tree to a working dir (rsync), make the change there, verify with cut_audit.py rebase-verify, and stage it as a patch card under \"Patches for next cut Sapote Mamey (vX)/\". Never hand-edit a sealed cut. See memory: never-make-the-actual-cut, check-before-create."}}'
fi
exit 0
