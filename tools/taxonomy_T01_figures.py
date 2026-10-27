#!/usr/bin/env python3
"""Render T01 using the printed paper ggplot layout and bundle palette/theme.

Inputs are explicit TSVs: --cohort needs strain,genus,block; --data needs strain
and similarity (T01), d4,d4_ci_low,d4_ci_high,type_strain (T05), or d4,similarity
(T06). Missing similarity is excluded and counted; missing dDDH is refused.
Cohort optional label_suffix, nudge_x, nudge_y preserve paper annotations without
strain-specific code. --merge-genus and --genus-order are display settings only.
"""
from __future__ import annotations

try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mamey.figure_stamp import stamp_file
from tools._min_text_check import add_args as _mt_args, enforce as _mt_enforce
TOOL = "taxonomy_T01_figures"
R_SCRIPT = 'suppressPackageStartupMessages({library(ggplot2); library(dplyr); library(ggrepel); library(ggtext)})\na <- commandArgs(TRUE)\nsource(a[1]); d <- read.delim(a[2], stringsAsFactors=FALSE, check.names=FALSE)\npaldata <- read.delim(a[3], stringsAsFactors=FALSE)\npal <- setNames(paldata$colour, paldata$genus)\nlayout <- a[4]; out <- a[5]; dpi <- as.numeric(a[6]); xmin <- as.numeric(a[10])\ngen <- paldata$genus; glab <- setNames(ifelse(grepl("aceae( bacterium)?$",gen),gen,paste0("<i>",gen,"</i>")),gen)\nd$genus_fig <- d$genus; d$isolate <- d$strain\nPAL <- pal; lv <- gen\nlegl <- setNames(ifelse(lv=="Other genera"|grepl("aceae( bacterium)?$",lv),lv,paste0("<i>",lv,"</i>")),lv)\nd$genus <- factor(d$genus,levels=rev(lv))\np <- ggplot(d, aes(x = similarity, fill = genus)) +\n  geom_histogram(breaks = seq(94.75, 100, by = 0.25), closed = "right", colour = "white", linewidth = 0.15) +\n  scale_fill_manual(values = PAL, breaks = lv, labels = legl, name = a[11]) +\n  scale_x_continuous(breaks = ceiling(xmin):100, labels = function(x) paste0(x, "%")) + coord_cartesian(xlim = c(xmin + 0.05, 100)) +\n  scale_y_continuous(breaks = function(l) { b <- scales::breaks_extended()(l); if (any(b != round(b))) b <- pretty(l); b[b == round(b)] }, expand = expansion(mult = c(0, 0.05))) +\n  labs(x = "16S rRNA gene similarity to the closest type strain", y = "Isolates") +\n  guides(fill = guide_legend(ncol = 2, keywidth = unit(7, "pt"), keyheight = unit(7, "pt"))) +\n  # Alex 2026-09-26: 1C looked small next to 1D because the legend sat under the bars; it now sits in the empty 95-98% area\n  theme_pub(7) + theme(panel.grid.major.x = element_blank(), axis.title = element_text(size = 7, colour = PUB_SUB),\n                      axis.text.x.bottom = element_markdown(size = 7, colour = PUB_INK), axis.text.y.left = element_markdown(size = 7, colour = PUB_INK),\n                      legend.text = element_markdown(size = 6.5), legend.title = element_text(size = 6.5, face = "bold"),\n                      legend.key.spacing.y = unit(0, "pt"), legend.margin = margin(2, 2, 2, 2), plot.margin = margin(3, 5, 2, 2), legend.position = "inside",\n                      legend.position.inside = c(0.02, 0.96), legend.justification = c(0, 1),\n                      legend.background = element_rect(fill = "white", colour = NA))\n\nw <- 3.4; h <- 3.05\nwrite.table(ggplot_build(p)$data[[1]][,c("count","xmin","xmax","group")],file=file.path(dirname(a[2]),"bins.tsv"),sep="\\t",row.names=FALSE)\nsource(a[9]); mt_save(p,out,w,h,list(min_text_pt=as.numeric(a[7]),print_width=if(a[8]=="auto") NULL else as.numeric(a[8]),dpi=dpi))\n'

def read_table(path, required):
    with path.open(newline="",encoding="utf-8-sig") as stream:
        reader=csv.DictReader(stream,delimiter="\t")
        if not required <= set(reader.fieldnames or []):
            raise ValueError(f"{path}: missing columns {sorted(required-set(reader.fieldnames or []))}")
        rows=list(reader)
    seen=set()
    for row in rows:
        if not row['strain'] or row['strain'] in seen: raise ValueError(f"{path}: empty or duplicate strain {row['strain']!r}")
        seen.add(row['strain'])
    return rows

def number(value, name, optional=False):
    if optional and (value is None or str(value).strip() in {"","NA","NaN"}): return None
    v=float(value)
    if not math.isfinite(v) or not 0<=v<=100: raise ValueError(f"{name}: expected finite percent 0..100")
    return v

