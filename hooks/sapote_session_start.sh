#!/usr/bin/env bash
# SessionStart hook — point Claude at an explicitly located Sapote-Mamey code root.
# A versioned folder name cannot establish release authority. The caller may open a
# code root directly or set SAPOTE_BUNDLE_ROOT to a verified code root. The hook
# only checks its shape and lists its front-door files; it does not verify a seal.
# Emits a JSON additionalContext block on stdout.
ROOT="${SAPOTE_WORKSPACE_ROOT:-${CLAUDE_PROJECT_DIR:-$PWD}}"

B=""
BOUND="${SAPOTE_BUNDLE_ROOT:-}"
if [ -n "$BOUND" ]; then
  if [ -f "$BOUND/pyproject.toml" ] && [ -f "$BOUND/mamey_run.py" ] && [ -f "$BOUND/bootstrap_contract.yml" ]; then
    B="$BOUND"
  fi
elif [ -f "$ROOT/pyproject.toml" ] && [ -f "$ROOT/mamey_run.py" ] && [ -f "$ROOT/bootstrap_contract.yml" ]; then
  # Opening a code root directly is an explicit location, without release selection.
  B="$ROOT"
fi

if [ -n "$B" ]; then
  # List root authority files and the shared agent contract, never tests/ copies.
  F=$(
    cd "$B" || exit
    {
      ls -1 2>/dev/null | grep -iE '^(AGENTS|CLAUDE)\.md$|^CURRENT_DOCS_INDEX'
    } | sort | paste -sd, - | sed 's/,/, /g'
  )
  [ -z "$F" ] && F="(none matched — list the folder to find them)"
  MSG="Sapote-Mamey house rules: the explicitly located code root is [$B]. Read its front-door files ($F) before work. This location is not a release claim; verify the bundle identity, hash and seal receipt for the task before treating it as current or released."
else
  MSG="Sapote-Mamey: no valid code root was explicitly located. Open the code root directly or set SAPOTE_BUNDLE_ROOT to a verified code root. A folder name alone cannot select a current release."
fi

# File-home and session-address directive.
HOMES="FILE-HOME RULE: 'strain_data/' is the canonical home for EVERYTHING — data, Mode-B cards, widgets, registers, analysis modules. Read 'strain_data/WHERE_THINGS_LIVE.md' first. CHECK BEFORE CREATE: search strain_data/ (and the newest dated Claude folder) for an existing folder/register/candidate-cut/widget and BUILD ON IT — never scatter new folders at the project top level or start parallel copies. Resolve strain data with mamey/strain_data_home.py, not ad-hoc globs. SESSION-ADDRESS RULE: your identity is your own session id, not a colour. Use the first 8 characters of the session id as your address and keep state only in 'sessions/<address>__<nickname>/STATE.md'. Read and write only your own STATE.md. Do NOT read or write .claude/current_chat_color: it is one shared value with no session binding, so every chat that trusts it inherits whatever another chat wrote there."
MSG="$MSG || $HOMES"

# Asset-discovery directive (the patch lane, 2026-08-06): stop chats re-downloading / re-deriving local data.
ASSETS="ASSET RULE: BEFORE downloading OR re-deriving any DB / model / reference / genome, check what is already local — run 'Tools/bin/python3 Tools/find_asset.py <keyword>' or read 'OFFICIAL_DATA/ASSET_REGISTRY.tsv'. Big assets are ALREADY on disk (full Pfam-A.hmm 2.1G at BigSCAPE/, GTDB at gtotree_gtdb/, reference genome pool 18G at Tools/reference_genomes/, blastp.sqlite, mamey_packages, conda envs incl. rgi/CARD, offline wheelhouse). A PreToolUse hook DENIES re-downloading a registered asset. New antiSMASH results go under '<cohort>/antismash_inputs_renamed/' — see 'OFFICIAL_DATA/ANTISMASH_INTAKE_PROTOCOL.md'; the Mamey package (not the zip) is what moves forward for judgment, but keep the zips for BiG-SCAPE."
MSG="$MSG || $ASSETS"

python3 - "$MSG" <<'PY'
import json, sys
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": sys.argv[1]}}))
PY
