#!/usr/bin/env Rscript
# Paired-locus extension of sapote_locus_map.R: shared theme/role palette,
# rigid source geometry, supplied protein links, actual DB comparison spans.
args <- commandArgs(trailingOnly=TRUE)
if(length(args)<1||length(args)>2||(length(args)==2&&args[2]!='--refresh')) stop('Usage: bigscape_locus_map.R prepared_output_directory [--refresh]')
refresh <- length(args)==2
suppressPackageStartupMessages({library(ggplot2);library(jsonlite);library(grid);library(svglite)})
out <- normalizePath(args[1]); cfg <- fromJSON(file.path(out,'plot_config.json'),simplifyVector=FALSE)
source(file.path(cfg$bundle_root,'tools','sapote_figure_theme.R'))
read_tsv <- function(name) read.delim(file.path(out,name),stringsAsFactors=FALSE,check.names=FALSE,na.strings=character())
g <- read_tsv('genes.tsv'); links <- read_tsv('links.tsv'); spans <- read_tsv('spans.tsv')
required <- c('track','locus_tag','display_start','display_end','display_strand','role','display_label')
if(!all(required %in% names(g)) || nrow(g)==0) stop('invalid gene table')
if(any(!is.finite(g$display_start)|!is.finite(g$display_end)|g$display_end<=g$display_start)) stop('invalid plotted gene interval')
if(any(!g$display_strand %in% c(-1,1))) stop('invalid strand')
if(anyDuplicated(paste(g$track,g$locus_tag))) stop('duplicate track/gene key')
tracks <- vapply(cfg$tracks,function(t)t$track,character(1)); if(length(tracks)!=2) stop('two tracks required')
yy <- setNames(c(3,0),tracks);g$y <- unname(yy[g$track])
ROLE_COLOURS <- c('biosynthetic'='#0072B2','biosynthetic-additional'='#56B4E9',
                  'transport'='#009E73','regulatory'='#E69F00','resistance'='#D55E00','other'='#BBBBBB')
g$plot_role <- ifelse(g$role %in% names(ROLE_COLOURS),g$role,'other')
ends <- lapply(cfg$tracks,function(t)sort(c(t$source_start,t$source_end)/1000))
lo <- min(vapply(ends,min,numeric(1))); hi <- max(vapply(ends,max,numeric(1))); xr <- hi-lo
if(!is.finite(xr)||xr<=0) stop('invalid locus extent')

