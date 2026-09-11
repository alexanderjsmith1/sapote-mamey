#!/usr/bin/env Rscript
# sapote_strain_figure.R — ggplot2 renderer for the per-strain 8-series figures.
#
# Sixteen figures ship a tidy `<strain>_8<x>_fig_<name>_data.csv` sidecar (with a leading
# `# provenance,...` banner line). Their schemas differ, but they reduce to five shapes:
#
#   RANKED_BAR   8d ab_ranked · 8e af_ranked · 8k novelty_ranked · 8n rggmci_rescue
#   COUNT_BAR    8g class_distribution · 8h cctt_map · 8j edge_composition · 8l kcb_anchors ·
#                8b composition (faceted by panel) · 8f funnel (stage-ordered)
#   SCATTER      8c dapr_scatter · 8g ab_af_panels
#   HISTOGRAM    8i length_hist
#   TABLE        8m genome_atlas · 8n two_pathway · 8a landscape (wide record table)
#
# Shape is chosen from the sidecar's own columns, so a schema change surfaces as a clear refusal
# rather than a mis-drawn figure.
#
# Usage:
#   Rscript sapote_strain_figure.R <..._data.csv> <out_prefix> [profile] [title]
#
# Claim-safety: AB/AF scores are capacity-level priors, not measured activity; novelty is
# reference-darkness, not proof of a new compound; a KCB anchor is similarity, not identity.

suppressPackageStartupMessages({
  library(ggplot2)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) stop("Usage: sapote_strain_figure.R <data.csv> <out_prefix> [profile] [title]")
data_csv   <- args[1]
out_prefix <- args[2]
profile    <- if (length(args) >= 3) toupper(args[3]) else "SINGLE_COLUMN"
title_arg  <- if (length(args) >= 4) args[4] else NA_character_

here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1]))
source(file.path(here, "sapote_figure_theme.R"))

# The banner is a real provenance record (`# provenance,Mamey deterministic ... KCB=similarity not
# identity`). Read it, keep it, and print it under the figure — dropping it would strip the ceiling
# statement the Python figure carries.
lines <- readLines(data_csv, warn = FALSE)
banner <- lines[startsWith(lines, "#")]
provenance <- if (length(banner)) sub("^#\\s*provenance,\\s*", "", banner[1]) else NA_character_

df <- utils::read.csv(text = paste(lines[!startsWith(lines, "#")], collapse = "\n"),
                      stringsAsFactors = FALSE, check.names = FALSE)
if (nrow(df) == 0) stop("sidecar has no rows")

stem  <- sub("_data$", "", tools::file_path_sans_ext(basename(data_csv)))
title <- if (!is.na(title_arg)) title_arg else gsub("_", " ", sub("^.*_8[a-z]+_fig_", "", stem))

num <- function(x) suppressWarnings(as.numeric(x))
has <- function(...) all(c(...) %in% names(df))

caption <- if (!is.na(provenance)) provenance else NULL

