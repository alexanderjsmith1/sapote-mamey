source(Sys.getenv("BIOASSAY_THEME"))
d$group <- factor(d$group,levels=rev(cfg$groups))
d$target <- factor(d$target,levels=unique(d$target))
d$material <- factor(d$material,levels=c("Crude extract","Fraction"),labels=c("Crude extracts","Fractions"))
d$block <- factor(d$block,levels=c("Human pathogen panel","Foulbrood"))
d$txt <- ifelse(!is.na(d$pct)&d$pct>=55,"white",PUB_INK)
tl <- function(x) {x <- sub("Foulbrood ","P. larvae\n",x); sub("Candida ","C. ",x)}
p <- ggplot(d,aes(target,group))+geom_tile(aes(fill=pct),colour="white",linewidth=.5)+
  geom_text(aes(label=label,colour=txt),size=PT,family=PUB_FONT)+scale_colour_identity()+
  facet_grid(material~block,scales="free_x",space="free_x",switch="y")+
  scale_x_discrete(labels=tl)+scale_fill_gradient(low="#EEF3F8",high="#1F4E79",limits=c(0,100),na.value="white",
  name="Isolates with strong activity",labels=function(x)paste0(x,"%"))+
  labs(x=NULL,y=prof$group_axis_label)+house()+
  guides(fill=guide_colourbar(direction="horizontal",
    theme=theme(legend.title.position="top",
      legend.key.width=unit(min(2.5,prof$a02_width_in-1.4),"in"),
      legend.key.height=unit(.14,"in"))))+
  theme(panel.grid=element_blank(),strip.placement="outside",axis.text.x=element_text(size=8,angle=30,hjust=1),
    axis.text.x.bottom=element_markdown(size=8,angle=30,hjust=1),legend.justification="center")
p$theme$legend.text <- element_text(size=8,family=PUB_FONT)
save_candidate(p,prof$a02_width_in,3.8)
