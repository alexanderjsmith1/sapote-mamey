#!/usr/bin/env Rscript
# Max-4-reference genome tree: branches, tip labels, then the isolation source and country as deposited.
# Usage: Rscript tools/render_max4_tree.R <treefile> <figure_metadata.tsv> <out stem> [prune]
#   prune = keep only the tips listed in figure_metadata.tsv.
# The usual route is tools/max4_tree_figure.py (metadata + render subcommands): it builds the metadata table, sets the MAX4_*
# options below from a JSON spec, checks the 8 pt floor in the PDF and writes a receipt with input and output SHA-256.
#
# Metadata columns (tab-separated, one row per drawn tip):
#   tip, role (QUERY / REFERENCE / OUTGROUP), label_concise (deposited organism, strain, [Type] only from NCBI Assembly
#   fromtype, accession in brackets), source_display, geography_display (both as deposited; empty when not deposited).
#   Optional: genus (MAX4_GENUS_DOTS), host_group (MAX4_QUERY_GROUPS), source_group and geo_group (MAX4_STRIPS).
#
# Tree handling: IQ-TREE "SH-aLRT/UFBoot" node labels keep the UFBoot part. Midpoint rooting by default, supports move with their
# splits (phangorn node.labels='support'). Only supports >= MAX4_SUPPORT_MIN and < 100 are printed: unlabelled nodes are 100
# (say so in the caption). Nothing interpretive is drawn on the plot.
#
# Options (environment variables; defaults in brackets):
#   Page:    MAX4_WIDTH [9.8] in; MAX4_HMAX [9]; MAX4_H fixed height; MAX4_ROWIN [0.16] in per row; MAX4_RESERVE [1.4] in kept
#            for the scale bar and margins in the row-fit check; MAX4_PAD [0] in added under the plot for legends; MAX4_DPI [600];
#            MAX4_MIN_BRANCH [1.5] in; MAX4_LEFT_PAD (alias MAX4_LEFT_PT) [4] pt; MAX4_SCALE_X [0] scale-bar start; MAX4_CLIP_OFF=1.
#   Text:    MAX4_LAB [8] tip labels; MAX4_SMALL [8] source, country, supports, scale; MAX4_HEAD [8.5] column titles and legends.
#            Any value below 8 pt is refused (FIGURE_STYLE.md floor). MAX4_WRAP [56] source wrap (characters); MAX4_WRAP_GEO [0 = off];
#            MAX4_LINEHEIGHT [0.85]; MAX4_SP_ROMAN=1 sets "Genus sp." with the genus italic and "sp." roman.
#   Tips:    MAX4_DROP_TIPS=a,b drop tips before rooting (display only; record each one and why); MAX4_META_EXTRA=1 lets the table
#            hold rows for tips not in the tree (ignored and counted); MAX4_ROOT=<tip> roots on an outgroup tip, MAX4_ROOT=__asis__
#            keeps the supplied root; MAX4_DROP_ROOT=1 roots on MAX4_ROOT and leaves that tip off the drawing;
#            MAX4_BREAK_TIP=<tip>=<drawn length> draws one long terminal branch shortened with a '//' mark (true length printed).
#   Support: MAX4_SUPPORT_MIN [50]; MAX4_SUPPORT_HJUST [-0.1] (1.15 = left of the node); MAX4_SUPPORT_BG=1 white box behind each
#            number; MAX4_SUPPORT_DODGE=1 moves numbers that would touch.
#   Columns: MAX4_NO_META=1 drops the source and country columns (they go in a table; the label column takes the width).
#   Colour:  MAX4_STRIPS=<groups.tsv> adds a source-group and a region strip beside the tip labels (needs the text columns).
#            groups.tsv columns: kind (source / geo), group, colour, and optional value_as_deposited. When the metadata has no
#            source_group / geo_group column, each tip's displayed value is looked up in value_as_deposited.
#            MAX4_GENUS_DOTS=<palette.tsv> (columns genus, colour) colours a dot at each tip by the metadata genus column, with a
#            Genus legend in MAX4_GENUS_ROWS [2] rows. MAX4_QUERY_GROUPS=<groups.tsv> (columns group, colour) colours the isolate
#            labels by the host_group column, legend title MAX4_QUERY_GROUP_TITLE [Host group (isolates)]; reference labels stay
#            black. MAX4_LEGEND_BOX [vertical] or horizontal; MAX4_LEGEND_KEY_PT [1.15 x MAX4_SMALL].
# Writes <stem>.pdf, <stem>.png and, when svglite is installed, <stem>.svg, each carrying the renderer stamp.
suppressPackageStartupMessages({library(ape);library(ggtree);library(ggplot2);library(patchwork)})
a<-commandArgs(trailingOnly=TRUE);tf<-a[1];mf<-a[2];stem<-a[3];prune<-length(a)>3&&a[4]=='prune'
env<-function(k,d='')Sys.getenv(k,d);num<-function(k,d)as.numeric(env(k,d));on<-function(k)env(k)=='1'
W<-num('MAX4_WIDTH','9.8');HMAX<-num('MAX4_HMAX','9');RES<-num('MAX4_RESERVE','1.4');PT<-ggplot2::.pt
LAB<-num('MAX4_LAB','8');SMALL<-num('MAX4_SMALL','8');HEAD<-num('MAX4_HEAD','8.5');DPI<-num('MAX4_DPI','600')
WRAP<-as.integer(env('MAX4_WRAP','56'));WRAPG<-as.integer(env('MAX4_WRAP_GEO','0'));LH<-num('MAX4_LINEHEIGHT','.85')
if(min(LAB,SMALL,HEAD)<8)stop(sprintf('MAX4_TEXT_BELOW_8PT: LAB %g, SMALL %g, HEAD %g (the house floor is 8 pt)',LAB,SMALL,HEAD))
LEFT<-num('MAX4_LEFT_PAD',env('MAX4_LEFT_PT','4'))
md<-read.delim(mf,quote='',check.names=FALSE,na.strings=character(),colClasses='character')
need<-c('tip','role','label_concise','source_display','geography_display');miss<-setdiff(need,names(md))
if(length(miss))stop('MAX4_METADATA_COLUMNS: missing ',paste(miss,collapse=', '))
tr<-read.tree(tf)
if(prune)tr<-keep.tip(tr,md$tip)
DROP<-trimws(strsplit(env('MAX4_DROP_TIPS'),',')[[1]]);DROP<-DROP[nzchar(DROP)]
if(length(DROP)){stopifnot(all(DROP %in% tr$tip.label));tr<-drop.tip(tr,DROP);md<-md[!md$tip %in% DROP,]}
n_extra<-sum(!md$tip %in% tr$tip.label)
if(on('MAX4_META_EXTRA'))md<-md[md$tip %in% tr$tip.label,]
if(anyDuplicated(md$tip))stop('MAX4_METADATA_DUPLICATE_TIP')
if(!setequal(md$tip,tr$tip.label))stop(sprintf('MAX4_TIP_MISMATCH: %d tree tips without a row, %d rows without a tip',
  sum(!tr$tip.label %in% md$tip),sum(!md$tip %in% tr$tip.label)))
