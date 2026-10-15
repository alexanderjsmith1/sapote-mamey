#!/usr/bin/env python3
"""Render C02 genus composition from an admitted isolate TSV in the printed ggplot layout."""
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
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from mamey.figure_stamp import stamp_file
from tools._min_text_check import add_args as _mt_args, enforce as _mt_enforce

R_SCRIPT=r'''
suppressPackageStartupMessages({library(ggplot2);library(ggtext)})
a<-commandArgs(TRUE)
# gridtext measures rich labels on an active device; keep real Arial metrics.
ragg::agg_png(filename=file.path(dirname(a[1]),"metrics.png"),width=2040,height=1830,res=600)
d<-read.delim(a[1],stringsAsFactors=FALSE);pal<-read.delim(a[2],stringsAsFactors=FALSE)
groups<-readLines(a[3]);genera<-readLines(a[4])
d$genus<-factor(d$genus,levels=genera);d$group<-factor(d$group,levels=groups)
PAL<-setNames(pal$colour,pal$genus);nh<-tapply(d$n,d$group,sum)
INK<-"#17212E";SUB<-"#54637A";FONT<-"Arial"
# a group name longer than 14 characters wraps at a space so five or more groups fit a single column at 8 pt; shorter names are unchanged
glab<-vapply(groups,function(g) if (nchar(g)>14) paste(strwrap(g,width=14),collapse="<br>") else g,character(1))
# groups that are genus names (an explicit list from the layout profile or --italic-groups) are set in italics
ital<-readLines(a[10]);glab<-ifelse(groups %in% ital,paste0("<i>",glab,"</i>"),glab)
xlab<-setNames(paste0(glab,"<br><span style='color:",SUB,"'>n = ",nh[groups],"</span>"),groups)
leg<-setNames(ifelse(grepl("^No 16S",genera),genera,paste0("<i>",genera,"</i>")),genera)
p<-ggplot(d,aes(x=group,y=n,fill=genus))+
 geom_col(width=0.72,colour="white",linewidth=0.12,position=position_stack(reverse=TRUE))+
 scale_fill_manual(values=PAL,breaks=genera,labels=leg,name=a[9],guide=guide_legend(ncol=2))+
 scale_x_discrete(labels=xlab,drop=FALSE)+scale_y_continuous(expand=expansion(mult=c(0,0.04)))+
 labs(x=NULL,y="Isolates")+theme_minimal(base_size=7,base_family=FONT)+
 theme(plot.title=element_text(face="bold",size=14,colour=INK),
 axis.text.x.bottom=element_markdown(size=7,colour=INK,lineheight=1.2),
 axis.title.y=element_text(colour=SUB,size=7),axis.text.y=element_text(size=7,colour=INK),
 legend.text=element_markdown(size=6.5),legend.title=element_text(size=6.5,face="bold"),
 legend.key.size=unit(6.5,"pt"),legend.key.spacing.y=unit(0.5,"pt"),legend.margin=margin(0,0,0,0),
 legend.box.spacing=unit(3,"pt"),legend.position="bottom",legend.title.position="top",
 panel.grid.major.x=element_blank(),panel.grid.minor=element_blank(),
 plot.background=element_rect(fill="white",colour=NA),plot.margin=margin(3,3,2,2))
source(a[6]); .pub_pdf <- function(p, f, w, h) ggsave(f, p, width = w, height = h, device = pdf_device, bg = "white")
pdf_device <- if (Sys.info()[["sysname"]]=="Darwin" && capabilities("aqua")) function(filename,...) grDevices::quartz(type="pdf",file=filename,...) else grDevices::cairo_pdf
mt_save(p, a[5], 3.4, 3.05, list(min_text_pt = as.numeric(a[7]), print_width = if (a[8] == "auto") NULL else as.numeric(a[8]), dpi = 600))
invisible(dev.off())
'''

# Group labels that are genus names, set in italics. An explicit list per layout, never guessed from the text;
# --italic-groups replaces it. bee and moss groups are not genera.
ITALIC_GROUPS={'bee':[],'moss':[],'attine':['Atta','Acromyrmex','Myrmicocrypta']}

def write_tsv(path,fields,rows):
 with Path(path).open('w',newline='',encoding='utf-8') as f:
  w=_SafeDictWriter(f,fieldnames=fields,delimiter='\t');w.writeheader();w.writerows(rows)

