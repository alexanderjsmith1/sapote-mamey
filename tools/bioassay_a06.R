source(Sys.getenv("BIOASSAY_THEME"))
# A06: share of tested isolates with strong activity, by 16S genus group and target.
# The number tested sits under each bar (n_label); strong/tested above the bars only with --bar-labels.
d$group<-factor(d$group,levels=c("Streptomyces","Other genera","No 16S sequence"))
d$target<-factor(d$target,levels=c("Candida sp.","E. coli","MRSA","P. larvae"))
cols<-c(Streptomyces=pal['Streptomyces'],"Other genera"=cfg$fallback,"No 16S sequence"=pal['Unassigned'])
names(cols)<-levels(d$group)
target_lab<-c("Candida sp."="<i>Candida</i> sp.","E. coli"="<i>E. coli</i>","MRSA"="MRSA","P. larvae"="<i>P. larvae</i>")
group_lab<-c("Streptomyces"="<i>Streptomyces</i>","Other genera"="Other genera","No 16S sequence"=prof$unassigned_label)
N_Y<- -2    # n labels sit in a band below the zero line
dodge<-position_dodge(.82)
p<-ggplot(d,aes(target,pct,fill=group))+
 geom_col(position=dodge,width=.76,colour="white",linewidth=.3)+
 geom_text(aes(label=n_label,y=N_Y),position=dodge,vjust=1,size=PT,family=PUB_FONT,colour=PUB_INK)+
 scale_fill_manual(values=cols,labels=group_lab)+scale_x_discrete(labels=target_lab)+
 scale_y_continuous(limits=c(-8,100),breaks=seq(0,100,25),labels=function(x)paste0(x,"%"),expand=expansion(mult=c(0,.02)))+
 geom_hline(yintercept=0,colour="#C9CED6",linewidth=.3)+
 labs(x=NULL,y=paste0("Isolates with strong activity\n(≥80% inhibition, ",switch(cfg$material,"Fraction"="fractions","HPLC fraction"="HPLC fractions","crude extract"),")"),fill=NULL)+house()+
 theme(legend.position="top",panel.grid.major.x=element_blank(),legend.margin=margin(0,0,0,0),legend.box.spacing=unit(2,"pt"),axis.text.x.bottom=element_markdown(size=8,margin=margin(t=1)))+guides(fill=guide_legend(nrow=1))
if (isTRUE(cfg$bar_labels)) {
  p<-p+geom_text(aes(label=label,y=ifelse(is.na(pct),0,pct)+2),position=dodge,angle=90,hjust=0,size=PT,family=PUB_FONT)+
    scale_y_continuous(limits=c(-8,115),breaks=seq(0,100,25),labels=function(x)paste0(x,"%"),expand=c(0,0))
}
save_candidate(p,5.6,3.7)