tr$node.label<-sub('.*/','',tr$node.label)   # UFBoot part of "SH-aLRT/UFBoot"
ROOT<-env('MAX4_ROOT')
if(ROOT=='__asis__'){og<-'as supplied (pre-rooted tree)'} else if(nzchar(ROOT)){stopifnot(ROOT %in% tr$tip.label);og<-ROOT
  tr<-ape::root(tr,outgroup=ROOT,resolve.root=TRUE,edgelabel=TRUE)
  if(on('MAX4_DROP_ROOT')){tr<-ape::drop.tip(tr,ROOT);md<-md[md$tip!=ROOT,];og<-paste(ROOT,'(rooted on, not drawn)')}
} else {og<-'none (midpoint-rooted)';tr<-phangorn::midpoint(tr,node.labels='support')}
BRK<-env('MAX4_BREAK_TIP')
if(nzchar(BRK)){BTIP<-sub('=[^=]*$','',BRK);BLEN<-as.numeric(sub('.*=','',BRK));stopifnot(BTIP %in% tr$tip.label,is.finite(BLEN))
  be<-which(tr$edge[,2]==match(BTIP,tr$tip.label));BTRUE<-tr$edge.length[be];stopifnot(BLEN<BTRUE);tr$edge.length[be]<-BLEN}
