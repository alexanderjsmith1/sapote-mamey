"""Count support-label overlaps in a tree SVG written by svglite (house rule: measure from the SVG).

A support label is a <text> whose content is 2-3 digits (optionally 100) and whose fill is not white.
White copies are halo passes and are skipped. Its box runs from the text anchor across textLength
(the width svglite measured), and from the baseline up to 0.716 em, the cap height of Arial and
Helvetica digits. Digits have no descenders.

Tip symbols are <circle> elements that are not white.
Lines are <line> and <polyline> segments that are not white. A segment drawn in the leader colour
(--leader-colour) that touches a label is that label's own leader. It is counted separately and is
not an overlap.

Writes one TSV row per overlap and prints the counts. Exit 0 always; the counts are the result.\nmeasure() returns the same counts for tests.
Usage: python3 svg_label_overlaps.py FIG.svg [--out overlaps.tsv] [--leader-colour #595959] [--pad 1]
--pad adds clearance round every label box, so labels that touch also count.
"""
import argparse, re, sys
try:  # CSV formula-cell guard, as in every other tools/ writer
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import xml.etree.ElementTree as ET

CAP = 0.716
NUM = re.compile(r'^\d{2,3}$')

def style(el):
    s = {}
    for part in (el.get('style') or '').split(';'):
        if ':' in part:
            k, v = part.split(':', 1); s[k.strip()] = v.strip()
    return s

def is_white(c):
    return (c or '').upper() in ('#FFFFFF', 'WHITE', '#FFF')

def seg_hits_box(x1, y1, x2, y2, b):
    """Liang-Barsky clip: does the segment enter the open box b = (x0, y0, x1, y1)?"""
    bx0, by0, bx1, by1 = b
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - bx0), (dx, bx1 - x1), (-dy, y1 - by0), (dy, by1 - y1)):
        if p == 0:
            if q <= 0: return False
        else:
            t = q / p
            if p < 0:
                if t > t1: return False
                t0 = max(t0, t)
            else:
                if t < t0: return False
                t1 = min(t1, t)
    return t1 - t0 > 1e-9

def boxes_overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

