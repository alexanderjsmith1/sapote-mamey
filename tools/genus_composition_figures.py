#!/usr/bin/env python3
"""Render C02 genus composition from an admitted isolate TSV in the printed ggplot layout.

With --unit-column the same roster draws C03 instead: a matrix of isolates by sampling unit (for example colony) and
genus, with the units grouped under their group (for example the host ant genus). The group is drawn exactly as the
input gives it; the tool never fills a missing group from another isolate of the unit."""
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
leg<-setNames(ifelse(grepl("^No 16S",genera)|grepl("aceae( bacterium)?$",genera),genera,paste0("<i>",genera,"</i>")),genera)
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

R_MATRIX=r'''
suppressPackageStartupMessages({library(ggplot2);library(ggtext)})
a<-commandArgs(TRUE)
ragg::agg_png(filename=file.path(dirname(a[1]),"metrics.png"),width=2040,height=1830,res=600)
d<-read.delim(a[1],stringsAsFactors=FALSE,check.names=FALSE)
d$group_lab<-factor(d$group_lab,levels=readLines(a[2]));d$unit_lab<-factor(d$unit_lab,levels=readLines(a[3]))
# a block name may carry a written \\n for a line break; it stays escaped in the files and is turned into one here
nl<-function(x) gsub("\\\\n","\n",x)
d$genus_lab<-factor(d$genus_lab,levels=rev(readLines(a[4])));d$block<-factor(nl(d$block),levels=nl(readLines(a[5])))
source(a[6]);COL<-SAPOTE_COHORT_PALETTE[[a[7]]];INK<-"#17212E";SUB<-"#54637A";FONT<-"Arial"
LOW<-grDevices::colorRampPalette(c("white",COL))(100)[19]   # the cohort colour, 18% strength, for a one-isolate cell
blocks<-nlevels(d$block)>1
p<-ggplot(d,aes(unit_lab,genus_lab))+
 geom_tile(aes(fill=n),colour="white",linewidth=0.8,width=0.92,height=0.86)+
 geom_text(aes(label=n,colour=n>max(d$n)/2),size=8/ggplot2::.pt,family=FONT)+
 (if (blocks) facet_grid(block~group_lab,scales="free",space="free",switch="y") else facet_grid(.~group_lab,scales="free_x",space="free_x"))+
 scale_fill_gradient(low=LOW,high=COL,limits=c(1,max(d$n)),guide="none")+
 scale_colour_manual(values=c(`FALSE`=INK,`TRUE`="white"),guide="none")+
 scale_x_discrete(position="top")+labs(x=NULL,y=NULL,title=a[8])+theme_minimal(base_size=8,base_family=FONT)+
 theme(text=element_text(colour=INK),axis.text.x.top=element_text(size=8,angle=90,hjust=0,vjust=0.5,colour=INK),
 axis.text.y.left=element_markdown(size=8,hjust=1,colour=INK),
 strip.text.x=element_markdown(size=8,lineheight=1.15,hjust=0,vjust=0,margin=margin(b=4)),
 strip.text.y.left=element_text(size=8,angle=0,hjust=1,face="bold",colour=SUB),strip.placement="outside",strip.clip="off",
 panel.grid=element_blank(),panel.spacing.x=unit(16,"pt"),panel.spacing.y=unit(6,"pt"),
 panel.background=element_rect(fill="#F7F7F7",colour=NA),plot.title=element_text(size=8,colour=SUB,hjust=0.5),
 plot.background=element_rect(fill="white",colour=NA),plot.margin=margin(4,10,4,4))
source(a[9]); .pub_pdf <- function(p, f, w, h) ggsave(f, p, width = w, height = h, device = pdf_device, bg = "white")
pdf_device <- if (Sys.info()[["sysname"]]=="Darwin" && capabilities("aqua")) function(filename,...) grDevices::quartz(type="pdf",file=filename,...) else grDevices::cairo_pdf
mt_save(p, a[10], 7.2, 1.9+0.2*nlevels(d$genus_lab), list(min_text_pt = as.numeric(a[11]), print_width = if (a[12] == "auto") NULL else as.numeric(a[12]), dpi = 600))
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

COHORT={'bee':'BEE','moss':'MOSS','attine':'ATTINE'}

def read_extra(path,columns):
 """Extra per-isolate columns for C03, keyed by strain; a blank cell stays blank."""
 with Path(path).open(newline='',encoding='utf-8-sig') as f:
  reader=csv.DictReader(f,delimiter='\t');missing=[c for c in columns if c not in (reader.fieldnames or [])]
  if missing:raise ValueError(f'--unit-column needs column(s) {missing}')
  return {r['strain'].strip():{c:(r[c] or '').strip() for c in columns} for r in reader}

def md_genus(g,unassigned):
 if g=='Unassigned':return unassigned
 return g if g.startswith('No 16S') or g.endswith(('aceae',' bacterium')) else f'<i>{g}</i>'

def matrix(a,rows,groups,italic):
 """C03: isolates by unit and genus, units grouped under their group. Writes the counts, a caption and RUN_INFO."""
 cols=[a.unit_column]+[c for c in ('row_block','group_basis') if c in csv.DictReader(Path(a.isolates).open(encoding='utf-8-sig'),delimiter='\t').fieldnames]
 extra=read_extra(a.isolates,cols)
 nounit=f'No {a.unit_label} on record'
 for r in rows:
  e=extra[r['strain']];r['unit']=e[a.unit_column] or nounit;r['block']=e.get('row_block','')
  r['group_basis']=e.get('group_basis','')
 units={}
 for r in rows:units.setdefault((r['group'],r['unit']),[]).append(r)
 for (g,u),v in units.items():
  if u!=nounit and len({x['group'] for x in rows if x['unit']==u})>1:
   raise ValueError(f'{a.unit_label} {u!r} is under more than one group: fix the input; the tool does not choose one')
 gn={g:sum(r['group']==g for r in rows) for g in groups}
 nu={g:len({r['unit'] for r in rows if r['group']==g}) for g in groups}
 def gwrap(g):
  # a group over one or two units has a narrow panel: one word per line, and a word over 8 letters broken after 7
  # (Myrmico-/crypta), or its title runs into the next group's
  parts=[g] if nu[g]>2 else [x for w in g.split() for x in ([w[:7]+'-',w[7:]] if len(w)>8 else [w])]
  return '<br>'.join(f'<i>{x}</i>' if g in italic else x for x in parts)
 glab={g:gwrap(g)+f'<br>({gn[g]})' for g in groups}
 un={u:sum(r['unit']==u for r in rows) for u in {r['unit'] for r in rows}}
 ulab=lambda u:f'{u} ({un[u]})'
 uorder=[ulab(u) for g in groups for u in sorted({r['unit'] for r in rows if r['group']==g},key=lambda u:(u==nounit,-un[u],u))]
 tn={x:sum(r['genus']==x for r in rows) for x in {r['genus'] for r in rows}}
 blocks=list(dict.fromkeys(r['block'] for r in rows))
 border={b:i for i,b in enumerate(blocks)}
 genera=sorted(tn,key=lambda x:(min(border[r['block']] for r in rows if r['genus']==x),x=='Unassigned' or x.startswith('No 16S'),-tn[x],x))
 gl={x:f'{md_genus(x,a.unassigned_label)} ({tn[x]})' for x in genera}
 cells={}
 for r in rows:
  k=(r['group'],r['unit'],r['genus']);cells.setdefault(k,dict(group=r['group'],unit=r['unit'],genus=r['genus'],block=r['block'],n=0))['n']+=1
 cells=list(cells.values())
 a.out.mkdir(parents=True,exist_ok=False);stem=a.out/'C03_genus_by_unit'
 write_tsv(stem.with_name(stem.name+'_numbers.tsv'),['group','unit','genus','block','n'],cells)
 write_tsv(a.out/'PLOTTED_ISOLATES.tsv',['strain','group','unit','genus','block','group_basis'],rows)
 with tempfile.TemporaryDirectory(prefix='REBUILDABLE_',dir=a.out) as td:
  td=Path(td)
  write_tsv(td/'cells.tsv',['group_lab','unit_lab','genus_lab','block','n'],[dict(group_lab=glab[c['group']],unit_lab=ulab(c['unit']),genus_lab=gl[c['genus']],block=c['block'],n=c['n']) for c in cells])
  (td/'groups.txt').write_text(''.join(glab[g]+'\n' for g in groups));(td/'units.txt').write_text(''.join(u+'\n' for u in uorder))
  (td/'genera.txt').write_text(''.join(gl[x]+'\n' for x in genera));(td/'blocks.txt').write_text(''.join(b+'\n' for b in blocks))
  (td/'render.R').write_text(R_MATRIX)
  subprocess.run([a.rscript,str(td/'render.R'),str(td/'cells.tsv'),str(td/'groups.txt'),str(td/'units.txt'),str(td/'genera.txt'),str(td/'blocks.txt'),
                  str(ROOT/'tools/sapote_figure_theme.R'),COHORT[a.layout],a.group_title,str(ROOT/'tools/sapote_min_text.R'),str(stem),str(a.min_text_pt),str(a.print_width or 'auto')],check=True)
 _mt_enforce(stem.with_suffix('.pdf'),a.min_text_pt)
 for suffix in ('.png','.pdf'):stamp_file(stem.with_suffix(suffix),'genus_composition_figures')
 basis={}
 for r in rows:basis[r['group_basis'] or 'not stated in the input']=basis.get(r['group_basis'] or 'not stated in the input',0)+1
 cap=(f'Isolates by {a.unit_label} and genus. Each cell is the number of isolates, and each column is one {a.unit_label}; '
      f'the columns are grouped as titled above them ({a.group_title}). Numbers in brackets count isolates. '
      'The group is drawn as the input table gives it. ')
 if any(r['group_basis'] for r in rows):
  cap+='Basis of the group, isolates: '+'; '.join(f'{k}, {v}' for k,v in sorted(basis.items(),key=lambda kv:-kv[1]))+'. '
 (a.out/'CAPTION.md').write_text(cap.strip()+'\n')
 def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
 info={'renderer':'genus_composition_figures','figure':'C03','layout':a.layout,'groups':groups,'unit_column':a.unit_column,'n_isolates':len(rows),
       'n_units':len(un),'isolates':str(a.isolates.resolve()),'isolates_sha256':sha(a.isolates),'group_basis':basis,'italic_groups':italic,'cohort_colour':COHORT[a.layout]}
 (a.out/'RUN_INFO.json').write_text(json.dumps(info,indent=2)+'\n');return 0

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--isolates',required=True,type=Path,help='admitted TSV, one row per isolate')
 p.add_argument('--layout',choices=('bee','moss','attine'),required=True)
 p.add_argument('--groups',nargs='+',help='explicit group order; required for attine')
 p.add_argument('--palette-set',choices=('moss','attine'))
 p.add_argument('--out',required=True,type=Path,help='fresh output directory')
 p.add_argument('--italic-groups',nargs='*',help='group names to set in italics (genus names); replaces the layout list; give none to set no group in italics')
 p.add_argument('--legend-title',default='Genus (16S rRNA)',help='key title; use it when a row is a family, not a genus')
 p.add_argument('--unit-column',help='C03: draw isolates by this column (for example colony) and genus, units grouped under their group; optional input columns row_block and group_basis')
 p.add_argument('--unit-label',help='C03: name of one unit in labels and caption (default: the column name)')
 p.add_argument('--group-title',default='Group',help='C03: title above the group columns, for example "Host ant genus of the colony"')
 p.add_argument('--unassigned-label',default='No 16S genus on record',help='C03: display text for genus Unassigned')
 p.add_argument('--rscript',default='Rscript');_mt_args(p);a=p.parse_args(argv)
 if not a.legend_title.strip():raise ValueError('--legend-title must not be empty')
 rows=read_roster(a.isolates)
 groups=a.groups or {'bee':['Bumblebees','Honeybees','Other bees','Wasps'],'moss':['Bryophytes','Lichens','Mushrooms']}.get(a.layout)
 if not groups or len(set(groups))!=len(groups):raise ValueError('unique --groups required')
 found={r['group'] for r in rows}
 if found!=set(groups):raise ValueError(f'group roster differs: input={sorted(found)}, requested={groups}')
 italic=[g for g in (ITALIC_GROUPS.get(a.layout,[]) if a.italic_groups is None else a.italic_groups) if g in groups]
 if a.unit_column:
  a.unit_label=a.unit_label or a.unit_column
  return matrix(a,rows,groups,italic)
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
