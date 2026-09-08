#!/usr/bin/env bash
# md_to_pdf.sh IN.md OUT.pdf [boss|technical]
#
# Primary path: colorful reportlab renderer (tools/render_deliverable_pdf.py) — indigo cover
# band, colored section headers, tinted callouts, styled tables, code boxes, embedded images.
#
# Fallback: the original layout-preflight + pandoc + xelatex path. Used automatically if the
# colorful renderer fails (e.g. a table cell taller than one page) OR if reportlab is not
# installed, so a PDF is always produced and a xelatex failure is still fatal in that mode.
set -euo pipefail
IN="$1"
OUT="${2:-${IN%.md}.pdf}"
PROFILE="${3:-boss}"
DIR="$(cd "$(dirname "$0")" && pwd)"

# ---- primary: colorful reportlab renderer ----
if python3 "$DIR/render_deliverable_pdf.py" "$IN" "$OUT" >/tmp/sapote_colorpdf.log 2>&1; then
  echo "wrote $OUT (colorful reportlab)"
  exit 0
fi
echo "colorful renderer unavailable/failed — falling back to pandoc+xelatex" >&2
[ -f /tmp/sapote_colorpdf.log ] && sed 's/^/  [colorpdf] /' /tmp/sapote_colorpdf.log >&2

# ---- fallback: layout preflight + pandoc + xelatex (plain but robust) ----
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

SAFE_MD="$TMP/safe.md"
APP_MD="${OUT%.pdf}.wide_tables_appendix.md"
QA_JSON="${OUT%.pdf}.render_preflight.json"

python3 "$DIR/sapote_md_preflight.py" "$IN" "$SAFE_MD" \
  --profile "$PROFILE" \
  --appendix-md "$APP_MD" \
  --qa-json "$QA_JSON"

pandoc "$SAFE_MD" -t latex -s -o "$TMP/d.tex"
# v9.7.409 portability: `sed -i` with no backup suffix is GNU-only; BSD/macOS sed reads the
# next token as the suffix and mangles the edit. Use perl -i (no backup), the form already
# blessed in make_public_tier.sh:494.
perl -i -ne 'print unless /usepackage\{(lmodern|textcomp)\}/' "$TMP/d.tex"
python3 - "$TMP/d.tex" <<'PY'
import sys
p=sys.argv[1]
s=open(p, encoding='utf-8').read()
if 'fontspec' not in s:
    s=s.replace('\\usepackage{','\\usepackage{fontspec}\n\\setmainfont{DejaVu Serif}\n\\setmonofont{DejaVu Sans Mono}\n\\usepackage{',1)
# Gentle PDF readability defaults.
if '\\usepackage{microtype}' not in s:
    s=s.replace('\\begin{document}', '\\usepackage{microtype}\n\\emergencystretch=3em\n\\sloppy\n\\begin{document}', 1)
open(p,'w',encoding='utf-8').write(s)
PY
xelatex -halt-on-error -interaction=nonstopmode -output-directory="$TMP" "$TMP/d.tex" >/tmp/sapote_xelatex_1.log 2>&1
xelatex -halt-on-error -interaction=nonstopmode -output-directory="$TMP" "$TMP/d.tex" >/tmp/sapote_xelatex_2.log 2>&1
test -s "$TMP/d.pdf"
cp "$TMP/d.pdf" "$OUT"
echo "wrote $OUT (pandoc+xelatex fallback)"
echo "preflight QA: $QA_JSON"
