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
# Resolve the caller's input/output before changing directories or preflighting.
IN=$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$IN")
OUT=$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$OUT")
RESOURCE_DIR=$(dirname "$IN")
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$(dirname "$OUT")"

# ---- primary: colorful reportlab renderer; atomic publication ----
if python3 "$DIR/render_deliverable_pdf.py" "$IN" "$TMP/primary.pdf" >"$TMP/colorpdf.log" 2>&1; then
  cp "$TMP/primary.pdf" "$OUT"
  echo "wrote $OUT (colorful reportlab)"
  exit 0
fi
echo "colorful renderer unavailable/failed — checking pandoc+xelatex fallback" >&2
sed 's/^/  [colorpdf] /' "$TMP/colorpdf.log" >&2
for TOOL in pandoc xelatex; do
  if ! command -v "$TOOL" >/dev/null 2>&1; then
    echo "PDF_TOOLCHAIN_UNAVAILABLE: primary renderer failed; fallback needs $TOOL" >&2
    exit 2
  fi
done
# Resolve local images against the original Markdown directory BEFORE preflight
# moves the document into a temp directory. Refuse missing artwork, not omit it.
python3 "$DIR/prepare_pdf_resources.py" "$IN" "$TMP/resources.md"
IN="$TMP/resources.md"

SAFE_MD="$TMP/safe.md"
APP_MD="${OUT%.pdf}.wide_tables_appendix.md"
QA_JSON="${OUT%.pdf}.render_preflight.json"

python3 "$DIR/sapote_md_preflight.py" "$IN" "$SAFE_MD" \
  --profile "$PROFILE" \
  --appendix-md "$APP_MD" \
  --qa-json "$QA_JSON"

pandoc "$SAFE_MD" --resource-path="$RESOURCE_DIR" -t latex -s -o "$TMP/d.tex"
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
xelatex -halt-on-error -interaction=nonstopmode -output-directory="$TMP" "$TMP/d.tex" >"$TMP/xelatex_1.log" 2>&1
xelatex -halt-on-error -interaction=nonstopmode -output-directory="$TMP" "$TMP/d.tex" >"$TMP/xelatex_2.log" 2>&1
test -s "$TMP/d.pdf"
cp "$TMP/d.pdf" "$OUT"
echo "wrote $OUT (pandoc+xelatex fallback)"
echo "preflight QA: $QA_JSON"
