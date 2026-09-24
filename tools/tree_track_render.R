# Shared rendering of explicitly selected, exact-tip assay values. No aggregation or name inference.
render_tree_tracks <- function(a, single=FALSE) {
  if (length(a) < 5 || length(a) > 7) stop('usage: <tree.newick> <tracks.tsv> <series.tsv> <out_prefix> <title> [threshold|none] [support_threshold|none]')
  suppressPackageStartupMessages({library(ape);library(ggtree);library(ggplot2);library(patchwork)})
  read_tsv <- function(path) read.delim(path, quote='', check.names=FALSE, na.strings=character(), colClasses='character')
  tk <- read_tsv(a[2]); spec <- read_tsv(a[3]); tr <- read.tree(a[1]); out <- a[4]
  if (inherits(tr,'multiPhylo') || is.null(tr$tip.label) || anyDuplicated(tr$tip.label)) stop('TREE_TRACK_REFUSED: one tree with unique exact tip IDs required')
  if (!all(c('tip','label','role') %in% names(tk)) || anyDuplicated(tk$tip) || any(!nzchar(tk$label)) || !setequal(tr$tip.label,tk$tip)) stop('TREE_TRACK_REFUSED: tree tips must exactly equal the unique metadata tips')
  if (!all(tk$role %in% c('query','reference','outgroup'))) stop('TREE_TRACK_REFUSED: unknown tip role')
  if (!all(c('column','label','colour') %in% names(spec)) || !nrow(spec) || anyDuplicated(spec$column) || anyDuplicated(spec$label) || any(!nzchar(spec$label)) || !all(spec$column %in% names(tk)) || any(!grepl('^#[0-9a-fA-F]{6}$',spec$colour))) stop('TREE_TRACK_REFUSED: invalid series contract')
  if (single && nrow(spec)!=1) stop('TREE_TRACK_REFUSED: single-bar renderer requires exactly one series')
  number_option <- function(i) {
    if (length(a)<i || a[i]=='none') return(NULL)
    v <- suppressWarnings(as.numeric(a[i])); if (length(v)!=1 || !is.finite(v)) stop('TREE_TRACK_REFUSED: threshold must be finite or none'); v
  }
  threshold <- number_option(6); support <- number_option(7)
  for (column in spec$column) {
    raw <- tk[[column]]; val <- suppressWarnings(as.numeric(raw))
    if (any(nzchar(raw) & !is.finite(val))) stop('TREE_TRACK_REFUSED: nonblank values must be finite numbers')
    if (any(tk$role!='query' & nzchar(raw))) stop('TREE_TRACK_REFUSED: reference/outgroup tips cannot carry query assay values')
    tk[[column]] <- val
  }
  if (any(file.exists(paste0(out,c('.pdf','.png','.tip_order.tsv'))))) stop('TREE_TRACK_REFUSED: output exists')
  dir.create(dirname(out),recursive=TRUE,showWarnings=FALSE)
  # Layout may request device metrics before ggsave; keep that scratch device off disk.
  grDevices::pdf(file=NULL)
  measurement_device <- grDevices::dev.cur()
  on.exit(if (measurement_device %in% grDevices::dev.list()) grDevices::dev.off(measurement_device), add=TRUE)
  p <- ggtree(ladderize(tr),linewidth=.55)
  d <- p$data[p$data$isTip,]; d <- d[order(d$y),]
  ix <- match(d$label,tk$tip); d$display <- tk$label[ix]; d$role <- tk$role[ix]
  n <- nrow(d); xr <- c(.4,n+.6); big <- n>40
  nd <- p$data[!p$data$isTip,]; sv <- suppressWarnings(as.numeric(nd$label))
  if (!is.null(support)) {
    nd <- nd[!is.na(sv)&sv>=support,]
    if(nrow(nd)) p <- p+geom_text(data=nd,aes(x=x,y=y,label=label),size=2.3,hjust=-.15,vjust=-.35,colour='grey35')
  }
  ptree <- p+coord_flip()+scale_x_continuous(expand=c(.02,0))+scale_y_continuous(limits=xr,expand=c(0,0))+theme(plot.margin=margin(0,10,6,10))
  plab <- ggplot(d,aes(x=y,y=0))+geom_text(aes(label=display,fontface=ifelse(role=='query','plain','italic')),angle=90,hjust=0,vjust=.5,size=if(big) 1.8 else 3)+
    scale_x_continuous(limits=xr,expand=c(0,0))+scale_y_continuous(limits=c(-.05,3.4),expand=c(0,0))+theme_void()+theme(plot.margin=margin(0,10,0,10))
  k <- nrow(spec); bw <- .84/k; off <- (seq_len(k)-(k+1)/2)*bw
  long <- do.call(rbind,lapply(seq_len(k),function(i) data.frame(x=d$y+off[i],v=tk[[spec$column[i]]][ix],series=spec$label[i])))
  long <- long[is.finite(long$v),]; long$series <- factor(long$series,levels=spec$label)
  pbar <- ggplot(long,aes(x=x,y=v,fill=series))+geom_col(width=bw*.92)+
    geom_point(data=long[long$v==0,,drop=FALSE],shape=21,size=2,stroke=.35)+
    scale_fill_manual(values=setNames(spec$colour,spec$label),name=NULL,drop=FALSE)+guides(fill=guide_legend(nrow=1))+
    scale_x_continuous(limits=xr,expand=c(0,0))+scale_y_continuous(expand=expansion(mult=c(.06,.1)))+
    labs(y='Selected inhibition (%)')+theme_minimal(base_size=10)+
    theme(axis.title.x=element_blank(),axis.text.x=element_blank(),panel.grid.major.x=element_blank(),panel.grid.minor=element_blank(),legend.position='top',plot.margin=margin(2,10,4,10))
  if (!is.null(threshold)) pbar <- pbar+geom_hline(yintercept=threshold,linetype='dotted',colour='#2563EB')
  subtitle <- paste0('Explicitly selected strain-level values; no aggregation by this renderer.\nBlank = not measured; recorded zero is marked by a dot.',if(!is.null(threshold)) paste0(' Dotted line = ',threshold,'% (display option).') else '')
  fig <- wrap_plots(list(pbar,plab,ptree),heights=c(2.8,2.3,2.4),ncol=1)+plot_annotation(title=a[5],subtitle=subtitle,theme=theme(plot.title=element_text(face='bold',size=13),plot.subtitle=element_text(size=9)))
  w <- if(big) min(40,2+n*(.15+.03*k)) else max(8,1.2+n*.75)
  pdf_device <- if (capabilities('aqua')) function(filename,width,height,...) grDevices::quartz(file=filename,type='pdf',width=width,height=height,...) else grDevices::pdf
  ggsave(paste0(out,'.pdf'),fig,width=w,height=10,limitsize=FALSE,device=pdf_device)
  if (!file.exists(paste0(out,'.pdf')) || file.info(paste0(out,'.pdf'))$size==0) stop('TREE_TRACK_REFUSED: PDF device did not produce an artifact')
  ggsave(paste0(out,'.png'),fig,width=w,height=10,dpi=160,limitsize=FALSE)
  write.table(data.frame(tip=d$label,label=d$display,role=d$role,position=d$y),paste0(out,'.tip_order.tsv'),sep='\t',row.names=FALSE,quote=FALSE)
}
