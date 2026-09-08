#!/bin/bash
cd '${SAPOTE_WORKSPACE_ROOT:-$PWD}'
PY="./Tools/bin/python3"; B="sapote_deliverables"
echo "== v3 markdown =="
$PY "$B/tools/build_v3.py" --all | tail -2
echo "== v3 docx (landscape, repeating headers) =="
$PY - << 'EOF'
import sys,glob,os
sys.path.insert(0,"Tools")
from md_to_docx import convert
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.shared import Inches
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
def landscape(doc):
    for sec in doc.sections:
        sec.orientation=WD_ORIENT.LANDSCAPE
        w,h=sec.page_width,sec.page_height
        sec.page_width,sec.page_height=max(w,h),min(w,h)
        sec.left_margin=sec.right_margin=Inches(0.5)
    for t in doc.tables:  # repeat header row
        tr=t.rows[0]._tr; tp=tr.get_or_add_trPr(); h=OxmlElement('w:tblHeader'); h.set(qn('w:val'),'true'); tp.append(h)
n=0
for md in sorted(glob.glob("sapote_deliverables/roster_v2/*_BGC_protein_roster_v3.md")):
    dx=md[:-3]+".docx"
    try:
        convert(md,dx); d=Document(dx); landscape(d); d.save(dx); n+=1
    except Exception as e: print("FAIL",os.path.basename(md),e)
print(f"v3 docx (landscape): {n}")
EOF
echo "== rebuild widgets (now 4-channel) =="
c=0; for j in "$B/roster_v2/"*_roster_v2.json; do s=$(basename "$j" _roster_v2.json); $PY "$B/tools/bgc_widget.py" --strain "$s" >/dev/null && c=$((c+1)); done; echo "widgets: $c"
echo "== index =="
$PY "$B/tools/build_cohort_index.py" | tail -1
echo "V3_ALL_DONE"
