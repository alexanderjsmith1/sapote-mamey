source(Sys.getenv("BIOASSAY_THEME"))
lev <- c("Strong (≥80%)","Moderate (50–79%)","Weak (25–49%)","Inactive (<25%)")
d$activity_class <- factor(d$activity_class,levels=lev)
order <- d %>% distinct(strain,row) %>% count(row) %>% arrange(desc(n),row) %>% pull(row)
order <- c(setdiff(order,prof$plain_rows),intersect(prof$plain_rows,order))
d$row <- factor(d$row,levels=rev(order))
# panel order: named species first, then the screens that recorded only "Candida", then the rest
tord <- c("C. albicans","C. auris","C. albicans or C. auris (not recorded)","Candida sp.")
d$target <- factor(d$target,levels=c(intersect(tord,unique(d$target)),setdiff(sort(unique(d$target)),tord)))
b <- d %>% count(target,row,activity_class,.drop=FALSE)
n <- d %>% count(target,row)
nt <- d %>% count(target)
p <- ggplot(b,aes(x=n,y=row,fill=activity_class))+geom_col(width=.74,colour="white",linewidth=.15)+
  geom_text(data=n,aes(x=n,y=row,label=n),inherit.aes=FALSE,hjust=-.25,size=PT,family=PUB_FONT)+
  facet_wrap(~target,nrow=1,labeller=as_labeller(setNames(paste0(sub(" or ","\nor ",sub(" \\(not recorded\\)","\n(not recorded)",nt$target)),"\n(",nt$n," isolates)"),nt$target)))+
  scale_fill_manual(values=setNames(c("#12355B","#4A7FB5","#9DBEDF","#E3E8EF"),lev),drop=FALSE)+
  scale_y_discrete(labels=genlab)+scale_x_continuous(breaks=c(1,10,25,50,100),expand=c(0,0))+
  coord_transform(x="sqrt",xlim=c(0,max(n$n)*1.5),expand=FALSE)+
  labs(x="Isolates tested, crude extracts (square-root scale)",y=NULL,fill=NULL)+house()+
  theme(legend.position="top",panel.grid.major.y=element_blank())+guides(fill=guide_legend(nrow=2,byrow=TRUE))
save_candidate(p,5.6,max(3.6,1.7+length(order)*.19))
