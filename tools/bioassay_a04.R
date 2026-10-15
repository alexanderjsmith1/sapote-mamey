source(Sys.getenv("BIOASSAY_THEME"))
library(ggrepel)
shapes <- setNames(rep(c(21,24,22,23,25),length.out=length(cfg$groups)),cfg$groups)
lab_mode <- if (is.null(prof$a04_point_labels)) "all" else prof$a04_point_labels
d$label <- switch(lab_mode,
  all = ifelse(d$genus!="Unassigned" & (cfg$material=="Fraction" | d$x>=10 | d$y>=10),d$strain,""),
  strong = ifelse(d$x>=80 & d$y>=80,d$strain,""),     # strong (>=80%) against both targets; leader lines below
  none = rep("",nrow(d)),
  nonzero = ifelse(d$x>0 | d$y>0,d$strain,""),    # every isolate not at 0% against both targets, any genus
  stop("a04_point_labels must be all, strong, nonzero or none"))
suffix <- if(cfg$material=="Fraction")"fractions" else "crude extract"
p <- ggplot(d,aes(x,y,fill=genus))+
  geom_hline(yintercept=80,colour="#C9D0D9",linewidth=.3,linetype="dashed")+
  geom_vline(xintercept=80,colour="#C9D0D9",linewidth=.3,linetype="dashed")+
  geom_point(aes(shape=group),size=2,colour=PUB_INK,stroke=.35)+
  # leader lines and wider spacing for the labelled subsets, so a label in a cluster points at its own point
  geom_text_repel(aes(label=label),size=PT,family=PUB_FONT,seed=11,max.overlaps=Inf,max.time=10,
                  segment.colour=if(lab_mode %in% c("strong","nonzero"))"#6B7483" else NA,segment.size=.25,min.segment.length=0,
                  box.padding=if(lab_mode %in% c("strong","nonzero")).5 else .2,point.padding=if(lab_mode %in% c("strong","nonzero")).35 else .15,
                  force=if(lab_mode %in% c("strong","nonzero"))3 else 1,max.iter=if(lab_mode %in% c("strong","nonzero"))50000 else 10000)+
  scale_shape_manual(values=shapes,name="Source")+scale_fill_manual(values=pal,labels=genlab,name="Genus (16S rRNA)")+
  scale_x_continuous(limits=c(min(-5,d$x-4),max(112,d$x+4)),breaks=seq(0,100,25),labels=function(v)paste0(v,"%"))+
  scale_y_continuous(limits=c(min(-5,d$y-4),max(112,d$y+4)),breaks=seq(0,100,25),labels=function(v)paste0(v,"%"))+
  labs(x=paste0("Best inhibition of ",if(is.null(prof$a04_candida_axis_label))"Candida sp." else prof$a04_candida_axis_label,", ",suffix),y=paste("Best inhibition of MRSA,",suffix))+house()+
  guides(fill=guide_legend(ncol=3,byrow=TRUE,order=1,override.aes=list(shape=21)),shape=guide_legend(nrow=1,order=2))
if(!isTRUE(prof$a04_source_shape))p<-p+guides(shape="none")
if(isTRUE(prof$split_candida) && !isTRUE(prof$a04_pool_candida)) {   # a04_pool_candida: one Candida axis even when A01 splits
  d$target <- factor(d$target,levels=c("C. albicans","C. auris","C. albicans or C. auris (not recorded)"))
  p$data <- d
  p <- p + facet_wrap(~target,nrow=1,drop=FALSE,labeller=label_wrap_gen(width=22)) +
    labs(x=paste("Best inhibition,",suffix)) +
    theme(panel.spacing.x=unit(12,"pt"))
}
save_candidate(p,7,5.8)
