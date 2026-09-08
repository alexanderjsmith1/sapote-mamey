#!/usr/bin/env bash
# GUARDRAIL (2026-08-06, after the .351 overstep): Claude Code must NEVER create a top-level folder
# that looks like a real Sapote-Mamey cut. The real release folder form is `Sapote Mamey vX.Y.Z/`
# (with a space) directly under the workspace root — that is what confused the Developer or User's team when Claude
# made one. Candidates ALWAYS live under `Patches for next cut Sapote Mamey (vX.Y.Z)/candidate_cut_*`.
#
# PreToolUse(Bash): DENY a create/copy/package op that WRITES a `Sapote Mamey v<digit>` folder anywhere
# NOT inside a "Patches for next cut ..." queue or a `candidate_cut_*` dir. Reading a sealed
# `sapote-mamey-*-CODE-*` tree as a SOURCE is unaffected.
#
# v9.7.355 (the review lane) — fixes two residual false-positives that survived the 2026-08-07 the patch lane narrowing,
# and closes one hole, by checking PER-ARGUMENT instead of on a space-broken token:
#   (E) a legit candidate path whose LAST segment is `Sapote Mamey vX` was DENIED, because the old
#       space-based token extraction (`[^"' ]*Sapote Mamey v...`) could not see the "Patches for next cut"
#       prefix (these folder names contain spaces). Now: the whole quoted arg is tested for a queue marker.
#   (F) `shasum ... "Sapote Mamey v9.7.354.zip"` was DENIED, because the verb regex matched `zip` as a  version-sync-ok
#       substring of the `.zip` extension. Now: the negative class excludes a leading `.` (`[^a-z.]`), so a
#       `.zip`/`.tar` FILENAME no longer counts as a packaging verb; a real `zip`/`tar` COMMAND still does.
#   (HOLE) `cp -R "<queue>/candidate_cut_x" "Sapote Mamey v9.7.355"` (create a top-level release folder in a  version-sync-ok
#       command that also names a candidate) was ALLOWED under a whole-command marker test. Per-argument, the
#       bare destination arg carries no marker → still DENIED.
# FAIL-CLOSED (v9.7.367 candidate, Indigo2 JOB-B): an internal error in a BLOCKING guardrail must
# DENY, not silently allow. Deny is a stdout JSON decision (exit 0), so plain `set -e` alone would
# still fail OPEN (nonzero without deny JSON = non-blocking error). Strict mode + ERR trap that
# EMITS the deny decision.
set -euo pipefail
_fail_closed() {
  printf '%s' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"GUARDRAIL INTERNAL ERROR in block_top_level_release_folder.sh - failing CLOSED. The hook itself broke (python3 missing? grep error?), not your command. Fix the hook, then retry."}}'
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

# Skip heredocs and file-writes (STATE saves, doc/memory writes): they mention version strings and words
# like "tar"/"zip" as TEXT, not as folder creation. (Kept from the patch lane narrowing.)
printf '%s' "$cmd" | grep -qE '<<[-]?[A-Za-z_'"'"'"]|(^|[^a-zA-Z])(cat|tee|printf|echo)[[:space:]]+.*(>>?|\|)' && exit 0

# Require a real create/copy/package verb as a COMMAND TOKEN — NOT a `.zip`/`.tar` file extension.
# The `.` in the negative class stops "backup.zip"/"x.tar" from matching the verbs zip/tar.
printf '%s' "$cmd" | grep -qE '(^|[^a-z.])(mkdir|cp|mv|rsync|ditto|install|zip|tar)([^a-z]|$)' || exit 0

# No space-form release-folder name at all → nothing to guard. (Note: the queue folder "Sapote Mamey (vX)"
# has a paren after the space, so it does NOT match `Sapote Mamey v[0-9]`; only the release form does.)
printf '%s' "$cmd" | grep -qE 'Sapote Mamey v[0-9]' || exit 0

deny=0
# Prefer PER-ARGUMENT checks. Release folders contain spaces, so in any real command they are quoted.
# For each quoted arg that names a `Sapote Mamey v<digit>` folder, allow it ONLY when that same arg also
# sits inside a queue ("Patches for next cut") or a candidate_cut_* dir. (Portable: no bash-4 `mapfile`.)
qcount=0
while IFS= read -r a; do
  [ -z "$a" ] && continue
  printf '%s' "$a" | grep -qE 'Sapote Mamey v[0-9]' || continue
  qcount=$((qcount+1))
  # v9.7.370 (the patch lane, hooks lane, the Developer or User-assigned 2026-08-18): an arg naming an EXISTING release
  # path is a REFERENCE to the real sealed folder (a read source / var assignment), not a creation —
  # a creation target does not exist yet. Writes INTO sealed trees are a different hook's job
  # (block_sealed_tree_edits.sh). Fixes the false-positive where reading FROM the sealed tree
  # (cp "<sealed>/file" "<queue>/file", or S="<sealed>" in a compound command) was denied twice
  # on 2026-08-18. The .355 HOLE case (cp <queue>/x "Sapote Mamey vX" — new top-level dest) still
  # denies: that destination does not exist.
  ap=${a#\"}; ap=${ap%\"}; ap=${ap#\'}; ap=${ap%\'}
  ap=${ap#*=}   # a quoted VAR="path" assignment: test the path part
  [ -e "$ap" ] && continue
  case "$a" in
    *"Patches for next cut"*|*candidate_cut*) : ;;   # inside a queue/candidate → allowed
    *) deny=1 ;;                                       # a bare/top-level release folder → deny
  esac
done < <(printf '%s' "$cmd" | grep -oE '"[^"]*"|'"'"'[^'"'"']*'"'"'')

# No quoted arg named a release folder (e.g. an unquoted path): fall back to a whole-command marker test.
if [ "$qcount" = 0 ]; then
  case "$cmd" in
    *"Patches for next cut"*|*candidate_cut*) : ;;
    *) deny=1 ;;
  esac
fi

if [ "$deny" = 1 ]; then
  printf '%s' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"BLOCKED by guardrail: do not create a top-level \"Sapote Mamey vX.Y.Z/\" folder — that mimics a real cut and confuses the team (the .351 overstep). Build a CANDIDATE under \"Patches for next cut Sapote Mamey (vX.Y.Z)/candidate_cut_*_AQUARIUS/\" and hand off a zip. The actual cut/seal is the Patch Chat + the Developer or User, never Claude Code. See memory: never-make-the-actual-cut, check-before-create."}}'
fi
exit 0
