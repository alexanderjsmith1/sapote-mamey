#!/bin/bash
# Stop hook — AUTOSAVE the session transcript (INCLUDING inner-monologue/thinking blocks) to the
# CURRENT chat's color folder, so continuity survives compaction without anyone remembering to run it.
#
# Color-safe: `.claude/` is shared across all color chats, so this must NOT hardcode a color. It reads
# the session_id from the Stop-hook stdin payload and finds the color folder whose `.session_id` pins
# that session (the reliable per-session anchor; newest-mtime is unsafe with concurrent color chats).
# Fires ONLY for a session that is pinned to a color folder; otherwise it does nothing. Throttled so
# rapid turns don't re-render redundantly. Fully silent, never blocks the turn (exit 0 always).
ROOT="${SAPOTE_WORKSPACE_ROOT:-${CLAUDE_PROJECT_DIR:-$PWD}}"
THROTTLE_SECONDS=60

payload=$(cat 2>/dev/null)
sid=$(printf '%s' "$payload" | python3 -c "import sys,json;
try: print(json.load(sys.stdin).get('session_id',''))
except Exception: print('')" 2>/dev/null)
[ -z "$sid" ] && exit 0

# resolve color by matching the session pin
color=""
for d in "$ROOT/sessions"/*/; do
  [ -f "$d/.session_id" ] || continue
  if grep -q "$sid" "$d/.session_id" 2>/dev/null; then color=$(basename "$d"); break; fi
done
[ -z "$color" ] && exit 0   # not a pinned color chat -> leave it alone

# throttle: skip if the latest transcript was written within THROTTLE_SECONDS
latest="$ROOT/sessions/$color/TRANSCRIPTS/transcript_latest.md"
if [ -f "$latest" ]; then
  # v9.7.409 portability: `stat -f %m` is the BSD/macOS form; on GNU/Linux `-f` means
  # --file-system and errors, so mt fell back to 0 (throttle inert). Try BSD then GNU.
  now=$(date +%s); mt=$(stat -f %m "$latest" 2>/dev/null || stat -c %Y "$latest" 2>/dev/null || echo 0)
  [ $(( now - mt )) -lt "$THROTTLE_SECONDS" ] && exit 0
fi

# Call the save_transcript.py shipped beside this hook, with flags it accepts. The old call named a
# workspace-only Tools/ copy and a --latest-only flag the bundled script lacks, and its silence hid that
# no transcript was written. A failure now leaves one stderr line; the hook still never blocks the turn.
here=$(cd "$(dirname "$0")" && pwd)
script="$here/save_transcript.py"
[ -f "$script" ] || script="$ROOT/Tools/save_transcript.py"
py="$ROOT/Tools/bin/python3"
[ -x "$py" ] || py=python3
if ! err=$(SAPOTE_ROOT="$ROOT" SAPOTE_CHAT_DIR=sessions "$py" "$script" --color "$color" --session "$sid" 2>&1 >/dev/null); then
  echo "save_transcript_stop: transcript not saved for $color: $(printf '%s' "$err" | tail -n 1)" >&2
fi
exit 0
