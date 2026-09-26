#!/usr/bin/env bash
# PostToolUse hook — logs every file Write/Edit to the provenance firehose (when/where/which-chat).
# Passes the tool-use JSON (this hook's stdin) straight to the python logger. Never blocks.
ROOT="${SAPOTE_WORKSPACE_ROOT:-${CLAUDE_PROJECT_DIR:-$PWD}}"
LOG="$ROOT/strain_data/_PROVENANCE/AUTO_FILE_LOG.tsv"
python3 "$ROOT/.claude/hooks/provenance_log.py" "$LOG" 2>/dev/null
exit 0
