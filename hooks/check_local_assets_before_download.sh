#!/usr/bin/env bash
# GUARDRAIL (2026-08-06): stop chats re-downloading / re-deriving data that is ALREADY LOCAL.
# Recurring, widespread issue — e.g. a chat tried to fetch ~2 GB of Pfam-A HMM that lives in BigSCAPE/.
# PreToolUse(Bash): if the command is a download (wget/curl/aria2/pip download/datasets/hmmfetch/gtdbtk/…)
# AND it names an asset registered in OFFICIAL_DATA/ASSET_REGISTRY.tsv, DENY and print the local path.
# Read-only network ops that don't match a registered asset pass untouched. Fail-open on any error.
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

# skip file-WRITES / heredocs / doc-generation — a `cat >> f <<EOF … download … EOF` mentions assets and
# download-words as CONTENT, it does not fetch anything. Only real fetch commands should be gated.
printf '%s' "$cmd" | grep -qE '<<[-]?[A-Za-z_'"'"'"]|(^|[^a-zA-Z])(cat|tee|printf|echo)[[:space:]]+.*(>>?|\|)' && exit 0

# quick pre-filter: only engage if this looks like a fetch OR a run-style invocation of a compute
# tool whose RESULTS are registered (2026-08-17 the Developer or User-flagged incident: a chat recommended re-running
# BiG-SCAPE with 5.3G of results registered on disk). Run-signature = tool name + flag/subcommand,
# so `ls BigSCAPE/`, docs, and greps never engage.
printf '%s' "$cmd" | grep -qiE '(wget|curl|aria2|ncbi-genome-download|datasets +download|pip +(download|install)|hmmfetch|git +lfs|gtdbtk +.*data|rsync +.*::|(bigscape|gtotree|antismash|clinker)([[:space:]]+-|[[:space:]]+cluster)|run_bigscape|bigscape\.py|antismash\.py)' || exit 0

ROOT="${CLAUDE_PROJECT_DIR:-${SAPOTE_WORKSPACE_ROOT:-$PWD}}"
PY="$ROOT/Tools/bin/python3"; [ -x "$PY" ] || PY=python3
FINDER="$ROOT/Tools/find_asset.py"
[ -f "$FINDER" ] || exit 0

# ask the resolver whether this download is redundant (exit 3 = yes, with details on stderr)
detail=$("$PY" "$FINDER" --check "$cmd" 2>&1); rc=$?
[ "$rc" -eq 3 ] || exit 0

reason="BLOCKED by guardrail: this data is ALREADY LOCAL — do not re-download it. $(printf '%s' "$detail" | tr '\n' ' ' | tr '\t' ' ')  Point your tool at that path, or run: Tools/bin/python3 Tools/find_asset.py <keyword>  to confirm. (If you truly need a different/newer version, say so explicitly.)"
printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":%s}}' "$(printf '%s' "$reason" | python3 -c 'import json,sys; sys.stdout.write(json.dumps(sys.stdin.read()))')"
exit 0
