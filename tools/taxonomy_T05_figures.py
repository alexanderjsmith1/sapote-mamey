#!/usr/bin/env python3
"""Render T05 using the printed paper ggplot layout and bundle palette/theme.

Inputs are explicit TSVs: --cohort needs strain,genus,block; --data needs strain
and similarity (T01), d4,d4_ci_low,d4_ci_high,type_strain (T05), or d4,similarity
(T06). Missing similarity is excluded and counted; missing dDDH is refused.
Cohort optional label_suffix, nudge_x, nudge_y preserve paper annotations without
strain-specific code. --merge-genus and --genus-order are display settings only.
Optional cohort column label_md replaces an isolate's label (markdown, e.g. a family-level
name or a second host line). Optional data columns ref_name, ref_strain, ref_accession give
the reference label in the house rule 6 form (deposited name and strain, accession below in
brackets); without them the type_strain text is shown. --highlight-genus GENUS=RRGGBB sets
one genus colour over the bundle palette; --legend-title, --legend-rows, --x-max, --x-label,
--design-width and --design-height reach the other thesis panel settings.
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
TOOL = "taxonomy_T05_figures"
OPTIONAL_DATA = {"ref_name", "ref_strain", "ref_accession"}
X_LABEL = "Digital DNA-DNA hybridization (dDDH, formula d4) with the closest type strain"
R_SCRIPT = 'suppressPackageStartupMessages({library(ggplot2); library(dplyr); library(ggrepel); library(ggtext)})\na <- commandArgs(TRUE)\nsource(a[1]); d <- read.delim(a[2], stringsAsFactors=FALSE, check.names=FALSE)\npaldata <- read.delim(a[3], stringsAsFactors=FALSE)\npal <- setNames(paldata$colour, paldata$genus)\nlayout <- a[4]; out <- a[5]; dpi <- as.numeric(a[6])\ngen <- paldata$genus; glab <- setNames(paste0("<i>",gen,"</i>"),gen)\nd$genus_fig <- d$genus; d$isolate <- d$strain\nd$label_suffix[is.na(d$label_suffix)] <- ""\ncfgt <- read.delim(a[10], stringsAsFactors=FALSE, colClasses="character", na.strings=character()); cfg <- setNames(cfgt$value, cfgt$key)\nd <- d %>% arrange(d4)\nAX <- theme(axis.title = element_text(size = 7, colour = PUB_INK), axis.title.x = element_markdown(size = 7, colour = PUB_INK, margin = margin(t = 3), lineheight = 1.1),\n            axis.title.y = element_text(size = 7, colour = PUB_INK, margin = margin(r = 3)),\n            axis.text.x.bottom = element_markdown(size = 7, colour = PUB_INK), axis.text.y.left = element_markdown(size = 6.5, colour = PUB_INK),\n            legend.text = element_markdown(size = 6.5), legend.title = element_text(size = 6.5, face = "bold"),\n            legend.key.size = unit(7, "pt"), legend.key.spacing.y = unit(0, "pt"), legend.margin = margin(0, 0, 0, 0),\n            legend.box.spacing = unit(2, "pt"), plot.margin = margin(3, 4, 2, 2))\n# A: one row per isolate\nd <- d %>% mutate(ts_md=sub("^(\\\\S+) (\\\\S+)", "<i>\\\\1 \\\\2</i>", type_strain),\n lab_md=paste0("<i>",genus,"</i> sp. ",strain,label_suffix)) %>% arrange(d4)\nif (all(c("ref_name","ref_strain","ref_accession") %in% names(d))) { ok <- !is.na(d$ref_name) & nzchar(d$ref_name)\n  d$ts_md[ok] <- paste0("<i>", sub(" subsp\\\\. ", "</i> subsp. <i>", d$ref_name[ok]), "</i> ", ifelse(is.na(d$ref_strain[ok]), "", d$ref_strain[ok]), "<br>(", d$ref_accession[ok], ")") }\nif ("label_md" %in% names(d)) { ok <- !is.na(d$label_md) & nzchar(d$label_md); d$lab_md[ok] <- d$label_md[ok] }\nn_all <- nrow(d)\nd$lab_md <- factor(d$lab_md, levels = d$lab_md)\npA <- ggplot(d, aes(y = lab_md)) +\n  geom_vline(xintercept = 70, linetype = "dashed", colour = "#6B7483", linewidth = 0.3) +\n  geom_errorbarh(aes(xmin = d4_ci_low, xmax = d4_ci_high), height = 0.35, colour = "#8A94A3", linewidth = 0.3) +\n  geom_point(aes(x = d4, fill = genus_fig), shape = 21, size = 1.9, colour = PUB_INK, stroke = 0.35) +\n  geom_richtext(data = d %>% filter(d4 < 70), aes(x = pmax(d4_ci_high, d4) + 1.5, label = ts_md), hjust = 0, size = 6.5 / .pt, fill = "white",\n                label.colour = NA, colour = PUB_SUB, label.padding = unit(0.3, "pt"), label.r = unit(0, "pt")) +\n  geom_richtext(data = d %>% filter(d4 >= 70), aes(x = pmin(d4_ci_low, d4) - 1.5, label = ts_md), hjust = 1, size = 6.5 / .pt, fill = "white",\n                label.colour = NA, colour = PUB_SUB, label.padding = unit(0.3, "pt"), label.r = unit(0, "pt")) +\n  scale_fill_manual(values = pal, breaks = gen, labels = glab, name = cfg[["legend_title"]]) +\n  scale_x_continuous(limits = c(0, as.numeric(cfg[["x_max"]])), breaks = seq(0, 100, 10), labels = function(v) paste0(v, "%"), expand = expansion(0)) +\n  scale_y_discrete(expand = expansion(add = c(0.6, 0.6))) +\n  labs(x = cfg[["x_label"]], y = NULL) +\n  guides(fill = guide_legend(nrow = as.integer(cfg[["legend_rows"]]), override.aes = list(size = 2))) +\n  theme_pub(base = 7) + AX + theme(legend.position = "bottom", panel.grid.major.y = element_blank(),\n                                   axis.text.y.left = element_markdown(size = 7, colour = PUB_INK), legend.text = element_markdown(size = 7),\n                                   legend.title = element_text(size = 7, face = "bold"))\n\np <- pA; w <- if (nzchar(cfg[["width"]])) as.numeric(cfg[["width"]]) else 7\nh <- if (nzchar(cfg[["height"]])) as.numeric(cfg[["height"]]) else if(layout=="moss") 4.2*(nrow(d)+5)/31 else 4.2\nsource(a[9]); mt_save(p,out,w,h,list(rows=nrow(d),min_text_pt=as.numeric(a[7]),print_width=if(a[8]=="auto") NULL else as.numeric(a[8]),dpi=dpi))\n'

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

def parse_highlight(items):
    out={}
    for item in items or []:
        genus,sep,colour=item.partition('=')
        colour=colour.strip(); colour=colour if colour.startswith('#') else '#'+colour
        if not sep or not genus.strip() or len(colour)!=7 or any(ch not in '0123456789abcdefABCDEF' for ch in colour[1:]):
            raise ValueError(f'--highlight-genus {item!r}: expected GENUS=RRGGBB')
        out[genus.strip()]=colour.upper()
    return out

def number(value, name, optional=False):
    if optional and (value is None or str(value).strip() in {"","NA","NaN"}): return None
    v=float(value)
    if not math.isfinite(v) or not 0<=v<=100: raise ValueError(f"{name}: expected finite percent 0..100")
    return v

def run(args):
    palette_path=ROOT/'mamey/data/genus_palette.json'
    config=json.loads(palette_path.read_text())
    colours=dict(config['default']); colours.update(config['sets'].get(args.palette_set or '',{}))
    highlight=parse_highlight(args.highlight_genus); colours.update(highlight)
    cohort=read_table(args.cohort, {'strain','genus','block'})
    required={'strain'} | ({'similarity'} if 'T05'=='T01' else {'d4','d4_ci_low','d4_ci_high','type_strain'} if 'T05'=='T05' else {'d4','similarity'})
    data=read_table(args.data,required); lookup={r['strain']:r for r in data}
    extra=set(lookup)-{r['strain'] for r in cohort}
    if extra: raise ValueError(f"data strains absent from cohort: {sorted(extra)}; subset explicitly before rendering")
    rows=[]; excluded=[]; merges=dict(x.split('=',1) for x in args.merge_genus)
    for c in cohort:
        if c['strain'] not in lookup: raise ValueError(f"missing data row: {c['strain']}")
        r=dict(c); r.update({k:v for k,v in lookup[c['strain']].items() if k in (required|OPTIONAL_DATA)-{'strain'}})
        if not c['genus'].strip() or not c['block'].strip(): raise ValueError('empty cohort genus or block')
        r['genus']=merges.get(c['genus'], c['genus'])
        r['label_suffix']=c.get('label_suffix','')
        r['nudge_x']=float(c.get('nudge_x') or 0); r['nudge_y']=float(c.get('nudge_y') or 0)
        if not math.isfinite(r['nudge_x']) or not math.isfinite(r['nudge_y']): raise ValueError('nonfinite label nudge')
        if 'T05'!='T01': r['d4']=number(r['d4'],'d4')
        if 'T05'=='T05':
            for k in ['d4_ci_low','d4_ci_high']: r[k]=number(r[k],k)
            if not r['d4_ci_low']<=r['d4']<=r['d4_ci_high']: raise ValueError('CI must contain d4')
            if not r['type_strain'].strip(): raise ValueError('missing closest type strain')
        if 'T05'!='T05':
            r['similarity']=number(r.get('similarity'),'similarity',True)
            if r['similarity'] is None:
                excluded.append(r['strain']); continue
            if 'T05'=='T01' and r['similarity']<94.75: raise ValueError('similarity below printed histogram bins; explicit alternate figure needed')
        rows.append(r)
    if not rows: raise ValueError('no measured rows to render')
    if 'T05'=='T01':
        counts=Counter(r['genus'] for r in rows)
        for r in rows:
            if counts[r['genus']]<args.pool_below: r['genus']='Other genera'
    present={r['genus'] for r in rows}
    if set(highlight)-present: raise ValueError(f"--highlight-genus not among plotted genera: {sorted(set(highlight)-present)}")
    order=(args.genus_order.split(',') if args.genus_order else sorted(present))
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
        settings=tmp/'settings.tsv'
        with settings.open('w',newline='') as f:
            writer=_SafeWriter(f,delimiter='\t'); writer.writerow(['key','value'])
            writer.writerows([('legend_title',args.legend_title),('legend_rows',args.legend_rows),('x_max',args.x_max),('x_label',args.x_label),
                              ('width',args.design_width or ''),('height',args.design_height or '')])
        palette=tmp/'palette.tsv'
        with palette.open('w',newline='') as f:
            writer=_SafeWriter(f,delimiter='\t'); writer.writerow(['genus','colour'])
            writer.writerows((g,colours.get(g,config['fallback'])) for g in order)
        subprocess.run([rscript,str(script),str(ROOT/'tools/sapote_pub_layout.R'),str(table),str(palette),args.layout,str(args.out),str(args.dpi),str(args.min_text_pt),str(args.print_width or 'auto'),str(ROOT/'tools/sapote_min_text.R'),str(settings)],check=True)
        _mt_enforce(args.out.with_suffix('.pdf'),args.min_text_pt)
    for p in products[:2]: stamp_file(p,TOOL)
    nums=[('cohort_rows',len(cohort)),('plotted_rows',len(rows)),('missing_similarity',len(excluded))]
    if 'T05'=='T01':
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
        if 'T05'=='T06':
            for x in [False,True]:
                for y in [False,True]: nums.append((f'quadrant:16s_ge_98.65={x}:d4_ge_70={y}',sum((r['similarity']>=98.65)==x and (r['d4']>=70)==y for r in rows)))
    with products[2].open('w',newline='') as f:
        writer=_SafeWriter(f,delimiter='\t'); writer.writerow(['metric','count']); writer.writerows(nums)
    bound=[{'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [args.cohort,args.data,palette_path,ROOT/'tools/sapote_pub_layout.R',ROOT/'tools/sapote_min_text.R',ROOT/'tools/_min_text_check.py',Path(__file__)]]
    products[3].write_text(json.dumps({'renderer':TOOL,'layout':args.layout,'palette_set':args.palette_set,'inputs':bound,'excluded_missing_similarity':excluded,'display_merges':merges,'highlight_genus':highlight,'settings':{'legend_title':args.legend_title,'legend_rows':args.legend_rows,'x_max':args.x_max,'x_label':args.x_label,'design_width':args.design_width,'design_height':args.design_height},'plotted_values':rows},indent=2)+'\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort',type=Path,required=True)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True,help='output stem, without suffix')
    parser.add_argument('--layout',choices=['bee','moss'],default='bee')
    parser.add_argument('--palette-set',choices=['moss','attine'])
    parser.add_argument('--genus-order',help='comma-separated legend order')
    parser.add_argument('--merge-genus',action='append',default=[],help='display-only genus mapping FROM=TO')
    parser.add_argument('--pool-below',type=int,default=3,help='T01 minimum count before pooling as Other genera')
    parser.add_argument('--dpi',type=int,default=600)
    parser.add_argument('--highlight-genus',action='append',default=[],help='GENUS=RRGGBB: this genus colour replaces the palette colour (repeatable)')
    parser.add_argument('--legend-title',default='Genus (16S rRNA)',help='genus key title')
    parser.add_argument('--legend-rows',type=int,default=2,help='rows in the genus key')
    parser.add_argument('--x-max',type=float,default=114,help='right end of the dDDH axis (percent; room for reference labels)')
    parser.add_argument('--x-label',default=X_LABEL,help='dDDH axis title')
    parser.add_argument('--design-width',type=float,help='design canvas width in inches (default 7)')
    parser.add_argument('--design-height',type=float,help='design canvas height in inches (default from the layout)')
    _mt_args(parser)
    args=parser.parse_args()
    if args.dpi<=0 or args.pool_below<1: parser.error('dpi and pool-below must be positive')
    if args.legend_rows<1 or not 100<=args.x_max<=130: parser.error('legend-rows must be positive and x-max between 100 and 130')
    try: run(args)
    except (ValueError,KeyError,FileExistsError,RuntimeError,subprocess.CalledProcessError) as exc: parser.exit(2,str(exc)+'\n')
if __name__=='__main__': main()
