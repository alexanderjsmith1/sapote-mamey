#!/usr/bin/env Rscript
# One tree, all 14 non-Streptomyces bee/wasp isolates, at most 4 references each. Sept 18 S2 style, no activity columns.
# v5 copy (20 Oct): adds MAX4_SMALL, MAX4_HEAD (source/country/support/scale/header pt), MAX4_DPI, MAX4_SUPPORT_BG, MAX4_SUPPORT_DODGE, MAX4_LEFT_PAD and MAX4_SCALE_X (scale-bar start, data units) knobs; defaults unchanged.
# Card 464 v2 (21 Oct): + MAX4_STRIPS colour strips and MAX4_NO_META (both opt-in); saved files carry the renderer stamp. Usage: Rscript tools/render_max4_tree.R <treefile> <figure_metadata.tsv> <out stem> [prune]
#   prune = keep only the tips in figure_metadata.tsv (PREVIEW from the 214-tip tree); omit for the batch 11 tree.
# Derived from ../../../../../September 28 Staging/FIG_S2_TREES_SEPT18/no_activity/render_S2.R. Changes:
#   - IQ-TREE "SH-aLRT/UFBoot" node labels: the UFBoot value is drawn (>= 70);
#   - no outgroup (owner, 2026-09-28): midpoint-rooted; support labels move with their splits (phangorn node.labels='support');
#   - up to 9 in tall; country printed as deposited text (no colour tiles: 20+ countries cannot be told apart by colour);
#   - only supports below 100 are printed (UFBoot >= 50); unlabelled nodes are 100 (say so in the caption);
#   - labels and deposited source come from figure_metadata.tsv (isolates: Table S1 host as deposited).
suppressPackageStartupMessages({library(ape);library(ggtree);library(ggplot2);library(patchwork)})
a<-commandArgs(trailingOnly=TRUE);tf<-a[1];mf<-a[2];stem<-a[3];prune<-length(a)>3&&a[4]=='prune'
W<-as.numeric(Sys.getenv('MAX4_WIDTH','9.8'));HMAX<-as.numeric(Sys.getenv('MAX4_HMAX','9'));RES<-as.numeric(Sys.getenv('MAX4_RESERVE','1.4'));PT<-ggplot2::.pt;LAB<-as.numeric(Sys.getenv('MAX4_LAB','7'));SMALL<-as.numeric(Sys.getenv('MAX4_SMALL','6'));HEAD<-as.numeric(Sys.getenv('MAX4_HEAD','7'));DPI<-as.numeric(Sys.getenv('MAX4_DPI','400'));WRAP<-as.integer(Sys.getenv('MAX4_WRAP','56'))   # MAX4_WIDTH/LAB/WRAP: print-width variants
md<-read.delim(mf,quote='',check.names=FALSE,na.strings=character(),colClasses='character')
tr<-read.tree(tf)
if(prune)tr<-keep.tip(tr,md$tip)
stopifnot(setequal(md$tip,tr$tip.label))
tr$node.label<-sub('.*/','',tr$node.label)   # UFBoot part of "SH-aLRT/UFBoot"
ROOT<-Sys.getenv('MAX4_ROOT','')   # MAX4_ROOT=<tip>: root on that outgroup tip, drawn as a labelled tip; MAX4_ROOT=__asis__: keep the supplied root (default: midpoint, no outgroup)
if(ROOT=='__asis__'){og<-'as supplied (pre-rooted tree)'} else if(nzchar(ROOT)){stopifnot(ROOT %in% tr$tip.label);og<-ROOT;tr<-ape::root(tr,outgroup=ROOT,resolve.root=TRUE,edgelabel=TRUE)} else {og<-'none (midpoint-rooted)';tr<-phangorn::midpoint(tr,node.labels='support')}   # no outgroup by default (owner, 2026-09-28)
BRK<-Sys.getenv('MAX4_BREAK_TIP','')   # MAX4_BREAK_TIP=<tip>=<drawn length>: draw that tip's terminal branch at the given length with a '//' break mark (true length printed to stdout; say it in the caption). Default: off
if(nzchar(BRK)){BTIP<-sub('=[^=]*$','',BRK);BLEN<-as.numeric(sub('.*=','',BRK));stopifnot(BTIP %in% tr$tip.label,is.finite(BLEN));be<-which(tr$edge[,2]==match(BTIP,tr$tip.label));BTRUE<-tr$edge.length[be];stopifnot(BLEN<BTRUE);tr$edge.length[be]<-BLEN}
query<-md$role=='QUERY'
p<-ggtree(tr,ladderize=TRUE,size=.4);if(nzchar(BRK)){bd<-p$data[p$data$isTip&p$data$label==BTIP,];p<-p+annotate('text',x=bd$branch,y=bd$y,label='//',size=LAB/ggplot2::.pt,fontface='bold',vjust=.35)};d<-p$data[p$data$isTip,];ix<-match(d$label,md$tip)
d$text<-md$label_concise[ix];d$query<-query[ix];d$geo<-md$geography_display[ix]
src<-trimws(md$source_display[ix]);src[tolower(src) %in% c('','not recorded','missing','na','n/a','not applicable','unknown','not collected')]<-NA;d$src<-src
d$geo[!nzchar(d$geo)]<-NA
n<-Ntip(tr);xmax<-max(p$data$x);yr<-c(-.9,n+.6)
scale_width<-10^floor(log10(xmax/5));if(xmax/5/scale_width>=5)scale_width<-5*scale_width else if(xmax/5/scale_width>=2)scale_width<-2*scale_width
d$src_w<-ifelse(is.na(d$src),'',vapply(d$src,function(z)paste(strwrap(z,WRAP),collapse='\n'),''))
pdf(NULL)
wid<-function(s,pt,face=1)grid::convertWidth(grid::grobWidth(grid::textGrob(s,gp=grid::gpar(fontsize=pt,fontface=face))),'inches',valueOnly=TRUE)
label_in<-max(mapply(function(s,q)wid(s,LAB,if(q)2 else 1),d$text,d$query))+.15
src_in<-max(c(wid('Isolation source',HEAD,2),vapply(unlist(strsplit(d$src_w,'\n')),wid,0,pt=SMALL)))+.15
GEO_IN<-max(c(wid('Country',HEAD,2),vapply(stats::na.omit(d$geo),wid,0,pt=SMALL)))+.1
invisible(dev.off())
NOMETA<-Sys.getenv('MAX4_NO_META','')=='1'   # MAX4_NO_META=1: no source/country columns (they go in a table); the label column takes the width
if(NOMETA){src_in<-0;GEO_IN<-0}
branch_in<-W-label_in-src_in-GEO_IN-.35
if(branch_in<as.numeric(Sys.getenv('MAX4_MIN_BRANCH','1.5')))stop(sprintf('FIT: only %.2f in for branches',branch_in))
H<-min(HMAX,max(3,.16*n+1.5))
if((H-RES)/n*72<LAB*1.05)stop(sprintf('FIT: %d rows do not fit %.1f in at %g pt',n,HMAX,LAB))
p<-p+geom_segment(data=d,aes(x=x,xend=xmax*1.06,y=y,yend=y),linetype='dotted',linewidth=.15,colour='grey75')+
  geom_treescale(x=as.numeric(Sys.getenv('MAX4_SCALE_X','0')),y=-.6,width=scale_width,fontsize=SMALL/PT,linesize=.3)+
  scale_x_continuous(limits=c(0,xmax*1.06),expand=c(0,0))+ylim(yr)+theme(plot.margin=margin(4,0,4,as.numeric(Sys.getenv('MAX4_LEFT_PAD','4'))))   # MAX4_LEFT_PAD: left margin in pt, so a short scale bar's label is not clipped
