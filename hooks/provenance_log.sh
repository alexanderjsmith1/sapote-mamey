#!/usr/bin/env bash
# PostToolUse hook — logs every file Write/Edit to the provenance firehose (when/where/which-chat).
# Passes the tool-use JSON (this hook's stdin) straight to the python logger. Never blocks.
ROOT="${SAPOTE_WORKSPACE_ROOT:-${CLAUDE_PROJECT_DIR:-$PWD}}"
LOG="$ROOT/strain_data/_PROVENANCE/AUTO_FILE_LOG.tsv"
MARKER="$ROOT/.claude/current_chat_color"
CHAT="unattributed"; [ -f "$MARKER" ] && CHAT=$(tr -d '\n' < "$MARKER")
python3 "$ROOT/.claude/hooks/provenance_log.py" "$LOG" "$CHAT" 2>/dev/null
exit 0
