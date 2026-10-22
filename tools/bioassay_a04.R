source(Sys.getenv("BIOASSAY_THEME"))
library(ggrepel)
shapes <- setNames(rep(c(21,24,22,23,25),length.out=length(cfg$groups)),cfg$groups)
lab_mode <- if (is.null(prof$a04_point_labels)) "all" else prof$a04_point_labels
d$label <- switch(lab_mode,
  all = ifelse(d$genus!="Unassigned" & (cfg$material=="Fraction" | d$x>=10 | d$y>=10),d$strain,""),
  strong = ifelse(d$x>=80 & d$y>=80,d$strain,""),     # strong (>=80%) against both targets; leader lines below
  either = ifelse(d$x>=80 | d$y>=80,d$strain,""),     # card 472 (owner, 21 Oct, Attine Fig. S19: "the long arrows are very awkward"): strong against either target
  none = rep("",nrow(d)),
  nonzero = ifelse(d$x>0 | d$y>0,d$strain,""),    # every isolate not at 0% against both targets, any genus
  stop("a04_point_labels must be all, strong, either, nonzero or none"))
# a04_label_max (card 472; owner, 21 Oct, Moss Fig. S10a: "omit 4 of them and state that the full data is in a table"):
# when more points qualify for a label, keep the ones strongest against both targets (highest of the two lower values,
# then the higher, then strain), and say how many were labelled; the full list is in the paper's table.
if (!is.null(prof$a04_label_max)) {
  k <- which(d$label != "")
  if (length(k) > as.integer(prof$a04_label_max)) {
    keep <- k[order(-pmin(d$x[k], d$y[k]), -pmax(d$x[k], d$y[k]), d$strain[k])][seq_len(as.integer(prof$a04_label_max))]
    d$label[setdiff(k, keep)] <- ""
    message(sprintf("a04 labels: %d of %d qualifying points labelled (a04_label_max)", length(keep), length(k)))
  }
}
suffix <- switch(cfg$material,"Fraction"="fractions","HPLC fraction"="HPLC fractions","crude extract")
# a04_point_size / a04_text_pt / a04_axis_ticks (bioassay_layouts.json): a collection with few isolates can draw larger
# points and text and an axis line with tick marks (the owner, 19 Oct, Attine Figs. S4a/S4b: "make the data points and text
# much larger ... the x-axis needs that '-'"). Defaults keep the earlier drawing.
PSIZE <- if (is.null(prof$a04_point_size)) 2 else as.numeric(prof$a04_point_size)
TPT <- if (is.null(prof$a04_text_pt)) 8 else as.numeric(prof$a04_text_pt)
# a04_label_column: labels of the crowded low corner (both values under 35%) are set in one column in the empty space
# to the right, sorted by height, each with a leader line, instead of being repelled; with larger text the repelled
# labels touched there and their positions changed from run to run (Attine Fig. S4a, 19 Oct).
lcol <- NULL
if (isTRUE(prof$a04_label_column)) {
  crowd <- d$label != "" & d$x < 35 & d$y < 35
  if (sum(crowd) >= 4) {   # a column only helps a real crowd
    lcol <- d[crowd, c("x", "y", "label")]
    LX <- 45; slots <- seq(-4, 48, length.out = nrow(lcol))
    # order the column so the leader lines cross as little as possible: try a range of common slopes, sort the points
    # by where a line of that slope from each point meets the column, and keep the order with the fewest crossings
    crossings <- function(o) {
      a <- lcol[o, ]; a$ly <- slots; n <- 0
      for (i in seq_len(nrow(a) - 1)) for (j in (i + 1):nrow(a)) {
        # segments (x,y)->(LX,ly); they cross if their vertical order flips between the right-most start and LX
        x0 <- max(a$x[i], a$x[j])
        yi <- a$y[i] + (a$ly[i] - a$y[i]) * (x0 - a$x[i]) / (LX - a$x[i])
        yj <- a$y[j] + (a$ly[j] - a$y[j]) * (x0 - a$x[j]) / (LX - a$x[j])
        if (sign(yi - yj) != 0 && sign(yi - yj) != sign(a$ly[i] - a$ly[j])) n <- n + 1
      }
      n
    }
    best <- NULL; bestn <- Inf
    for (s in seq(-1, 3, by = 0.05)) {
      o <- order(lcol$y + s * (LX - lcol$x), lcol$x)
      k <- crossings(o)
      if (k < bestn) { bestn <- k; best <- o }
    }
    lcol <- lcol[best, ]; lcol$lx <- LX; lcol$ly <- slots
    d$label[crowd] <- ""
  }
}
p <- ggplot(d,aes(x,y,fill=genus))+
  geom_hline(yintercept=80,colour="#C9D0D9",linewidth=.3,linetype="dashed")+
  geom_vline(xintercept=80,colour="#C9D0D9",linewidth=.3,linetype="dashed")+
  geom_point(aes(shape=group),size=PSIZE,colour=PUB_INK,stroke=.35)+
  # leader lines and wider spacing for the labelled subsets, so a label in a cluster points at its own point
  geom_text_repel(aes(label=label),size=TPT/ggplot2::.pt,family=PUB_FONT,seed=as.integer(Sys.getenv("BIOASSAY_REPEL_SEED","11")),max.overlaps=Inf,max.time=60,
                  segment.colour=if(lab_mode %in% c("strong","either","nonzero"))"#6B7483" else NA,segment.size=.25,min.segment.length=0,point.size=PSIZE,   # point.size = the drawn point size, so labels clear the points
                  
                  box.padding=as.numeric(Sys.getenv("BIOASSAY_REPEL_PAD","1"))*(if(lab_mode %in% c("strong","nonzero")).5 else .2)*TPT/8,point.padding=as.numeric(Sys.getenv("BIOASSAY_REPEL_PAD","1"))*if(lab_mode %in% c("strong","either","nonzero")).35 else .15,
                  force=(if(lab_mode %in% c("strong","nonzero"))3 else 1)*TPT/8,max.iter=if(lab_mode %in% c("strong","nonzero"))50000 else 10000)+
  scale_shape_manual(values=shapes,name=if(is.null(prof$group_axis_label))"Source" else prof$group_axis_label)+scale_fill_manual(values=pal,labels=genlab,name="Genus (16S rRNA)")+
  scale_x_continuous(limits=c(min(-5,d$x-4),max(112,d$x+4)),breaks=seq(0,100,25),labels=function(v)paste0(v,"%"))+
  scale_y_continuous(limits=c(min(-5,d$y-4),max(112,d$y+4)),breaks=seq(0,100,25),labels=function(v)paste0(v,"%"))+
  labs(x=paste0("Best inhibition of ",if(is.null(prof$a04_candida_axis_label))"Candida sp." else prof$a04_candida_axis_label,", ",suffix),y=paste("Best inhibition of MRSA,",suffix))+house()+
  guides(fill=guide_legend(ncol=if (TPT > 8) 2 else 3,byrow=TRUE,order=1,override.aes=list(shape=21)),shape=guide_legend(nrow=1,order=2))   # larger text: two legend columns fit the width