# Same arrow construction as the bundled R route, translated for each row.
arrow_poly <- function(i){
 s<-g$display_start[i];e<-g$display_end[i];y<-g$y[i];h<-min((e-s)/3,xr*.006)
 xs<-if(g$display_strand[i]>0)c(s,e-h,e,e-h,s)else c(e,s+h,s,s+h,e)
 data.frame(id=paste(g$track[i],g$locus_tag[i]),x=xs,y=y+c(-.055,-.055,0,.055,.055),role=g$plot_role[i])
}
poly <- do.call(rbind,lapply(seq_len(nrow(g)),arrow_poly))
ribbons <- NULL
if(nrow(links)){
 for(i in seq_len(nrow(links))){
  l<-links[i,];ya<-yy[[l$track_a]];yb<-yy[[l$track_b]]
  if(ya==yb) stop('link joins same track')
  da<-if(ya>yb)-.09 else .09;db<-if(ya>yb).09 else -.09
  ribbons<-rbind(ribbons,data.frame(id=i,x=c(l$a_start,l$a_end,l$b_end,l$b_start),y=c(ya+da,ya+da,yb+db,yb+db)))
 }
}
# Measure short label widths at 8pt on a memory-only device. Conservative panel
# allowance and three fixed lanes keep labels outside the ribbons. Genes stay fixed.
grDevices::pdf(file=NULL,width=cfg$width_in,height=cfg$body_height_in)
g$label_visible_on_figure <- FALSE;g$label_y <- NA_real_
for(t in tracks){
 ids<-which(g$track==t);ids<-ids[order((g$display_start[ids]+g$display_end[ids])/2)]
 right<-rep(-Inf,3);sign<-if(t==tracks[1])1 else -1
 for(i in ids){
  if(!nzchar(g$display_label[i]))next
  grob<-textGrob(g$display_label[i],gp=gpar(fontsize=8,fontfamily='sans'))
  width_in<-convertWidth(grobWidth(grob),'inches',valueOnly=TRUE)
  half<-(width_in+.025)/2*xr/(cfg$width_in-1.2);x<-(g$display_start[i]+g$display_end[i])/2
  lane<-which(x-half>right)[1]
  if(!is.na(lane)){g$label_visible_on_figure[i]<-TRUE;g$label_y[i]<-yy[[t]]+sign*(.19+.23*(lane-1));right[lane]<-x+half}
 }
}
grDevices::dev.off()
shown<-g[g$label_visible_on_figure,,drop=FALSE];shown$x<-(shown$display_start+shown$display_end)/2
heads<-do.call(rbind,lapply(seq_along(cfg$tracks),function(i){t<-cfg$tracks[[i]];data.frame(x=lo,y=if(i==1)4.22 else -1.09,label=t$heading)}))
counts<-do.call(rbind,lapply(seq_along(tracks),function(i){ids<-g$track==tracks[i];data.frame(x=hi,y=if(i==1)3.94 else -.88,label=sprintf('%d/%d gene labels',sum(g$label_visible_on_figure[ids]),sum(ids)))}))
bounds<-do.call(rbind,lapply(seq_along(tracks),function(i)data.frame(x=ends[[i]],y=yy[[tracks[i]]]-.09,yend=yy[[tracks[i]]]+.09)))
spans$y<-unname(yy[spans$track]);spans$y<-spans$y+ifelse(spans$track==tracks[1],-1,1)*ifelse(spans$kind=='lcs',.17,.30)
spans$span_name<-ifelse(spans$kind=='lcs','LCS CDS envelope','Comparable CDS span')
p<-ggplot()
if(!is.null(ribbons))p<-p+geom_polygon(data=ribbons,aes(x=x,y=y,group=id),fill='#9FAAB0',alpha=.20,colour=NA)
p<-p+geom_hline(yintercept=c(3,0),colour=SAPOTE_GRID,linewidth=.25)+
 geom_polygon(data=poly,aes(x=x,y=y,group=id,fill=role),colour=SAPOTE_INK,linewidth=.17)+
 geom_segment(data=bounds,aes(x=x,xend=x,y=y,yend=yend),colour=SAPOTE_INK,linewidth=.25)+
 geom_segment(data=spans,aes(x=display_start,xend=display_end,y=y,yend=y,colour=span_name),linewidth=.5)+
 geom_segment(data=shown,aes(x=x,xend=x,y=y+ifelse(track==tracks[1],.09,-.09),yend=label_y-ifelse(track==tracks[1],.07,-.07)),colour='#87959E',linewidth=.15)+
 geom_text(data=shown,aes(x=x,y=label_y,label=display_label),size=8/.pt,colour=SAPOTE_INK)+
 geom_text(data=heads,aes(x=x,y=y,label=label),hjust=0,lineheight=1.2,size=8/.pt,colour=SAPOTE_INK)+
 geom_text(data=counts,aes(x=x,y=y,label=label),hjust=1,size=8/.pt,colour='#54637A')+
 scale_fill_manual(values=ROLE_COLOURS,name='antiSMASH role')+
 scale_colour_manual(values=c('LCS CDS envelope'='#17212E','Comparable CDS span'='#0072B2'),name='BiG-SCAPE')+
 scale_x_continuous(expand=expansion(mult=.025),breaks=scales::breaks_pretty(n=6))+
 scale_y_continuous(limits=c(-1.55,4.55),breaks=NULL,expand=expansion(mult=0))+
 labs(title=cfg$title,subtitle=cfg$subtitle,x='Distance from declared matched-gene midpoint (kb)',y=NULL)+
 sapote_theme(base_pt=8)+sapote_no_grid()+
 theme(axis.line.x=element_line(colour='#87959E',linewidth=.3),axis.ticks.x=element_line(colour=SAPOTE_INK,linewidth=.3),
       legend.position='bottom',legend.box='vertical',legend.title=element_text(size=8),legend.text=element_text(size=8),
       plot.title=element_text(size=9,face='bold'),plot.subtitle=element_text(size=8),
       plot.margin=margin(12,14,8,14),legend.margin=margin(2,0,0,0),axis.title.x=element_text(size=8,margin=margin(t=7)))+
 guides(fill=guide_legend(nrow=2,byrow=TRUE),colour=guide_legend(nrow=1))

