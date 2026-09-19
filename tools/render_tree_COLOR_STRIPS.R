#!/usr/bin/env Rscript
# GTR-05 renderer: repaired baseline layout + canonical source/geography colour strips.
# Palettes copied verbatim from the shared EPA-ng registry
#   06_ALL_EPA_NG_DISPLAY_CORRECTIONS_R04/render_tree.R lines 15-16
# so colours are deterministic across the GToTree and EPA-ng figure families.
# Single documented extension: 'Pacific Ocean' is absent from the registry's geo_palette
# (which carries 'Indian Ocean' only). The hex reused here is the one already on disk in the
# round-3 GTR-05 renderer, so no new colour is invented. It collides with no registry geo hex.
suppressPackageStartupMessages({library(ape);library(ggtree);library(ggplot2);library(patchwork)})
a<-commandArgs(trailingOnly=TRUE);if(length(a)==1)a<-c(a,'both');stopifnot(length(a)==2,a[2]%in%c('concise','experiment_id','both'))
# Required default: both label variants. `Rscript render_tree_COLOR_STRIPS.R <panel_dir>` (or `... both`) renders
# the concise figure and the experiment-ID figure; naming one variant renders only that one.
if(a[2]=='both'){script<-sub('^--file=','',grep('^--file=',commandArgs(),value=TRUE)[1]);if(!file.exists(script))script<-gsub('~+~',' ',script,fixed=TRUE)
  for(v in c('concise','experiment_id')){st<-system2('Rscript',c(shQuote(script),shQuote(a[1]),v));if(st!=0)stop('variant failed: ',v)};quit(status=0)}
panel<-normalizePath(a[1]);panel_id<-basename(panel);variant<-a[2];setwd(panel)
tr<-read.tree('tree.treefile');md<-read.delim('figure_metadata.tsv',quote='',check.names=FALSE,na.strings=character(),stringsAsFactors=FALSE)
stopifnot(setequal(tr$tip.label,md$tip),!anyDuplicated(md$tip),Ntip(tr)==nrow(md))
outtip<-md$tip[md$role=='OUTGROUP'];stopifnot(length(outtip)==1);tr<-root(tr,outgroup=outtip,resolve.root=TRUE,edgelabel=TRUE)
lines<-readLines('tree.iqtree',warn=FALSE);model<-sub('^Model of substitution:[[:space:]]*','',grep('^Model of substitution:',lines,value=TRUE)[1]);if(is.na(model))model<-'MFP-selected model'

source_palette<-c('Bumblebee'='#0072B2','Honeybee'='#E69F00','Other bee'='#56B4E9','Wasp'='#CC79A7','Ant'='#882255','Attine'='#882255','Beehive pollen'='#AA7700','Bryophyte'='#44AA99','Lichen'='#AA4499','Lichen-moss mixture'='#DDCC77','Soil'='#8C510A','Plant-associated'='#228833','Marine-associated'='#332288','Mangrove'='#117733','Freshwater-associated'='#88CCEE','Freshwater sediment'='#88CCEE','Salt lake'='#999933','Animal-associated'='#D55E00','Animal/clinical'='#D55E00','Other documented'='#666666','Fungal-associated'='#AA3377','Built environment'='#999999','Rock-associated'='#999999','Coastal sediment'='#88AA99','Biofilter'='#A6761D','Termite'='#663399','Waste-associated'='#6B6B3D','Air-associated'='#BBBBBB')
geo_palette<-c('Africa'='#E69F00','Antarctica'='#56B4E9','Asia'='#CC79A7','Europe'='#332288','North America'='#44AA99','South America'='#D55E00','Oceania'='#882255','Europe / Asia'='#7B3294','Indian Ocean'='#999933','US'='#009E73','Canada'='#0072B2','Pacific Ocean'='#4477AA')

