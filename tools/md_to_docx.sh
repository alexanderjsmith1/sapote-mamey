#!/usr/bin/env bash
# md_to_docx.sh [--replace] IN.md [OUT.docx] — Word deliverable via pandoc (no LaTeX required).
#
# The output must be a new path unless --replace is given. It is never the input. With --replace,
# an existing regular file is replaced only after pandoc has written the new document in full;
# a symlink or folder at the output name is refused. Refusals print REFUSED and exit 2.
set -euo pipefail
REPLACE=0
if [ "${1:-}" = "--replace" ]; then REPLACE=1; shift; fi
if [ $# -lt 1 ] || [ $# -gt 2 ]; then
  echo "usage: md_to_docx.sh [--replace] IN.md [OUT.docx]" >&2
  exit 2
fi
IN="$1"; OUT="${2:-${IN%.md}.docx}"
if [ ! -f "$IN" ]; then
  echo "REFUSED: input Markdown is not a readable file: $IN" >&2
  exit 2
fi
if [ -e "$OUT" ] || [ -L "$OUT" ]; then
  if [ "$IN" -ef "$OUT" ]; then
    echo "REFUSED: output is the input Markdown: $OUT" >&2
    exit 2
  fi
  if [ "$REPLACE" -ne 1 ]; then
    echo "REFUSED: output already exists: $OUT; choose a new path or pass --replace" >&2
    exit 2
  fi
  if [ -L "$OUT" ] || [ ! -f "$OUT" ]; then
    echo "REFUSED: --replace only replaces a regular file: $OUT" >&2
    exit 2
  fi
fi
if ! command -v pandoc >/dev/null 2>&1; then
  echo "DOCX_TOOLCHAIN_UNAVAILABLE: pandoc not found" >&2
  exit 2
fi
OUT_DIR=$(dirname "$OUT")
if [ ! -d "$OUT_DIR" ]; then
  echo "REFUSED: output folder does not exist: $OUT_DIR" >&2
  exit 2
fi
STAGED=$(mktemp "$OUT_DIR/.$(basename "$OUT").XXXXXX")
trap 'rm -f "$STAGED"' EXIT
pandoc "$IN" -f markdown -t docx -o "$STAGED"
test -s "$STAGED"
if [ "$REPLACE" -eq 1 ]; then
  mv -f "$STAGED" "$OUT"
else
  # ln refuses an existing destination, so a file that appeared during the render is kept.
  if ! ln "$STAGED" "$OUT" 2>/dev/null; then
    echo "REFUSED: output appeared during the render: $OUT" >&2
    exit 2
  fi
fi
echo "wrote $OUT"