SMIN<-as.numeric(Sys.getenv('MAX4_SUPPORT_MIN','50'))   # lowest UFBoot printed (default 50)
nd<-p$data[!p$data$isTip,];value<-suppressWarnings(as.numeric(nd$label));nd<-nd[!is.na(value)&value>=SMIN&value<100,]
SHJ<-as.numeric(Sys.getenv('MAX4_SUPPORT_HJUST','-.1'))   # 1.15 puts the label left of its node, above the branch leading in
nd$vj<- -.45;nd$hj<-SHJ   # MAX4_SUPPORT_DODGE=1: when two support numbers would touch (rows apart < 1.3 and x apart < one label width), the one nearer the tips is drawn right of its node between its two tip branches when it joins two tips, otherwise the upper one is lifted a line (default off)
if(Sys.getenv('MAX4_SUPPORT_DODGE','')=='1'&&nrow(nd)>1){lw<-2.4*SMALL/72/branch_in*xmax*1.06;o<-order(-nd$y);for(k in 2:length(o)){i<-o[k];j<-o[seq_len(k-1)];hit<-j[abs(nd$y[j]-nd$y[i])<1.3&abs(nd$x[j]-nd$x[i])<lw];for(h in hit){m<-if(nd$x[h]>nd$x[i])h else i;kids<-p$data[p$data$parent==nd$node[m]&p$data$node!=nd$node[m],];if(nrow(kids)==2&&all(kids$isTip)){nd$vj[m]<-.5;nd$hj[m]<- -.25} else {u<-if(nd$y[h]>nd$y[i])h else i;nd$vj[u]<- -1.45}}}}
SBG<-Sys.getenv('MAX4_SUPPORT_BG','')=='1'   # MAX4_SUPPORT_BG=1: white box behind each support number so a crossing branch line cannot run through it (default off)
ndr<-nd[nd$vj==.5,];nd<-nd[nd$vj!=.5,]   # right-of-node labels sit between two branches: plain text, no box
if(nrow(ndr))p<-p+geom_text(data=ndr,aes(x=x,y=y,label=label),size=SMALL/PT,hjust=ndr$hj,vjust=.5,colour='grey35')
if(nrow(nd)){if(SBG)p<-p+geom_label(data=nd,aes(x=x,y=y,label=label),size=SMALL/PT,hjust=nd$hj,vjust=nd$vj,colour='grey35',fill='white',label.size=0,label.padding=grid::unit(0.4,'pt'),label.r=grid::unit(0,'pt')) else p<-p+geom_text(data=nd,aes(x=x,y=y,label=label),size=SMALL/PT,hjust=nd$hj,vjust=nd$vj,colour='grey35')}
d$plot_label<-vapply(d$text,function(z){m<-regexpr('^(?:Candidatus [A-Z][a-z]+ [a-z]+|[A-Z][a-z]+ (?:sp\\.|[a-z]+))',z,perl=TRUE);if(m[1]<0)return(encodeString(z,quote='"'));k<-attr(m,'match.length');paste0('italic(',encodeString(substr(z,1,k),quote='"'),')~',encodeString(trimws(substring(z,k+1)),quote='"'))},character(1))
q<-ggplot(d,aes(x=0,y=y))+geom_text(aes(label=plot_label,colour=query,fontface=ifelse(query,'bold','plain')),parse=TRUE,hjust=0,size=LAB/PT)+
  scale_colour_manual(values=c('FALSE'='#202124','TRUE'='#bb0000'),guide='none')+scale_x_continuous(limits=c(0,1),expand=c(0,0))+ylim(yr)+theme_void()+theme(plot.margin=margin(4,2,4,2))