# --- Display alias layer (Alex's ruling 2026-09-14) -------------------------------------------
# Applied at RENDER time only. The underlying metadata keeps every value as deposited; nothing is
# re-categorised in the data. Two rulings:
#   (a) "collapse marine and ocean samples to 'Marine' for readability"
#   (b) long deposited descriptions do not belong in the tree - they squeeze the branches.
#       The verbatim detail is exported to a supplement table instead (see *_SUPPLEMENT_*.tsv).
# Alex named 'Marine' and 'Plant' explicitly; the short form is applied consistently to the
# '-associated' family. Revert by emptying these two vectors.
# 'Animal' was reverted 2026-09-14: Alex flagged it as ambiguous with invertebrates (the bee/wasp
# categories are also animals). The registry's 'Animal-associated' stands unchanged until the
# vocabulary question is settled. M46's deposited 'Mammoth faeces' is an OPEN metadata question
# (frozen/permafrost material? 'Other terrestrial'? 'Faeces'?) - recorded, not decided, not blocking.
src_alias<-c('Marine-associated'='Marine','Plant-associated'='Plant')
geo_alias<-c('Pacific Ocean'='Marine','Indian Ocean'='Marine')
source_palette<-c(source_palette,'Not recorded'='#DDDDDD','Laboratory mutant'='#984EA3','Marine'='#332288','Plant'='#228833','Animal'='#D55E00')
# 'Marine' is one label, so it gets one colour in both strips. Where a tip is Marine on both axes
# the two cells are the same hue, separated by the white cell border (Alex's ruling on the
# Bumblebee/Canada case: the border is sufficient).
geo_palette<-c(geo_palette,'Not recorded'='#DDDDDD','Marine'='#332288','Russia'='#A50F15','Turkey'='#F0E442','Virgin Islands'='#FB9A99','Costa Rica'='#B15928','Northern Cyprus'='#6A3D9A')  # held countries: own category+colour per Alex 2026-09-14
# v9.7.430 display contract: focal-tip colour is a knob. The bundle's EPA-ng renderer defaults to
# black; this panel family has been reviewed and accepted with red queries, so red is the default
# HERE and black is one export away (GG_FOCAL_COLOUR='#000000'). The point of the contract is that
# the colour is configurable rather than hardcoded -- which it now is.
focal_colour<-Sys.getenv('GG_FOCAL_COLOUR','#bb0000')
relabel<-function(x,map){i<-x%in%names(map);x[i]<-unname(map[x[i]]);x}