# ---- shape selection -----------------------------------------------------------------------------
if (has("rank") && ncol(df) >= 6) {
  # RANKED_BAR — the last column is the ranked measure (Antibacterial / Antifungal / score).
  value_col <- names(df)[ncol(df)]
  label_col <- if (has("bgc_id")) "bgc_id" else names(df)[2]
  df$.value <- num(df[[value_col]])
  df$.label <- factor(df[[label_col]], levels = rev(df[[label_col]][order(num(df$rank))]))
  fill_col  <- if (has("boundary")) "boundary" else NULL
  p <- ggplot(df, aes(x = .value, y = .label)) +
    (if (is.null(fill_col)) geom_col(fill = SAPOTE_COHORT_PALETTE[["REFERENCE"]],
                                     colour = SAPOTE_INK, linewidth = 0.18, width = 0.72)
     else geom_col(aes(fill = .data[[fill_col]]), colour = SAPOTE_INK, linewidth = 0.18, width = 0.72)) +
    geom_text(aes(x = sapote_bar_label_x(.value, ceiling_at = max(.value, na.rm = TRUE) * 1.12),
                  label = format(round(.value, 1), trim = TRUE)),
              hjust = 0, size = 8 / .pt, colour = SAPOTE_INK) +
    ggplot2::expand_limits(x = max(df$.value, na.rm = TRUE) * 1.2) +
    ggplot2::labs(x = value_col, y = NULL, title = title, caption = caption) +
    sapote_theme() + ggplot2::theme(legend.position = if (is.null(fill_col)) "none" else "right")
  height <- sapote_height_in(nrow(df))

} else if (has("stage", "value")) {
  # FUNNEL — stage order is the sidecar's row order and must not be re-sorted.
  df$.value <- num(df$value)
  df$.stage <- factor(df$stage, levels = rev(df$stage))
  p <- ggplot(df, aes(x = .value, y = .stage)) +
    geom_col(fill = SAPOTE_COHORT_PALETTE[["BEE"]], colour = SAPOTE_INK, linewidth = 0.18, width = 0.7) +
    geom_text(aes(x = sapote_bar_label_x(.value, ceiling_at = max(.value, na.rm = TRUE) * 1.12),
                  label = .value), hjust = 0, size = 8 / .pt, colour = SAPOTE_INK) +
    ggplot2::expand_limits(x = max(df$.value, na.rm = TRUE) * 1.2) +
    ggplot2::labs(x = "count", y = NULL, title = title, caption = caption) +
    sapote_theme()
  height <- sapote_height_in(nrow(df))

} else if (has("panel", "category", "count")) {
  # COUNT_BAR, faceted by panel (8b composition).
  df$.count <- num(df$count)
  p <- ggplot(df, aes(x = .count, y = stats::reorder(category, .count))) +
    geom_col(fill = SAPOTE_COHORT_PALETTE[["MOSS"]], colour = SAPOTE_INK, linewidth = 0.18, width = 0.7) +
    geom_text(aes(x = .count, label = .count), hjust = -0.25, size = 8 / .pt, colour = SAPOTE_INK) +
    ggplot2::facet_wrap(~ panel, scales = "free_y", ncol = 1) +
    ggplot2::expand_limits(x = max(df$.count, na.rm = TRUE) * 1.18) +
    ggplot2::labs(x = "count", y = NULL, title = title, caption = caption) +
    sapote_theme()
  height <- max(3.4, 0.34 * nrow(df) + 2.0)

} else if (ncol(df) >= 2 && any(grepl("count$", names(df))) &&
           is.character(df[[1]]) && !has("PC1")) {
  # COUNT_BAR — one label column and one count column (8g class_distribution, 8h cctt_map,
  # 8j edge_composition, 8l kcb_anchors).
  count_col <- names(df)[grepl("count$", names(df))][1]
  df$.count <- num(df[[count_col]])
  df$.label <- stats::reorder(df[[1]], df$.count)
  p <- ggplot(df, aes(x = .count, y = .label)) +
    geom_col(fill = SAPOTE_COHORT_PALETTE[["WASP"]], colour = SAPOTE_INK, linewidth = 0.18, width = 0.72) +
    geom_text(aes(x = .count, label = .count), hjust = -0.25, size = 8 / .pt, colour = SAPOTE_INK) +
    ggplot2::expand_limits(x = max(df$.count, na.rm = TRUE) * 1.18) +
    ggplot2::labs(x = count_col, y = NULL, title = title, caption = caption) +
    sapote_theme()
  height <- sapote_height_in(nrow(df))

} else if (has("AB_auto", "AF_auto")) {
  # SCATTER — antibacterial vs antifungal capacity prior.
  df$.ab <- num(df$AB_auto); df$.af <- num(df$AF_auto)
  fill_col <- if (has("lead_tier")) "lead_tier" else if (has("boundary")) "boundary" else NULL
  p <- ggplot(df, aes(x = .ab, y = .af)) +
    (if (is.null(fill_col)) geom_point(size = 1.8, alpha = 0.85, colour = SAPOTE_INK)
     else geom_point(aes(colour = .data[[fill_col]]), size = 1.8, alpha = 0.85)) +
    ggplot2::labs(x = "Antibacterial prior (AB_auto)", y = "Antifungal prior (AF_auto)",
                  title = title, caption = caption, colour = fill_col) +
    sapote_theme() + ggplot2::theme(legend.position = if (is.null(fill_col)) "none" else "right")
  if (has("bgc_id") && nrow(df) <= 60) {
    if (requireNamespace("ggrepel", quietly = TRUE)) {
      p <- p + ggrepel::geom_text_repel(aes(label = bgc_id), size = 8 / .pt,
                                        min.segment.length = 0, max.overlaps = Inf,
                                        segment.linewidth = 0.2)
    } else {
      warning("ggrepel not installed — point labels omitted rather than drawn over the data")
    }
  }
  height <- 4.2

} else if (has("length_kb") && ncol(df) <= 3) {
  # HISTOGRAM — BGC length, split by edge status.
  df$.len <- num(df$length_kb)
  fill_col <- if (has("edge_status")) "edge_status" else NULL
  p <- ggplot(df, aes(x = .len)) +
    (if (is.null(fill_col)) geom_histogram(bins = 20, fill = SAPOTE_COHORT_PALETTE[["ATTINE"]],
                                           colour = SAPOTE_INK, linewidth = 0.18)
     else geom_histogram(aes(fill = .data[[fill_col]]), bins = 20, colour = SAPOTE_INK,
                         linewidth = 0.18, position = "stack")) +
    ggplot2::labs(x = "BGC length (kb)", y = "BGCs", title = title, caption = caption,
                  fill = fill_col) +
    sapote_theme() + ggplot2::theme(legend.position = if (is.null(fill_col)) "none" else "right")
  height <- 3.6

} else {
  # TABLE — wide per-BGC records (8a landscape, 8m genome_atlas, 8n two_pathway). Rendered as text
  # so nothing is invented; a bar chart of a record table would imply an ordering that is not there.
  show <- df[, seq_len(min(ncol(df), 6)), drop = FALSE]
  cells <- do.call(rbind, lapply(seq_len(nrow(show)), function(i)
    data.frame(row = i, col = seq_along(show), text = as.character(unlist(show[i, ])),
               stringsAsFactors = FALSE)))
  header <- data.frame(row = 0, col = seq_along(show), text = names(show), stringsAsFactors = FALSE)
  p <- ggplot(mapping = aes(x = col, y = -row, label = text)) +
    geom_text(data = header, fontface = "bold", hjust = 0, size = 8 / .pt, colour = SAPOTE_INK) +
    geom_text(data = cells, hjust = 0, size = 8 / .pt, colour = SAPOTE_INK) +
    ggplot2::scale_x_continuous(limits = c(0.5, ncol(show) + 1.5)) +
    ggplot2::labs(title = title, caption = caption) +
    sapote_theme() +
    sapote_no_grid() +   # SEXTANT_422j: the panel.grid blank below is inert on its own
    ggplot2::theme(axis.text = ggplot2::element_blank(), axis.title = ggplot2::element_blank(),
                   panel.grid = ggplot2::element_blank())
  height <- max(3.4, 0.22 * nrow(show) + 1.6)
}

p <- p + ggplot2::theme(plot.caption = ggplot2::element_text(size = 8, hjust = 0))
paths <- sapote_save_pair(p, out_prefix, profile, height)
cat(paste(paths, collapse = "\n"), "\n", sep = "")
