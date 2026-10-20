source(Sys.getenv("BIOASSAY_THEME"))
library(ggrepel)
shapes <- setNames(rep(c(21,24,22,23,25),length.out=length(cfg$groups)),cfg$groups)
d$label <- ifelse(d$genus!="Unassigned" & (cfg$material=="Fraction" | d$x>=10 | d$y>=10),d$strain,"")
suffix <- if(cfg$material=="Fraction")"fractions" else "crude extract"
p <- ggplot(d,aes(x,y,fill=genus))+
  geom_hline(yintercept=80,colour="#C9D0D9",linewidth=.3,linetype="dashed")+
  geom_vline(xintercept=80,colour="#C9D0D9",linewidth=.3,linetype="dashed")+
  geom_point(aes(shape=group),size=2,colour=PUB_INK,stroke=.35)+
  geom_text_repel(aes(label=label),size=PT,family=PUB_FONT,seed=11,max.overlaps=Inf,max.time=60,   # label settings follow tools/bioassay_a04.R (card 018c0f08_453_bioassay_a07_every_fraction_and_a03_genus_labels)
                  segment.colour=NA,segment.size=.25,min.segment.length=0,point.size=2,box.padding=.2,point.padding=.15)+
  scale_shape_manual(values=shapes,name="Source")+scale_fill_manual(values=pal,labels=genlab,name="Genus (16S rRNA)")+
  scale_x_continuous(limits=c(min(-5,d$x-4),max(112,d$x+4)),breaks=seq(0,100,25),labels=function(v)paste0(v,"%"))+
  scale_y_continuous(limits=c(min(-5,d$y-4),max(112,d$y+4)),breaks=seq(0,100,25),labels=function(v)paste0(v,"%"))+
  labs(x=paste("Best inhibition of Candida sp.,",suffix),y=paste("Best inhibition of MRSA,",suffix))+house()+
  guides(fill=guide_legend(ncol=3,byrow=TRUE,order=1,override.aes=list(shape=21)),shape=guide_legend(nrow=1,order=2))
if(!isTRUE(prof$a04_source_shape))p<-p+guides(shape="none")
save_candidate(p,7,5.8)
