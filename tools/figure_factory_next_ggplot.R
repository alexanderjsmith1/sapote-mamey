#!/usr/bin/env Rscript
# figure_factory_next_ggplot.R — ggplot2 template for the Figure Factory Next evidence-coverage
# figure, rendered from the factory's own plotted-data sidecar.
#
# This is a SECOND RENDERER OF THE SAME NUMBERS, not a second analysis. It reads
# `figure_factory_next_data.csv` — the tidy table the Python renderer plotted, emitted alongside it
# and hashed into the same receipt — so the R figure cannot disagree with the Python one about what
# was measured. It performs no aggregation, no filtering and no policy: every cohort/role decision
# was already made upstream by mamey/figure_factory_next.py::_aggregate.
#
# Usage:
#   Rscript figure_factory_next_ggplot.R <figure_factory_next_data.csv> <out_prefix> [profile] [title]
#
#     profile : SINGLE_COLUMN (default, 3.5 in) or DOUBLE_COLUMN (7.2 in)
#     title   : optional; defaults to the caption-free neutral title
#
# Emits <out_prefix>.svg and <out_prefix>.png at 300 dpi.
#
# Claim-safety: the figure reports observed/declared evidence coverage. Coverage is not production,
# and a high bar is not a compound identity. The caption is authored by the factory
# (figure_factory_next_caption.md) and is deliberately NOT re-generated here.

suppressPackageStartupMessages({
  library(ggplot2)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: figure_factory_next_ggplot.R <data.csv> <out_prefix> [profile] [title]")
}
data_csv   <- args[1]
out_prefix <- args[2]
profile    <- if (length(args) >= 3) toupper(args[3]) else "SINGLE_COLUMN"
title      <- if (length(args) >= 4) args[4] else "Evidence readiness by channel"

source(file.path(dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])),
                 "sapote_figure_theme.R"))

# ---- read the sidecar --------------------------------------------------------------------------
# These are exactly the columns mamey/figure_factory_next.py::_aggregate emits. A missing column is a
# hard stop: silently plotting a partial table is how a figure starts disagreeing with its own data.
REQUIRED <- c("group_kind", "sensitivity_identity", "cohort", "genus", "channel", "metric",
              "denominator_key", "identity_count", "numerator", "denominator", "percent",
              "assembly_flagged_metric_rows", "assembly_default_off_metric_rows",
              "source_metric_rows")

df <- utils::read.csv(data_csv, stringsAsFactors = FALSE, check.names = FALSE,
                      colClasses = "character")
missing <- setdiff(REQUIRED, names(df))
if (length(missing)) {
  stop(sprintf("sidecar is missing required column(s): %s", paste(missing, collapse = ", ")))
}
if (nrow(df) == 0) stop("sidecar has no plotted rows")

for (col in c("numerator", "denominator", "percent", "identity_count",
              "assembly_flagged_metric_rows", "assembly_default_off_metric_rows",
              "source_metric_rows")) {
  df[[col]] <- as.numeric(df[[col]])
}

unknown_cohorts <- setdiff(unique(df$cohort), names(SAPOTE_COHORT_PALETTE))
if (length(unknown_cohorts)) {
  stop(sprintf("cohort(s) with no palette entry: %s — add them to figure_policy.py first",
               paste(unknown_cohorts, collapse = ", ")))
}

# ---- labels ------------------------------------------------------------------------------------
# Row order is the sidecar's order, which is the Python renderer's sorted bucket order. Preserve it
# exactly (factor levels reversed so the first row plots at the TOP, matching invert_yaxis()).
df$label <- sapote_wrap_labels(
  paste0(ifelse(df$group_kind == "SENSITIVITY", "sensitivity | ", ""),
         df$cohort, " | ", df$genus, " | ", df$channel, " | ", df$metric),
  width = sapote_wrap(profile)
)
df$label <- factor(df$label, levels = rev(df$label))
df$value_label <- paste0(df$numerator, "/", df$denominator)

# Assembly-state marker: hollow diamond for FLAG rows, cross for DEFAULT_OFF rows, nothing otherwise.
df$marker <- ifelse(df$assembly_flagged_metric_rows > 0, "flagged",
             ifelse(df$assembly_default_off_metric_rows > 0, "default_off", NA_character_))
markers <- df[!is.na(df$marker), , drop = FALSE]

# ---- plot --------------------------------------------------------------------------------------
# Value labels sit OUTSIDE the bar end and the markers further out again (sapote_figure_theme.R), so
# no text is ever drawn over the data it describes.
p <- ggplot(df, aes(x = percent, y = label, fill = cohort)) +
  geom_col(colour = SAPOTE_INK, linewidth = 0.18, width = 0.72) +
  geom_text(aes(x = sapote_bar_label_x(percent), label = value_label),
            hjust = 0, size = 8 / .pt, colour = SAPOTE_INK) +
  scale_fill_manual(values = SAPOTE_COHORT_PALETTE, drop = FALSE) +
  scale_x_continuous(limits = c(0, 115), breaks = c(0, 20, 40, 60, 80, 100), expand = c(0, 0)) +
  labs(x = "Observed / declared denominator (%)", y = NULL, title = title) +
  sapote_theme()

if (nrow(markers)) {
  p <- p +
    geom_point(data = markers,
               aes(x = sapote_bar_marker_x(percent), y = label, shape = marker),
               inherit.aes = FALSE, colour = SAPOTE_ACCENT, size = 1.6, stroke = 0.6) +
    # 5 = hollow diamond (assembly FLAG); 4 = cross (assembly DEFAULT_OFF).
    scale_shape_manual(values = c(flagged = 5, default_off = 4))
}

paths <- sapote_save_pair(p, out_prefix, profile, sapote_height_in(nrow(df)))
cat(paste(paths, collapse = "\n"), "\n", sep = "")