query<-md$role=='QUERY'
p<-ggtree(tr,ladderize=TRUE,size=.4)
if(nzchar(BRK)){bd<-p$data[p$data$isTip&p$data$label==BTIP,];p<-p+annotate('text',x=bd$branch,y=bd$y,label='//',size=LAB/PT,fontface='bold',vjust=.35)}
d<-p$data[p$data$isTip,];ix<-match(d$label,md$tip)
d$text<-md$label_concise[ix];d$query<-query[ix];d$geo<-md$geography_display[ix]
NULLS<-c('','not recorded','missing','na','n/a','not applicable','unknown','not collected')
src<-trimws(md$source_display[ix]);src[tolower(src) %in% NULLS]<-NA;d$src<-src
d$geo[tolower(trimws(d$geo)) %in% NULLS]<-NA
n<-Ntip(tr);xmax<-max(p$data$x);yr<-c(-.9,n+.6)
scale_width<-10^floor(log10(xmax/5));if(xmax/5/scale_width>=5)scale_width<-5*scale_width else if(xmax/5/scale_width>=2)scale_width<-2*scale_width
wrapv<-function(v,w)ifelse(is.na(v),'',if(w>0)vapply(v,function(z)paste(strwrap(z,w),collapse='\n'),'') else v)
d$src_w<-wrapv(d$src,WRAP);d$geo_w<-wrapv(d$geo,WRAPG)
pdf(NULL)
wid<-function(s,pt,face=1)grid::convertWidth(grid::grobWidth(grid::textGrob(s,gp=grid::gpar(fontsize=pt,fontface=face))),'inches',valueOnly=TRUE)
lines_of<-function(v){x<-unlist(strsplit(v,'\n'));x[nzchar(x)]}
label_in<-max(mapply(function(s,q)wid(s,LAB,if(q)2 else 1),d$text,d$query))+.15
src_in<-max(c(wid('Isolation source',HEAD,2),vapply(lines_of(d$src_w),wid,0,pt=SMALL)))+.15
GEO_IN<-max(c(wid('Country',HEAD,2),vapply(lines_of(d$geo_w),wid,0,pt=SMALL)))+.1
invisible(dev.off())
NOMETA<-on('MAX4_NO_META')
if(NOMETA){src_in<-0;GEO_IN<-0}
branch_in<-W-label_in-src_in-GEO_IN-.35
cat(sprintf('columns (in): label %.2f, source %.2f, country %.2f, branches %.2f\n',label_in,src_in,GEO_IN,branch_in))
if(branch_in<num('MAX4_MIN_BRANCH','1.5'))stop(sprintf('FIT: only %.2f in for branches',branch_in))
H<-min(HMAX,max(3,num('MAX4_ROWIN','.16')*n+1.5));if(nzchar(env('MAX4_H')))H<-num('MAX4_H','0')
if((H-RES)/n*72<LAB*1.05)stop(sprintf('FIT: %d rows do not fit %.1f in at %g pt',n,H,LAB))
p<-p+geom_segment(data=d,aes(x=x,xend=xmax*1.06,y=y,yend=y),linetype='dotted',linewidth=.15,colour='grey75')+
  geom_treescale(x=num('MAX4_SCALE_X','0'),y=-.6,width=scale_width,fontsize=SMALL/PT,linesize=.3)+
  scale_x_continuous(limits=c(0,xmax*1.06),expand=c(0,0))+ylim(yr)+theme(plot.margin=margin(4,0,4,LEFT))
if(on('MAX4_CLIP_OFF'))p<-p+coord_cartesian(clip='off')
SMIN<-num('MAX4_SUPPORT_MIN','50')
nd<-p$data[!p$data$isTip,];value<-suppressWarnings(as.numeric(nd$label));nd<-nd[!is.na(value)&value>=SMIN&value<100,]
nd$vj<- -.45;nd$hj<-num('MAX4_SUPPORT_HJUST','-.1')
if(on('MAX4_SUPPORT_DODGE')&&nrow(nd)>1){lw<-2.4*SMALL/72/branch_in*xmax*1.06;o<-order(-nd$y)
  for(k in 2:length(o)){i<-o[k];j<-o[seq_len(k-1)];hit<-j[abs(nd$y[j]-nd$y[i])<1.3&abs(nd$x[j]-nd$x[i])<lw]
    for(h in hit){m<-if(nd$x[h]>nd$x[i])h else i;kids<-p$data[p$data$parent==nd$node[m]&p$data$node!=nd$node[m],]
      if(nrow(kids)==2&&all(kids$isTip)){nd$vj[m]<-.5;nd$hj[m]<- -.25} else {u<-if(nd$y[h]>nd$y[i])h else i;nd$vj[u]<- -1.45}}}}
ndr<-nd[nd$vj==.5,];nd<-nd[nd$vj!=.5,]   # right-of-node labels sit between two branches: plain text, no box
if(nrow(ndr))p<-p+geom_text(data=ndr,aes(x=x,y=y,label=label),size=SMALL/PT,hjust=ndr$hj,vjust=.5,colour='grey35')
if(nrow(nd)){if(on('MAX4_SUPPORT_BG'))p<-p+geom_label(data=nd,aes(x=x,y=y,label=label),size=SMALL/PT,hjust=nd$hj,vjust=nd$vj,colour='grey35',fill='white',label.size=0,label.padding=grid::unit(0.4,'pt'),label.r=grid::unit(0,'pt'))
  else p<-p+geom_text(data=nd,aes(x=x,y=y,label=label),size=SMALL/PT,hjust=nd$hj,vjust=nd$vj,colour='grey35')}
