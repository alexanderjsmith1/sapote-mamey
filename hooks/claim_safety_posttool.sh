#!/usr/bin/env bash
# PostToolUse hook (Write|Edit|MultiEdit) — write-time claim-safety guardrail (ADVISORY, never blocks).
# Runs the claim-safety linter + the majority-read-aware named-compound guard on the SINGLE file just
# written, so an overclaim surfaces immediately (not 90 min later at Stop). Scoped to report artefacts
# under 'strain_data/'; exempts patch cards / scratchpad / the guard tooling itself to stay quiet.
ROOT="${SAPOTE_WORKSPACE_ROOT:-${CLAUDE_PROJECT_DIR:-$PWD}}"
PY="$ROOT/Tools/bin/python3"; [ -x "$PY" ] || PY="python3"
# extract the written file path from this hook's stdin JSON
FP=$("$PY" -c 'import sys,json;
try:
    d=json.load(sys.stdin); print((d.get("tool_input",{}) or {}).get("file_path","") or "")
except Exception:
    print("")' 2>/dev/null)
[ -z "$FP" ] && exit 0
low=$(printf '%s' "$FP" | tr '[:upper:]' '[:lower:]')
case "$low" in
  *.md|*.csv|*.txt|*.tsv|*.docx) : ;;
  *) exit 0 ;;
esac
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
SCOPE_ARGS=(--path "$FP" --root "$ROOT")
[ -n "${SAPOTE_DELIVERABLE_ROOT:-}" ] && SCOPE_ARGS+=(--report-root "$SAPOTE_DELIVERABLE_ROOT")
if ! PYTHONDONTWRITEBYTECODE=1 "$PY" "$HOOK_DIR/claim_safety_scope.py" "${SCOPE_ARGS[@]}"; then
  exit 0
fi
case "$low" in
  *"patches for next cut"*|*"/scratchpad"*|*"_provenance"*|*"guardrail"*|*"claim_safety"*) exit 0 ;;
esac
[ -f "$FP" ] || exit 0
"$PY" "$ROOT/Tools/claim_safety_check.py" --quiet-if-clean "$FP" 2>/dev/null || true
"$PY" "$ROOT/Tools/guardrail_named_compound.py" --quiet-if-clean "$FP" 2>/dev/null || true
exit 0
