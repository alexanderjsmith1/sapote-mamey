source(Sys.getenv("BIOASSAY_THEME"))
library(ggrepel)
# A07: one point per fraction; best Candida (any species) against best MRSA. Each isolate with a fraction strong against both is labeled once.
shapes <- setNames(rep(c(21,24,22,23,25),length.out=length(cfg$groups)),cfg$groups)
# one label per isolate strong against both targets, on its fraction with the highest lower value of the two
d$score <- ifelse(d$x>=80 & d$y>=80, pmin(d$x,d$y), -Inf)
top <- ave(d$score, d$strain, FUN=max)
first <- !duplicated(paste(d$strain, d$score)) & d$score==top & is.finite(d$score)
d$label <- ifelse(first, paste(d$strain, d$fraction), "")
suffix <- switch(cfg$material,"HPLC fraction"="single HPLC fraction","single fraction")
p <- ggplot(d,aes(x,y,fill=genus))+
  geom_hline(yintercept=80,colour="#C9D0D9",linewidth=.3,linetype="dashed")+
  geom_vline(xintercept=80,colour="#C9D0D9",linewidth=.3,linetype="dashed")+
  geom_point(aes(shape=group),size=1.8,colour=PUB_INK,stroke=.3,alpha=.9)+
  geom_text_repel(aes(label=label),size=PT,family=PUB_FONT,seed=as.integer(Sys.getenv("BIOASSAY_A07_REPEL_SEED","11")),max.overlaps=Inf,max.time=120,segment.colour="#6B7483",
                  segment.size=.25,min.segment.length=0,point.size=1.8,box.padding=as.numeric(Sys.getenv("BIOASSAY_REPEL_PAD","1"))*.45,point.padding=as.numeric(Sys.getenv("BIOASSAY_REPEL_PAD","1"))*.3,force=6,max.iter=1e6)+
  scale_shape_manual(values=shapes,name=if(is.null(prof$group_axis_label))"Source" else prof$group_axis_label)+
  scale_fill_manual(values=pal,labels=genlab,name="Genus (16S rRNA)")+
  scale_x_continuous(limits=c(min(-5,d$x-4),max(as.numeric(Sys.getenv("BIOASSAY_A07_XMAX","112")),d$x+4)),breaks=seq(0,100,25),labels=function(v)paste0(v,"%"))+
  scale_y_continuous(limits=c(min(-5,d$y-4),max(112,d$y+4)),breaks=seq(0,100,25),labels=function(v)paste0(v,"%"))+
  labs(x=sp_md(paste0("Best inhibition of ",if(is.null(prof$a04_candida_axis_label))"Candida sp." else prof$a04_candida_axis_label,", ",suffix)),
       y=paste("Best inhibition of MRSA,",suffix))+house()+
  guides(fill=guide_legend(ncol=3,byrow=TRUE,order=1,override.aes=list(shape=21)),shape=guide_legend(nrow=1,order=2))
if(!isTRUE(prof$a04_source_shape))p<-p+guides(shape="none")
save_candidate(p,7,6)
