#!/usr/bin/env bash
# guardrails_stop.sh — advisory Stop hook. Runs the FAST crown-jewel guardrail (no hard-excluded strain
# in the governed per-BGC master) on every turn end. Silent when clean; never blocks (always exits 0).
# Heavier guardrails (diff-integrity, no-fabrication, blastp-ingest) run on demand via Tools/guardrails.py.
ROOT="${SAPOTE_WORKSPACE_ROOT:-${CLAUDE_PROJECT_DIR:-$PWD}}"
PY="$ROOT/miniconda3/bin/python"
MASTER="$ROOT/strain_data/SAPOTE_PER_BGC_MASTER_all_AS.csv"
[ -x "$PY" ] || PY="python3"
if [ -f "$MASTER" ]; then
  out="$("$PY" "$ROOT/Tools/guardrails.py" exclusions "$MASTER" 2>/dev/null)"
  if echo "$out" | grep -q "FAIL"; then
    echo "⚠ GUARDRAIL: hard-excluded strain leaked into the governed master —" >&2
    echo "$out" | sed 's/^/  /' >&2
    echo "  fix: rerun 'strain_data/_rebuild_governed_master.py' (see Tools/GUARDRAILS.md)" >&2
  fi
fi
exit 0
