#!/usr/bin/env bash
# Stop hook: run the master's-student QC gate on any tree artefact touched in the
# last 90 min. Advisory only — always exits 0 (never blocks). Silent when clean.
PY="${SAPOTE_WORKSPACE_ROOT:-${CLAUDE_PROJECT_DIR:-$PWD}}/Tools/bin/python3"
CHK="${SAPOTE_WORKSPACE_ROOT:-${CLAUDE_PROJECT_DIR:-$PWD}}/Tools/signoff_check.py"
CLM="${SAPOTE_WORKSPACE_ROOT:-${CLAUDE_PROJECT_DIR:-$PWD}}/Tools/claim_safety_check.py"
[ -x "$PY" ] || PY="python3"
# v9.7.413 (Razzle Dazzle Rose): SERIALIZE. Every chat fires this hook at every turn-end; with many
# sessions open the scans stack (3 concurrent observed 2026-09-04, load avg 39/179/143, fseventsd at
# 90% CPU). The .412 bounded scan cut one call from ~2 min to ~21 s, but concurrency was the other
# half of that fix and did not land with it. A portable mkdir lock (flock is absent on macOS) makes a
# concurrent caller skip: the checks are advisory and the next turn-end re-runs them, so nothing is
# lost. A lock older than 10 min is treated as stale (a killed run) and reclaimed. Still always exit 0.
LOCK="${TMPDIR:-/tmp}/sapote_signoff_stop.lock"
if [ -d "$LOCK" ] && [ -n "$(find "$LOCK" -maxdepth 0 -mmin +10 2>/dev/null)" ]; then rmdir "$LOCK" 2>/dev/null; fi
if ! mkdir "$LOCK" 2>/dev/null; then exit 0; fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT
if [ -f "$CHK" ]; then
  "$PY" "$CHK" --quiet-if-clean --minutes 90 2>/dev/null || true
fi
# CLAIM-SAFETY gate: flag product-identity overclaims / missing denominators in any report
# artefact (.md/.csv/.docx) written in the last 90 min. Advisory only, never blocks.
if [ -f "$CLM" ]; then
  "$PY" "$CLM" --quiet-if-clean --minutes 90 --root "${SAPOTE_WORKSPACE_ROOT:-${CLAUDE_PROJECT_DIR:-$PWD}}/strain_data" 2>/dev/null || true
fi
exit 0
