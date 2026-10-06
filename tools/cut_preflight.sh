#!/usr/bin/env bash
# Cut preflight: refuse release-root review artifacts and purge working-copy bytecode.
# Source these functions; this file performs no work when sourced or invoked alone.
# Purging is for an explicitly selected disposable cut working copy, never source evidence.

sapote_assert_no_review_root() {
  local root="${1:?working root required}" entry
  [[ -d "$root" ]] || { echo "REFUSED: cut root is not a directory: $root" >&2; return 1; }
  for entry in "$root"/REVIEW_CANDIDATE_* "$root"/PROPOSED_FIXES*; do
    if [[ -e "$entry" || -L "$entry" ]]; then
      echo "REFUSED: review-stage artifact at release root: $entry" >&2
      return 1
    fi
  done
}

sapote_purge_cut_bytecode() {
  local root="${1:?disposable working root required}" offender
  root="$(cd "$root" && pwd -P)" || return 1
  [[ "$root" != / ]] || { echo "REFUSED: filesystem root is not a cut working copy" >&2; return 1; }
  # Do not follow a cache-named symlink or silently discard its provenance.
  offender="$(find "$root" -type l \( -name __pycache__ -o -name '*.pyc' -o -name '*.pyo' \) -print -quit)" || return 1
  [[ -z "$offender" ]] || { echo "REFUSED: bytecode cache symlink needs adjudication: $offender" >&2; return 1; }
  find "$root" -type d -name __pycache__ -prune -exec rm -rf -- {} + || return 1
  find "$root" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete || return 1
  offender="$(find "$root" \( -type d -name __pycache__ -o -type f \( -name '*.pyc' -o -name '*.pyo' \) \) -print -quit)" || return 1
  [[ -z "$offender" ]] || { echo "REFUSED: bytecode remains in cut working copy: $offender" >&2; return 1; }
}
