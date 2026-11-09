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
# PYTHON is one executable locator, including paths with spaces; never shell arguments.
export PYTHON="${PYTHON:-python3}"
if ! "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' >/dev/null 2>&1; then
  echo "REFUSED: Python 3.12 or newer required; PYTHON executable unavailable or incompatible: $PYTHON" >&2
  exit 2
fi
# Resolve the caller's input/output before changing directories or preflighting.
IN=$("$PYTHON" -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$IN")
OUT=$("$PYTHON" -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$OUT")
RESOURCE_DIR=$(dirname "$IN")
APP_MD="${OUT%.pdf}.wide_tables_appendix.md"
QA_JSON="${OUT%.pdf}.render_preflight.json"
RECEIPT_JSON="${OUT%.pdf}.resource_bindings.json"
# Every destination either route can write must be new, distinct and not the input.
# Checked before either route runs, so neither route replaces an earlier PDF or sidecar.
"$PYTHON" - "$DIR" "$IN" "$OUT" "$RECEIPT_JSON" "$QA_JSON" "$APP_MD" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]).parent))
from mamey.output_transaction import preflight_output_roster
source, outputs = Path(sys.argv[2]), [Path(p) for p in sys.argv[3:]]
taken = [str(p) for p in outputs if p.exists() or p.is_symlink()]
if taken:
    print("REFUSED: output already exists (choose a new PDF path): " + ", ".join(taken), file=sys.stderr)
    sys.exit(2)
try:
    preflight_output_roster(outputs, protected_paths=(source,))
except ValueError as exc:
    print(f"REFUSED: {exc}: " + ", ".join(str(p) for p in outputs), file=sys.stderr)
    sys.exit(2)
PY
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$(dirname "$OUT")"

# ---- primary: colorful reportlab renderer; publish without replacing ----
if MAMEY_PDF_LINK_OUTPUT_DIR="$(dirname "$OUT")" "$PYTHON" "$DIR/render_deliverable_pdf.py" "$IN" "$TMP/primary.pdf" >"$TMP/colorpdf.log" 2>&1; then
  "$PYTHON" - "$TMP/primary.pdf" "$OUT" <<'PY'
import os, shutil, sys, tempfile
from pathlib import Path
draft, out = Path(sys.argv[1]), Path(sys.argv[2])
fd, staged = tempfile.mkstemp(prefix=f".{out.name}.", suffix=".tmp", dir=out.parent)
try:
    with os.fdopen(fd, "wb") as handle, draft.open("rb") as source:
        shutil.copyfileobj(source, handle)
    os.link(staged, out)  # refuses an existing destination
finally:
    os.unlink(staged)
PY
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
PANDOC=$(command -v pandoc)
export PANDOC
# Resolve local images against the original Markdown directory BEFORE preflight
# moves the document into a temp directory. Refuse missing artwork, not omit it.
MAMEY_PDF_LINK_OUTPUT_DIR="$(dirname "$OUT")" "$PYTHON" "$DIR/prepare_pdf_resources.py" "$IN" "$TMP/resources.md"
IN="$TMP/resources.md"

SAFE_MD="$TMP/safe.md"

"$PYTHON" "$DIR/sapote_md_preflight.py" "$IN" "$SAFE_MD" \
  --profile "$PROFILE" \
  --appendix-md "$APP_MD" \
  --qa-json "$QA_JSON"

SAPOTE_PDF_RESOURCE_MAP="$TMP/resources.resource_map.json" \
  "$PANDOC" "$SAFE_MD" --resource-path="$RESOURCE_DIR" -f markdown -t latex -s \
  --lua-filter="$DIR/pdf_resource_filter.lua" -o "$TMP/d.tex"
# v9.7.409 portability: `sed -i` with no backup suffix is GNU-only; BSD/macOS sed reads the
# next token as the suffix and mangles the edit. Use perl -i (no backup), the form already
# blessed in make_public_tier.sh:494.
perl -i -ne 'print unless /usepackage\{(lmodern|textcomp)\}/' "$TMP/d.tex"
"$PYTHON" - "$TMP/d.tex" <<'PY'
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
"$PYTHON" "$DIR/publish_pdf_fallback_pair.py" "$TMP" "$TMP/d.pdf" "$OUT" "$RECEIPT_JSON"
echo "wrote $OUT (pandoc+xelatex fallback)"
echo "preflight QA: $QA_JSON"
