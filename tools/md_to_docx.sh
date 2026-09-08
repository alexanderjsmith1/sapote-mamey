#!/usr/bin/env bash
# md_to_docx.sh IN.md [OUT.docx] — Word deliverable via pandoc (no LaTeX required).
set -e
IN="$1"; OUT="${2:-${IN%.md}.docx}"
pandoc "$IN" -o "$OUT" && echo "wrote $OUT"
