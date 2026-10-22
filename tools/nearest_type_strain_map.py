#!/usr/bin/env python3
"""Draw a supplied anchor tree and supplied isolate assignments; no nearest search."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools._map_export import read_table,write_table,print_setup,output_preflight,export,record_table_output
from mamey.figure_theme import PALETTE

TOOL='nearest_type_strain_map'
PALETTE_PATH=ROOT/'mamey/data/genus_palette.json'


def load(tree_path, anchor_path, mapping_path, palette_set='default'):
    from Bio import Phylo
    tree=Phylo.read(tree_path,'newick');tips=[t.name for t in tree.get_terminals()]
    if not tips or any(not t for t in tips) or len(set(tips))!=len(tips):raise ValueError('TREE_TIPS: unique named tips required')
    for clade in tree.find_clades():
        if clade is tree.root and clade.branch_length is None:continue
        if clade.branch_length is None or not math.isfinite(clade.branch_length) or clade.branch_length<0:
            raise ValueError('TREE_LENGTH: finite nonnegative branch lengths required')
    rows,fields=read_table(anchor_path,('tip','deposited_organism_name'))
    anchors={r['tip']:r for r in rows}
    if len(anchors)!=len(rows) or set(anchors)!=set(tips):raise ValueError('ANCHOR_TIPS: exactly one anchor per tree tip required')
    raw=json.loads(PALETTE_PATH.read_text());colors=dict(raw['default'])
    if palette_set!='default':
        if palette_set not in raw.get('sets',{}):raise ValueError('UNKNOWN_PALETTE_SET: '+palette_set)
        colors.update(raw['sets'][palette_set])
    present='fromtype' in fields
    for row in rows:
        name=row['deposited_organism_name']
        if not name.strip():raise ValueError('EMPTY_DEPOSITED_NAME: '+row['tip'])
        value=row.get('fromtype','').strip().lower()
        if value not in ('','0','1','true','false'):raise ValueError('INVALID_FROMTYPE: '+row['tip'])
        row['type_marker']=present and value in ('1','true')
        matches=[g for g in colors if name==g or name.startswith(g+' ')]
        genus=max(matches,key=len) if matches else name.split()[0]
        row['genus']=genus;row['color']=colors.get(genus,raw['fallback']);row['fallback_color']=raw['fallback']
    mapping,_=read_table(mapping_path,('isolate','anchor_tip','host_as_recorded'))
    seen=set();counts=Counter()
    for row in mapping:
        if not row['isolate'].strip() or row['isolate'] in seen:raise ValueError('ISOLATE_ID: unique nonblank isolate required')
        seen.add(row['isolate'])
        if row['anchor_tip'] not in anchors:raise ValueError('UNKNOWN_ANCHOR: '+row['anchor_tip'])
        counts[row['anchor_tip'],row['host_as_recorded']]+=1
    return tree,anchors,counts,len(mapping),present


def raw_fallback(anchors):
    """The palette fallback colour, as load() recorded it on each anchor row."""
    return next(iter(anchors.values())).get('fallback_color')


def _lum(h):
    h=h.lstrip('#');c=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    c=[x/12.92 if x<=.03928 else ((x+.055)/1.055)**2.4 for x in c]
    return .2126*c[0]+.7152*c[1]+.0722*c[2]


def text_colour(hex_colour,min_contrast=4.5):
    """The genus colour for tip text, darkened toward black until it reaches min_contrast against white (WCAG); dark
    colours are returned unchanged. Light genus colours (a yellow, a pale pink) printed as text could not be read."""
    if not isinstance(hex_colour,str) or not hex_colour.startswith('#') or len(hex_colour)!=7:return hex_colour
    h=hex_colour.lstrip('#');rgb=[int(h[i:i+2],16) for i in (0,2,4)];f=1.0
    while (1.05)/(_lum('#%02x%02x%02x'%tuple(round(v*f) for v in rgb))+.05)<min_contrast and f>0:f=round(f-.05,2)
    return '#%02x%02x%02x'%tuple(round(v*max(f,0)) for v in rgb)


def draw(tree,anchors,counts,width=7.2,floor=8,tip_dots=False,row_in=.17):
    plt=print_setup(width,floor)
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    from matplotlib.ticker import MaxNLocator
    tips=tree.get_terminals();hosts=sorted({host for tip,host in counts})
    host_colors=[PALETTE[k] for k in (('gold','teal','coral','navy') if len(hosts)<=4 else ('gold','teal','coral','muted','navy'))]
    if len(hosts)>len(host_colors):raise ValueError('HOST_PALETTE_LIMIT: at most five host labels')
    palette=dict(zip(hosts,host_colors))
    # layout in inches: one row per tip (0.17 in unless --row-height), then the axis labels, then the legends with only the rows they need
    fallback=raw_fallback(anchors)
    shown={}
    for r in anchors.values():
        shown['Other genera' if r['color']==fallback else r['genus']]=r['color']
    other=sorted({r['genus'] for r in anchors.values() if r['color']==fallback})
    leg_rows=max(-(-len(shown)//3),len(hosts))
    rows_in=len(tips)*row_in;axis_in=.45;leg_in=.5+leg_rows*.19;top_in=.12
    height=max(3.8,top_in+rows_in+axis_in+leg_in)
    bottom=(axis_in+leg_in)/height;h=rows_in/height
    fig=plt.figure(figsize=(width,height));treeax=fig.add_axes([.06,bottom,.23,h]);namesax=fig.add_axes([.31,bottom,.44,h]);barax=fig.add_axes([.78,bottom,.19,h])
    ys={tip:len(tips)-1-i for i,tip in enumerate(tips)}
    def ypos(clade):
        if clade not in ys:ys[clade]=sum(ypos(c) for c in clade.clades)/len(clade.clades)
        return ys[clade]
    ypos(tree.root);depths=tree.depths();maximum=max(depths.values())
    if maximum<=0:raise ValueError('TREE_LENGTH: positive total depth required')
    for c in tree.find_clades():
        if c.clades:
            treeax.plot([depths[c]]*2,[min(ys[x] for x in c.clades),max(ys[x] for x in c.clades)],color=PALETTE['ink'],lw=.65)
            for child in c.clades:treeax.plot([depths[c],depths[child]],[ys[child]]*2,color=PALETTE['ink'],lw=.65)
    bars=[]
    for tip in tips:
        row=anchors[tip.name];y=ys[tip]
        treeax.plot([depths[tip],maximum*1.04],[y,y],ls=':',color=PALETTE['muted'],lw=.5)
        if tip_dots:treeax.scatter([depths[tip]],[y],s=14,c=row['color'],zorder=3)   # off by default: the name colour carries the genus
        namesax.text(0,y,row['deposited_organism_name']+(' [T]' if row['type_marker'] else ''),va='center',fontsize=floor,fontstyle='italic',color=text_colour(row['color']))
        left=0
        for host in hosts:
            n=counts[tip.name,host]
            barax.barh(y,n,left=left,height=.62,color=palette[host],edgecolor='white',linewidth=.3)
            bars.append(dict(tip=tip.name,host_as_recorded=host,isolates=n));left+=n
    for ax in (treeax,namesax,barax):ax.set_ylim(-.6,len(tips)-.4);ax.set_yticks([]);ax.grid(False)
    namesax.set_xlim(0,1);namesax.axis('off')
    treeax.set_xlim(0,maximum*1.05);treeax.set_xlabel('Branch length');treeax.xaxis.set_major_locator(MaxNLocator(nbins=3))
    barax.set_xlabel('Isolates');barax.xaxis.set_major_locator(MaxNLocator(nbins=3,integer=True));barax.set_xlim(0,max(1,max(sum(counts[t.name,h] for h in hosts) for t in tips))*1.05)
    for ax in (treeax,barax):
        for side in ('left','top','right'):ax.spines[side].set_visible(False)
    order=sorted(g for g in shown if g!='Other genera')+(['Other genera'] if 'Other genera' in shown else [])
    gl=fig.legend(handles=[Patch(facecolor=shown[g],edgecolor='none',label=g) for g in order],loc='lower left',bbox_to_anchor=(.03,.015),ncol=3,frameon=False,title='Genus',title_fontsize=floor)
    for t in gl.get_texts():
        if t.get_text()!='Other genera':t.set_fontstyle('italic')
    fig._other_genera=other
    fig.legend(handles=[Patch(facecolor=palette[h],label=h or '(blank as recorded)') for h in hosts],loc='lower right',bbox_to_anchor=(.98,.015),ncol=1,frameon=False,title='Host as recorded',title_fontsize=floor)
    fig.canvas.draw();right=barax.get_window_extent().x0-6
    if any(t.get_window_extent().x1>right for t in namesax.texts):raise ValueError('TIP_TEXT_DOES_NOT_FIT: increase print width')
    return fig,bars,palette


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('tree','anchors','isolate-map','out'):p.add_argument('--'+arg,required=True,type=Path)
    p.add_argument('--palette-set',default='default');p.add_argument('--print-width',type=float,default=7.2);p.add_argument('--min-text-pt',type=float,default=8)
    p.add_argument('--row-height',type=float,default=.17,help='inches per tip row (default 0.17); at least 0.14 so 8 pt names do not touch')
    p.add_argument('--tip-dots',action='store_true',help='also draw a genus-coloured dot at each tip (off: the coloured name carries the genus)')
    a=p.parse_args(argv)
    if not .14<=a.row_height<=.4:raise ValueError('ROW_HEIGHT_RANGE: 0.14 to 0.4 in')
    output_preflight(a.out)
    tree,anchors,counts,n,present=load(a.tree,a.anchors,a.isolate_map,a.palette_set)
    fig,bars,host_colors=draw(tree,anchors,counts,a.print_width,a.min_text_pt,a.tip_dots,a.row_height)
    info=dict(type_marker_source='supplied NCBI fromtype column' if present else 'column absent; no type markers',palette_set=a.palette_set,
              isolate_rows=n,host_bar_sum=sum(r['isolates'] for r in bars),host_colors=host_colors,
              other_genera=getattr(fig,'_other_genera',[]),
              tree_action='supplied topology, root and branch lengths retained; no inference or nearest search',
              tip_labels=[dict(tip=k,name=v['deposited_organism_name'],type_marker=v['type_marker'],genus=v['genus'],color=v['color'],text_color=text_colour(v['color'])) for k,v in anchors.items()],
              tip_dots=a.tip_dots)
    export(fig,a.out,TOOL,[a.tree,a.anchors,a.isolate_map,PALETTE_PATH,Path(__file__),ROOT/'tools/_map_export.py',ROOT/'mamey/figure_theme.py',ROOT/'mamey/figure_stamp.py'],info,a.min_text_pt)
    write_table(a.out/'host_counts.tsv',bars,['tip','host_as_recorded','isolates'])
    record_table_output(a.out,"host_counts.tsv")
    from matplotlib import pyplot as plt
    plt.close(fig)
    return 0

if __name__=='__main__':raise SystemExit(main())
