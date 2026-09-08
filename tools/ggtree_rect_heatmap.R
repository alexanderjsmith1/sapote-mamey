#!/usr/bin/env Rscript
# ggtree_rect_heatmap.R — rectangular phylogram + aligned dotted tip labels + isolation-source heatmap
# strips (coarse Category + fine Source), focal-strain highlight, and a tree-scale bar. The "rect2" mode:
# for a FULL cohort/reference tree annotated with host/isolation metadata (distinct from the placement
# figure, which is for a single query set). Uses aplot to align two independently-coloured strips to the
# tree tips — no ggnewscale dependency.
#
# Usage:
#   Rscript ggtree_rect_heatmap.R <tree.nwk> <metadata.tsv> <out_prefix> [focal_csv]
# metadata.tsv columns (tab): tip, label, category, source   (tip must match a tree tip label;
#   label = the text to show; category = coarse class; source = fine host/isolation source)
# focal_csv: optional comma-separated tips to red-highlight (e.g. <focal_tip1>,<focal_tip2>).
#
# Emits <out_prefix>.pdf and <out_prefix>.png. Claim-safety: metadata is descriptive context; a colour
# is not a tested host association; judgment deferred.

suppressPackageStartupMessages({
  library(ape); library(ggtree); library(ggplot2); library(aplot); library(treeio); library(patchwork)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) stop("Usage: ggtree_rect_heatmap.R <nwk> <metadata.tsv> <out_prefix> [focal_csv]")
nwk <- args[1]; tsv <- args[2]; out <- args[3]
focal <- if (length(args) >= 4 && nzchar(args[4])) strsplit(args[4], ",")[[1]] else character(0)

tr <- read.tree(nwk)
md <- read.delim(tsv, sep = "\t", quote = "", stringsAsFactors = FALSE, check.names = FALSE)
for (c in c("tip", "label", "category", "source")) if (!c %in% names(md)) md[[c]] <- NA
md$disp <- ifelse(is.na(md$label) | md$label == "", md$tip, md$label); md$label <- NULL
md <- md[md$tip %in% tr$tip.label, , drop = FALSE]
norm <- function(z) toupper(gsub("[-_ ]","",z)); md$focal <- norm(md$tip) %in% norm(focal)
n <- length(tr$tip.label)

# fixed coarse-category palette (matches the reference figure); fallback grey for anything unlisted
cat_pal <- c("soil" = "#7a5230", "soil/rock" = "#b08d57", "plant" = "#2ca02c",
             "lichen" = "#66c2a5", "marine" = "#4aa3c7", "insect-associated" = "#8856a7",
             "clinical/animal" = "#d94801")
src_vals <- sort(unique(md$source[!is.na(md$source) & md$source != ""]))
# stable fine-source palette: a fixed set recycled deterministically
base_cols <- c("#f4a6a0","#d6d64a","#c5b0d5","#808000","#ffd8a8","#d9d9d9","#2ca25f","#f5c2f5",
               "#3a7d3a","#4aa3c7","#a6e6e6","#a1d99b","#c8b89a","#8B0000","#e6842a","#111111",
               "#f7e08a","#dcb0f2","#7fb069","#b5651d","#6a51a3","#e7298a","#66c2a5","#fc8d62")
src_pal <- setNames(base_cols[((seq_along(src_vals) - 1) %% length(base_cols)) + 1], src_vals)

# base tree: rectangular, ladderized, aligned dotted labels, tree-scale bar
lsize <- if (n > 120) 1.7 else if (n > 60) 2.0 else 2.4
# Label offset. `offset` is in TREE UNITS (substitutions/site), so a hardcoded value is wrong at
# every scale but one: on the Actinacidiphila rect2 trees (max depth 0.050-0.056) the previous
# constant 0.01 was 18-20 PERCENT of the whole tree depth, while on a deep backbone such as
# Nocardioides (depth ~1.0) the same constant is ~1 percent and invisible. Derive it from the tree.
xr      <- max(ape::node.depth.edgelength(tr), na.rm = TRUE)
lab_off <- 0.02 * xr

p <- ggtree(tr, size = 0.3, ladderize = TRUE) %<+% md +
  geom_tiplab(aes(label = ifelse(focal, NA, disp)), align = TRUE, linetype = "dotted", linesize = 0.2,
              size = lsize, offset = lab_off) +
  ggtree::hexpand(0.38)
# focal highlight: red-filled label box on the focal tips
if (any(md$focal)) {
  p <- p + geom_tiplab(aes(label = ifelse(focal, disp, NA)), align = TRUE,
                       linetype = NA, linesize = 0, colour = "#c00000",
                       fontface = "bold", size = lsize, offset = lab_off, na.rm = TRUE)
}

# order metadata by tree tip order for the strips
tip_order <- rev(ggtree::get_taxa_name(p))
mk_strip <- function(col, pal, title) {
  d <- data.frame(tip = md$tip, val = md[[col]], stringsAsFactors = FALSE)
  d$tip <- factor(d$tip, levels = tip_order)
  ggplot(d, aes(x = 0, y = tip, fill = val)) +
    geom_tile(width = 1, height = 1) +
    scale_fill_manual(values = pal, na.value = "#eeeeee", name = title, drop = FALSE) +
    theme_void() + theme(legend.key.size = unit(3.4, "mm"), legend.text = element_text(size = 6),
                         legend.title = element_text(size = 7))
}
s_cat <- mk_strip("category", cat_pal, "Isolation source")
s_src <- mk_strip("source",   src_pal, "Strain class")

combined <- s_src |> insert_left(s_cat, width = 1) |> insert_left(p, width = 13)

h <- max(5, 0.14 * n + 1.5); w <- 12
# GG_METHODS: methods block below the whole figure on the same page (croppable). Stacked via patchwork.
mth <- Sys.getenv("GG_METHODS")
final <- combined; h_total <- h
if (nzchar(mth)) {
  mthw <- paste(strwrap(mth, width = 125), collapse = "\n")
  nlines <- length(strsplit(mthw, "\n")[[1]])
  cap <- ggplot() +
    annotate("text", x = 0, y = 1, label = mthw, hjust = 0, vjust = 1, size = 3.6, colour = "grey20", lineheight = 1.2) +
    scale_x_continuous(limits = c(0, 1), expand = c(0, 0)) +
    scale_y_continuous(limits = c(0, 1), expand = c(0, 0)) +
    theme_void() + theme(plot.margin = margin(2, 6, 2, 6))
  caph <- 0.30 * nlines + 0.6
  final <- aplot::as.patchwork(combined) / cap + patchwork::plot_layout(heights = c(h, caph))
  h_total <- h + caph
}
ggsave(paste0(out, ".pdf"), final, width = w, height = h_total, limitsize = FALSE)
ggsave(paste0(out, ".png"), final, width = w, height = h_total, dpi = 200, limitsize = FALSE)
cat(sprintf("wrote %s.{pdf,png}  tips=%d focal=%d categories=%d sources=%d\n",
            out, n, sum(md$focal), length(unique(na.omit(md$category))), length(src_vals)))