LEG<-FALSE
GD<-env('MAX4_GENUS_DOTS')
if(nzchar(GD)){stopifnot('genus' %in% names(md));d$genus<-md$genus[ix];gp<-read.delim(GD,quote='',colClasses='character')
  GC<-setNames(gp$colour,gp$genus);gs<-sort(unique(d$genus))
  if(!all(gs %in% names(GC)))stop('MAX4_GENUS_PALETTE: no colour for ',paste(setdiff(gs,names(GC)),collapse=', '))
  p<-p+geom_point(data=d,aes(x=x,y=y,colour=genus),size=1.5)+scale_colour_manual(values=GC[gs],name='Genus')+
    guides(colour=guide_legend(nrow=as.integer(env('MAX4_GENUS_ROWS','2')),override.aes=list(size=2.5),title.theme=element_text(size=HEAD,face='bold'),label.theme=element_text(size=SMALL,face='italic')))
  LEG<-TRUE}
SPR<-on('MAX4_SP_ROMAN')
d$plot_label<-vapply(d$text,function(z){
  if(SPR&&regexpr('^[A-Z][a-z]+ sp\\.',z,perl=TRUE)[1]>0){g<-sub(' sp\\..*$','',z);return(paste0('italic(',encodeString(g,quote='"'),')~',encodeString(trimws(substring(z,nchar(g)+1)),quote='"')))}
  m<-regexpr('^(?:Candidatus [A-Z][a-z]+ [a-z]+|[A-Z][a-z]+ (?:sp\\.|[a-z]+))',z,perl=TRUE);if(m[1]<0)return(encodeString(z,quote='"'))
  k<-attr(m,'match.length');paste0('italic(',encodeString(substr(z,1,k),quote='"'),')~',encodeString(trimws(substring(z,k+1)),quote='"'))},character(1))
QG<-env('MAX4_QUERY_GROUPS')
if(nzchar(QG)){stopifnot('host_group' %in% names(md));d$hg<-md$host_group[ix];qg<-read.delim(QG,quote='',colClasses='character')
  HGC<-setNames(qg$colour,qg$group);hs<-unique(d$hg[d$query])
  if(!all(hs %in% names(HGC)))stop('MAX4_QUERY_GROUP_COLOURS: no colour for ',paste(setdiff(hs,names(HGC)),collapse=', '))
  HGC<-HGC[names(HGC) %in% hs]
  q<-ggplot(d,aes(x=0,y=y))+geom_text(aes(label=plot_label,colour=ifelse(query,hg,'Reference'),fontface=ifelse(query,'bold','plain')),parse=TRUE,hjust=0,size=LAB/PT,key_glyph='point')+
    scale_colour_manual(values=c(HGC,Reference='#202124'),breaks=names(HGC),name=env('MAX4_QUERY_GROUP_TITLE','Host group (isolates)'))+
    guides(colour=guide_legend(override.aes=list(size=2.5,shape=15),title.theme=element_text(size=HEAD,face='bold'),label.theme=element_text(size=SMALL)))
  LEG<-TRUE
} else q<-ggplot(d,aes(x=0,y=y))+geom_text(aes(label=plot_label,colour=query,fontface=ifelse(query,'bold','plain')),parse=TRUE,hjust=0,size=LAB/PT)+
    scale_colour_manual(values=c('FALSE'='#202124','TRUE'='#bb0000'),guide='none')
q<-q+scale_x_continuous(limits=c(0,1),expand=c(0,0))+ylim(yr)+theme_void()+theme(plot.margin=margin(4,2,4,2))
s<-ggplot(d,aes(x=0,y=y))+geom_text(aes(label=src_w),hjust=0,size=SMALL/PT,lineheight=LH,colour='grey15')+scale_x_continuous(limits=c(0,1),expand=c(0,0))+ylim(yr)+
  theme_void()+labs(title='Isolation source')+theme(plot.title=element_text(size=HEAD,face='bold',hjust=0),plot.margin=margin(4,2,4,4))
g<-ggplot(d,aes(x=0,y=y))+geom_text(aes(label=geo_w),hjust=0,size=SMALL/PT,lineheight=LH,colour='grey15')+scale_x_continuous(limits=c(0,1),expand=c(0,0))+ylim(yr)+
  theme_void()+labs(title='Country')+theme(plot.title=element_text(size=HEAD,face='bold',hjust=0),plot.margin=margin(4,1,4,2))
