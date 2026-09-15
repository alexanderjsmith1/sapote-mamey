#!/usr/bin/env Rscript
# Standalone renderer for admitted source tables. No database discovery or evidence admission.
args <- commandArgs(trailingOnly=TRUE)
if (length(args)<2L) stop('Usage: Rscript render_screening_exploration.R INPUT_DIR OUTPUT_DIR [--overwrite] [--score-0-100]')
opts <- if(length(args)>2L) args[-c(1,2)] else character()
if (any(!opts %in% c('--overwrite','--score-0-100')) || anyDuplicated(opts)) stop('Unknown or duplicate option')
for (pkg in c('ggplot2','patchwork')) if (!requireNamespace(pkg,quietly=TRUE)) stop(paste('Missing R package',pkg))
suppressPackageStartupMessages(library(ggplot2))
suppressPackageStartupMessages(library(patchwork))
input <- normalizePath(args[1],mustWork=TRUE)
dir.create(args[2],recursive=TRUE,showWarnings=FALSE)
output <- normalizePath(args[2],mustWork=TRUE)
if (input==output) stop('Input and output directories must differ')
overwrite <- '--overwrite' %in% opts
score_bounded <- '--score-0-100' %in% opts
full_args <- commandArgs(trailingOnly=FALSE)
script_path <- sub('^--file=', '', full_args[grepl('^--file=',full_args)])
script_path <- gsub('~+~',' ',script_path,fixed=TRUE)
source(file.path(dirname(normalizePath(script_path,mustWork=TRUE)),'sapote_figure_theme.R'))
# Generic categories use the documented blue/green family, not cohort-role colors.
palette <- c('#2c6fbb','#a8ddb5','#52a878','#1d6e44','#666666')
theme_set(sapote_theme(base_pt=11) + theme(legend.position='bottom',
 legend.title=element_blank(),plot.margin=margin(18,22,18,18)))
