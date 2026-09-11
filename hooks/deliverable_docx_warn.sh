#!/bin/bash
# Stop hook (ADVISORY, never blocks): WARN when a DESIGNATED deliverable folder has a .md with
# no matching .docx. Folders opt in via .claude/deliverable_folders.txt (one relative path per
# line; blank lines and #comments ignored). This is only a nudge — the portable, canonical way
# to make the trio is:  Tools/bin/python3 Tools/render_deliverable.py --dir "<folder>"
# Per the portable-rules-principle, the capability lives in that tool; this hook just reminds.
# Fast by design: it only inspects the listed folders (no tree walk). Always exit 0 (no Stop loop).
ROOT="${SAPOTE_WORKSPACE_ROOT:-${CLAUDE_PROJECT_DIR:-$PWD}}"
LIST="$ROOT/.claude/deliverable_folders.txt"
[ -f "$LIST" ] || exit 0

missing=""
while IFS= read -r rel || [ -n "$rel" ]; do
  case "$rel" in ''|\#*) continue;; esac
  dir="$ROOT/$rel"
  [ -d "$dir" ] || continue
  while IFS= read -r md; do
    [ -f "${md%.md}.docx" ] || missing="$missing
  $rel/$(basename "$md")"
  done < <(find "$dir" -maxdepth 1 -type f -name '*.md' 2>/dev/null)
done < "$LIST"

if [ -n "$missing" ]; then
  echo "ℹ DELIVERABLE-DOCX: these designated-deliverable .md files have no matching .docx:$missing" >&2
  echo "  render the trio with: Tools/bin/python3 Tools/render_deliverable.py --dir \"<folder>\"" >&2
fi
exit 0
