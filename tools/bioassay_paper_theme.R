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
  axis.title=element_markdown(size=8,colour=TITLE_COL),axis.title.x=element_markdown(size=8,colour=TITLE_COL),axis.title.y=element_markdown(size=8,colour=TITLE_COL),
  strip.text=element_markdown(size=8),strip.text.x=element_markdown(size=8),strip.text.y=element_markdown(size=8),
  legend.text=element_markdown(size=8),legend.title=element_text(size=8),legend.position="bottom",
  panel.grid.minor=element_blank(),plot.margin=margin(8,10,8,8),legend.box="vertical",
  legend.key.spacing.y=unit(4,"pt"),legend.key.spacing.x=unit(5,"pt"))

# Species names in strip titles and axis titles are italic (Candida, C. albicans, C. auris, E. coli, P. larvae); plain strings in, markdown out.
sp_md <- function(x) gsub("\\b(C\\. albicans|C\\. auris|E\\. coli|P\\. larvae)\\b","<i>\\1</i>",gsub("Candida","<i>Candida</i>",x))
genlab <- function(x) ifelse(x=="Unassigned",prof$unassigned_label,ifelse(x %in% c("Other genera",prof$plain_rows) | grepl("aceae( bacterium)?$",x),x,paste0("<i>",x,"</i>")))
PRINT_WIDTH_IN <- 7.2    # DOUBLE_COLUMN publication width (docs/FIGURE_STYLE.md, "Publication artwork gate")
# A collection's print_width_in (bioassay_layouts.json) is the text column its paper places figures in, so 8 pt text
# prints at 8 pt; a 7.2 in figure placed in a 6.0 in column printed its text near 6.7 pt (the owner, 19 Oct, ruling 155).
if (!is.null(prof$print_width_in)) PRINT_WIDTH_IN <- as.numeric(prof$print_width_in)
EDGE_IN <- 0.15          # white space kept on every side; equal left and right, so the content is centered
.ink_margins <- function(file) {   # white space (inches at the probe resolution) around everything drawn
  a <- png::readPNG(file); ink <- (a[,,1] < .995) | (a[,,2] < .995) | (a[,,3] < .995)   # any non-white pixel: the palest heat-map tile (#EEF3F8) is lighter than 0.92 and was left out
  cols <- which(colSums(ink) > 0); rows <- which(rowSums(ink) > 0)
  c(t=min(rows) - 1, r=ncol(a) - max(cols), b=nrow(a) - max(rows), l=min(cols) - 1)
}
save_candidate <- function(p,w,h) {
  # Every panel is saved at the house double-column width. The plot margins are set so the drawn content
  # (axis labels, legends, strips, bar counts) sits EDGE_IN from each side of the page: three probe renders
  # measure the white space, and the margins are corrected by the difference.
  w <- PRINT_WIDTH_IN; dpi <- 150; mar <- c(t=8, r=10, b=8, l=8)
  for (i in 1:3) {
    probe <- tempfile(fileext=".png")
    ggsave(probe, p + theme(plot.margin=margin(mar["t"],mar["r"],mar["b"],mar["l"])), width=w, height=h, dpi=dpi, bg="white")
    m <- .ink_margins(probe) / dpi * 72.27; unlink(probe)   # points
    mar <- mar + (EDGE_IN * 72.27 - m)
  }
  p <- p + theme(plot.margin=margin(mar["t"],mar["r"],mar["b"],mar["l"]))
  ggsave(paste0(cfg$stem,".png"),p,width=w,height=h,dpi=600,bg="white")
  ggsave(paste0(cfg$stem,".svg"),p,width=w,height=h,bg="white",device=svglite::svglite)
  .pub_pdf(p,paste0(cfg$stem,".pdf"),w,h)
  sapote_stamp_files_required(paste0(cfg$stem,c(".png",".pdf",".svg")), paste0("bioassay_",tolower(cfg$kind)))
  writeLines(jsonlite::toJSON(list(width_in=w,height_in=h,minimum_text_pt=8,dpi=600,edge_in=EDGE_IN),auto_unbox=TRUE),paste0(cfg$stem,"_PRINT_SIZE.json"))
}