load <- function(name,cols) {
 p <- file.path(input,name)
 if (!file.exists(p)) return(NULL)
 d <- read.csv(p,check.names=FALSE,stringsAsFactors=FALSE)
 if (!nrow(d) || !all(cols %in% names(d))) stop(paste('Missing rows or required columns in',name))
 d
}
numeric_check <- function(d,cols,nonnegative=FALSE) {
 for (col in cols) {
  if (!is.numeric(d[[col]]) || any(!is.finite(d[[col]]))) stop(paste('Invalid numeric field',col))
  if (nonnegative && any(d[[col]]<0)) stop(paste('Negative count',col))
 }
}
emitted <- character()
context <- load('render_context.csv',c('key','value'))
setting <- function(key,default) {
 if (is.null(context)) return(default)
 if (anyDuplicated(context$key)) stop('Duplicate render context key')
 v <- context$value[context$key==key]
 if (length(v)==1L && nzchar(v)) as.character(v) else default
}
save_plot <- function(p,stem,w,h) {
 if (!grepl('^[a-z0-9_]+$',stem)) stop('Unsafe output name')
 paths <- file.path(output,paste0(stem,c('.png','.pdf','_caption.txt')))
 if (!overwrite && any(file.exists(paths))) stop(paste('Output exists; use --overwrite:',stem))
 # Move editable caption prose off the artwork before saving.
 writeLines(as.character(p$labels$caption),paths[3])
 p <- p + labs(caption=NULL)
 ggsave(paths[1],p,width=w,height=h,dpi=300,bg='white')
 ggsave(paths[2],p,width=w,height=h,device=grDevices::pdf,useDingbats=FALSE,bg='white')
 emitted <<- c(emitted,paths)
}
d <- load('overlap.csv',c('category','count','total'))
if (!is.null(d)) {
 numeric_check(d,c('count','total'),TRUE)
 if (length(unique(d$total))!=1L || sum(d$count)!=d$total[1] || anyDuplicated(d$category)) stop('Invalid overlap denominator or categories')
 d$category <- factor(d$category,levels=rev(d$category))
 p <- ggplot(d,aes(count,category,fill=category))+geom_col(width=.62,show.legend=FALSE)+
  geom_text(aes(label=paste0(count,'  (',sprintf('%.1f',100*count/total),'%)')),hjust=-.12,size=4)+
  scale_fill_manual(values=rev(palette))+scale_x_continuous(expand=expansion(mult=c(0,.25)))+
  labs(title='How the recorded screening calls overlap',subtitle=paste(d$total[1],setting('collection_label','source collection'),'strain rows | owner-recorded qualitative calls'),
       x='Strain rows',y=NULL,caption='Percentages use all source strain rows, including not tested. Neither positive means two recorded negatives.\nCandida retains the source label. These calls do not establish potency or a common assay condition.')
 save_plot(p,'01_screening_overlap',9,5.7)
}
d <- load('host_calls.csv',c('host','organism','positive','tested','not_tested','percent'))
if (!is.null(d)) {
 numeric_check(d,c('positive','tested','not_tested'),TRUE)
 if (any(d$positive>d$tested) || any(d$tested==0) || any(abs(d$percent-100*d$positive/d$tested)>1e-6)) stop('Invalid host denominator')
 d$host <- factor(d$host,levels=rev(unique(d$host)))
 p <- ggplot(d,aes(percent,host,colour=organism))+
  geom_segment(aes(x=0,xend=percent,yend=host),colour='#D6DFE2',linewidth=1)+geom_point(size=4)+
  geom_text(aes(label=paste0(positive,'/',tested)),hjust=-.45,size=3.8)+
  facet_wrap(~organism,nrow=1)+scale_colour_manual(values=palette[1:2],guide='none')+
  scale_x_continuous(limits=c(0,100),breaks=seq(0,100,25),labels=function(x)paste0(x,'%'))+
  labs(title='Recorded activity across host groups',subtitle='Positive strains divided by strains with a positive or negative call',x='Positive fraction of tested strains',y=NULL,
       caption='Other Apidae combines the source sublabels. Untested strains are excluded from each denominator.\nDescriptive only: unequal sampling and unresolved insect-level clustering limit comparisons.')
 save_plot(p,'02_activity_by_host',10,5.5)
}
d <- load('concentration_observations.csv',c('dataset','organism','concentration_ug_ml','inhibition_pct','assay_plate','fraction_plate','source_well'))
if (!is.null(d)) {
 numeric_check(d,c('concentration_ug_ml','inhibition_pct'))
 if (any(!d$concentration_ug_ml %in% c(15,30,60,120))) stop('Unsupported concentration')
 keycols <- c('dataset','organism','assay_plate','fraction_plate','source_well')
 ids <- do.call(paste,c(d[keycols],sep='|'))
 if (anyDuplicated(paste(ids,d$concentration_ug_ml)) || any(table(ids)!=4L)) stop('Incomplete or duplicate concentration records')
 if (score_bounded) {
  d$raw_inhibition_pct <- d$inhibition_pct
  d$score_0_100_pct <- pmax(0,pmin(100,d$raw_inhibition_pct))
  d$inhibition_pct <- d$score_0_100_pct
  scorefile <- file.path(output,'concentration_scored_data.csv')
  if (!overwrite && file.exists(scorefile)) stop('Scored data exists; use --overwrite')
  write.csv(d,scorefile,row.names=FALSE)
 }
 slugs <- gsub('[^a-z0-9]+','_',tolower(unique(d$dataset)))
 if (any(!nzchar(slugs)) || anyDuplicated(slugs)) stop('Dataset names do not form unique safe output names')
 for (j in seq_along(slugs)) {
  dataset <- unique(d$dataset)[j];a <- d[d$dataset==dataset,];a$dose <- factor(a$concentration_ug_ml,levels=c(15,30,60,120))
  n <- aggregate(inhibition_pct~organism,a,function(x)length(x)/4)
  lab <- setNames(paste0(n$organism,'\nn = ',n$inhibition_pct,' complete fraction-assay records'),n$organism)
  p <- ggplot(a,aes(dose,inhibition_pct))+
   geom_hline(yintercept=c(0,100),colour='#AAB9BE',linetype='dashed',linewidth=.35)+
   geom_point(position=position_jitter(width=.13,height=0,seed=42),alpha=.14,size=.65,colour=palette[1])+
   geom_boxplot(width=.45,outlier.shape=NA,fill='white',alpha=.7,colour='#163D48',linewidth=.4)+
   facet_wrap(~organism,nrow=1,labeller=as_labeller(lab))+
   labs(title=paste(dataset,'fraction screening across concentrations'),
    subtitle='Recorded 384-well inhibition | complete, metadata-matched fraction-assay records only',
    x=expression('Concentration ('*mu*'g/mL)'),y='Recorded inhibition (%)',
    caption='Each point is a recorded fraction-assay observation; concentrations are not independent replicates.\nBoxes show medians and interquartile ranges across sampled fractions. Values outside 0-100% remain visible.\nCrudes, incomplete records and unresolved identity conflicts are excluded. This is a subset of the full screen.')
  if (score_bounded) {
   p <- p + scale_y_continuous(limits=c(0,100),breaks=seq(0,100,25),expand=expansion(mult=c(.03,.04))) +
    labs(subtitle='Inhibition scored from 0 to 100% | complete, metadata-matched fraction-assay records',
     y='Inhibition score (%)',
     caption='Scores below 0% are set to 0%; scores above 100% are set to 100%. Boxes are recomputed from these scores.\nOwner reports that extract precipitation can raise OD600 and produce artifactual negative inhibition values.\nRaw values are preserved separately. Four concentrations per fraction-assay record are not independent replicates.')
   save_plot(p,paste0('03_concentrations_',slugs[j],'_scored'),12,6.4)
  } else {
  save_plot(p,paste0('03_concentrations_',slugs[j]),12,6.4)
  outside <- aggregate(inhibition_pct~organism,a,function(x)sum(x< -25 | x>110))
  zoomlab <- setNames(paste0(n$organism,'\nn = ',n$inhibition_pct,' records; ',outside$inhibition_pct[match(n$organism,outside$organism)],' observations outside view'),n$organism)
  pz <- p + coord_cartesian(ylim=c(-25,110)) + facet_wrap(~organism,nrow=1,labeller=as_labeller(zoomlab)) +
   labs(subtitle='Zoomed view from -25 to 110% | see companion full-range figure for every observation',
    caption='Viewport zoom only: all observations remain in the source table and boxplot calculations.\nFour observations per complete fraction-assay record; these are not independent biological replicates.\nCrudes, incomplete records and unresolved identity conflicts are excluded. No potency estimate or significance test.')
  save_plot(pz,paste0('03_concentrations_',slugs[j],'_zoom'),12,6.4)
  }
 }
}
d <- load('wider_inventory.csv',c('organism','format_label','records'))
if (!is.null(d)) {
 numeric_check(d,'records',TRUE)
 totals <- aggregate(records~organism,d,sum);d$organism<-factor(d$organism,levels=totals$organism[order(totals$records)])
 p <- ggplot(d,aes(records,organism,fill=format_label))+geom_col(width=.65)+
  scale_fill_manual(values=c('384 well tagged'=palette[1],'96 well tagged'=palette[2],'Format untagged'='#B9C6CB'))+
  labs(title='The assay archive contains more than two targets',subtitle=paste(sum(d$records),'owner-called source records, including control records'),
  x='Source records',y=NULL,caption='Plate format is classified only when stated in the assay-header text; untagged does not mean untested.\nCounts include controls and repeat assay records. They are not unique strain counts or hit rates.\nFoulbrood and UNKNOWN retain their recorded labels; no organism identity is inferred.')
 save_plot(p,'04_assay_archive_coverage',10,6.7)
}
d <- load('modeb_machinery.csv',c('strain','family','loci_with_annotation','loci_in_snapshot','percent_loci'))
if (!is.null(d)) {
 numeric_check(d,c('loci_with_annotation','loci_in_snapshot','percent_loci'),TRUE)
 if (any(d$loci_in_snapshot==0) || any(d$loci_with_annotation>d$loci_in_snapshot) || any(abs(d$percent_loci-100*d$loci_with_annotation/d$loci_in_snapshot)>1e-6) || anyDuplicated(d[c('strain','family')])) stop('Invalid machinery denominator or duplicate cell')
 d$strain<-factor(d$strain,levels=rev(unique(d$strain)));d$family<-factor(d$family,levels=unique(d$family))
 den<-unique(d[c('strain','loci_in_snapshot')]);labs_y<-setNames(paste0(den$strain,'  [',den$loci_in_snapshot,']'),den$strain)
 p<-ggplot(d,aes(family,strain,fill=percent_loci))+geom_tile(colour='white',linewidth=.3)+
  scale_fill_gradient(low='#F1F5F4',high='#087F8C',limits=c(0,100),name='% of regions')+
  scale_y_discrete(labels=labs_y)+scale_x_discrete(labels=function(x)gsub('_',' ',x))+
  theme(axis.text.x=element_text(angle=40,hjust=1,size=9),axis.text.y=element_text(size=8),panel.grid=element_blank())+
  labs(title='Biosynthetic machinery in the Mode B database',subtitle=paste(setting('architecture_label','Admitted architecture snapshot'),'| each region counted once per annotation family'),
  x=NULL,y=NULL,caption='Brackets show the region denominator for each stored strain partition. Zero means no stored annotation in this channel.\nSnapshot coverage is not chapter admission: cohort membership, assembly quality and package equivalence require review.\nAnnotation presence does not establish expression, metabolite identity or observed bioactivity.')
 save_plot(p,'05_modeb_machinery',10.5,max(6,2.8+.215*length(unique(d$strain))))
}
d <- load('selected_class_profiles.csv',c('strain','class','regions','total_regions','Candida','MRSA'))
if (!is.null(d)) {
 numeric_check(d,c('regions','total_regions'),TRUE)
 if (any(d$regions>d$total_regions) || anyDuplicated(d[c('strain','class')])) stop('Invalid class count')
 d$strain<-factor(d$strain,levels=rev(unique(d$strain)));d$class<-factor(d$class,levels=unique(d$class))
 p1<-ggplot(d,aes(class,strain,fill=regions))+geom_tile(colour='white',linewidth=1)+geom_text(aes(label=regions),size=5)+
  scale_fill_gradient(low='#F1F5F4',high='#72BBC1',guide='none')+labs(title='A  Regions carrying each class label',x=NULL,y=NULL)+theme(panel.grid=element_blank())
 a<-unique(d[c('strain','Candida','MRSA')]);a<-rbind(data.frame(strain=a$strain,assay='Candida',call=a$Candida),data.frame(strain=a$strain,assay='MRSA',call=a$MRSA));a$label<-ifelse(a$call=='positive','+','-')
 if(any(!a$call %in% c('positive','negative')))stop('Unsupported qualitative call in selected profiles')
 p2<-ggplot(a,aes(assay,strain,fill=call))+geom_tile(colour='white',linewidth=1)+geom_text(aes(label=label),size=6)+
  scale_fill_manual(values=c(positive='#79C0B6',negative='#E0E7E9'),guide='none')+labs(title='B  Recorded calls',x=NULL,y=NULL)+theme(panel.grid=element_blank(),axis.text.y=element_blank())
 p<-(p1+p2+plot_layout(widths=c(2.3,1)))+plot_annotation(title='Genome annotations beside observed screening calls',
  subtitle=paste(length(unique(d$strain)),'selected strains |',setting('package_label','admitted package inventories and owner calls')),
  caption='Classes can overlap within a region; columns must not be summed. These are selected examples, not a cohort comparison.\nPositive (+) and negative (-) are strain-level qualitative calls. No region, class or gene is assigned as their cause.')
 save_plot(p,'06_genome_and_screening_examples',11,5.3)
}
if (!length(emitted)) stop('No supported input tables found')
writeLines(c(capture.output(sessionInfo()),'',paste('Created',emitted)),file.path(output,'R_SESSION.txt'))
cat(length(emitted)/2,'figure pairs created\n')
