#!/usr/bin/env Rscript
# Render a canonical bioassay Figure Factory summary as an SVG/PNG heatmap.
# The Python producer validates control, inclusion, target, material-lineage,
# replicate, time-point, and plate-format states before this script is called.
#
# Usage:
#   Rscript sapote_bioassay_figure.R <summary.tsv> <out_prefix> [profile] [title]

suppressPackageStartupMessages(library(ggplot2))

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: sapote_bioassay_figure.R <summary.tsv> <out_prefix> [profile] [title]")
}
summary_path <- args[1]
out_prefix <- args[2]
profile <- if (length(args) >= 3) toupper(args[3]) else "SINGLE_COLUMN"
title <- if (length(args) >= 4) args[4] else "Bioassay observations"

here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1]))
source(file.path(here, "sapote_figure_theme.R"))

required <- c(
  "strain_id", "material_id", "material_type", "parent_material_id", "lineage_state",
  "material_amount_mg", "dose_state", "stock_concentration_mg_ml", "delivered_amount_ug",
  "final_concentration_ug_ml", "target", "target_state", "timepoint_hours", "observation_count", "experiment_count",
  "replicate_count", "mean_inhibition_pct", "min_inhibition_pct", "max_inhibition_pct"
)
df <- utils::read.delim(summary_path, sep = "\t", quote = "", stringsAsFactors = FALSE,
                        check.names = FALSE)
if (!all(required %in% names(df))) stop("BIOASSAY_SUMMARY_SCHEMA: required columns are missing")
if (nrow(df) == 0) stop("BIOASSAY_SUMMARY_EMPTY: no included observations")

number_fields <- c("timepoint_hours", "observation_count", "experiment_count", "replicate_count",
                   "mean_inhibition_pct", "min_inhibition_pct", "max_inhibition_pct")
for (field in number_fields) {
  df[[field]] <- suppressWarnings(as.numeric(df[[field]]))
  if (any(!is.finite(df[[field]]))) stop(paste0("BIOASSAY_SUMMARY_VALUE: non-numeric ", field))
}

# An ambiguous organism remains visually explicit and is never folded into a verified species.
df$target_display <- ifelse(df$target_state == "AMBIGUOUS",
                            paste0(df$target, " [ambiguous]"), df$target)
dose_label <- ifelse(is.na(df$final_concentration_ug_ml) | df$final_concentration_ug_ml == "",
                     "dose unrecorded", paste0(df$final_concentration_ug_ml, " ug/mL"))
df$column <- paste0(df$target_display, " | ", format(df$timepoint_hours, trim = TRUE),
                    " h | ", dose_label)
df$row <- paste(df$strain_id, df$material_id, df$material_type, sep = " | ")
df$cell <- paste0(format(round(df$mean_inhibition_pct, 1), trim = TRUE), "%\n",
                  "n=", df$observation_count, "; exp=", df$experiment_count)

# Preserve deterministic input order while showing later time points to the right.
col_order <- unique(df$column[order(df$target_display, df$timepoint_hours)])
row_order <- rev(unique(df$row))
df$column <- factor(df$column, levels = col_order)
df$row <- factor(df$row, levels = row_order)

p <- ggplot(df, aes(x = column, y = row, fill = mean_inhibition_pct)) +
  geom_tile(colour = "white", linewidth = 0.35) +
  geom_text(aes(label = cell), size = 8 / .pt, lineheight = 0.9, colour = SAPOTE_INK) +
  scale_fill_gradient2(low = "#4575B4", mid = "#FFFFBF", high = "#D73027",
                       midpoint = 50, name = "Mean inhibition (%)") +
  labs(x = "Recorded target, time point, and final assay concentration", y = "Strain | material | material type",
       title = title,
       caption = "Cell labels show the arithmetic mean, retained observation count (n), and experiment count (exp).") +
  sapote_theme() +
  theme(axis.text.x = element_text(angle = 35, hjust = 1),
        plot.caption = element_text(size = 8, hjust = 0))

width <- if (profile == "DOUBLE_COLUMN") 7.2 else 4.25
height <- max(3.4, 1.7 + 0.34 * length(row_order))
ggsave(paste0(out_prefix, ".svg"), p, width = width, height = height, limitsize = FALSE)
ggsave(paste0(out_prefix, ".png"), p, width = width, height = height, dpi = 300, limitsize = FALSE)
cat(paste0(out_prefix, ".svg\n", out_prefix, ".png\n"))
