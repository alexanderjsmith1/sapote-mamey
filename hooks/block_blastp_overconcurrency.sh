#!/usr/bin/env bash

cmd=$(python3 -c 'import json,sys
try:
    payload = json.load(sys.stdin)
    command = (payload.get("tool_input") or {}).get("command") or ""
    if isinstance(command, str): sys.stdout.write(command)
except (ValueError, AttributeError, TypeError):
    pass' 2>/dev/null)
[ -z "$cmd" ] && exit 0

printf '%s' "$cmd" | grep -qE 'nr_rid_runner\.py[[:space:]]+run' || exit 0

# Exempt INSPECTION commands, decided by what the command actually RUNS, not by whether an
# inspection word appears anywhere in it. Matching `grep`/`cat `/`kill ` as substrings let a real
# launch walk straight past the cap the moment it was piped or chained -- `... run --lane 3 | grep RID`
# and `... run --lane 3 && cat out.log` were both exempted while the bare launch was denied.
# Leading VAR=value assignments are skipped so `SAPOTE_BLASTP_MAX_LANES=12 python3 ...` is still a launch.
head_word=$(printf '%s' "$cmd" | python3 -c '
import shlex, sys, os
try:
    source = sys.stdin.read()
    if "$(" in source or "`" in source or "\n" in source:
        sys.stdout.write("compound")
        raise SystemExit(0)
    lexer = shlex.shlex(source, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    parts = list(lexer)
    separators = {";", "&&", "||", "|", "&"}
    if any(tok in separators for tok in parts):
        commands = [[]]
        for tok in parts:
            if tok in separators: commands.append([])
            else: commands[-1].append(tok)
        inspectors = {"ps", "pgrep", "pkill", "grep", "egrep", "rg", "kill", "tail", "cat", "head", "less", "wc", "awk", "sed"}
        safe = all(c and os.path.basename(c[0]) in inspectors for c in commands)
        sys.stdout.write("ps" if safe else "compound")
        raise SystemExit(0)
except ValueError:
    parts = []
for tok in parts:
    if "=" in tok and not tok.startswith(("-", "/")) and tok.split("=", 1)[0].replace("_", "").isalnum():
        continue          # leading environment assignment
    sys.stdout.write(os.path.basename(tok))
    break
' 2>/dev/null)
case "$head_word" in
  ps|pgrep|pkill|grep|egrep|rg|kill|tail|cat|head|less|wc|awk|sed) exit 0;;
esac

CAP="${SAPOTE_BLASTP_MAX_LANES:-10}"
case "$CAP" in *[!0-9]*|"") echo "Invalid BLASTp lane cap" >&2; exit 2;; esac
[ "$CAP" -ge 1 ] && [ "$CAP" -le 12 ] || { echo "BLASTp lane cap must be 1 through 12" >&2; exit 2; }
cmd_cap=$(printf '%s' "$cmd" | grep -oE 'SAPOTE_BLASTP_MAX_LANES=[0-9]+' | head -1 | cut -d= -f2)
if [ -n "$cmd_cap" ] && [ "$cmd_cap" -gt "$CAP" ] 2>/dev/null; then
  [ "$cmd_cap" -gt 12 ] && cmd_cap=12
  CAP="$cmd_cap"
fi

processes=$(ps -eo command 2>/dev/null) || { echo "Cannot inspect BLASTp runner count" >&2; exit 2; }
# Count the RUNNER, not the launcher. Anchoring on a leading `python` missed every ordinary
# wrapper -- `nohup python3 ... run`, `env python3 ... run`, `caffeinate -i python3 ... run`,
# `/bin/sh -c python3 ... run` and a shebang launch `./nr_rid_runner.py run` all counted as ZERO,
# so live lanes were invisible and the cap permitted more concurrent NCBI submitters than it says.
# Over-counting is the safe direction for this gate, so match the script token anywhere in the
# command line and only drop lines whose own executable is a text-search tool.
live=$(printf '%s\n' "$processes" \
  | grep -E 'nr_rid_runner\.py[[:space:]]+run' \
  | grep -vE '^([^ ]*/)?(grep|egrep|fgrep|rg|ag|ack)[[:space:]]' \
  | wc -l | tr -d ' ')
live=${live:-0}

deny() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":%s}}' "$1"
  exit 0
}
json_escape() { printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'; }

if [ "$live" -ge "$CAP" ]; then
  deny "$(json_escape "BLOCKED: $live BLASTp submitters already live; launching another would exceed the concurrency cap ($CAP).

docs/ONLINE_BLASTP_PROTOCOL.md §3: 'one submission at a time, poll on a delay.' On 2026-08-21, 43 concurrent lanes got NCBI-throttled for ~90 min. Keep the fleet small.

If you truly intend more (e.g. draining a backlog), raise the cap explicitly for this launch:
  SAPOTE_BLASTP_MAX_LANES=<n> <your command>
and watch blastp_health.py for submit-failures.")"
fi

if [ "$live" -ge 1 ] && ! printf '%s' "$cmd" | grep -qE 'sleep[[:space:]]+[0-9]+[[:space:]]*&&'; then
  deny "$(json_escape "BLOCKED: $live BLASTp runner(s) already live and this launch has no stagger — that risks simultaneous NCBI submissions (the 2026-08-21 mistake: 4 lanes fired RIDs within 6 seconds).

Prefix a stagger delay so first-submissions spread out, e.g.:
  sleep 90 && RID_QUERIES=... nr_rid_runner.py run ...
Stagger each additional lane by ~60-120s. The first lane (none live) needs no sleep.")"
fi

exit 0
