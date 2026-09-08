#!/bin/bash
cd '${SAPOTE_WORKSPACE_ROOT:-$PWD}'
PY="./Tools/bin/python3"
BASE="sapote_deliverables"
echo "== v2 markdown =="
$PY "$BASE/tools/build_v2_md.py" --all
echo "== docx =="
$PY - << 'EOF'
import sys,glob,os
sys.path.insert(0,"Tools")
from md_to_docx import convert
for md in sorted(glob.glob("sapote_deliverables/roster_v2/*_BGC_protein_roster_v2.md")):
    dx=md[:-3]+".docx"
    try: convert(md,dx); print("docx",os.path.basename(dx))
    except Exception as e: print("FAIL",md,e)
EOF
echo "== widgets =="
for j in "$BASE/roster_v2/"*_roster_v2.json; do
  s=$(basename "$j" _roster_v2.json)
  $PY "$BASE/tools/bgc_widget.py" --strain "$s" >/dev/null && echo "widget $s"
done
echo "== index =="
$PY "$BASE/tools/build_cohort_index.py"
echo "BUILD_ALL_DONE"
