#!/usr/bin/env Rscript
# class_signature_matrix.R — strain-by-class tile matrix of committed-step class tiers.
#
# Input: the matrix TSV written from `class-believability` output, one row per strain and class,
# with columns strain, block, class, best_tier, n_high, n_medium. best_tier is HIGH, MEDIUM, LOW,
# SUSPECT or none. Each tile is the strain's best region-level tier for that class; the number in a
# tile counts that strain's regions at HIGH or MEDIUM.
#
# Usage:
#   Rscript class_signature_matrix.R <matrix.tsv> <out_prefix> [profile] [title]
#
# Writes <out_prefix>.svg and <out_prefix>.png through sapote_save_pair(). Use a fresh folder.
# A tier reads the region's gene set; it does not name a product or show that one is made.

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) stop("usage: class_signature_matrix.R <matrix.tsv> <out_prefix> [profile] [title]")
in_tsv  <- args[[1]]
out_pre <- args[[2]]
profile <- if (length(args) >= 3) args[[3]] else "DOUBLE_COLUMN"
title   <- if (length(args) >= 4) args[[4]] else "Signature-enzyme class tiers per strain"

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
here <- if (length(script_arg)) dirname(normalizePath(sub("^--file=", "", script_arg[[1]]))) else "tools"
source(file.path(here, "sapote_figure_theme.R"))

for (f in c(paste0(out_pre, ".svg"), paste0(out_pre, ".png"))) {
  if (file.exists(f)) stop(sprintf("refusing to overwrite %s; use a fresh output folder", f))
}

d <- utils::read.delim(in_tsv, check.names = FALSE, stringsAsFactors = FALSE, na.strings = character())
need <- c("strain", "block", "class", "best_tier", "n_high", "n_medium")
miss <- setdiff(need, names(d))
if (length(miss)) stop(sprintf("%s: missing columns %s", in_tsv, paste(miss, collapse = ", ")))
tiers <- c("HIGH", "MEDIUM", "LOW", "SUSPECT", "none")
bad <- setdiff(unique(d$best_tier), tiers)
if (length(bad)) stop(sprintf("unknown best_tier value(s): %s", paste(bad, collapse = ", ")))

class_labels <- c(
  diketopiperazine_cdps = "DKP\n(CDPS)",
  lassopeptide          = "Lasso-\npeptide",
  lanthipeptide_class_i = "Lanthi-\npeptide I",
  thioamitide           = "Thio-\namitide",
  phenazine             = "Phen-\nazine",
  polyene_mycosamine    = "Polyene\n(myco-\nsamine)",
  aminocyclitol         = "Amino-\ncyclitol",
  nis_siderophore       = "NIS\nsidero-\nphore",
  butyrolactone         = "Butyro-\nlactone",
  melanin               = "Mela-\nnin",
  ectoine               = "Ectoine",
  phosphonate           = "Phos-\nphonate"
)
cls_order <- intersect(names(class_labels), unique(d$class))
extra <- setdiff(unique(d$class), cls_order)
cls_order <- c(cls_order, sort(extra))
lab <- ifelse(cls_order %in% names(class_labels), class_labels[cls_order], cls_order)
d$class <- factor(d$class, levels = cls_order, labels = lab)

# Strains keep the file's row order inside each block (top to bottom).
d$strain <- factor(d$strain, levels = rev(unique(d$strain)))
d$block  <- factor(d$block, levels = unique(d$block))  # blocks in file order
d$best_tier <- factor(d$best_tier, levels = tiers,
                      labels = c("HIGH", "MEDIUM", "LOW (gateway only)", "SUSPECT (label, no gateway)", "none"))
n_hm <- d$n_high + d$n_medium
d$label <- ifelse(n_hm > 0, as.character(n_hm), "")

# Colours: theme constants. HIGH and MEDIUM use the palette's two blues, LOW the grid grey, SUSPECT
# the accent, none is blank.
fills <- c("HIGH" = SAPOTE_COHORT_PALETTE[["BEE"]], "MEDIUM" = SAPOTE_COHORT_PALETTE[["WASP"]],
           "LOW (gateway only)" = SAPOTE_GRID, "SUSPECT (label, no gateway)" = SAPOTE_ACCENT,
           "none" = "#FFFFFF")
d$text_col <- ifelse(d$best_tier == "HIGH", "#FFFFFF", SAPOTE_INK)

p <- ggplot2::ggplot(d, ggplot2::aes(x = class, y = strain, fill = best_tier)) +
  ggplot2::geom_tile(colour = SAPOTE_GRID, linewidth = 0.3) +
  ggplot2::geom_text(ggplot2::aes(label = label, colour = text_col), size = 8 / ggplot2::.pt) +
  ggplot2::scale_colour_identity() +
  ggplot2::scale_fill_manual(values = fills, drop = TRUE, name = NULL) +
  ggplot2::scale_x_discrete(position = "top") +
  ggplot2::facet_grid(block ~ ., scales = "free_y", space = "free_y",
                      labeller = ggplot2::label_wrap_gen(width = 14)) +
  ggplot2::labs(title = title, x = NULL, y = NULL) +
  sapote_theme(8) +
  sapote_no_grid() +
  ggplot2::theme(legend.position = "bottom", legend.direction = "horizontal",
                 strip.text.y = ggplot2::element_text(angle = 0, hjust = 0, size = 8),
                 legend.text = ggplot2::element_text(size = 8),   # the theme default is 0.8 x base
                 plot.title = ggplot2::element_text(size = 9, hjust = 0),
                 axis.text.x.top = ggplot2::element_text(size = 8, lineheight = 0.9),
                 panel.spacing.y = ggplot2::unit(4, "pt")) +
  ggplot2::guides(fill = ggplot2::guide_legend(nrow = 1, override.aes = list(colour = SAPOTE_INK, linewidth = 0.2)))

n_rows <- length(unique(d$strain))
height <- 0.165 * n_rows + 2.2
sapote_save_pair(p, out_pre, profile, height)
