"""SVG label geometry and caption-method records for installed bioassay routes.

The SVG detector retains the producing script's svglite/house-ink geometry.
Its declared scope is supplied labels and supported SVG marks, not visual QA.
Methods prose is operator supplied; counts and source hashes come from the run.
The existing generated CAPTION.md is preserved verbatim.
"""
import json
from collections import Counter
import sys
from pathlib import Path
_ROOT = str(Path(__file__).resolve().parents[1])   # runs from any directory
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from tools._figure_route_common import table,sha
from mamey.figure_policy import validate_caption_methods,CAPTION_METHOD_SCHEMA
import re
from pathlib import Path

INK = '#17212E'
LABEL = re.compile(r"<text x='([\d.]+)' y='([\d.]+)'(?: text-anchor='(\w+)')? style='font-size: ([\d.]+)px;[^']*' textLength='([\d.]+)px'[^>]*>(__LABEL_PATTERN__)</text>")


def boxes(svg, label_pattern):
    s = Path(svg).read_text()
    pattern=re.compile(LABEL.pattern.replace('__LABEL_PATTERN__',label_pattern))
    labels = []
    for x, y, anchor, fs, tl, txt in pattern.findall(s):
        x, y, fs, tl = float(x), float(y), float(fs), float(tl)
        x0 = x - tl / 2 if anchor == 'middle' else x - tl if anchor == 'end' else x
        labels.append((txt, x0, y - 0.72 * fs, x0 + tl, y + 0.05 * fs))
    for tx, ty, anchor, fs, tl, txt in re.findall(r"<text transform='translate\(([\d.]+),([\d.]+)\) rotate\(-90\)'(?: text-anchor='(\w+)')? style='font-size: ([\d.]+)px;[^']*' textLength='([\d.]+)px'[^>]*>(__LABEL_PATTERN__)</text>".replace('__LABEL_PATTERN__',label_pattern), s):
        tx, ty, fs, tl = float(tx), float(ty), float(fs), float(tl)
        lo, hi = (-tl, 0) if anchor == 'end' else (-tl / 2, tl / 2) if anchor == 'middle' else (0, tl)   # along the text
        labels.append((txt, tx - 0.72 * fs, ty - hi, tx + 0.05 * fs, ty - lo))
    pts = []
    for cx, cy, r in re.findall(r"<circle cx='([\d.]+)' cy='([\d.]+)' r='([\d.]+)' style='[^']*stroke: " + INK, s):
        cx, cy, r = float(cx), float(cy), float(r); pts.append((cx - r, cy - r, cx + r, cy + r))
    for p in re.findall(r"<polygon points='([\d., ]+)' style='[^']*stroke: " + INK, s):
        xy = [tuple(map(float, q.split(','))) for q in p.split()]
        pts.append((min(a for a, b in xy), min(b for a, b in xy), max(a for a, b in xy), max(b for a, b in xy)))
    for x, y, w, h in re.findall(r"<rect x='([\d.]+)' y='([\d.]+)' width='([\d.]+)' height='([\d.]+)' style='[^']*stroke: " + INK, s):
        x, y, w, h = map(float, (x, y, w, h))
        if w < 12 and h < 12:
            pts.append((x, y, x + w, y + h))
    return labels, pts


def hit(a, b, pad=0.2):
    return a[0] < b[2] - pad and b[0] < a[2] - pad and a[1] < b[3] - pad and b[1] < a[3] - pad



def overlaps(svg, labels):
    pattern='(?:'+'|'.join(re.escape(x) for x in sorted(set(labels),key=len,reverse=True) if x)+')'
    boxes_,points=boxes(svg,pattern)
    problems=[]
    for i,(label,*box) in enumerate(boxes_):
        for point in points:
            if hit(box,point):problems.append(label+' overlaps a supported point mark')
        for label2,*box2 in boxes_[i+1:]:
            if hit(box,box2):problems.append(label+' overlaps label '+label2)
    return dict(svg=str(Path(svg).resolve()),sha256=sha(svg),detected_labels=len(boxes_),detected_point_marks=len(points),
                scope='supplied label strings; svglite text/house-ink circles, polygons, small rectangles',
                problems=problems,visual_qa='NOT_PERFORMED')

def record(folder,context,labels,*,scatter=False):
    folder=Path(folder)
    run=json.loads((folder/'RUN_INFO.json').read_text())
    plot=table(folder/'plot_data.tsv',[])
    metadata=dict(context)
    metadata['caption_schema_version']=CAPTION_METHOD_SCHEMA
    metadata['source_bindings']='; '.join(str(r['path'])+' sha256='+r['sha256'] for r in run['inputs'])
    groups=Counter(r.get('group','recorded ungrouped rows') for r in plot)
    metadata['group_denominators']='; '.join(k+' rows='+str(v) for k,v in sorted(groups.items()))
    typed=sum(bool(r.get('state')) for r in plot)
    metadata['typed_missingness']=(f'plotted_rows={len(plot)}; typed_rows={typed}; rows_missing_state_key='+str(sum('state' not in r for r in plot))
                                  if any('state' in r for r in plot) else f'plotted_rows={len(plot)}; no_typed_state_column_in_plotted_rows')
    metadata['denominator']=f"{len(plot)} plotted rows; {len({r.get('strain') for r in plot if r.get('strain')})} explicit isolate identifiers in plotted rows; units and tested denominators follow the recorded panel"
    validation=validate_caption_methods(metadata,nonstandard_visual=True)
    checks=[overlaps(svg,labels) for svg in sorted(folder.glob('*.svg'))] if scatter else []
    caption=(folder/'CAPTION.md').read_text()
    record=dict(metadata,validation=validation,public_caption=caption,svg_label_checks=checks,
                assay_state_policy='preserve installed renderer inputs/outputs; no recoding here',visual_qa='NOT_PERFORMED')
    with (folder/'CAPTION_METHODS.json').open('x') as stream:json.dump(record,stream,indent=2,ensure_ascii=False)
    if any(c['problems'] for c in checks):raise ValueError('SVG label overlaps found; see CAPTION_METHODS.json')
    return record