def measure(svg, pad=0.0, leader='#595959', ambig_gap=4.0):
    """Return (n_labels, rows, own_leaders); rows are (kind, label, other, box) for every overlap found.
    Kind 'ambiguous-pair': two labels whose glyph boxes overlap in y (or come within 1 pt) and sit within ambig_gap pt of
    each other horizontally, with a vertical branch line between them, so a reader cannot tell which node each belongs to.
    This test always uses glyph boxes; --pad does not widen it."""
    root = ET.parse(svg).getroot()
    ns = '{http://www.w3.org/2000/svg}'
    labels, segs, dots = [], [], []
    for el in root.iter():
        tag = el.tag.replace(ns, '')
        st = style(el)
        if tag == 'text':
            txt = (el.text or '').strip()
            if not NUM.match(txt) or is_white(st.get('fill')): continue
            fs = float(st['font-size'].replace('px', '')); x = float(el.get('x')); y = float(el.get('y'))
            w = float((el.get('textLength') or '0').replace('px', ''))
            anc = el.get('text-anchor', 'start')
            x0 = x - w if anc == 'end' else (x - w / 2 if anc == 'middle' else x)
            if el.get('transform'): raise ValueError('rotated support text not handled: ' + txt)
            labels.append(dict(text=txt, box=(x0 - pad, y - CAP * fs - pad, x0 + w + pad, y + pad), glyph=(x0, y - CAP * fs, x0 + w, y)))
        elif tag == 'circle':
            if is_white(st.get('fill')) and is_white(st.get('stroke')): continue
            cx, cy, r = float(el.get('cx')), float(el.get('cy')), float(el.get('r'))
            dots.append((cx - r, cy - r, cx + r, cy + r))
        elif tag in ('line', 'polyline'):
            col = st.get('stroke', '#000000')
            if is_white(col) or st.get('stroke') == 'none': continue
            if tag == 'line':
                pts = [(float(el.get('x1')), float(el.get('y1'))), (float(el.get('x2')), float(el.get('y2')))]
            else:
                v = [float(t) for t in re.split(r'[ ,]+', el.get('points').strip())]
                pts = list(zip(v[0::2], v[1::2]))
            for p, q in zip(pts, pts[1:]):
                segs.append(dict(p=p, q=q, colour=col.upper(), dashed='stroke-dasharray' in (el.get('style') or '')))
    rows = []
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            if boxes_overlap(labels[i]['box'], labels[j]['box']):
                rows.append(('label-label', labels[i]['text'], labels[j]['text'], '%.2f,%.2f' % labels[i]['box'][:2]))
    leaders = 0
    for L in labels:
        for s in segs:
            if seg_hits_box(*s['p'], *s['q'], L['box']):
                if s['colour'] == leader.upper():
                    leaders += 1; continue
                rows.append(('label-line', L['text'], ('dotted ' if s['dashed'] else '') + s['colour'] + ' %.2f,%.2f-%.2f,%.2f' % (*s['p'], *s['q']), '%.2f,%.2f' % L['box'][:2]))
        for dbox in dots:
            if boxes_overlap(L['box'], dbox):
                rows.append(('label-symbol', L['text'], 'circle %.2f,%.2f' % ((dbox[0] + dbox[2]) / 2, (dbox[1] + dbox[3]) / 2), '%.2f,%.2f' % L['box'][:2]))
    verts = [s for s in segs if abs(s['p'][0] - s['q'][0]) < 1e-6 and s['colour'] != leader.upper() and not s['dashed']]
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            a, b = labels[i]['glyph'], labels[j]['glyph']
            if a[0] > b[0]: a, b = b, a
            gap = b[0] - a[2]
            if not (0 <= gap <= ambig_gap) or a[1] > b[3] + 1 or b[1] > a[3] + 1: continue
            ylo, yhi = max(a[1], b[1]) - 1, min(a[3], b[3]) + 1
            hit = [v for v in verts if a[2] <= v['p'][0] <= b[0] and min(v['p'][1], v['q'][1]) < yhi and max(v['p'][1], v['q'][1]) > ylo]
            if hit:
                rows.append(('ambiguous-pair', labels[i]['text'], labels[j]['text'] + ' gap %.2f pt across x=%.2f' % (gap, hit[0]['p'][0]), '%.2f,%.2f' % a[:2]))
    return len(labels), rows, leaders

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('svg'); ap.add_argument('--out'); ap.add_argument('--leader-colour', default='#595959')
    ap.add_argument('--pad', type=float, default=0.0, help='clearance in pt added round each label box; 0 = glyph boxes')
    ap.add_argument('--ambig-gap', type=float, default=4.0, help='max horizontal gap (pt) for an ambiguous pair across a vertical line')
    a = ap.parse_args()
    n, rows, leaders = measure(a.svg, a.pad, a.leader_colour, a.ambig_gap)
    k = lambda kind: sum(r[0] == kind for r in rows)
    sys.stdout.write(f'{a.svg.split("/")[-1]} [pad {a.pad:g} pt]: support labels {n}; label-label overlaps {k("label-label")}; '
                     f'label-line overlaps {k("label-line")}; label-symbol overlaps {k("label-symbol")}; ambiguous pairs (gap <= {a.ambig_gap:g} pt) {k("ambiguous-pair")}; own leaders touching {leaders}\n')
    if a.out:
        with open(a.out, 'w', newline='') as f:
            w = _SafeWriter(f, delimiter='\t', lineterminator='\n'); w.writerow(['kind', 'label', 'other', 'label_box_x0_y0_pt']); w.writerows(rows)

if __name__ == '__main__':
    main()