def read_roster(path):
 with Path(path).open(newline='',encoding='utf-8-sig') as f:
  reader=csv.DictReader(f,delimiter='\t');fields=reader.fieldnames or []
  if len(set(fields))!=len(fields):raise ValueError('duplicate headers')
  group=next((c for c in ('group','block','host_group','source_group') if c in fields),None)
  genus=next((c for c in ('genus','genus_16S') if c in fields),None)
  if 'strain' not in fields or not group or not genus:raise ValueError('requires strain, group/block/host_group/source_group and genus/genus_16S')
  rows=[];seen=set()
  for row in reader:
   if None in row or any(v is None for v in row.values()):raise ValueError('non-rectangular input')
   strain=row['strain'].strip();g=row[group].strip();tax=row[genus].strip()
   if not strain or not g or not tax or strain in seen:raise ValueError('unique nonblank strain, group and genus required')
   if any('\n' in v or '\r' in v or '\t' in v for v in (strain,g,tax)):raise ValueError('multiline metadata')
   seen.add(strain);rows.append(dict(strain=strain,group=g,genus=tax))
 if not rows:raise ValueError('empty isolate roster')
 return rows

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--isolates',required=True,type=Path,help='admitted TSV, one row per isolate')
 p.add_argument('--layout',choices=('bee','moss','attine'),required=True)
 p.add_argument('--groups',nargs='+',help='explicit group order; required for attine')
 p.add_argument('--palette-set',choices=('moss','attine'))
 p.add_argument('--out',required=True,type=Path,help='fresh output directory')
 p.add_argument('--italic-groups',nargs='*',help='group names to set in italics (genus names); replaces the layout list; give none to set no group in italics')
 p.add_argument('--legend-title',default='Genus (16S rRNA)',help='key title; use it when a row is a family, not a genus')
 p.add_argument('--rscript',default='Rscript');_mt_args(p);a=p.parse_args(argv)
 if not a.legend_title.strip():raise ValueError('--legend-title must not be empty')
 rows=read_roster(a.isolates)
 groups=a.groups or {'bee':['Bumblebees','Honeybees','Other bees','Wasps'],'moss':['Bryophytes','Lichens','Mushrooms']}.get(a.layout)
 if not groups or len(set(groups))!=len(groups):raise ValueError('unique --groups required')
 found={r['group'] for r in rows}
 if found!=set(groups):raise ValueError(f'group roster differs: input={sorted(found)}, requested={groups}')
 italic=[g for g in (ITALIC_GROUPS.get(a.layout,[]) if a.italic_groups is None else a.italic_groups) if g in groups]
 palette_path=ROOT/'mamey/data/genus_palette.json';palette=json.loads(palette_path.read_text());colours=dict(palette['default'])
 if a.palette_set:colours.update(palette['sets'][a.palette_set])
 totals={g:sum(r['genus']==g for r in rows) for g in {r['genus'] for r in rows}}
 genera=sorted(totals,key=lambda g:(g.startswith('No 16S'),-totals[g],g))
 numbers=[dict(group=group,genus=genus,n=sum(r['group']==group and r['genus']==genus for r in rows),group_n=sum(r['group']==group for r in rows)) for group in groups for genus in genera]
 def colour(g):
  # Historic palette spelling is a lookup alias, never a taxonomy rewrite.
  return colours.get('Mycolicobacterium' if g=='Mycolicibacterium' else g,colours.get('Unassigned',palette['fallback']) if g.startswith('No 16S') else palette['fallback'])
 a.out.mkdir(parents=True,exist_ok=False);stem=a.out/'C02_genus_composition'
 write_tsv(stem.with_name(stem.name+'_numbers.tsv'),['group','genus','n','group_n'],numbers)
 write_tsv(a.out/'PLOTTED_ISOLATES.tsv',['strain','group','genus'],rows)
 with tempfile.TemporaryDirectory(prefix='REBUILDABLE_',dir=a.out) as td:
  td=Path(td);write_tsv(td/'counts.tsv',['group','genus','n','group_n'],numbers)
  write_tsv(td/'colours.tsv',['genus','colour'],[dict(genus=g,colour=colour(g)) for g in genera])
  (td/'groups.txt').write_text('\n'.join(groups)+'\n');(td/'genera.txt').write_text('\n'.join(genera)+'\n');(td/'italic.txt').write_text(''.join(g+'\n' for g in italic));(td/'render.R').write_text(R_SCRIPT)
  subprocess.run([a.rscript,str(td/'render.R'),str(td/'counts.tsv'),str(td/'colours.tsv'),str(td/'groups.txt'),str(td/'genera.txt'),str(stem),str(ROOT/'tools/sapote_min_text.R'),str(a.min_text_pt),str(a.print_width or 'auto'),a.legend_title,str(td/'italic.txt')],check=True)
 _mt_enforce(stem.with_suffix('.pdf'),a.min_text_pt)
 for suffix in ('.png','.pdf'):stamp_file(stem.with_suffix(suffix),'genus_composition_figures')
 def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
 info={'renderer':'genus_composition_figures','layout':a.layout,'groups':groups,'n_isolates':len(rows),'isolates':str(a.isolates.resolve()),'isolates_sha256':sha(a.isolates),'palette':str(palette_path),'palette_sha256':sha(palette_path),'palette_set':a.palette_set,'legend_title':a.legend_title,'italic_groups':italic,'fallback_genera':[g for g in genera if g not in colours and not g.startswith('No 16S') and g!='Mycolicibacterium']}
 (a.out/'RUN_INFO.json').write_text(json.dumps(info,indent=2)+'\n');return 0

if __name__=='__main__':raise SystemExit(main())