def run(args):
    palette_path=getattr(args,'palette_json',None) or ROOT/'mamey/data/genus_palette.json'
    config=json.loads(palette_path.read_text())
    if not isinstance(config.get('default'),dict) or not isinstance(config.get('sets'),dict) or not isinstance(config.get('fallback'),str):
        raise ValueError('palette JSON must use the bundle default/sets/fallback schema')
    supplied=list(config['default'].values())+[config['fallback']]+[v for d in config['sets'].values() for v in d.values()]
    import re
    if any(not isinstance(v,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',v) for v in supplied):
        raise ValueError('palette colours must be six-digit hex')
    colours=dict(config['default']); colours.update(config['sets'].get(args.palette_set or '',{}))
    cohort=read_table(args.cohort, {'strain','genus','block'})
    required={'strain'} | ({'similarity'} if 'T01'=='T01' else {'d4','d4_ci_low','d4_ci_high','type_strain'} if 'T01'=='T05' else {'d4','similarity'})
    data=read_table(args.data,required); lookup={r['strain']:r for r in data}
    extra=set(lookup)-{r['strain'] for r in cohort}
    if extra: raise ValueError(f"data strains absent from cohort: {sorted(extra)}; subset explicitly before rendering")
    rows=[]; excluded=[]; merges=dict(x.split('=',1) for x in args.merge_genus)
    for c in cohort:
        if c['strain'] not in lookup: raise ValueError(f"missing data row: {c['strain']}")
        r=dict(c); r.update({k:v for k,v in lookup[c['strain']].items() if k in required-{'strain'}})
        if not c['genus'].strip() or not c['block'].strip(): raise ValueError('empty cohort genus or block')
        r['genus']=merges.get(c['genus'], c['genus'])
        r['label_suffix']=c.get('label_suffix','')
        r['nudge_x']=float(c.get('nudge_x') or 0); r['nudge_y']=float(c.get('nudge_y') or 0)
        if not math.isfinite(r['nudge_x']) or not math.isfinite(r['nudge_y']): raise ValueError('nonfinite label nudge')
        if 'T01'!='T01': r['d4']=number(r['d4'],'d4')
        if 'T01'=='T05':
            for k in ['d4_ci_low','d4_ci_high']: r[k]=number(r[k],k)
            if not r['d4_ci_low']<=r['d4']<=r['d4_ci_high']: raise ValueError('CI must contain d4')
            if not r['type_strain'].strip(): raise ValueError('missing closest type strain')
        if 'T01'!='T05':
            r['similarity']=number(r.get('similarity'),'similarity',True)
            if r['similarity'] is None:
                excluded.append(r['strain']); continue
            if 'T01'=='T01' and r['similarity']<94.75: raise ValueError('similarity below printed histogram bins; explicit alternate figure needed')
        rows.append(r)
    if not rows: raise ValueError('no measured rows to render')
    # The axis starts at the data: one empty whole percent below the lowest value, never below the printed 94.75 bins.
    # Bins and the numbers table are unchanged; only the drawn range moves. --x-min overrides.
    lowest=min(r['similarity'] for r in rows)
    x_min=args.x_min if args.x_min is not None else max(94.75, math.floor(lowest)-0.25)
    # A lowest value of exactly 94.75 is counted in the first bin (its left edge is closed), so the axis may start there.
    if not (94.75<=x_min<lowest or x_min==lowest==94.75): raise ValueError(f'--x-min {x_min} must be >= 94.75 and below the lowest value')
    if 'T01'=='T01':
        counts=Counter(r['genus'] for r in rows)
        for r in rows:
            if counts[r['genus']]<args.pool_below: r['genus']='Other genera'
    order=(args.genus_order.split(',') if args.genus_order else list(colours))
    present={r['genus'] for r in rows}
    order=[x for x in order if x in present]+sorted(present-set(order))
    if len(order)!=len(set(order)): raise ValueError('duplicate genus order')
    products=[args.out.with_suffix('.png'),args.out.with_suffix('.pdf'),args.out.with_name(args.out.name+'_numbers.tsv'),args.out.with_name(args.out.name+'_run.json')]
    if any(p.exists() for p in products): raise FileExistsError('refusing to overwrite figure or sidecar')
    rscript=shutil.which('Rscript')
    if not rscript: raise RuntimeError('Rscript is required for the printed ggplot layout')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=TOOL+'_',dir=args.out.parent) as tmp:
        tmp=Path(tmp); script=tmp/'render.R'; script.write_text(R_SCRIPT)
        table=tmp/'values.tsv'; keys=sorted(set().union(*(r.keys() for r in rows)))
        with table.open('w',newline='') as f:
            writer=_SafeDictWriter(f,keys,delimiter='\t'); writer.writeheader(); writer.writerows(rows)
        palette=tmp/'palette.tsv'
        with palette.open('w',newline='') as f:
            writer=_SafeWriter(f,delimiter='\t'); writer.writerow(['genus','colour'])
            writer.writerows((g,colours.get(g,config['fallback'])) for g in order)
        subprocess.run([rscript,str(script),str(ROOT/'tools/sapote_pub_layout.R'),str(table),str(palette),args.layout,str(args.out),str(args.dpi),str(args.min_text_pt),str(args.print_width or 'auto'),str(ROOT/'tools/sapote_min_text.R'),str(x_min),args.legend_title],check=True)
        _mt_enforce(args.out.with_suffix('.pdf'),args.min_text_pt)
        if 'T01'=='T01':
            with (tmp/'bins.tsv').open() as f:
                bins=list(csv.DictReader(f,delimiter='\t'))
            for b in bins:
                g=list(reversed(order))[int(b['group'])-1]
                lo=float(b['xmin']); hi=float(b['xmax'])
                expected=sum(r['genus']==g and (lo<r['similarity']<=hi or abs(lo-94.75)<1e-8 and r['similarity']==lo) for r in rows)
                if float(b['count'])!=expected: raise ValueError('ggplot histogram bin disagrees with numbers')
            if sum(float(b['count']) for b in bins)!=len(rows): raise ValueError('ggplot histogram denominator disagrees with numbers')
    for p in products[:2]: stamp_file(p,TOOL)
    nums=[('cohort_rows',len(cohort)),('plotted_rows',len(rows)),('missing_similarity',len(excluded))]
    if 'T01'=='T01':
        nums += [('similarity_below_98.65',sum(r['similarity']<98.65 for r in rows)),('similarity_at_least_98.65',sum(r['similarity']>=98.65 for r in rows))]
        nums += [('genus:'+g,sum(r['genus']==g for r in rows)) for g in order]
        # Same right-closed 0.25 percentage-point bins as geom_histogram.
        for i in range(21):
            lo=94.75+i*.25; hi=lo+.25
            for g in order:
                n=sum(r['genus']==g and (lo<r['similarity']<=hi or i==0 and r['similarity']==lo) for r in rows)
                nums.append((f'bin:{lo:.2f}:{hi:.2f}:{g}',n))
    else:
        nums += [('d4_below_70',sum(r['d4']<70 for r in rows)),('d4_at_least_70',sum(r['d4']>=70 for r in rows))]
        if 'T01'=='T06':
            for x in [False,True]:
                for y in [False,True]: nums.append((f'quadrant:16s_ge_98.65={x}:d4_ge_70={y}',sum((r['similarity']>=98.65)==x and (r['d4']>=70)==y for r in rows)))
    with products[2].open('w',newline='') as f:
        writer=_SafeWriter(f,delimiter='\t'); writer.writerow(['metric','count']); writer.writerows(nums)
    bound=[{'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [args.cohort,args.data,palette_path,ROOT/'tools/sapote_pub_layout.R',ROOT/'tools/sapote_min_text.R',ROOT/'tools/_min_text_check.py',Path(__file__)]]
    products[3].write_text(json.dumps({'renderer':TOOL,'layout':args.layout,'palette_set':args.palette_set,'inputs':bound,'excluded_missing_similarity':excluded,'display_merges':merges,'x_min':x_min,'legend_title':args.legend_title,'plotted_values':rows},indent=2)+'\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--palette-json',type=Path,help='bundle-schema palette JSON; input is hashed, never installed')
    parser.add_argument('--cohort',type=Path,required=True)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--x-min',type=float,default=None,help='left end of the similarity axis (default: one whole percent below the lowest value, at least 94.75)')
    parser.add_argument('--out',type=Path,required=True,help='output stem, without suffix')
    parser.add_argument('--layout',choices=['bee','moss'],default='bee')
    parser.add_argument('--palette-set',choices=['moss','attine'])
    parser.add_argument('--genus-order',help='comma-separated legend order')
    parser.add_argument('--merge-genus',action='append',default=[],help='display-only genus mapping FROM=TO')
    parser.add_argument('--pool-below',type=int,default=3,help='T01 minimum count before pooling as Other genera')
    parser.add_argument('--dpi',type=int,default=600)
    parser.add_argument('--legend-title',default='Genus (16S rRNA)',help='key title; use it when a row is a family, not a genus')
    _mt_args(parser)
    args=parser.parse_args()
    if args.dpi<=0 or args.pool_below<1: parser.error('dpi and pool-below must be positive')
    if not args.legend_title.strip(): parser.error('--legend-title must not be empty')
    try: run(args)
    except (ValueError,KeyError,FileExistsError,RuntimeError,subprocess.CalledProcessError) as exc: parser.exit(2,str(exc)+'\n')
if __name__=='__main__': main()
