source(Sys.getenv("BIOASSAY_THEME"))
if(!is.null(prof$a03_genus_keep)) {
  d$genus <- ifelse(d$genus %in% prof$a03_genus_keep,d$genus,"Other genera")
}
pal <- c(pal,"Other genera"=cfg$fallback)
shapes <- setNames(rep(c(21,24,22,23,25),length.out=length(cfg$groups)),cfg$groups)
p <- ggplot(d,aes(x,y,fill=genus))+
  geom_hline(yintercept=80,colour="#C9D0D9",linewidth=.3,linetype="dashed")+
  geom_vline(xintercept=80,colour="#C9D0D9",linewidth=.3,linetype="dashed")+
  geom_point(aes(shape=group),size=2,colour=PUB_INK,stroke=.35)+
  scale_shape_manual(values=shapes,name="Source")+scale_fill_manual(values=pal,labels=genlab,name="Genus (16S rRNA)")+
  scale_x_continuous(limits=c(min(-4,d$x-3),max(105,d$x+3)),breaks=seq(0,100,25),labels=function(v)paste0(v,"%"))+
  scale_y_continuous(limits=c(min(-4,d$y-3),max(105,d$y+3)),breaks=seq(0,100,25),labels=function(v)paste0(v,"%"))+
  labs(x="Best inhibition of P. larvae (either strain), crude extract",y="Best inhibition of MRSA, crude extract")+house()+
  guides(fill=guide_legend(ncol=3,byrow=TRUE,order=1,override.aes=list(shape=21)),shape=guide_legend(nrow=1,order=2))
if(!isTRUE(prof$a03_source_shape))p<-p+guides(shape="none")
save_candidate(p,5.6,prof$a03_height_in)
