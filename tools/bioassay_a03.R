source(Sys.getenv("BIOASSAY_THEME"))
label_genus <- identical(cfg$point_labels,"genus")   # --point-labels genus: every genus kept, every isolate with a 16S genus labeled
if(!is.null(prof$a03_genus_keep) && !label_genus) {
  d$genus <- ifelse(d$genus %in% prof$a03_genus_keep,d$genus,"Other genera")
}
pal <- c(pal,"Other genera"=cfg$fallback)
suffix <- switch(cfg$material,"Fraction"="fractions","HPLC fraction"="HPLC fractions","crude extract")
shapes <- setNames(rep(c(21,24,22,23,25),length.out=length(cfg$groups)),cfg$groups)
p <- ggplot(d,aes(x,y,fill=genus))+
  geom_hline(yintercept=80,colour="#C9D0D9",linewidth=.3,linetype="dashed")+
  geom_vline(xintercept=80,colour="#C9D0D9",linewidth=.3,linetype="dashed")+
  geom_point(aes(shape=group),size=2,colour=PUB_INK,stroke=.35)+
  # Every layer gets every point (unlabeled ones with an empty label) so each label avoids all points.
  # --point-labels genus: labels of points near the 0% MRSA row fan out in a band below the axis; the others sit next to
  # their points
  {if(label_genus) list(
     ggrepel::geom_text_repel(aes(label=ifelse(genus!="Unassigned" & y>=12, strain, "")), size=PT, family=PUB_FONT,
       seed=as.integer(Sys.getenv("BIOASSAY_REPEL_SEED","11")), max.overlaps=Inf, max.time=15, max.iter=1e6, point.size=3,   # 3 covers the drawn point and its outline
       box.padding=.4, point.padding=.05, force=12, force_pull=.15, min.segment.length=0, segment.colour="#6B7483", segment.size=.25),
     ggrepel::geom_text_repel(aes(label=ifelse(genus!="Unassigned" & y<12, strain, "")), size=PT, family=PUB_FONT,
       seed=11, direction="x", nudge_y=-14-0*0, ylim=c(-Inf,-9), angle=90, hjust=1, max.overlaps=Inf, max.time=4, max.iter=1e5,
       point.size=2, box.padding=.12, force=2, min.segment.length=0, segment.colour="#6B7483", segment.size=.25)) else NULL}+
  scale_shape_manual(values=shapes,name=if(is.null(prof$group_axis_label))"Source" else prof$group_axis_label)+scale_fill_manual(values=pal,labels=genlab,name="Genus (16S rRNA)")+
  scale_x_continuous(limits=c(min(-4,d$x-3),max(105,d$x+3)),breaks=seq(0,100,25),labels=function(v)paste0(v,"%"))+
  scale_y_continuous(limits=c(if(label_genus) -32 else min(-4,d$y-3),if(label_genus) 118 else max(105,d$y+3)),breaks=seq(0,100,25),labels=function(v)paste0(v,"%"))+
  labs(x=paste("Best inhibition of P. larvae (either strain),",suffix),y=paste("Best inhibition of MRSA,",suffix))+house()+
  guides(fill=guide_legend(ncol=3,byrow=TRUE,order=1,override.aes=list(shape=21)),shape=guide_legend(nrow=1,order=2))
if(!isTRUE(prof$a03_source_shape))p<-p+guides(shape="none")
save_candidate(p,5.6,if(label_genus) 8.2 else prof$a03_height_in)
