#!/usr/bin/env bash
# GUARDRAIL (2026-08-17, the Developer or User — third request for the same thing): guardrail infrastructure edited
# in the WORKSPACE must ALSO be staged into the Sapote-Mamey bundle patch queue. Sapote Mamey is a
# software product that replicates this workflow — a hook/tool/registry improvement that lives only
# in this workspace's .claude/ or Tools/ does NOT ship, so the product never learns it.
#
# PostToolUse(Write|Edit): if the edited file is guardrail infrastructure (.claude/hooks/*,
# Tools/*.py, OFFICIAL_DATA/ASSET_REGISTRY.tsv), remind that a matching card must exist in the
# OPEN patch queue, and say exactly where. Warn-only (never blocks); fail-open on any error.
set -u
ROOT="${CLAUDE_PROJECT_DIR:-${SAPOTE_WORKSPACE_ROOT:-$PWD}}"

inp=$(cat 2>/dev/null) || exit 0
# .402 jq-family port (ROSTER_402 seed #1): payload parse via python3 stdlib, not jq —
# jq is absent in clean/container shells and the silent-empty form disarmed this hook
# there. Same repair shape as bgc_node_name_guard (.401 seal-gate repair).
fp=$(printf '%s' "$inp" | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = d.get("tool_input") or {}
sys.stdout.write(ti.get("file_path") or "")' 2>/dev/null || true)
[ -z "$fp" ] && exit 0

case "$fp" in
  *"/.claude/hooks/"*|*"/Tools/"*.py|*"/OFFICIAL_DATA/ASSET_REGISTRY.tsv") : ;;
  *) exit 0 ;;
esac
# edits inside the patch queue or the bundle itself ARE the staging — don't nag those
case "$fp" in
  *"Patches for next cut"*|*"sapote-mamey-v9."*) exit 0 ;;
esac

# find the newest open patch-queue folder
queue=$(ls -d "$ROOT"/Patches\ for\ next\ cut\ Sapote\ Mamey\ \(v9.7.*\) 2>/dev/null | sort -V | tail -1)
base=$(basename "$fp")
staged=""
[ -n "$queue" ] && staged=$(grep -rl "$base" "$queue" 2>/dev/null | head -1)

if [ -n "$staged" ]; then
  exit 0   # something in the queue already references this file — assume staged
fi

cat <<EOF
REMINDER (the Developer or User standing rule, 2026-08-17): you just edited guardrail infrastructure
($base) in the WORKSPACE. Sapote Mamey is a software product replicating this
workflow — hooks, Tools/*.py, and the asset registry SHIP IN THE BUNDLE. Stage a
matching card NOW in: ${queue:-<open patch queue not found>}
Bundle targets: hooks/ (portable via \$SAPOTE_WORKSPACE_ROOT — see
tests/test_hooks_workspace_portability.py), tools/, and the registry as a
schema+example. Do not end the session with this unstaged.
EOF
exit 0