s<-ggplot(d,aes(x=0,y=y))+geom_text(aes(label=src_w),hjust=0,size=SMALL/PT,lineheight=.85,colour='grey15')+scale_x_continuous(limits=c(0,1),expand=c(0,0))+ylim(yr)+
  theme_void()+labs(title='Isolation source')+theme(plot.title=element_text(size=HEAD,face='bold',hjust=0),plot.margin=margin(4,2,4,4))
g<-ggplot(d,aes(x=0,y=y))+geom_text(aes(label=ifelse(is.na(geo),'',geo)),hjust=0,size=SMALL/PT,colour='grey15')+scale_x_continuous(limits=c(0,1),expand=c(0,0))+ylim(yr)+
  theme_void()+labs(title='Country')+theme(plot.title=element_text(size=HEAD,face='bold',hjust=0),plot.margin=margin(4,1,4,2))
fig<-if(NOMETA) wrap_plots(list(p,q),widths=c(branch_in,label_in),nrow=1) else wrap_plots(list(p,q,s,g),widths=c(branch_in,label_in,src_in,GEO_IN),nrow=1)
STR<-Sys.getenv('MAX4_STRIPS','')   # 21 Oct copy (owner ruling 265, "we want the colored bars"): MAX4_STRIPS=<GROUPS.tsv> adds a source-group and a region colour strip
if(nzchar(STR)&&!NOMETA){                     # beside the tip labels (metadata columns source_group, geo_group); the as-deposited text columns stay. Default: off
  gt<-read.delim(STR,quote='',check.names=FALSE,colClasses='character')
  d$sg<-md$source_group[ix];d$gg<-md$geo_group[ix];stopifnot(all(nzchar(d$sg)),all(nzchar(d$gg)))
  pal<-function(k,v){x<-unique(gt[gt$kind==k,c('group','colour')]);x<-x[x$group %in% v,];stopifnot(!anyDuplicated(x$group));x}
  sp<-pal('source',d$sg);gp<-pal('geo',d$gg)
  strip<-function(col,pl,title,nr)ggplot(d,aes(x=0,y=y,fill=.data[[col]]))+geom_tile(width=1,height=.84,colour=NA)+
    scale_fill_manual(values=setNames(pl$colour,pl$group),breaks=pl$group,name=title,guide=guide_legend(nrow=nr,title.position='left',order=if(col=='sg')1 else 2))+
    scale_x_continuous(expand=c(0,0))+ylim(yr)+theme_void()+theme(plot.margin=margin(4,1,4,1))
  STRIP_IN<-.15
  fig<-wrap_plots(list(p,q,strip('sg',sp,'Source group',2),strip('gg',gp,'Region',1),s,g),widths=c(branch_in-2*STRIP_IN-.06,label_in,STRIP_IN,STRIP_IN,src_in,GEO_IN),nrow=1)+
    plot_layout(guides='collect')&theme(legend.position='bottom',legend.box='vertical',legend.box.just='left',legend.justification='left',legend.title=element_text(size=HEAD,face='bold'),
      legend.text=element_text(size=SMALL),legend.key.size=grid::unit(SMALL*1.15,'pt'),legend.spacing.x=grid::unit(3,'pt'),legend.box.spacing=grid::unit(2,'pt'))
}
ggsave(paste0(stem,'.pdf'),fig,width=W,height=H,device='pdf')
ggsave(paste0(stem,'.png'),fig,width=W,height=H,dpi=DPI)
source(file.path(dirname(sub('^--file=','',grep('^--file=',commandArgs(FALSE),value=TRUE)[1])),'sapote_figure_theme.R'))   # renderer stamp (bundle provenance rule)
sapote_stamp_files(c(paste0(stem,'.pdf'),paste0(stem,'.png')),tool='render_max4_tree.R')
if(nzchar(BRK))cat(sprintf('break: %s terminal branch drawn at %.3f (true %.4f subs/site)\n',BTIP,BLEN,BTRUE));cat(sprintf('%s: tips drawn=%d isolates=%d; root %s; %.1fx%.2f in; row pitch %.1f pt\n',basename(stem),n,sum(query),og,W,H,(H-RES)/n*72))
