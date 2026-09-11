#!/usr/bin/env bash
# bootstrap.sh — set up the Sapote-Mamey runtime + test deps in one command (W18).
#
# Reconstituting the environment (conda + HMMER/DIAMOND/BLASTp + Python wheels) on
# every fresh machine/sandbox is a tax and a place to get a subtly-different setup.
# This script makes it one command and is offline-friendly: point it at a directory
# of pre-downloaded wheels/sdists with --wheels.
#
# Usage:
#   bash bootstrap.sh                       # install from PyPI (needs network)
#   bash bootstrap.sh --wheels ./wheels     # install offline from a local dir
#
# It installs the package in editable mode plus the test extras. It does NOT install
# the external binaries (HMMER/DIAMOND/BLASTp) — those come from conda/bioconda; the
# script prints the exact conda line to run.
set -euo pipefail

WHEELS=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --wheels)
      if [ "$#" -lt 2 ] || [ -z "$2" ]; then
        echo "--wheels requires a local dependency directory" >&2
        exit 2
      fi
      case "$2" in
        -*) echo "--wheels value must be a directory path, not another option: $2" >&2; exit 2 ;;
      esac
      WHEELS="$2"
      shift 2
      ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done

PY="${PYTHON:-python3}"
echo "==> python: $("$PY" --version)"

PIP_ARGS=(--upgrade)
# A-02: ship the declared build requirements and their transitive dependencies so
# `pip install -e .` resolves setuptools>=68 + wheel under build
# isolation in a fresh no-network venv (py3.13 ships no setuptools). The bundled wheels/ dir is
# always on --find-links, so build dependencies resolve both online and offline.
BUNDLED_WHEELS="$(cd "$(dirname "$0")" && pwd)/wheels"
if [ -d "$BUNDLED_WHEELS" ]; then
  echo "==> bundled build wheels: $BUNDLED_WHEELS"
  PIP_ARGS+=(--find-links "$BUNDLED_WHEELS")
fi
if [ -n "$WHEELS" ]; then
  if [ ! -d "$WHEELS" ]; then
    echo "offline wheel directory not found: $WHEELS" >&2
    exit 2
  fi
  echo "==> offline install from $WHEELS (build deps come from the bundled wheels/ above)"
  PIP_ARGS+=(--no-index --find-links "$WHEELS")
fi

echo "==> installing mamey + test deps"
"$PY" -m pip install "${PIP_ARGS[@]}" pytest
# editable install of the package itself (reads pyproject in the current dir)
"$PY" -m pip install "${PIP_ARGS[@]}" -e ".[all]" || {
  echo "   (editable install of .[all] failed — falling back to core deps only)"
  "$PY" -m pip install "${PIP_ARGS[@]}" -e "."
}

echo "==> smoke test"
"$PY" -m pytest tests/test_version_sync.py -q || { echo "version-sync smoke test FAILED"; exit 1; }

cat <<'EOF'

==> external aligners (not pip-installable) — run this once with conda:
    conda create -n sapote -c bioconda -c conda-forge hmmer diamond blast python=3.12
    conda activate sapote

bootstrap done.
EOF
