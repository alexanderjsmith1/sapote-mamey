#!/usr/bin/env bash
# SessionStart hook — point Claude at the LATEST Sapote-Mamey bundle's front-door
# instructions. Fully dynamic so version bumps / new cuts / file renames / an extra
# nesting level (e.g. a CODE-source-<buildstamp>/ subfolder) never break the pointer:
#   1) pick the newest top-level bundle folder (sort -V),
#   2) locate the directory that actually holds the front door (000_READ_ME_FIRST /
#      CLAUDE_START_HERE), at whatever depth,
#   3) list the real front-door files at that level (never tests/ copies).
# Emits a JSON additionalContext block on stdout.
ROOT="${SAPOTE_WORKSPACE_ROOT:-${CLAUDE_PROJECT_DIR:-$PWD}}"

# Collect candidate bundle dirs across EVERY naming convention this project has used, and pick the
# newest by the numeric patch (9.7.NNN). The old glob only matched the underscore form
# (`Sapote_Mamey_v9_7_330`), so once cuts started landing as space-named release folders
# (`Sapote Mamey v9.7.352`) and lowercase CODE trees (`sapote-mamey-v9.7.352-CODE-...`) the pointer  # version-sync-ok (historical example)
# got pin-stuck on .330. Now all three are considered; on a version tie a *-CODE-* tree wins (that is
# the Developer or User's canonical working form). .zip archives are skipped.
D=""; _best_key=-1
while IFS= read -r _d; do
  [ -d "$_d" ] || continue
  case "$_d" in *.zip) continue;; esac
  # 2026-08-17 (INDIGO2 catch, the review lane fix): a CANDIDATE cut must NEVER resolve as the current
  # bundle — only the Developer or User's seal makes a bundle current. Without this, SessionStart and the version
  # guard disagree about "current" the moment a .NNN-CANDIDATE folder appears (two automated
  # context sources contradicting each other = governance bug, workflow doc G5).
  case "$_d" in *CANDIDATE*|*candidate*) continue;; esac
  _n=$(printf '%s\n' "$_d" | grep -oE '9[._]7[._][0-9]+' | head -1 | grep -oE '[0-9]+$')
  [ -n "$_n" ] || continue
  case "$_d" in *-CODE-*) _key=$((_n*2+1));; *) _key=$((_n*2));; esac
  if [ "$_key" -gt "$_best_key" ]; then _best_key=$_key; D="$_d"; fi
done < <(ls -d "$ROOT"/Sapote_Mamey_v* "$ROOT"/Sapote\ Mamey\ v* "$ROOT"/sapote-mamey-v* 2>/dev/null)

B=""
if [ -n "$D" ]; then
  # The bundle root is the dir containing the front door — could be D or a nested subfolder.
  ANCHOR=$(find "$D" -maxdepth 3 -type f \( -iname '000_READ_ME_FIRST*' -o -iname 'CLAUDE_START_HERE.md' \) 2>/dev/null | sort | head -1)
  if [ -n "$ANCHOR" ]; then B=$(dirname "$ANCHOR"); else B="$D"; fi
fi

if [ -n "$B" ]; then
  # Real front-door files at the bundle root (non-recursive ls => excludes tests/ copies).
  F=$(ls "$B" 2>/dev/null | grep -iE '(START_HERE|READ_ME_FIRST)\.(md|txt)$|^CURRENT_DOCS_INDEX' | paste -sd, - | sed 's/,/, /g')
  [ -z "$F" ] && F="(none matched — list the folder to find them)"
  MSG="Sapote-Mamey house rules: the current bundle root is [$B]. Before any Sapote-Mamey run, audit, patch, or Mode-B work, read its front-door files ($F) and treat CURRENT_DOCS_INDEX as the authority for which docs are current. Versions/filenames change across cuts — this path was resolved live to the newest bundle, so use it rather than any remembered path."
else
  MSG="Sapote-Mamey: no Sapote_Mamey_v* bundle folder found under the workspace root; ask the user for the current bundle location before any Sapote-Mamey work."
fi

# Canonical file-home directive (the Developer or User, 2026-08-03): strain_data is the home for everything.
HOMES="FILE-HOME RULE: 'strain_data/' is the canonical home for EVERYTHING — data, Mode-B cards, widgets, registers, analysis modules. Read 'strain_data/WHERE_THINGS_LIVE.md' first. CHECK BEFORE CREATE: search strain_data/ (and the newest dated Claude folder) for an existing folder/register/candidate-cut/widget and BUILD ON IT — never scatter new folders at the project top level or start parallel copies. Resolve strain data with mamey/strain_data_home.py, not ad-hoc globs. COLOR-CHAT RULE: do NOT self-assign a color — read 'sessions/CHAT_REGISTRY.md' (it mirrors the Developer or User's paper notebook); only an the Developer or User-confirmed row is real; if you have no confirmed color, ASK the Developer or User, then write it to .claude/current_chat_color and keep sessions/<color>/STATE.md current. Read ONLY your OWN confirmed color's STATE.md — never inherit another chat's STATE (that causes identity/work collisions)."
MSG="$MSG || $HOMES"

# Asset-discovery directive (the patch lane, 2026-08-06): stop chats re-downloading / re-deriving local data.
ASSETS="ASSET RULE: BEFORE downloading OR re-deriving any DB / model / reference / genome, check what is already local — run 'Tools/bin/python3 Tools/find_asset.py <keyword>' or read 'OFFICIAL_DATA/ASSET_REGISTRY.tsv'. Big assets are ALREADY on disk (full Pfam-A.hmm 2.1G at BigSCAPE/, GTDB at gtotree_gtdb/, reference genome pool 18G at Tools/reference_genomes/, blastp.sqlite, mamey_packages, conda envs incl. rgi/CARD, offline wheelhouse). A PreToolUse hook DENIES re-downloading a registered asset. New antiSMASH results go under '<cohort>/antismash_inputs_renamed/' — see 'OFFICIAL_DATA/ANTISMASH_INTAKE_PROTOCOL.md'; the Mamey package (not the zip) is what moves forward for judgment, but keep the zips for BiG-SCAPE."
MSG="$MSG || $ASSETS"

python3 - "$MSG" <<'PY'
import json, sys
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": sys.argv[1]}}))
PY
