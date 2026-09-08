#!/usr/bin/env bash
# GUARDRAIL CANDIDATE (the review lane, 2026-08-10) — NOT YET WIRED. Structural hook work routes through the patch lane.
#
# WHY: on 2026-08-10 the review lane launched a correlated subquery over the 522,894-row BLASTp store, left it
# unattended for 60 minutes at 97% CPU, and blocked another chat's migration. the Developer or User found out from the other
# chat, not from the chat that did it. the Developer or User: "That should be COMMON SENSE."
#
# This PreToolUse Bash hook DENIES the two mechanically-detectable forms of that mistake:
#   (A) touching the LIVE blastp.sqlite  -> take a .backup snapshot and query the copy
#   (B) detaching a process (nohup / trailing &) -> unattended compute needs the Developer or User's approval first
#
# It deliberately does NOT try to guess "is this query slow?" — that is not decidable from a string and
# false positives would train people to ignore the hook. It blocks the two things that actually went wrong.
#
# Reading, ls-ing, greping, and documenting the store are ALL still allowed. Only live-DB *access* and
# detachment are denied.

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

# Scan only the part BEFORE any heredoc (<<): a heredoc BODY is document CONTENT written to a file, never
# an executed write/detach target. Without this, a STATE-log append whose body merely mentions "nohup" or
# "blastp.sqlite" false-triggers the guards below (observed 2026-08-19, the roster lane). No heredoc =>
# scan == cmd (behavior unchanged). Residual: a heredoc-write itself backgrounded with a trailing & after
# the closing marker won't be caught — an accepted edge (the harness background mechanism is the sanctioned
# path, and non-heredoc & / nohup are still caught).
scan="${cmd%%<<*}"

deny() {
  # shellcheck disable=SC2016
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":%s}}' "$1"
  exit 0
}

json_escape() { printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

# ---------------------------------------------------------------- (A) live BLASTp store
# Allow the sanctioned escape hatch: taking a snapshot (".backup") is exactly what we want people to do.
if printf '%s' "$scan" | grep -qiE 'blastp\.sqlite'; then
  if ! printf '%s' "$scan" | grep -qiE '\.backup|blastp_snapshot|scratchpad'; then
    deny "$(json_escape 'BLOCKED: do not query the LIVE "BLASTp Database/blastp.sqlite" — the BLASTp runners write to it continuously, and a long read blocks them (this happened 2026-08-10: 60 min at 97% CPU blocked another chat).

Take a snapshot and query the copy instead:
  sqlite3 "BLASTp Database/blastp.sqlite" ".backup '"'"'<scratchpad>/blastp_snapshot.sqlite'"'"'"
  sqlite3 <scratchpad>/blastp_snapshot.sqlite "SELECT ..."

Sanity check on any snapshot: SELECT SUM(hit_any) FROM gene_coverage  ->  25681 of 29635 genes.
Reading/greping/ls-ing the file is fine; querying the live DB is not.')"
  fi
fi

# ---------------------------------------------------------------- (B) unattended / detached compute
# nohup, or a trailing & at the end of the command (not inside a string, not && ).
if printf '%s' "$scan" | grep -qE '(^|[[:space:];|])nohup[[:space:]]' \
   || printf '%s' "$scan" | grep -qE '[^&>]&[[:space:]]*$'; then
  deny "$(json_escape 'BLOCKED: do not detach or background a process without the Developer or User'"'"'s explicit approval.

Standing rule (the Developer or User, 2026-08-10): anything long-running or CPU-heavy — full-corpus scans, correlated
subqueries, tree/GToTree runs, re-runs — is ASKED FOR FIRST, stating expected runtime and what it locks.
Nothing runs unattended.

If it genuinely needs to run: say so in the reply, state the cost, get approval, then run it in the
foreground where it is visible — or use the harness background-task mechanism, which is tracked.')"
fi

exit 0