# a04_legend_compact (card 472; owner, 21 Oct, Moss Fig. S10b: "Try to get the Genus and Source group keys to take up 1 line
# each"): with this many genera or fewer, the genus key is one line with its title on the left, like the source key; with
# more, the title sits above the keys and the keys pack in four columns instead of spreading across the page.
if (!is.null(prof$a04_legend_compact)) {
  ng <- length(unique(d$genus))
  p <- p + guides(fill = if (ng <= as.integer(prof$a04_legend_compact))
                    guide_legend(nrow=1, title.position="left", order=1, override.aes=list(shape=21))
                  else guide_legend(ncol=4, byrow=TRUE, title.position="top", order=1, override.aes=list(shape=21)),
                  shape=guide_legend(nrow=1, title.position="left", order=2)) +
    theme(legend.box="vertical", legend.box.just="left")
}
if(!isTRUE(prof$a04_source_shape))p<-p+guides(shape="none")
if (TPT != 8) p <- p + theme(text=element_text(size=TPT),axis.text=element_text(size=TPT),
                             axis.text.x.bottom=element_markdown(size=TPT),axis.text.y.left=element_markdown(size=TPT),   # house() sets these by name
                             axis.title=element_text(size=TPT,colour=TITLE_COL),axis.title.x=element_text(size=TPT,colour=TITLE_COL),
                             axis.title.y=element_text(size=TPT,colour=TITLE_COL),
                             legend.text=element_markdown(size=TPT),legend.title=element_text(size=TPT))
if (!is.null(lcol)) {
  seg <- geom_segment(data=lcol,aes(x=x,y=y,xend=lx-1.2,yend=ly),inherit.aes=FALSE,colour="#6B7483",linewidth=.25)
  p$layers <- c(list(seg), p$layers)   # leader lines under the points
  p <- p + geom_text(data=lcol,aes(x=lx,y=ly,label=label),inherit.aes=FALSE,hjust=0,size=TPT/ggplot2::.pt,family=PUB_FONT)
}
if (isTRUE(prof$a04_axis_ticks)) p <- p + theme(axis.line=element_line(colour=PUB_INK,linewidth=.3),
                                                axis.ticks=element_line(colour=PUB_INK,linewidth=.3),axis.ticks.length=unit(3,"pt"))
if(isTRUE(prof$split_candida) && !isTRUE(prof$a04_pool_candida)) {   # a04_pool_candida: one Candida axis even when A01 splits
  d$target <- factor(d$target,levels=c("C. albicans","C. auris","C. albicans or C. auris (not recorded)"))
  p$data <- d
  p <- p + facet_wrap(~target,nrow=1,drop=FALSE,labeller=label_wrap_gen(width=22)) +
    labs(x=paste("Best inhibition,",suffix)) +
    theme(panel.spacing.x=unit(12,"pt"))
}
save_candidate(p,7,if (is.null(prof$a04_height_in)) 5.8 else as.numeric(prof$a04_height_in))   # a04_height_in: room for larger labels
