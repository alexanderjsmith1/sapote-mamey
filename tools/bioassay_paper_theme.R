# Shared bundle theme and export for the paper bioassay candidate renderers.
suppressPackageStartupMessages({library(ggplot2);library(ggtext);library(jsonlite);library(dplyr);library(tidyr)})
cfg <- jsonlite::fromJSON(Sys.getenv("BIOASSAY_CONFIG"))
source(cfg$theme)
source(file.path(dirname(cfg$theme), "sapote_stamp_required.R"))
d <- read.delim(cfg$data, check.names=FALSE, stringsAsFactors=FALSE, na.strings="")
PT <- 8 / ggplot2::.pt
pal <- unlist(cfg$palette)
prof <- cfg$profile   # collection display rules from mamey/data/bioassay_layouts.json (or --layout-config)
TITLE_COL <- if (isTRUE(prof$axis_title_ink)) PUB_INK else PUB_SUB   # axis_title_ink: plain ink axis titles
house <- function() theme_pub(base=9) + theme(text=element_text(size=8),
  axis.text=element_text(size=8),axis.text.x.bottom=element_markdown(size=8),axis.text.y.left=element_markdown(size=8),
  axis.title=element_text(size=8,colour=TITLE_COL),axis.title.x=element_text(size=8,colour=TITLE_COL),axis.title.y=element_text(size=8,colour=TITLE_COL),
  strip.text=element_text(size=8),strip.text.x=element_text(size=8),strip.text.y=element_text(size=8),
  legend.text=element_markdown(size=8),legend.title=element_text(size=8),legend.position="bottom",
  panel.grid.minor=element_blank(),plot.margin=margin(8,10,8,8),legend.box="vertical",
  legend.key.spacing.y=unit(4,"pt"),legend.key.spacing.x=unit(5,"pt"))

genlab <- function(x) ifelse(x=="Unassigned",prof$unassigned_label,ifelse(x %in% c("Other genera",prof$plain_rows),x,paste0("<i>",x,"</i>")))
save_candidate <- function(p,w,h) {
  ggsave(paste0(cfg$stem,".png"),p,width=w,height=h,dpi=600,bg="white")
  ggsave(paste0(cfg$stem,".svg"),p,width=w,height=h,bg="white",device=svglite::svglite)
  .pub_pdf(p,paste0(cfg$stem,".pdf"),w,h)
  sapote_stamp_files_required(paste0(cfg$stem,c(".png",".pdf",".svg")), paste0("bioassay_",tolower(cfg$kind)))
  writeLines(jsonlite::toJSON(list(width_in=w,height_in=h,minimum_text_pt=8,dpi=600),auto_unbox=TRUE),paste0(cfg$stem,"_PRINT_SIZE.json"))
}