svg_path<-file.path(out,'locus_plot_only.svg');pdf_path<-file.path(out,'locus_with_caption.pdf')
if(!refresh&&(file.exists(svg_path)||file.exists(pdf_path)))stop('image destination already exists')
svglite::svglite(svg_path,width=cfg$width_in,height=cfg$body_height_in);print(p);dev.off()
cap_lines<-strwrap(cfg$caption,width=108);band_h<-.38+.16*length(cap_lines)
grDevices::cairo_pdf(pdf_path,width=cfg$width_in,height=cfg$body_height_in+band_h,family='sans')
grid.newpage();pushViewport(viewport(layout=grid.layout(2,1,heights=unit(c(cfg$body_height_in,band_h),'inches'))))
print(p,newpage=FALSE,vp=viewport(layout.pos.row=1))
pushViewport(viewport(layout.pos.row=2));grid.lines(x=unit(c(.2,cfg$width_in-.2),'inches'),y=unit(band_h-.04,'inches'),gp=gpar(col='#C8D0D8',lwd=.5))
grid.text(paste(cap_lines,collapse='\n'),x=unit(.2,'inches'),y=unit(band_h-.22,'inches'),just=c('left','top'),gp=gpar(fontsize=8,fontfamily='sans',col=SAPOTE_INK,lineheight=1.25))
popViewport(2);dev.off()
if(isTRUE(cfg$preview_png)){
 ragg::agg_png(file.path(out,'locus_plot_only.png'),width=cfg$width_in,height=cfg$body_height_in,units='in',res=300,background='white');print(p);dev.off()
}
stamped<-c(svg_path,pdf_path);if(isTRUE(cfg$preview_png))stamped<-c(stamped,file.path(out,'locus_plot_only.png'))
sapote_stamp_files(stamped,tool='bigscape_locus_map.R')  # provenance stamp, as every bundle renderer must
write.table(g,file.path(out,'genes.tsv'),sep='\t',quote=TRUE,row.names=FALSE,na='')
versions<-lapply(c('ggplot2','svglite','jsonlite','ragg','scales'),function(x)as.character(packageVersion(x)));names(versions)<-c('ggplot2','svglite','jsonlite','ragg','scales')
write_json(list(R=R.version.string,platform=R.version$platform,packages=versions,font_family='sans',label_method='8pt grid text-width measurement; three fixed external lanes; explicit suppression counts',ggrepel_used=FALSE,
 palette=as.list(ROLE_COLOURS),width_in=cfg$width_in,body_height_in=cfg$body_height_in,minimum_font_pt=8,
 label_counts=lapply(tracks,function(t)list(track=t,shown=sum(g$label_visible_on_figure[g$track==t]),total=sum(g$track==t))),
 source_figure='selected BiG-SCAPE DB plus externally supplied protein correspondences',source_theme=file.path(cfg$bundle_root,'tools/sapote_figure_theme.R'),
 native_devices=list(svg='svglite',pdf='cairo_pdf',png=if(isTRUE(cfg$preview_png))'ragg'else'NOT_REQUESTED')),file.path(out,'R_RUNTIME.json'),auto_unbox=TRUE,pretty=TRUE)
cat(sprintf('R paired map: %d genes, %d links; label counts %s\n',nrow(g),nrow(links),paste(vapply(tracks,function(t)sprintf('%d/%d',sum(g$label_visible_on_figure[g$track==t]),sum(g$track==t)),character(1)),collapse=', ')))
