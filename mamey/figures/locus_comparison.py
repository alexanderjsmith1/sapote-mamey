"""Portable, evidence-supplied locus comparisons; no search or linkage inference.

Coordinates are zero-based, half-open. An orientation is a rigid whole-track
transform. Each contig remains a separate track, including RGGMCI candidates.
"""
from __future__ import annotations
import hashlib
import colorsys
import json
import math
import re
from pathlib import Path
# every raster write clamps DPI under the Agg pixel ceiling (mamey/render_safe.py)
try:
    from ..render_safe import safe_savefig_dpi as _safe_dpi
except ImportError:  # loaded by file path (tests/test_locus_comparison.py), outside the package
    from mamey.render_safe import safe_savefig_dpi as _safe_dpi

PALETTE = ('#4477AA', '#228833', '#AA3377', '#EE7733', '#009988', '#995500',
           '#EE99AA', '#66AADD', '#CCBB44', '#CC3311', '#7744AA', '#117733')


def _number(value, name):
    """Reject booleans and nonfinite numeric evidence."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name}: finite number required')
    return value


def validate(spec):
    """Validate the portable input before importing a graphics dependency."""
    if spec.get('schema') != 'locus-comparison-v1':
        raise ValueError('schema must be locus-comparison-v1')
    if not isinstance(spec.get('title'), str) or not spec['title'].strip():
        raise ValueError('title required')
    if not isinstance(spec.get('synthetic'), bool):
        raise ValueError('synthetic must be explicit true/false')
    if spec.get('identity_side', 'a') not in ('a', 'b'):
        raise ValueError('identity_side must be a or b')
    tracks = spec.get('tracks', [])
    if not 2 <= len(tracks) <= 12:
        raise ValueError('supply 2 to 12 separate locus tracks')
    ids, lookup = set(), {}
    for t in tracks:
        if not isinstance(t.get('id'), str) or not t['id'] or t['id'] in ids:
            raise ValueError('unique track IDs required')
        ids.add(t['id'])
        if not t.get('label') or not t.get('identity'):
            raise ValueError('track label and identity required')
        ident = t['identity']
        keys = ('strain', 'contig', 'region', 'bgc') if t.get('kind') == 'bgc' else ('accession', 'description')
        if t.get('kind') not in ('bgc', 'reference') or any(not str(ident.get(k, '')).strip() for k in keys):
            raise ValueError('complete BGC identity or reference accession/description required')
        if type(t.get('orientation')) is not int or t['orientation'] not in (-1, 1):
            raise ValueError('explicit orientation +1 or -1 required')
        if 'sequence_length' in t and (type(t['sequence_length']) is not int or t['sequence_length'] <= 0):
            raise ValueError('positive integer sequence_length required')
        genes = t.get('genes', [])
        if not genes:
            raise ValueError('empty track')
        for g in genes:
            key = (t['id'], g.get('id'))
            if not isinstance(g.get('id'), str) or not g['id'] or key in lookup:
                raise ValueError('unique gene IDs per track required')
            if any(type(g.get(k)) is not int for k in ('start', 'end', 'strand')):
                raise ValueError('integer coordinates and strand required')
            if g['start'] < 0 or g['end'] <= g['start'] or g['strand'] not in (-1, 1):
                raise ValueError('invalid half-open gene interval or strand')
            if 'sequence_length' in t and g['end'] > t['sequence_length']:
                raise ValueError('gene outside contig boundary')
            if type(g.get('missing_stop_codon', False)) is not bool:
                raise ValueError('missing_stop_codon must be boolean')
            if not re.fullmatch(r'[a-f0-9]{64}', g.get('aa_sha256', '')):
                raise ValueError('normalized AA SHA-256 required for every gene')
            if not isinstance(g.get('label'), str) or len(g['label']) > 32:
                raise ValueError('gene label must be a string of at most 32 characters')
            if not isinstance(g.get('group', ''), str):
                raise ValueError('group must be a string')
            lookup[key] = g
        if (t['id'], t.get('anchor_gene')) not in lookup:
            raise ValueError('anchor gene must exist on its track')
    seen = set()
    for link in spec.get('links', []):
        ends = [tuple(link.get(k, [])) for k in ('a', 'b')]
        if any(len(k) != 2 or k not in lookup for k in ends) or ends[0][0] == ends[1][0]:
            raise ValueError('link endpoints must exist on different tracks')
        pair = tuple(sorted(ends))
        if pair in seen:
            raise ValueError('duplicate correspondence')
        seen.add(pair)
        ga, gb = (lookup[k] for k in ends)
        if not ga.get('group') or ga['group'] != gb.get('group'):
            raise ValueError('link must join the same explicitly supplied correspondence group')
        if not isinstance(link.get('evidence'), str) or not link['evidence'].strip():
            raise ValueError('link evidence required')
        for field in ('identity_pct', 'query_coverage_pct', 'reference_coverage_pct'):
            if field in link and not 0 <= _number(link[field], field) <= 100:
                raise ValueError(f'{field}: percentage outside 0..100')
    if not isinstance(spec.get('sources'), list) or (not spec['synthetic'] and not spec['sources']):
        raise ValueError('research inputs require source path and SHA-256 records')
    for s in spec['sources']:
        if not s.get('path') or not re.fullmatch('[a-f0-9]{64}', s.get('sha256', '')):
            raise ValueError('invalid source binding')
    display = spec.get('display', {})
    if not isinstance(display, dict):
        raise ValueError('display must be an object')
    for key, default in (('label_rotation', 0), ('font_size', 10), ('width_in', 18)):
        n = _number(display.get(key, default), 'display.' + key)
        if (key == 'label_rotation' and not 0 <= n <= 80) or (key != 'label_rotation' and n <= 0):
            raise ValueError('invalid display.' + key)
    if display.get('view', 'slide' if display.get('label_rotation') else 'report') not in ('slide', 'report'):
        raise ValueError('display.view must be slide or report')
    if 'axis_label' in display and not isinstance(display['axis_label'], str):
        raise ValueError('display.axis_label must be a string')
    if 'axis_zero_track' in display and display['axis_zero_track'] not in ids:
        raise ValueError('display.axis_zero_track must name an existing track')
    for track in tracks:
        tid = track['id']
        _number(track.get('offset_bp', 0), tid + '.offset_bp')
        row = track.get('row', tid)
        if type(row) not in (str, int) or (isinstance(row, str) and not row):
            raise ValueError(tid + ': row must be a nonempty string or integer')
        for key, allowed in (('label_side', ('above', 'below', 'none')), ('heading_side', ('above', 'below', 'left')), ('heading_align', ('left', 'right'))):
            if key in track and track[key] not in allowed:
                raise ValueError(tid + ': invalid ' + key)
        if 'subtitle' in track and not isinstance(track['subtitle'], str):
            raise ValueError(tid + ': subtitle must be a string')
    return lookup


def layout(spec):
    """Return exact rigid transforms and strand agreement; never reorder genes."""
    lookup = validate(spec)
    rows = []
    for t in spec['tracks']:
        g = lookup[(t['id'], t['anchor_gene'])]
        anchor = (g['start'] + g['end']) / 2
        for g in t['genes']:
            a = t['orientation'] * (g['start'] - anchor) + t.get('offset_bp', 0)
            b = t['orientation'] * (g['end'] - anchor) + t.get('offset_bp', 0)
            rows.append(dict(track=t['id'], gene=g['id'], native_start=g['start'], native_end=g['end'],
                             native_strand=g['strand'], display_start=min(a, b), display_end=max(a, b),
                             display_strand=t['orientation'] * g['strand'], anchor_bp=anchor,
                             orientation=t['orientation'], offset_bp=t.get('offset_bp', 0), group=g.get('group', ''), aa_sha256=g['aa_sha256']))
    by = {(r['track'], r['gene']): r for r in rows}
    links = []
    for link in spec.get('links', []):
        a, b = (by[tuple(link[k])] for k in ('a', 'b'))
        links.append(dict(link, displayed_strands_agree=a['display_strand'] == b['display_strand']))
    return rows, links


def verify_drawn_orientation(spec, drawn, receipt):
    """Reject disagreement between source transform, actual arrows and receipt."""
    rows, _ = layout(spec)
    expected = {(r['track'], r['gene']): r for r in rows}
    if receipt.get('orientation') != {t['id']: t['orientation'] for t in spec['tracks']}:
        raise ValueError('orientation receipt disagrees with source transform')
    if len(drawn) != len(expected) or len({(r['track'],r['gene']) for r in drawn}) != len(expected):
        raise ValueError('drawn gene identity mismatch')
    for r in drawn:
        ref = expected.get((r['track'], r['gene']))
        if ref is None or r['display_strand'] != ref['display_strand']:
            raise ValueError('drawn strand disagrees with orientation receipt')
        if any(not math.isclose(r[k],ref[k],abs_tol=1e-6) for k in ('display_start','display_end')):
            raise ValueError('drawn coordinates disagree with orientation receipt')
    return True


def render(input_path, outdir):
    """Read a small JSON manifest and export SVG, PNG, PDF, data and receipt."""
    path, out = Path(input_path).resolve(), Path(outdir).resolve()
    raw = path.read_bytes()
    spec = json.loads(raw)
    rows, links = layout(spec)
    for src in spec['sources']:
        p = Path(src['path'])
        p = p if p.is_absolute() else path.parent / p
        digest = hashlib.sha256()
        with p.open('rb') as f:
            for block in iter(lambda: f.read(1024 * 1024), b''):
                digest.update(block)
        if digest.hexdigest() != src['sha256']:
            raise ValueError(f'source hash mismatch: {p}')
    outputs = ('comparison.svg', 'comparison.png', 'comparison.pdf', 'display_coordinates.json', 'receipt.json')
    if any((out / name).exists() for name in outputs):
        raise FileExistsError('output already exists; choose a fresh output directory')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrow, Polygon
    matplotlib.rcParams['svg.fonttype'] = 'none'
    if _slide_view(spec):
        return _render_slide(spec, raw, rows, links, out, outputs)
    tracks = spec['tracks']
    by = {(r['track'], r['gene']): r for r in rows}
    genes = validate(spec)
    groups = sorted({r['group'] for r in rows if r['group']})
    colors = {g: (PALETTE[i] if len(groups) <= len(PALETTE) else '#%02x%02x%02x' % tuple(round(c*255) for c in colorsys.hsv_to_rgb(i/len(groups), .62, .72))) for i, g in enumerate(groups)}
    y = {t['id']: (len(tracks) - i - 1) * 1.4 for i, t in enumerate(tracks)}
    fig, ax = plt.subplots(figsize=(18, 3 + 2.2 * len(tracks)))
    fig.subplots_adjust(left=.05, right=.97, top=.83, bottom=.27)
    fig.text(.05, .95, spec['title'], fontsize=18, weight='bold', color='#163344')
    fig.text(.05, .90, 'Supplied gene correspondences; whole-locus orientation; common kb scale', fontsize=11)
    for link in links:
        a, b = (by[tuple(link[k])] for k in ('a', 'b'))
        ya, yb = y[a['track']], y[b['track']]
        delta = .10 if yb > ya else -.10
        ax.add_patch(Polygon([(a['display_start']/1000, ya+delta), (a['display_end']/1000, ya+delta),
                              (b['display_end']/1000, yb-delta), (b['display_start']/1000, yb-delta)],
                             facecolor=colors[a['group']], alpha=.19, edgecolor='none', zorder=1))
    lo = min(r['display_start'] for r in rows)/1000
    hi = max(r['display_end'] for r in rows)/1000
    for t in tracks:
        if 'sequence_length' in t:
            anchor = by[(t['id'], t['anchor_gene'])]['anchor_bp']
            ends = [(t['orientation']*(x-anchor)+t.get('offset_bp',0))/1000 for x in (0,t['sequence_length'])]
            lo=min(lo,*ends);hi=max(hi,*ends)
    pad = max((hi-lo)*.025, .05)
    ax.set_xlim(lo-pad, hi+pad)
    texts = []
    drawn = []
    for t in tracks:
        yy = y[t['id']]
        ident = t['identity']
        identity = ' / '.join(str(ident[k]) for k in ('strain','contig','region','bgc')) if t['kind']=='bgc' else ident['description']+' / '+ident['accession']
        below = t is tracks[-1]
        ax.text(lo-pad, yy-.38 if below else yy+.58, t['label'], weight='bold', fontsize=12)
        ax.text(lo-pad, yy-.57 if below else yy+.41, identity, fontsize=9, color='#405664')
        rr = [r for r in rows if r['track']==t['id']]
        ax.plot([min(r['display_start'] for r in rr)/1000,max(r['display_end'] for r in rr)/1000], [yy,yy],color='#a8b5bc',lw=.7)
        if 'sequence_length' in t:
            anchor=by[(t['id'],t['anchor_gene'])]['anchor_bp']
            for native,word in ((0,'contig start'),(t['sequence_length'],'contig end')):
                xx=(t['orientation']*(native-anchor)+t.get('offset_bp',0))/1000
                ax.plot([xx,xx],[yy-.13,yy+.13],color='#172f40',lw=1.5,zorder=5)
                ax.text(xx,yy-.39,f'{word} ({native:,} bp)',ha='left' if xx<(lo+hi)/2 else 'right',fontsize=8,zorder=5)
        for r in rr:
            s,e=r['display_start']/1000,r['display_end']/1000
            st=r['display_strand'];g=genes[(r['track'],r['gene'])]
            arrow=FancyArrow(s if st>0 else e,yy,(e-s)*st,0,width=.10,head_width=.19,
                         head_length=min((e-s)*.35,(hi-lo)*.009),length_includes_head=True,
                         facecolor=colors.get(r['group'],'#d6dcdf'),edgecolor='#405664',lw=.7,zorder=3)
            ax.add_patch(arrow)
            drawn.append(dict(track=r['track'],gene=r['gene'],display_strand=1 if arrow._dx>0 else -1,
                              display_start=min(arrow._x,arrow._x+arrow._dx)*1000,
                              display_end=max(arrow._x,arrow._x+arrow._dx)*1000))
            if g['label']:
                texts.append((t['id']+':gene', ax.text((s+e)/2,yy+.16,g['label']+('*' if g.get('missing_stop_codon') else ''),ha='center',va='bottom',fontsize=10,zorder=4)))
    # A target with one supplied comparison can show identity without an ambiguous denominator.
    for key in genes:
        incoming = [link for link in links if tuple(link[spec.get('identity_side','a')]) == key and 'identity_pct' in link]
        if len(incoming) == 1:
            r = by[key]
            texts.append((key[0]+':identity', ax.text((r['display_start']+r['display_end'])/2000,y[key[0]]-.18,
                    f"{incoming[0]['identity_pct']:.1f}%",ha='center',va='top',fontsize=9,zorder=5,bbox=dict(facecolor='white',edgecolor='none',pad=.5,alpha=.85))))
    ax.set_ylim(-.85,max(y.values())+.85)
    ax.set_yticks([])
    for side in ('top','right','left'):ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color('#a8b5bc')
    ax.set_xlabel('Distance from each declared anchor midpoint (kb); same scale on every track')
    ax.axvline(0,color='#a8b5bc',ls=':',lw=.7,zorder=0)
    fig.text(.05,.17,spec.get('identity_caption','Identity percentages: supplied protein comparison; see source evidence.'),fontsize=10)
    fig.text(.05,.13,spec.get('label_caption',''),fontsize=10)
    fig.text(.05,.09,'Colors and ribbons show supplied correspondences, not proven function, production or physical linkage.',fontsize=10)
    fig.text(.05,.055,'Grey: no supplied correspondence group. Individual genes are never moved to improve visual agreement.',fontsize=10)
    if any(g.get('missing_stop_codon') for g in genes.values()):
        fig.text(.05,.02,'* Missing stop codon in the source CDS; contig end is an assembly limit, not a proven pathway boundary.',fontsize=10)
    # Keep the requested single baseline. Refuse dense overlaps instead of staggering silently.
    fig.canvas.draw()
    renderer=fig.canvas.get_renderer()
    for track in {tid for tid, _ in texts}:
        boxes=sorted([tx.get_window_extent(renderer) for tid,tx in texts if tid==track],key=lambda b:b.x0)
        if any(a.x1+2>b.x0 for a,b in zip(boxes,boxes[1:])):
            plt.close(fig)
            raise ValueError('gene labels overlap; shorten labels or select a narrower locus view')
    for tx in list(fig.texts) + list(ax.texts) + [ax.xaxis.label]:
        if tx.get_visible() and tx.get_text().strip():
            box = tx.get_window_extent(renderer)
            if box.x0 < 0 or box.y0 < 0 or box.x1 > fig.bbox.width or box.y1 > fig.bbox.height:
                plt.close(fig)
                raise ValueError('text outside figure boundary; shorten labels or title')
    orientation_receipt={'orientation':{t['id']:t['orientation'] for t in tracks}}
    verify_drawn_orientation(spec,drawn,orientation_receipt)
    out.mkdir(parents=True,exist_ok=True)
    for ext in ('svg','png','pdf'):fig.savefig(out/f'comparison.{ext}',dpi=_safe_dpi(fig,180))
    plt.close(fig)
    (out/'display_coordinates.json').write_text(json.dumps({'genes':rows,'links':links,'drawn_arrows':drawn},indent=2)+'\n')
    receipt=dict(schema='locus-comparison-receipt-v1',input_sha256=hashlib.sha256(raw).hexdigest(),
                 sources=spec['sources'],coordinate_system='0-based half-open; display bp relative to anchors',
                 orientation={t['id']:t['orientation'] for t in tracks},
                 track_count=len(tracks),link_count=len(links),
                 displayed_strand_agreements=sum(x['displayed_strands_agree'] for x in links),
                 drawn_orientation_check='PASS',
                 assembly_markers={t['id']:{'sequence_length':t.get('sequence_length'),'missing_stop_genes':[g['id'] for g in t['genes'] if g.get('missing_stop_codon')]} for t in tracks},
                 group_colors=colors,visual_qa='REQUIRES_HUMAN_REVIEW',
                 files={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in outputs[:-1]})
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def _slide_view(spec):
    display = spec.get('display', {})
    return display.get('view', 'slide' if display.get('label_rotation') else 'report') == 'slide'


def _label_polygon(text, renderer):
    """Measured text rectangle in display pixels, rotated about its label anchor."""
    # Measure unrotated text with the same renderer/font, including descent.
    angle = text.get_rotation()
    text.set_rotation(0)
    box = text.get_window_extent(renderer)
    text.set_rotation(angle)
    point = text.axes.transData.transform(text.xy)
    offset = text.get_position()
    point = (point[0] + offset[0] * text.figure.dpi / 72,
             point[1] + offset[1] * text.figure.dpi / 72)
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    return [(point[0] + c*(x-point[0])-s*(y-point[1]),
             point[1] + s*(x-point[0])+c*(y-point[1]))
            for x,y in ((box.x0-1,box.y0-1),(box.x1+1,box.y0-1),
                        (box.x1+1,box.y1+1),(box.x0-1,box.y1+1))]


def _polygons_overlap(a, b):
    """Separating-axis check; unlike axis-aligned boxes, respects angled labels."""
    for poly in (a, b):
        for i, p in enumerate(poly):
            q = poly[(i+1) % len(poly)]
            axis = (p[1]-q[1], q[0]-p[0])
            aa = [x*axis[0]+y*axis[1] for x,y in a]
            bb = [x*axis[0]+y*axis[1] for x,y in b]
            if max(aa) <= min(bb) or max(bb) <= min(aa):
                return False
    return True


def _render_slide(spec, raw, rows, links, out, outputs):
    """Measured slide layout using the same validated geometry and export contract."""
    import textwrap
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrow, Polygon
    from matplotlib.transforms import Bbox
    tracks, display = spec['tracks'], spec.get('display', {})
    genes = validate(spec)
    by = {(r['track'], r['gene']): r for r in rows}
    groups = sorted({r['group'] for r in rows if r['group']})
    colors = {g: (PALETTE[i] if len(groups) <= len(PALETTE) else '#%02x%02x%02x' % tuple(round(c*255) for c in colorsys.hsv_to_rgb(i/len(groups), .62, .72))) for i,g in enumerate(groups)}
    row_ids = [t.get('row', t['id']) for t in tracks]
    order = list(dict.fromkeys(row_ids))
    if len(order) < 2:
        raise ValueError('slide view requires at least two distinct rows')
    y = {t['id']: (len(order)-1-order.index(row))*2.4 for t,row in zip(tracks,row_ids)}
    top, bottom = max(y.values()), min(y.values())
    sides = {}
    for t in tracks:
        tid = t['id']; yy = y[tid]
        expected = 'above' if yy == top else 'below' if yy == bottom else 'none'
        side = t.get('label_side', expected)
        heading = t.get('heading_side', 'left' if expected == 'none' else expected)
        if side not in (expected, 'none') or heading != ('left' if expected == 'none' else expected):
            raise ValueError(f'{tid}: slide labels/headings must face away from ribbon space')
        sides[tid] = (side, heading)
    fs, rotation = display.get('font_size',10), display.get('label_rotation',40)
    fig, ax = plt.subplots(figsize=(display.get('width_in',18),3+2*len(order)))
    try:
        fig.subplots_adjust(left=.05,right=.95,top=.83,bottom=.15)
        fig.text(.05,.96,spec['title'],fontsize=18,weight='bold',color='#163344',va='top')
        fig.text(.05,.90,'Supplied gene correspondences; whole-locus orientation; common kb scale',fontsize=11)
        lo=min(r['display_start'] for r in rows)/1000; hi=max(r['display_end'] for r in rows)/1000
        markers = {}
        for t in tracks:
            if 'sequence_length' in t:
                anchor=by[(t['id'],t['anchor_gene'])]['anchor_bp']
                ends=[(t['orientation']*(n-anchor)+t.get('offset_bp',0))/1000 for n in (0,t['sequence_length'])]
                markers[t['id']]=ends;lo=min(lo,*ends);hi=max(hi,*ends)
        pad=max((hi-lo)*.025,.05)
        ax.set_xlim(lo-pad,hi+pad);ax.set_ylim(bottom-.8,top+.8)
        drawn=[];labels=[];headings=[];omitted=[]
        for link in links:
            a,b=(by[tuple(link[k])] for k in ('a','b'));ya,yb=y[a['track']],y[b['track']]
            if ya==yb:raise ValueError(f"correspondence on shared row: {a['track']} / {b['track']}")
            delta=.10 if yb>ya else -.10
            ax.add_patch(Polygon([(a['display_start']/1000,ya+delta),(a['display_end']/1000,ya+delta),
                                  (b['display_end']/1000,yb-delta),(b['display_start']/1000,yb-delta)],facecolor=colors[a['group']],alpha=.19,edgecolor='none',zorder=1))
        for t in tracks:
            tid=t['id'];yy=y[tid];side,hside=sides[tid];rr=[r for r in rows if r['track']==tid]
            ax.plot([min(r['display_start'] for r in rr)/1000,max(r['display_end'] for r in rr)/1000],[yy,yy],color='#a8b5bc',lw=.7)
            for xx in markers.get(tid,[]):ax.plot([xx,xx],[yy-.13,yy+.13],color='#172f40',lw=1.5,zorder=5)
            for r in rr:
                s,e=r['display_start']/1000,r['display_end']/1000;st=r['display_strand'];g=genes[(tid,r['gene'])]
                arrow=FancyArrow(s if st>0 else e,yy,(e-s)*st,0,width=.10,head_width=.19,head_length=min((e-s)*.35,(hi-lo)*.009),length_includes_head=True,facecolor=colors.get(r['group'],'#d6dcdf'),edgecolor='#405664',lw=.7,zorder=3);ax.add_patch(arrow)
                drawn.append(dict(track=tid,gene=r['gene'],display_strand=1 if arrow._dx>0 else -1,display_start=min(arrow._x,arrow._x+arrow._dx)*1000,display_end=max(arrow._x,arrow._x+arrow._dx)*1000))
                label=g['label']+('*' if g.get('missing_stop_codon') else '')
                incoming=[link for link in links if tuple(link[spec.get('identity_side','a')])==(tid,r['gene']) and 'identity_pct' in link]
                if label.strip() and t['kind']=='bgc' and len(incoming)==1 and not re.search(r'\d+(?:\.\d+)?%\*?$',label):label+=f" {incoming[0]['identity_pct']:.0f}%"
                if side!='none' and label.strip():
                    up=side=='above';lab=ax.annotate(label,((s+e)/2,yy),xytext=(0,7 if up else -7),textcoords='offset points',ha='left',va='bottom' if up else 'top',fontsize=fs,rotation=rotation if up else -rotation,rotation_mode='anchor',zorder=4)
                    labels.append((tid,r['gene'],lab,bool(incoming) or g.get('missing_stop_codon',False)))
                if g.get('missing_stop_codon'):
                    ax.text((s+e)/2,yy,'*',fontsize=fs,ha='center',va='center',zorder=5)
            ident=t['identity'];sub=t.get('subtitle') or (' / '.join(str(ident[k]) for k in ('strain','contig','region','bgc')) if t['kind']=='bgc' else ident['description']+' / '+ident['accession'])
            if tid in markers:sub+=f"; contig start (0 bp), contig end ({t['sequence_length']:,} bp) marked"
            if any(g.get('missing_stop_codon') for g in t['genes']):sub+='; * missing stop codon'
            headings.append((t,hside,sub,rr))
        # Reserve measured horizontal room for left headings, then thin labels by
        # measured oriented rectangles across each shared row, not just each track.
        fig.canvas.draw();renderer=fig.canvas.get_renderer()
        left_width=0
        for t,hside,sub,rr in headings:
            if hside=='left':
                probe=ax.text(0,0,textwrap.fill(t['label'],26)+'\n'+textwrap.fill(sub,28),fontsize=12)
                left_width=max(left_width,probe.get_window_extent(renderer).width+12);probe.remove()
        if left_width:
            frac=left_width/ax.bbox.width
            if frac>=.6:raise ValueError('middle heading exceeds available figure width')
            ax.set_xlim(lo-pad-(hi-lo+2*pad)*frac/(1-frac),hi+pad)
        fig.canvas.draw();renderer=fig.canvas.get_renderer()
        kept=[]
        for tid,gid,lab,priority in sorted(labels,key=lambda x:(not x[3],ax.transData.transform(x[2].xy)[0])):
            poly=_label_polygon(lab,renderer)
            if any(y[tid]==y[kt] and _polygons_overlap(poly,kpoly) for kt,_,_,kpoly in kept):
                lab.set_visible(False);omitted.append({'track':tid,'gene':gid,'text':lab.get_text()});continue
            kept.append((tid,gid,lab,poly))
        # Headings are offset exactly six points beyond measured visible labels.
        placed=[];heading_artists=[];heading_records=[]
        for t,hside,sub,rr in headings:
            tid=t['id'];yy=y[tid];right=t.get('heading_align','left')=='right'
            hx=(max(r['display_end'] for r in rr) if right else min(r['display_start'] for r in rr))/1000;ha='right' if right else 'left'
            labs=[lab for kt,_,lab,_ in kept if y[kt]==yy];base_y=ax.transData.transform((hx,yy))[1]
            extent=max([((lab.get_window_extent(renderer).y1-base_y) if hside=='above' else (base_y-lab.get_window_extent(renderer).y0))*72/fig.dpi for lab in labs]+[0]);offset=extent+6
            bold=textwrap.fill(t['label'],26 if hside=='left' else 34);grey=textwrap.fill(sub,28 if hside=='left' else 48)
            for attempt in range(100):
                if hside=='left':
                    a=ax.annotate(bold,(min(r['display_start'] for r in rr)/1000-pad,yy),xytext=(0,3),textcoords='offset points',ha='right',va='bottom',fontsize=12,weight='bold')
                    b=ax.annotate(grey,a.xy,xytext=(0,-3),textcoords='offset points',ha='right',va='top',fontsize=9,color='#405664')
                else:
                    above=hside=='above';first=grey if above else bold
                    a=ax.annotate(first,(hx,yy),xytext=(0,offset if above else -offset),textcoords='offset points',ha=ha,va='bottom' if above else 'top',fontsize=9 if above else 12,weight='normal' if above else 'bold',color='#405664' if above else 'black')
                    height=a.get_window_extent(renderer).height*72/fig.dpi
                    b=ax.annotate(bold if above else grey,(hx,yy),xytext=(0,(offset+height+2)*(1 if above else -1)),textcoords='offset points',ha=ha,va='bottom' if above else 'top',fontsize=12 if above else 9,weight='bold' if above else 'normal',color='black' if above else '#405664')
                box=Bbox.union([a.get_window_extent(renderer),b.get_window_extent(renderer)])
                if not any(box.overlaps(other) for py,other in placed if py==yy):break
                if hside=='left':raise ValueError(f'headings overlap on track {tid}')
                a.remove();b.remove();offset+=box.height*72/fig.dpi+6
            else:raise ValueError(f'headings overlap on track {tid}')
            placed.append((yy,box));heading_artists.extend([a,b]);heading_records.append({'track':tid,'side':hside,'row_y':yy,'label_extent_pt':extent,'offset_pt':offset,'texts':[a.get_text(),b.get_text()]})
        # Solve data limits from point offsets, preserving the row pitch and scale.
        artists=[lab for _,_,lab,_ in kept]+heading_artists
        top_pt=bot_pt=0
        for art in artists:
            box=art.get_window_extent(renderer);ay=ax.transData.transform(art.xy)[1];yy=art.xy[1]
            if yy==top:top_pt=max(top_pt,(box.y1-ay)*72/fig.dpi)
            if yy==bottom:bot_pt=max(bot_pt,(ay-box.y0)*72/fig.dpi)
        H=ax.bbox.height*72/fig.dpi
        if top_pt+bot_pt+20>=H:
            fig.set_size_inches(fig.get_figwidth(),fig.get_figheight()+(top_pt+bot_pt+40-H)/72/.68);fig.canvas.draw();H=ax.bbox.height*72/fig.dpi
        span=(top-bottom)/(1-(top_pt+bot_pt+20)/H)
        ax.set_ylim(bottom-(bot_pt+10)*span/H,top+(top_pt+10)*span/H)
        zero_track=display.get('axis_zero_track') or next((t['id'] for t in tracks if t['kind']=='reference'),tracks[0]['id'])
        zero=min(r['display_start'] for r in rows if r['track']==zero_track)/1000
        xlo,xhi=ax.get_xlim();step=10**math.floor(math.log10(max((xhi-xlo)/10,.001)))
        step=next(k*step for k in (1,2,5,10) if (xhi-xlo)/(k*step)<=12)
        ticks=[zero+i*step for i in range(int(max(0,xhi-zero)/step)+1)]
        ax.set_xticks(ticks);ax.set_xticklabels([f'{i*step:g}' for i in range(len(ticks))]);ax.set_xlim(xlo,xhi)
        ax.set_xlabel(display.get('axis_label','kb from the first reference gene as drawn; same scale on every track'))
        ax.set_yticks([])
        for side in ('top','right','left'):ax.spines[side].set_visible(False)
        ax.spines['bottom'].set_color('#a8b5bc')
        fig.canvas.draw();renderer=fig.canvas.get_renderer()
        # Recheck final measured labels, including tracks sharing a row.
        for i,(tid,_,lab,_) in enumerate(kept):
            poly=_label_polygon(lab,renderer)
            if any(y[tid]==y[kt] and _polygons_overlap(poly,_label_polygon(other,renderer)) for kt,_,other,_ in kept[i+1:]):raise ValueError(f'gene labels overlap on track {tid}:gene')
        for art in list(fig.texts)+list(ax.texts)+[ax.xaxis.label]+ax.get_xticklabels():
            if art.get_visible() and art.get_text().strip():
                box=art.get_window_extent(renderer)
                if box.x0<0 or box.y0<0 or box.x1>fig.bbox.width or box.y1>fig.bbox.height:raise ValueError(f'text outside figure boundary ({art.get_text()!r})')
        orientation={'orientation':{t['id']:t['orientation'] for t in tracks}}
        verify_drawn_orientation(spec,drawn,orientation)
        out.mkdir(parents=True,exist_ok=True)
        for ext in ('svg','png','pdf'):fig.savefig(out/f'comparison.{ext}',dpi=_safe_dpi(fig,180))
        (out/'display_coordinates.json').write_text(json.dumps({'genes':rows,'links':links,'drawn_arrows':drawn},indent=2)+'\n')
        receipt=dict(schema='locus-comparison-receipt-v1',input_sha256=hashlib.sha256(raw).hexdigest(),sources=spec['sources'],coordinate_system='0-based half-open; orientation*(native-anchor midpoint)+offset_bp',orientation=orientation['orientation'],track_count=len(tracks),link_count=len(links),displayed_strand_agreements=sum(l['displayed_strands_agree'] for l in links),drawn_orientation_check='PASS',assembly_markers={t['id']:{'sequence_length':t.get('sequence_length'),'missing_stop_genes':[g['id'] for g in t['genes'] if g.get('missing_stop_codon')]} for t in tracks},group_colors=colors,visual_qa='REQUIRES_HUMAN_REVIEW',display_view='slide',heading_placements=heading_records,row_y=y,offset_bp={t['id']:t.get('offset_bp',0) for t in tracks},axis_zero_track=zero_track,axis_zero_bp=zero*1000,axis_ticks_kb=[i*step for i in range(len(ticks))],omitted_gene_labels=omitted,visible_gene_labels=[{'track':tid,'gene':gid,'text':lab.get_text()} for tid,gid,lab,_ in kept],files={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in outputs[:-1]})
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt
    finally:
        plt.close(fig)
