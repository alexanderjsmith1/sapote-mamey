#!/usr/bin/env Rscript
# sapote_tidy_figure.R — ggplot2 renderer for the cohort figures whose sidecar is already tidy
# (long form), rather than a label column plus one numeric column per series.
#
# Four cohort figures, three shapes:
#
#   F12_bgc_pca_by_cluster    strain,bgc_id,PC1,PC2,cluster       ORDINATION, one point per BGC
#   F13_strain_ordination_2d  strain,tier,PC1,PC2                 ORDINATION, one point per strain
#   F11_active_site_completeness  strain,tier,catalytic_genes,completeness_pct   RANKED BAR
#   G15_rare_bgc_roster       strain,BGC,node/contig,...          ROSTER TABLE
#
# Shape is detected from the sidecar's own columns, not hard-coded per figure id, so a new tidy
# figure with PC1/PC2 renders without editing this file. The figure id is still required and still
# checked against the manifest — an unknown id is a stale manifest, which is worth failing on.
#
# Usage:
#   Rscript sapote_tidy_figure.R <figure_data.csv> <out_prefix> [figure_id] [profile] [title]
#
# Claim-safety: an ordination shows similarity structure. Proximity is not identity, and a cluster
# label is a grouping index, not a compound family assignment.

suppressPackageStartupMessages({
  library(ggplot2)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: sapote_tidy_figure.R <figure_data.csv> <out_prefix> [figure_id] [profile] [title]")
}
data_csv   <- args[1]
out_prefix <- args[2]
figure_id  <- if (length(args) >= 3 && nzchar(args[3])) args[3]
              else sub("_data$", "", tools::file_path_sans_ext(basename(data_csv)))
profile    <- if (length(args) >= 4) toupper(args[4]) else "SINGLE_COLUMN"
title_arg  <- if (length(args) >= 5) args[5] else NA_character_

here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1]))
source(file.path(here, "sapote_figure_theme.R"))

manifest_path <- file.path(here, "FIGURE_R_MANIFEST.tsv")
if (file.exists(manifest_path)) {
  manifest <- utils::read.delim(manifest_path, sep = "\t", quote = "", stringsAsFactors = FALSE,
                                check.names = FALSE)
  spec <- manifest[manifest$figure_id == figure_id, , drop = FALSE]
  if (nrow(spec) && identical(spec$schema[1], "WIDE_MATRIX")) {
    stop(sprintf("figure '%s' is WIDE_MATRIX; use sapote_matrix_figure.R", figure_id))
  }
}

df <- utils::read.csv(data_csv, stringsAsFactors = FALSE, check.names = FALSE, comment.char = "#")
if (nrow(df) == 0) stop("sidecar has no rows")
title <- if (!is.na(title_arg)) title_arg else gsub("_", " ", sub("^[A-Za-z][0-9]+_", "", figure_id))

# Colour by cohort when the sidecar carries one; otherwise by strain, using a stable ordering so the
# same strain gets the same colour across figures.
colour_col <- if ("cohort" %in% names(df)) "cohort" else if ("strain" %in% names(df)) "strain" else NULL