p<-ggtree(tr,ladderize=TRUE,size=.55);d<-p$data[p$data$isTip,];ix<-match(d$label,md$tip)
d$text<-if(variant=='experiment_id')md$label_experiment[ix] else md$label_concise[ix];d$query<-md$role[ix]=='QUERY';d$class<-md$reference_class[ix];d$source<-md$source_display[ix];d$source_cat<-relabel(md$source_category[ix],src_alias);d$geo<-relabel(md$geography_display[ix],geo_alias);d$candida<-ifelse(d$query,ifelse(is.na(md$Candida[ix]),'',as.character(md$Candida[ix])),'');d$mrsa<-ifelse(d$query,ifelse(is.na(md$MRSA[ix]),'',as.character(md$MRSA[ix])),'')
# Hard gate: an unmatched level would silently become NA and drop the row's colour.
# A cell is empty ONLY when the strain's own collection/BioSample record was checked and
# carries no such field (see METADATA_GAP_RESOLUTIONS_2026-09-14.tsv for the per-strain
# receipt). Empty becomes NA so it renders as a blank cell with no legend entry -- a
# pseudo-category like 'Not recorded' would read as a finding rather than an absence.
d$source_cat[!nzchar(d$source_cat)]<-NA;d$geo[!nzchar(d$geo)]<-NA
n_blank_src<-sum(is.na(d$source_cat));n_blank_geo<-sum(is.na(d$geo))
stopifnot(all(d$source_cat[!is.na(d$source_cat)]%in%names(source_palette)),all(d$geo[!is.na(d$geo)]%in%names(geo_palette)))
n<-Ntip(tr);xmax<-max(p$data$x);nd<-p$data[!p$data$isTip & nzchar(p$data$label) & p$data$label!='Root',]
p<-p+geom_segment(data=d,aes(x=x,xend=xmax*1.014,y=y,yend=y),linetype=if(Sys.getenv('GG_LEADER')=='bold')'15' else 'dotted',linewidth=if(Sys.getenv('GG_LEADER')=='bold').9 else .16,lineend='round',colour=if(Sys.getenv('GG_LEADER')=='bold')'grey55' else 'grey75')+geom_treescale(x=0,y=0,width=max(.02,signif(xmax/5,1)),fontsize=3)+scale_x_continuous(limits=c(0,xmax*1.02),expand=c(0,0))+ylim(-.7,n+.7)+theme(plot.margin=margin(5,0,5,12))
nd<-nd[!is.na(suppressWarnings(as.numeric(nd$label))) & suppressWarnings(as.numeric(nd$label))>=70,];if(nrow(nd))p<-p+geom_text(data=nd,aes(x=x,y=y,label=label),size=2.5,hjust=ifelse(nd$x>xmax*.82,1.08,-.10),vjust=-.35,colour='#4b5563')
d$plot_label<-vapply(d$text,function(z){m<-regexpr("^[A-Z][a-z]+ (?:sp\\.|[a-z]+)",z,perl=TRUE);if(m[1]<0)return(encodeString(z,quote='"'));k<-attr(m,'match.length');paste0('italic(',encodeString(substr(z,1,k),quote='"'),')~',encodeString(trimws(substring(z,k+1)),quote='"'))},character(1))
q<-ggplot(d,aes(x=0,y=y))+geom_text(aes(label=plot_label,colour=query),parse=TRUE,hjust=0,size=3.5)+scale_colour_manual(values=c('FALSE'=Sys.getenv('GG_REF_COLOUR','#202124'),'TRUE'=focal_colour),guide='none')+scale_x_continuous(limits=c(0,1),expand=c(0,0))+ylim(-.7,n+.7)+theme_void()+theme(plot.margin=margin(5,4,5,3))
# Strip renderer, mirroring the shared EPA-ng mk(): palette subset to the values actually present,
# so the legend lists this panel's categories only.
mk<-function(field,title,pal){ggplot(d[!is.na(d[[field]]),,drop=FALSE],aes(x=0,y=y,fill=.data[[field]]))+geom_tile(width=.85,height=.96,colour='white',linewidth=.4)+scale_fill_manual(values=pal[sort(unique(stats::na.omit(d[[field]])))],name=title,na.translate=FALSE)+ylim(-.7,n+.7)+theme_void()+labs(title=title)+theme(plot.title=element_text(size=9,hjust=.5),legend.position='bottom',legend.text=element_text(size=8),legend.title=element_text(size=9),plot.margin=margin(5,1,5,1))+guides(fill=guide_legend(ncol=4))}
txt<-function(field,title,size=3.7,bold=FALSE){ggplot(d,aes(x=0,y=y))+geom_text(aes(label=.data[[field]]),size=size,fontface=if(bold)'bold'else'plain')+scale_x_continuous(limits=c(-.5,.5),expand=c(0,0))+ylim(-.7,n+.7)+theme_void()+labs(title=title)+theme(plot.title=element_text(size=9,hjust=.5,face=if(bold)'bold'else'plain'),plot.margin=margin(5,1,5,1))}
genus<-sub('_(EXPANDED|DEDUP|AS[0-9]+)$','',sub('^GTR-[0-9]+-','',panel_id));genus_title<-tools::toTitleCase(tolower(genus))
inp<-grep('^Input data:',lines,value=TRUE)[1];sites<-sub('.* with ([0-9]+) amino-acid sites.*','\\1',inp)
caption<-sprintf('GToTree 2.0.0 phylogeny using the explicit 138-profile Actinobacteria HMM. %d genomes; %s aligned amino-acid sites. IQ-TREE 3.1.3 selected %s with 1,000 ultrafast bootstrap replicates; node labels show UFBoot support of 70%% or higher; lower percentages are omitted. Branch lengths are substitutions per aligned amino-acid site. Rooted on the previously designated outgroup. Colour strips show the assigned isolation-source category and geographic region, drawn from the shared source/geography colour registry used across the EPA-ng and GToTree figure families. Marine and named-ocean samples are displayed together as Marine. %s The verbatim as-deposited isolation source for every tip is provided in the accompanying supplement table rather than in the figure. SCG completeness and redundancy are provided in the accompanying genome QC tables.',n,sites,model,sprintf('A blank colour cell means that strain\'s own culture-collection or BioSample record was checked and carries no such field; it is a verified absence, not an unchecked cell, and the per-strain receipt is in METADATA_GAP_RESOLUTIONS_2026-09-14.tsv. This panel has %d blank isolation-source and %d blank geography cells.',n_blank_src,n_blank_geo))
pdf(NULL);label_inches<-max(vapply(d$text,function(z)grid::convertWidth(grid::grobWidth(grid::textGrob(z,gp=grid::gpar(fontsize=3.5*72.27/25.4))),'inches',valueOnly=TRUE),numeric(1)))+.4;dev.off()
widths<-c(6.5,label_inches,.8,.8,.9,.9)
fig<-(p+q+mk('source_cat','Isolation\nsource',source_palette)+mk('geo','Geography',geo_palette)+txt('candida','Candida\nInhibition',if(isTRUE(any(nchar(as.character(d$candida))>2,na.rm=TRUE)))3.4 else 4.8,TRUE)+txt('mrsa','MRSA\ninhibition',if(isTRUE(any(nchar(as.character(d$mrsa))>2,na.rm=TRUE)))3.4 else 4.8,TRUE)+plot_layout(widths=widths,guides='collect'))+plot_annotation(title=paste0(panel_id,' - ',genus_title,' core-genome phylogeny'),subtitle=if(variant=='experiment_id')'Experiment/sample identifiers shown where bound in the owner supplemental table' else 'Concise labels; experiment-ID companion supplied',theme=theme(plot.title=element_text(size=16,face='bold'),plot.subtitle=element_text(size=10)))
cap_chars<-max(90,floor(sum(widths)*13))
cap_txt<-paste(strwrap(caption,width=cap_chars),collapse='\n')
cap_lines<-length(strsplit(cap_txt,'\n')[[1]])
fig<-fig+plot_annotation(caption=cap_txt,theme=theme(plot.caption=element_text(size=7.2,hjust=0,lineheight=1.15,colour='#333333',margin=margin(t=8))))
fig<-fig&theme(legend.position='bottom');stem<-paste0(panel_id,'_SET2_REVIEW_R03_COLOR_',variant);height<-max(8,2.5+n*.34)+cap_lines*.135;width<-sum(widths)+.4
ggsave(paste0(stem,'.pdf'),fig,width=width,height=height,limitsize=FALSE);ggsave(paste0(stem,'.png'),fig,width=width,height=height,dpi=220,limitsize=FALSE)
write.table(data.frame(tip=d$label,y=d$y,label=d$text,query=d$query,genome_role=d$class,source_deposited=d$source,source_category=d$source_cat,source_colour=unname(source_palette[d$source_cat]),geography=d$geo,geography_colour=unname(geo_palette[d$geo]),Candida=d$candida,MRSA=d$mrsa),paste0(stem,'_display_audit.tsv'),sep='\t',quote=FALSE,row.names=FALSE)
writeLines(caption,paste0(stem,'_caption.txt'))
# Supplement table: the verbatim as-deposited detail removed from the figure, so nothing is lost.
# This is the artifact the caption points a reader to (supplement / Zenodo).
sup<-data.frame(tip=d$label,display_label=d$text,role=ifelse(d$query,'Owner query','Reference'),genome_role=d$class,
  isolation_source_as_deposited=d$source,source_category_displayed=d$source_cat,
  source_category_registry=md$source_category[ix],geography_displayed=d$geo,
  geography_registry=md$geography_display[ix],stringsAsFactors=FALSE)
sup<-sup[order(-d$y),]
write.table(sup,paste0(panel_id,'_SUPPLEMENT_source_and_geography_as_deposited.tsv'),sep='\t',quote=FALSE,row.names=FALSE)
cat(sprintf('[geometry] tree %.2f in of %.2f in total = %.1f%%\n',6.5,width,100*6.5/width))
