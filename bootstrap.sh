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

BUNDLE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Resolve caller-relative wheel paths before anchoring installation to this source.
if [ -n "$WHEELS" ]; then
  if [ ! -d "$WHEELS" ]; then
    echo "offline wheel directory not found: $WHEELS" >&2
    exit 2
  fi
  WHEELS="$(cd "$WHEELS" && pwd)"
fi

# Bind the selected executable before cd, preserving a virtualenv symlink path.
PY_CHOICE="${PYTHON:-python3}"
if ! PY="$(command -v "$PY_CHOICE")"; then
  echo "selected Python executable not found: $PY_CHOICE; set PYTHON to an installed Python 3.12+ environment" >&2
  exit 2
fi
case "$PY" in
  /*) ;;
  *) PY="$PWD/$PY" ;;
esac
if [ ! -f "$PY" ] || [ ! -x "$PY" ]; then
  echo "selected Python executable not found: $PY_CHOICE; supply one executable file, not a shell command" >&2
  exit 2
fi
# Refuse unsupported interpreters before any package-manager mutation.
if ! "$PY" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 2)'; then
  echo "Python 3.12+ required; select an installed compatible interpreter with PYTHON (see docs/INSTALL.md)" >&2
  exit 2
fi
echo "==> python: $("$PY" --version)"

# Build-dependency pip children may omit --isolated and inherit exported PIP_*.
# Clear ambient settings before creating our own PIP_ARGS/PIP_COMMAND arrays.
if [ -n "$WHEELS" ]; then
  while IFS= read -r offline_pip_env_name; do
    case "$offline_pip_env_name" in
      PIP_*) unset -v "$offline_pip_env_name" ;;
    esac
  done < <(compgen -e)
fi

PIP_ARGS=(--upgrade)
# A-02: ship the declared build requirements and their transitive dependencies so
# `pip install -e .` resolves setuptools>=68 + wheel under build
# isolation in a fresh no-network venv (py3.13 ships no setuptools). The bundled wheels/ dir is
# always on --find-links, so build dependencies resolve both online and offline.
BUNDLED_WHEELS="$BUNDLE_ROOT/wheels"
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

# Offline mode ignores ambient pip settings for this process and its descendants.
PIP_COMMAND=("$PY" -m pip)
if [ -n "$WHEELS" ]; then
  export PIP_CONFIG_FILE=/dev/null
  PIP_COMMAND+=(--isolated)
fi

# Check the selected environment before any package installation is attempted.
if ! "${PIP_COMMAND[@]}" --version; then
  echo "bootstrap HOLD: pip is unavailable or cannot start in selected Python: $PY. Next: select or repair a Python 3.12+ environment with pip using an approved package source (see docs/INSTALL.md). No package installation was attempted." >&2
  exit 2
fi

cd "$BUNDLE_ROOT"
echo "==> installing mamey + test deps from $BUNDLE_ROOT"
if ! "${PIP_COMMAND[@]}" install "${PIP_ARGS[@]}" pytest; then
  echo "bootstrap HOLD: test dependency installation failed. Next: inspect the pip error above and verify this selected environment and complete compatible test wheel pool." >&2
  exit 1
fi
INSTALL_SCOPE="ALL_EXTRAS"
# Editable install and smoke test are pinned to the directory containing this script.
"${PIP_COMMAND[@]}" install "${PIP_ARGS[@]}" -e ".[all]" || {
  echo "   (editable install of .[all] failed — falling back to core deps only)"
  if ! "${PIP_COMMAND[@]}" install "${PIP_ARGS[@]}" -e "."; then
    echo "bootstrap HOLD: core installation failed. Next: inspect the pip error above and verify the selected environment and compatible core/build wheels." >&2
    exit 1
  fi
  INSTALL_SCOPE="CORE_ONLY"
}

echo "==> smoke test"
"$PY" -m pytest tests/test_version_sync.py -q || { echo "version-sync smoke test FAILED. Next: inspect version-sync diagnostics for this selected source before claiming readiness." >&2; exit 1; }

cat <<'EOF'

==> external aligners (not pip-installable) — run this once with conda:
    conda create -n sapote -c bioconda -c conda-forge hmmer diamond blast python=3.12
    conda activate sapote

EOF
echo "bootstrap done: $INSTALL_SCOPE (version-sync smoke passed; selected workflows still need their own checks)."
if [ "$INSTALL_SCOPE" = "CORE_ONLY" ]; then
  echo "Next: resolve the optional pip error above and retry the selected extras in this same Python; an offline retry needs a complete compatible extras wheel pool."
fi
