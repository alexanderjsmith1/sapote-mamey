#!/bin/bash
# PostToolUse (Write|Edit) hook: when a .md file is written, verify its LOCAL file links resolve
# on disk and are %-encoded. Advisory WARN to stderr (exit 2 surfaces it to Claude so a broken
# link gets fixed BEFORE it reaches the Developer or User). Never blocks a different tool; only inspects .md.
# Portable capability lives in Tools/check_md_links.py; this hook just runs it on what was written.
ROOT="${SAPOTE_WORKSPACE_ROOT:-${CLAUDE_PROJECT_DIR:-$PWD}}"
PY="$ROOT/Tools/bin/python3"; [ -x "$PY" ] || PY=python3
CHK="$ROOT/Tools/check_md_links.py"
# .402 jq-family port (ROSTER_402 seed #1): payload parse via python3 stdlib, not jq —
# jq is absent in clean/container shells and the silent-empty form disarmed this hook
# there. Same repair shape as bgc_node_name_guard (.401 seal-gate repair).
inp=$(cat 2>/dev/null) || inp=""
fp=$(printf '%s' "$inp" | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = d.get("tool_input") or {}
sys.stdout.write(ti.get("file_path") or ti.get("notebook_path") or "")' 2>/dev/null || true)
case "$fp" in
  *.md) : ;;
  *) exit 0 ;;
esac
[ -f "$fp" ] && [ -f "$CHK" ] || exit 0
out="$("$PY" "$CHK" --quiet-if-clean "$fp" 2>/dev/null)"
if [ -n "$out" ]; then
  echo "⚠ MD-LINK: broken/un-encoded file link(s) in the .md just written —" >&2
  echo "$out" | sed 's/^/  /' >&2
  echo "  fix before showing the user; %20/%28/%29-encode spaces/parens and confirm the path exists." >&2
  exit 2
fi
exit 0
