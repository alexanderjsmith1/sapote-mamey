#!/usr/bin/env Rscript
suppressPackageStartupMessages({library(ape);library(ggtree);library(ggplot2);library(patchwork)})
a<-commandArgs(trailingOnly=TRUE);stopifnot(length(a)==3);folder<-normalizePath(a[1]);geometry<-normalizePath(a[2]);source(geometry);code_dir<-dirname(geometry);output_stem<-a[3];stopifnot(grepl('^[A-Za-z0-9][A-Za-z0-9_.-]+$',output_stem));setwd(folder)
md<-read.delim('metadata.tsv',quote='',check.names=FALSE,na.strings=character());tr<-read.tree('tree.newick')
settings<-read.delim('settings.tsv',quote='',na.strings=character());get<-function(k){v<-settings$value[match(k,settings$key)];if(length(v)!=1||is.na(v)||!nzchar(v))stop(paste0('SERIES_SETTING_MISSING:',k));v}
required<-c('tip','role','type_status','taxon_display','label_concise','label_experiment','raw_source','source_category','raw_geography','geography','candida_state','mrsa_state','assay_provenance')
stopifnot(all(required%in%names(md)),!anyDuplicated(md$tip),setequal(tr$tip.label,md$tip))
outgroup<-get('outgroup_tip');if(!outgroup%in%tr$tip.label)stop('SERIES_OUTGROUP_MISSING');tr<-root(tr,outgroup=outgroup,resolve.root=FALSE,edgelabel=TRUE)
missing_display<-c('', 'n/a', 'na', 'none', 'not recorded', 'unknown', 'unresolved', 'unresolved source', 'missing')
for(field in c('taxon_display','label_concise','label_experiment','source_category','geography')){
  value<-tolower(trimws(as.character(md[[field]])))
  if(any(is.na(value)|value%in%missing_display))stop(paste0('SERIES_DISPLAY_METADATA_INCOMPLETE:',field))
}
pal<-read.delim(file.path(code_dir,'phylo_display_palette.tsv'),quote='',na.strings=character());source_pal<-setNames(pal$color[pal$field=='source'],pal$value[pal$field=='source']);geo_pal<-setNames(pal$color[pal$field=='geography'],pal$value[pal$field=='geography'])
if(!all(md$source_category%in%names(source_pal))||!all(md$geography%in%names(geo_pal)))stop('SERIES_PALETTE_UNSUPPORTED')
p<-ggtree(tr,ladderize=TRUE,size=.25);d<-p$data[p$data$isTip,];d<-cbind(d,md[match(d$label,md$tip),setdiff(names(md),'tip'),drop=FALSE]);names(d)[names(d)=='label']<-paste0('label',seq_len(sum(names(d)=='label')))
d$text<-if(get('view')%in%c('publication-detailed','internal'))d$label_experiment else d$label_concise;d$identity<-p$data$label[p$data$isTip];d$query<-d$role=='query';n<-nrow(d);xmax<-max(p$data$x)
size<-if(n>120)2.0 else 2.6
italicize<-function(s,taxon){q<-function(z)encodeString(z,quote='"');if(!startsWith(s,taxon))stop('SERIES_LABEL_TAXON_DRIFT');rest<-trimws(substring(s,nchar(taxon)+1));if(nzchar(rest))paste0('italic(',q(taxon),')~',q(rest))else paste0('italic(',q(taxon),')')}
d$plot_label<-mapply(italicize,d$text,d$taxon_display,USE.NAMES=FALSE)
p<-p+geom_segment(data=d,aes(x=x,xend=xmax*1.01,y=y,yend=y),linetype='dotted',linewidth=.15,colour='grey65')+geom_treescale(x=0,y=0,width=.01,fontsize=2.4)+scale_x_continuous(limits=c(0,xmax*1.015),expand=c(0,0))+ylim(-.6,n+.6)+theme(plot.margin=margin(5,0,5,8))
nd<-p$data[!p$data$isTip,];nd$support<-suppressWarnings(as.numeric(nd$label));cutoff<-as.numeric(get('support_cutoff'));nd<-nd[!is.na(nd$support)&nd$support>=cutoff,];if(nrow(nd))p<-p+geom_text(data=nd,aes(x=x,y=y,label=support),size=2.25,hjust=-.12,vjust=-.25,colour='#444444')
q<-ggplot(d,aes(x=0,y=y))+geom_text(aes(label=plot_label,colour=query),parse=TRUE,hjust=0,size=size)+scale_colour_manual(values=c('FALSE'='black','TRUE'=Sys.getenv('GG_FOCAL_COLOUR','#000000')),guide='none')+scale_x_continuous(limits=c(0,1),expand=c(0,0))+ylim(-.6,n+.6)+theme_void()+theme(plot.margin=margin(5,5,5,3))
mk<-function(field,title){vals<-d[[field]];palette<-if(field=='source_category')source_pal else geo_pal;stopifnot(all(vals %in% names(palette)));ggplot(data.frame(y=d$y,value=vals),aes(x=0,y=y,fill=value))+geom_tile(width=.85,height=1)+scale_fill_manual(values=palette,name=title,drop=TRUE)+ylim(-.6,n+.6)+theme_void()+labs(title=title)+theme(plot.title=element_text(size=8,hjust=.5),legend.position='bottom',legend.text=element_text(size=6),legend.title=element_text(size=7),plot.margin=margin(5,3,5,3))+guides(fill=guide_legend(ncol=5))}
ord<-order(d$y)
for(field in c('source_category','geography')){palette<-if(field=='source_category')source_pal else geo_pal;audit<-validate_annotation_strip(mk(field,field),d$identity[ord],d[[field]][ord],palette);write.table(audit,paste0(output_stem,'.',field,'_actual_cells.tsv'),sep='\t',quote=FALSE,row.names=FALSE)}
assay_symbol<-c(positive='+',negative='-',not_tested='n.t.',missing='?');d$Candida<-ifelse(d$query,assay_symbol[d$candida_state],'');d$MRSA<-ifelse(d$query,assay_symbol[d$mrsa_state],'')
txt<-function(field,title){ggplot(d,aes(x=0,y=y))+geom_text(aes(label=.data[[field]]),size=2.7)+scale_x_continuous(limits=c(-.5,.5),expand=c(0,0))+ylim(-.6,n+.6)+theme_void()+labs(title=title)+theme(plot.title=element_text(size=8,hjust=.5,face='bold'),plot.margin=margin(5,2,5,2))}
pdf(NULL);label_inches<-max(vapply(d$text,function(z)grid::convertWidth(grid::grobWidth(grid::textGrob(z,gp=grid::gpar(fontsize=size*72.27/25.4))),'inches',valueOnly=TRUE),numeric(1)))+.5;dev.off()
other_widths<-c(label_inches,1.0,1.25,1.25);plots<-list(q,mk('source_category','Isolation source'),txt('Candida','Candida Inhibition'),txt('MRSA','MRSA inhibition'))
if(get('view')!='publication-noloc'){plots<-append(plots,list(mk('geography','Geography')),after=2);other_widths<-append(other_widths,1.1,after=2)}
requested_fraction<-as.numeric(get('tree_fraction'));min_tree_inches<-6.5;tree_inches<-max(min_tree_inches,requested_fraction/(1-requested_fraction)*sum(other_widths));widths<-c(tree_inches,other_widths);plots<-append(list(p),plots)
actual_fraction<-tree_inches/sum(widths);if(actual_fraction+1e-9<requested_fraction)stop('SERIES_LAYOUT_TREE_AREA_REGRESSION')
method_caption<-sprintf('%s; model %s; %s support, %s replicates; displayed cutoff %s; %s.',get('inference_program'),get('model'),get('support_type'),get('support_replicates'),get('support_cutoff'),get('rooting'))
caption<-paste(strwrap(paste(method_caption,paste(readLines('caption.txt'),collapse=' ')),width=160),collapse='\n')
writeLines(c(method_caption,readLines('caption.txt')),paste0(output_stem,'.methods.txt'))
fig<-wrap_plots(plots,widths=widths,guides='collect')+plot_annotation(title=get('title'),caption=caption,theme=theme(plot.title=element_text(size=11),plot.caption=element_text(size=8,hjust=0)))
fig<-fig & theme(legend.position='bottom')
h<-max(6,n*(if(n>120).105 else .15)+3.1);w<-sum(widths)+.4
for(ext in c('pdf','png'))ggsave(paste0(output_stem,'.',ext),fig,width=w,height=h,dpi=150,limitsize=FALSE)
write.tree(tr,paste0(output_stem,'.newick'))
write.table(data.frame(profile=get('layout_profile'),requested_tree_fraction=requested_fraction,actual_tree_fraction=actual_fraction,tree_inches=tree_inches,label_inches=label_inches,figure_inches=w),paste0(output_stem,'.layout_audit.tsv'),sep='\t',quote=FALSE,row.names=FALSE)
writeLines(capture.output(sessionInfo()),paste0(output_stem,'.R_SESSION.txt'))
