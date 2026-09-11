#!/usr/bin/env bash
# Patch hygiene guard: warn immediately when a patch queue contains cruft or an invalid packet.
# .402 jq-family port (ROSTER_402 seed #1): payload parse via python3 stdlib, not jq —
# jq is absent in clean/container shells and the silent-empty form disarmed this hook
# there. Same repair shape as bgc_node_name_guard (.401 seal-gate repair).
inp=$(cat 2>/dev/null) || inp=""
path=$(printf '%s' "$inp" | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = d.get("tool_input") or {}
sys.stdout.write(ti.get("file_path") or "")' 2>/dev/null || true)
[ -z "$path" ] && exit 0
case "$path" in
  *"Patches for next cut"*) ;;
  *) exit 0 ;;
esac
queue=$(printf '%s' "$path" | sed -E 's#(.*/Patches for next cut[^/]*)/.*#\1#')
[ -d "$queue" ] || exit 0
arts=$(find "$queue" \( -name '*.pyc' -o -name '__pycache__' -o -name '.DS_Store' -o -name '*.orig' \) 2>/dev/null | head -8)

packet=$(printf '%s' "$path" | sed -E 's#(.*/Patches for next cut[^/]*/[^/]+).*#\1#')
bundle_root=$(cd "$(dirname "$0")/.." && pwd)
preflight="$bundle_root/tools/patch_packet_preflight.py"
packet_note=""
if [ -d "$packet" ] && [ -f "$preflight" ]; then
  packet_note=$(python3 "$preflight" "$packet" --summary-only 2>/dev/null || true)
fi

if [ -n "$arts" ] || printf '%s' "$packet_note" | grep -q ': FAIL '; then
  python3 - "$queue" "$arts" "$packet_note" <<'PY'
import json, sys
queue, arts, packet_note = sys.argv[1:]
parts = []
if arts:
    parts.append("Build cruft found:\n  " + "\n  ".join(arts.splitlines()))
if ": FAIL " in packet_note:
    parts.append("Patch-packet preflight failed:\n  " + packet_note.strip())
msg = ("PATCH-PACKET HYGIENE WARNING: this queue is not ready for handoff or cut selection. "
       "Run tools/patch_packet_preflight.py and correct every failure.\n" + "\n".join(parts))
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}))
PY
fi
exit 0
