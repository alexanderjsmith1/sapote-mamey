# CANDIDATE seal-gate wiring — add hook-integrity verification to the pre-package gate.
# Fold target: full_suite_before_package.sh (the PreToolUse Bash guard that runs before packaging a cut).
# Insert this block just BEFORE the packaging command is allowed through. It fails the seal (deny) if the
# bundle's guard hooks drift from the manifest, are non-portable, or a manifested hook is missing.
# `--gate` makes workspace cruft advisory-only (cruft never reaches the bundle), so it won't block a seal.
#
# Requires: sapote_hooks/ present in the bundle (this card ships it) with HOOKS_MANIFEST.tsv + the hook
# files. Resolve HOOKS_TOOL / BUNDLE_HOOKS to wherever the fold places sapote_hooks + the canonical hooks.

HOOKS_TOOL="${CLAUDE_PROJECT_DIR:?}/sapote_hooks/sapote_hooks.py"          # adjust to in-bundle path
BUNDLE_HOOKS="${CLAUDE_PROJECT_DIR:?}/sapote_hooks/hooks"                   # canonical bundle hook dir
if [ -f "$HOOKS_TOOL" ]; then
  if ! gate_out=$(python3 "$HOOKS_TOOL" verify --gate --bundle "$BUNDLE_HOOKS" 2>&1); then
    reason=$(printf 'BLOCKED before packaging: guardrail-hook integrity gate FAILED.\n\n%s\n\nFix: run `python3 %s verify --gate --bundle %s`, resolve DRIFT/MISSING/UNMANIFESTED/NON-PORTABLE, then re-seal. (Workspace cruft is advisory and does not fail this gate.)' "$gate_out" "$HOOKS_TOOL" "$BUNDLE_HOOKS" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":%s}}' "$reason"
    exit 0
  fi
fi