parts<-if(NOMETA) list(p,q) else list(p,q,s,g);widths<-if(NOMETA) c(branch_in,label_in) else c(branch_in,label_in,src_in,GEO_IN)
STR<-env('MAX4_STRIPS')
if(nzchar(STR)&&!NOMETA){
  gt<-read.delim(STR,quote='',check.names=FALSE,colClasses='character')
  look<-function(kind,vals){x<-gt[gt$kind==kind,];if(!'value_as_deposited' %in% names(x))stop('MAX4_STRIPS: no group column in the metadata and no value_as_deposited column in the groups table')
    out<-x$group[match(vals,x$value_as_deposited)];if(anyNA(out))stop('MAX4_STRIPS: no group for ',paste(unique(vals[is.na(out)]),collapse=', '));out}
  d$sg<-if('source_group' %in% names(md)) md$source_group[ix] else look('source',md$source_display[ix])
  d$gg<-if('geo_group' %in% names(md)) md$geo_group[ix] else look('geo',md$geography_display[ix])
  stopifnot(all(nzchar(d$sg)),all(nzchar(d$gg)))
  pal<-function(k,v){x<-unique(gt[gt$kind==k,c('group','colour')]);x<-x[x$group %in% v,];stopifnot(!anyDuplicated(x$group));x}
  sp<-pal('source',d$sg);gq<-pal('geo',d$gg)
  strip<-function(col,pl,title,nr)ggplot(d,aes(x=0,y=y,fill=.data[[col]]))+geom_tile(width=1,height=.84,colour=NA)+
    scale_fill_manual(values=setNames(pl$colour,pl$group),breaks=pl$group,name=title,guide=guide_legend(nrow=nr,title.position='left',order=if(col=='sg')1 else 2))+
    scale_x_continuous(expand=c(0,0))+ylim(yr)+theme_void()+theme(plot.margin=margin(4,1,4,1))
  STRIP_IN<-.15
  parts<-list(p,q,strip('sg',sp,'Source group',2),strip('gg',gq,'Region',1),s,g)
  widths<-c(branch_in-2*STRIP_IN-.06,label_in,STRIP_IN,STRIP_IN,src_in,GEO_IN);LEG<-TRUE
}
fig<-wrap_plots(parts,widths=widths,nrow=1)
if(LEG)fig<-fig+plot_layout(guides='collect')&theme(legend.position='bottom',legend.box=env('MAX4_LEGEND_BOX','vertical'),legend.box.just='left',legend.justification='left',
  legend.title=element_text(size=HEAD,face='bold'),legend.text=element_text(size=SMALL),legend.key.size=grid::unit(num('MAX4_LEGEND_KEY_PT',SMALL*1.15),'pt'),
  legend.spacing.x=grid::unit(3,'pt'),legend.box.spacing=grid::unit(2,'pt'),legend.margin=margin(0,0,0,0))
H<-H+num('MAX4_PAD','0')
out<-c(paste0(stem,'.pdf'),paste0(stem,'.png'))
if(any(file.exists(c(out,paste0(stem,'.svg')))))stop('MAX4_REFUSE_OVERWRITE: ',stem)
ggsave(out[1],fig,width=W,height=H,device='pdf')
ggsave(out[2],fig,width=W,height=H,dpi=DPI)
if(requireNamespace('svglite',quietly=TRUE)){ggsave(paste0(stem,'.svg'),fig,width=W,height=H,device=svglite::svglite);out<-c(out,paste0(stem,'.svg'))}
script_path<-sub('^--file=','',grep('^--file=',commandArgs(FALSE),value=TRUE)[1])
if(!file.exists(script_path))script_path<-gsub('~+~',' ',script_path,fixed=TRUE)   # Rscript writes spaces in its own path as ~+~
source(file.path(dirname(script_path),'sapote_figure_theme.R'))   # renderer stamp (bundle provenance rule)
sapote_stamp_files(out,tool='render_max4_tree.R')
if(nzchar(BRK))cat(sprintf('break: %s terminal branch drawn at %.3f (true %.4f subs/site)\n',BTIP,BLEN,BTRUE))
if(length(DROP))cat(sprintf('dropped before rooting: %s\n',paste(DROP,collapse=', ')))
if(n_extra)cat(sprintf('metadata rows without a tree tip: %d%s\n',n_extra,if(on('MAX4_META_EXTRA')) ' (ignored)' else ''))
cat(sprintf('%s: tips drawn=%d isolates=%d; root %s; %.1fx%.2f in; row pitch %.1f pt\n',basename(stem),n,sum(d$query),og,W,H,(H-RES)/n*72))
