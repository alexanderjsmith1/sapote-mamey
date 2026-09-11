#!/usr/bin/env bash
# bgc_node_name_guard.sh — PostToolUse (Write|Edit|MultiEdit|NotebookEdit)
# GOVERNANCE (the Developer or User, 2026-08-06): every AS-strain per-BGC file/document MUST carry the
# node/contig identifier (e.g. NODE_162). A bare "BGC016" with no node token is a
# wrong-attribution risk and is FORBIDDEN for AS strains.
#
# This is a non-blocking WARNING (surfaces via exit 2 so the assistant sees it). It can be
# promoted to a hard PreToolUse DENY once existing files are remediated + sibling chats notified
# (set BGC_NAME_GUARD_DENY=1 and move the hook to PreToolUse). See the strain_data cleanup plan.
#
# v9.7.401 EXTENSION (BC2, ROSTER_401_SEEDS.md item 3 -- VERIFY/EXTEND per audit control #5):
# the original check only ever looked at the FILENAME. Reproduced live: a genuinely-named file
# (e.g. "notes.md") whose BODY cites a bare strain+BGC-number with no node token entirely
# escapes this guard, even under the correct strain_data/AS-NNN/ scope -- the exact
# wrong-attribution shape (WAC-01375) this guard exists to catch, just moved from the filename
# into the prose. For .md/.csv files in scope, now ALSO scans the file's own on-disk content
# (this hook is PostToolUse, so the write has already landed by the time it runs) via the
# bundle's own authoritative gate, `mamey.bgc_citation_gate.find_nodeless_bgc_citations()` --
# the exact line-scoped logic `mamey verify-citations` already uses, reused rather than
# reimplemented as a second, independently-drifting regex (the same "don't write the Nth
# resolver" lesson from this round's rglob-consolidation cards).
#
# NOTE, per the seed's own instruction: conversational/CHAT text that is never written to a
# file is fundamentally outside what any hook can see -- a PreToolUse/PostToolUse hook only
# ever observes tool calls (Write/Edit/...), never the assistant's own prose to the user. That
# half of the node-less-citation risk stays behavioral (the FATAL-ERROR rule in
# AGENTS.md and the self-check prompt), not mechanizable here.
set -euo pipefail
input=$(cat)
# seal-gate repair (.401): payload parse via python3 (already this hook's content-scan
# dependency), not jq — jq is absent in clean/container shells and the jq||true form
# silently disarmed the guard there (reproduced: 2 test failures on a jq-less PATH).
fp=$(printf '%s' "$input" | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
ti = d.get("tool_input") or {}
sys.stdout.write(ti.get("file_path") or ti.get("notebook_path") or "")' 2>/dev/null || true)
[ -z "${fp:-}" ] && exit 0

# scope: only per-BGC files under an AS-strain subtree of strain_data
case "$fp" in
  *"strain_data/AS-"[0-9]*) : ;;
  *) exit 0 ;;
esac

base=$(basename "$fp")

# -- filename check (unchanged) --
name_hit=0
if printf '%s' "$base" | grep -Eiq 'BGC[_-]?[0-9]{1,4}'; then
  if ! printf '%s' "$base" | grep -Eiq 'NODE[_-]?[0-9]|contig[_-]?[0-9]|scaffold[_-]?[0-9]|(^|[^A-Za-z])tig[0-9]|N[CZ]_[0-9]|CP[0-9]{5}'; then
    name_hit=1
  fi
fi

# -- content check (NEW): .md/.csv only, reusing the bundle's own authoritative gate --
content_findings=""
case "$base" in
  *.md|*.csv)
    if [ -f "$fp" ]; then
      bundle_root=$(cd "$(dirname "$0")/.." && pwd)
      content_findings=$(PYTHONPATH="$bundle_root" python3 - "$fp" 2>/dev/null <<'PY' || true
import sys
from mamey.bgc_citation_gate import find_nodeless_bgc_citations
path = sys.argv[1]
try:
    text = open(path, encoding="utf-8", errors="replace").read()
except OSError:
    sys.exit(0)
for ln, line in find_nodeless_bgc_citations(text):
    print(f"  line {ln}: {line[:120]}")
PY
)
    fi
    ;;
esac

if [ "$name_hit" -eq 0 ] && [ -z "$content_findings" ]; then
  exit 0
fi

{
  echo "⚠️  BGC-NODE-NAME GUARD — '$base'"
  if [ "$name_hit" -eq 1 ]; then
    echo "    Filename names a BGC by number only, with NO node/contig identifier."
  fi
  if [ -n "$content_findings" ]; then
    echo "    Content cites a strain+BGC-number with NO node/contig token on these line(s):"
    printf '%s\n' "$content_findings"
  fi
  echo "    House rule (the Developer or User 2026-08-06): every AS-strain BGC file/document MUST include the node/contig"
  echo "    token (e.g. AS-XXX_NODE162_r001_BGC016_ModeB.md, or per-BGC folder AS-XXX/NODE162_r001_BGC016/)."
  echo "    Bare 'BGC016' is a wrong-attribution risk. Get the node from the strain's inventory crosswalk"
  echo "    (sealed package _2_inventory.csv / BGC_Crosswalk) before naming per-BGC files."
} >&2
exit 2