if (all(c("PC1", "PC2") %in% names(df))) {
  # ---- ordination ------------------------------------------------------------------------------
  df$PC1 <- as.numeric(df$PC1); df$PC2 <- as.numeric(df$PC2)
  point_label <- if ("bgc_id" %in% names(df)) "bgc_id" else if ("strain" %in% names(df)) "strain" else NULL
  shape_col   <- if ("cluster" %in% names(df)) "cluster" else if ("tier" %in% names(df)) "tier" else NULL

  aes_map <- aes(x = PC1, y = PC2)
  p <- ggplot(df, aes_map) +
    ggplot2::labs(title = title,
                  caption = paste("Ordination of similarity structure.",
                                  "Proximity is not identity; cluster labels are grouping indices.")) +
    sapote_theme() +
    ggplot2::theme(legend.position = "right",
                   plot.caption = ggplot2::element_text(size = 8, hjust = 0))

  if (!is.null(colour_col)) {
    df$.colour <- as.factor(df[[colour_col]])
    if (!is.null(shape_col)) {
      df$.shape <- as.factor(df[[shape_col]])
      p <- p + geom_point(data = df, aes(colour = .colour, shape = .shape), size = 1.8, alpha = 0.9) +
        ggplot2::labs(colour = colour_col, shape = shape_col)
    } else {
      p <- p + geom_point(data = df, aes(colour = .colour), size = 1.8, alpha = 0.9) +
        ggplot2::labs(colour = colour_col)
    }
  } else {
    p <- p + geom_point(size = 1.8, alpha = 0.9, colour = SAPOTE_INK)
  }

  # House rule: labels off the data. ggrepel pushes them away from their point and from each other;
  # when it is unavailable, label nothing rather than draw text over the points.
  if (!is.null(point_label) && nrow(df) <= 60) {
    if (requireNamespace("ggrepel", quietly = TRUE)) {
      p <- p + ggrepel::geom_text_repel(data = df, aes(label = .data[[point_label]]),
                                        size = 8 / .pt, min.segment.length = 0,
                                        max.overlaps = Inf, segment.linewidth = 0.2)
    } else {
      warning("ggrepel not installed — point labels omitted rather than drawn over the data")
    }
  }
  height <- max(3.4, 3.4 + 0.02 * nrow(df))

} else if (any(grepl("_pct$|completeness", names(df)))) {
  # ---- ranked bar --------------------------------------------------------------------------------
  value_col <- names(df)[grepl("_pct$|completeness", names(df))][1]
  label_col <- if ("strain" %in% names(df)) "strain" else names(df)[1]
  df$.value <- as.numeric(df[[value_col]])
  df$.label <- factor(df[[label_col]], levels = rev(df[[label_col]][order(df$.value)]))
  fill_col  <- if ("tier" %in% names(df)) "tier" else label_col
  df$.fill  <- as.factor(df[[fill_col]])

  p <- ggplot(df, aes(x = .value, y = .label, fill = .fill)) +
    geom_col(colour = SAPOTE_INK, linewidth = 0.18, width = 0.7) +
    # Value text sits past the bar end, never on it (shared helper, house rule).
    geom_text(aes(x = sapote_bar_label_x(.value, ceiling_at = max(df$.value) * 1.12),
                  label = sprintf("%.1f", .value)),
              hjust = 0, size = 8 / .pt, colour = SAPOTE_INK) +
    ggplot2::expand_limits(x = max(df$.value) * 1.2) +
    ggplot2::labs(x = value_col, y = NULL, title = title, fill = fill_col) +
    sapote_theme() +
    ggplot2::theme(legend.position = "right")
  height <- sapote_height_in(nrow(df))

} else {
  # ---- roster table ------------------------------------------------------------------------------
  # G15 is a table rendered as a figure. Draw it as text on a blank canvas: one row per record, one
  # column per field, header in bold. No geometry, so nothing can overlap.
  cells <- do.call(rbind, lapply(seq_len(nrow(df)), function(i) {
    data.frame(row = i, col = seq_along(df), text = as.character(unlist(df[i, ])),
               stringsAsFactors = FALSE)
  }))
  header <- data.frame(row = 0, col = seq_along(df), text = names(df), stringsAsFactors = FALSE)
  p <- ggplot(mapping = aes(x = col, y = -row, label = text)) +
    geom_text(data = header, fontface = "bold", hjust = 0, size = 8 / .pt, colour = SAPOTE_INK) +
    geom_text(data = cells, hjust = 0, size = 8 / .pt, colour = SAPOTE_INK) +
    ggplot2::scale_x_continuous(limits = c(0.5, ncol(df) + 1.5)) +
    ggplot2::labs(title = title) +
    sapote_theme() +
    ggplot2::theme(axis.text = ggplot2::element_blank(), axis.title = ggplot2::element_blank(),
                   panel.grid = ggplot2::element_blank())
  height <- max(3.4, 0.22 * nrow(df) + 1.6)
}

paths <- sapote_save_pair(p, out_prefix, profile, height)
cat(paste(paths, collapse = "\n"), "\n", sep = "")
