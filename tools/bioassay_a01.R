source(Sys.getenv("BIOASSAY_THEME"))
lev <- c("Strong (≥80%)","Moderate (50–79%)","Weak (25–49%)","Inactive (<25%)")
d$activity_class <- factor(d$activity_class,levels=lev)
# x axis: "count" draws isolates tested (linear or square root, below); "share" draws each row as 100% with strong / tested
# printed at its end, so rows of very different size read on one scale.
share <- identical(cfg$x_axis,"share")
ALL <- "All isolates"; OTHER <- "Other genera"
n_folded <- 0
if (share) {
  # genus rows with fewer than a01_share_min_isolates isolates draw as one "Other genera" row: a one-isolate row at 100%
  # strong would read as a strong genus. Group rows, plain rows and the unassigned row are never folded.
  min_n <- if (is.null(prof$a01_share_min_isolates)) 3L else as.integer(prof$a01_share_min_isolates)
  rs <- d %>% distinct(strain,row,genus) %>% group_by(row) %>%
    summarise(n=n(),is_genus=all(row==genus) & first(row)!="Unassigned" & !(first(row) %in% prof$plain_rows),.groups="drop")
  small <- rs$row[rs$is_genus & rs$n < min_n]
  n_folded <- length(small)
  d$row[d$row %in% small] <- OTHER
  d <- bind_rows(mutate(d,row=ALL),d)
}
if (share) {
  order <- d %>% filter(!row %in% c(ALL,OTHER,"Unassigned")) %>% distinct(strain,row) %>% count(row) %>% arrange(desc(n),row) %>% pull(row)
  order <- c(ALL,setdiff(order,prof$plain_rows),intersect(c(OTHER,"Unassigned"),unique(d$row)),intersect(prof$plain_rows,order))
} else {
  order <- d %>% distinct(strain,row) %>% count(row) %>% arrange(desc(n),row) %>% pull(row)
  order <- c(setdiff(order,prof$plain_rows),intersect(prof$plain_rows,order))
}
d$row <- factor(d$row,levels=rev(order))
rowlab <- function(x) ifelse(x==ALL,"<b>All isolates</b>",ifelse(x==OTHER,sprintf("Other genera (%d)",n_folded),genlab(x)))
# panel order: named species first, then the screens that recorded only "Candida", then the rest
tord <- c("C. albicans","C. auris","C. albicans or C. auris (not recorded)","Candida sp.")
d$target <- factor(d$target,levels=c(intersect(tord,unique(d$target)),setdiff(sort(unique(d$target)),tord)))
b <- d %>% count(target,row,activity_class,.drop=FALSE)
n <- d %>% count(target,row)
nt <- d %>% filter(!share | row!=ALL) %>% distinct(target,strain) %>% count(target)
strips <- as_labeller(setNames(gsub("\n","<br>",sp_md(paste0(sub(" or ","\nor ",sub(" \\(not recorded\\)","\n(not recorded)",nt$target)),"\n(",nt$n," isolates)"))),nt$target))
mat <- switch(cfg$material,"Fraction"="fractions","HPLC fraction"="HPLC fractions","crude extracts")
if (share) {
  st <- d %>% filter(activity_class==lev[1]) %>% count(target,row,name="strong")
  n <- n %>% left_join(st,by=c("target","row")) %>% mutate(strong=coalesce(strong,0L),lab=sprintf("%d / %d",strong,n))
  p <- ggplot(b,aes(x=n,y=row,fill=activity_class))+
    geom_col(position=position_fill(),width=.74,colour="white",linewidth=.15)+
    geom_text(data=n,aes(x=1.03,y=row,label=lab),inherit.aes=FALSE,hjust=0,size=PT,family=PUB_FONT)+
    # two lines, no wider than the counts under it: one line ran under the next panel and off the page
    annotate("text",x=1.03,y=length(order)+.62,label="strong /\ntested",hjust=0,vjust=0,lineheight=.9,size=PT,family=PUB_FONT,colour=PUB_SUB)+
    facet_wrap(~target,nrow=1,labeller=strips)+
    scale_fill_manual(values=setNames(c("#12355B","#4A7FB5","#9DBEDF","#E3E8EF"),lev),drop=FALSE)+
    scale_y_discrete(labels=rowlab)+
    scale_x_continuous(breaks=c(0,.25,.5,.75,1),labels=function(x) paste0(round(100*x),"%"),expand=c(0,0))+
    coord_cartesian(xlim=c(0,1),ylim=c(.5,length(order)+.5),clip="off")+
    labs(x=paste0("Share of isolates tested, ",mat),y=NULL,fill=NULL)+house()+
    theme(legend.position="top",panel.grid.major.y=element_blank(),panel.spacing.x=unit(52,"pt"))+
    guides(fill=guide_legend(nrow=2,byrow=TRUE))
  write.table(n %>% left_join(tidyr::pivot_wider(b,names_from=activity_class,values_from=n,values_fill=0),by=c("target","row")) %>%
                mutate(row=as.character(row),row_label=gsub("<[^>]+>","",rowlab(row))),
              paste0(cfg$stem,"_share_rows.tsv"),sep="\t",quote=FALSE,row.names=FALSE)
} else {
lin_axis <- max(n$n) <= 20   # linear when every row is small; see the axis below
p <- ggplot(b,aes(x=n,y=row,fill=activity_class))+geom_col(width=.74,colour="white",linewidth=.15)+
  geom_text(data=n,aes(x=n,y=row,label=n),inherit.aes=FALSE,hjust=-.25,size=PT,family=PUB_FONT)+
  facet_wrap(~target,nrow=1,labeller=strips)+
  scale_fill_manual(values=setNames(c("#12355B","#4A7FB5","#9DBEDF","#E3E8EF"),lev),drop=FALSE)+
  scale_y_discrete(labels=genlab)+
  # a square-root axis keeps a 100-isolate row and a 1-isolate row on one panel, but it squeezes the outer part of a
  # stacked bar: one strong isolate of three drew as a sixth of the bar (Attine Fig. 7A, the owner, 19 Oct: "is this
  # correct?"). Rows of 20 isolates or fewer are drawn on a linear axis, where every isolate has the same width.
  (if (lin_axis) list(scale_x_continuous(breaks=scales::breaks_pretty(n=4),expand=c(0,0)),
                      coord_cartesian(xlim=c(0,max(n$n)*1.18),expand=FALSE))
   else list(scale_x_continuous(breaks=c(1,10,25,50,100),expand=c(0,0)),
             coord_transform(x="sqrt",xlim=c(0,max(n$n)*1.5),expand=FALSE)))+
  labs(x=paste0("Isolates tested, ",mat,if (lin_axis) "" else " (square-root scale)"),y=NULL,fill=NULL)+house()+
  theme(legend.position="top",panel.grid.major.y=element_blank())+guides(fill=guide_legend(nrow=2,byrow=TRUE))
}
save_candidate(p,5.6,max(3.6,1.7+length(order)*.19))
