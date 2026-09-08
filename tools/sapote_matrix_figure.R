#!/usr/bin/env Rscript
# sapote_matrix_figure.R — ggplot2 renderer for every WIDE_MATRIX cohort figure.
#
# 28 of the 32 cohort figures that emit a plotted-data sidecar share ONE schema:
#
#     <label column>,<series 1>,<series 2>,...
#     domain hits,3999.0,3118.0
#
# a label column followed by one numeric column per strain (or per class, for the square
# class x class and strain x strain matrices). So they need one renderer, not 28 — the per-figure
# differences are geometry (heatmap vs bubble), colormap, and colourbar label, and those come from
# tools/FIGURE_R_MANIFEST.tsv, which tools/gen_figure_r_manifest.py DERIVES from the Python sources.
#
# Usage:
#   Rscript sapote_matrix_figure.R <figure_data.csv> <out_prefix> [figure_id] [profile] [title]
#
#     figure_id : key into FIGURE_R_MANIFEST.tsv. Defaults to the sidecar's basename with the
#                 trailing `_data` removed, which is how the factory names them on disk.
#     profile   : SINGLE_COLUMN (default) or DOUBLE_COLUMN.
#
# Emits <out_prefix>.svg and <out_prefix>.png at 300 dpi.
#
# Claim-safety: these figures report counts, domain occurrences and similarity scores. A count is
# capacity evidence, never production, and a KCB similarity score is not a compound identity.

suppressPackageStartupMessages({
  library(ggplot2)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: sapote_matrix_figure.R <figure_data.csv> <out_prefix> [figure_id] [profile] [title]")
}
data_csv   <- args[1]
out_prefix <- args[2]
figure_id  <- if (length(args) >= 3 && nzchar(args[3])) args[3]
              else sub("_data$", "", tools::file_path_sans_ext(basename(data_csv)))
profile    <- if (length(args) >= 4) toupper(args[4]) else "SINGLE_COLUMN"
title_arg  <- if (length(args) >= 5) args[5] else NA_character_

here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1]))
source(file.path(here, "sapote_figure_theme.R"))

# ---- manifest ----------------------------------------------------------------------------------
manifest_path <- file.path(here, "FIGURE_R_MANIFEST.tsv")
if (!file.exists(manifest_path)) {
  stop("FIGURE_R_MANIFEST.tsv is missing; regenerate with tools/gen_figure_r_manifest.py --apply")
}
manifest <- utils::read.delim(manifest_path, sep = "\t", quote = "", stringsAsFactors = FALSE,
                              check.names = FALSE)
spec <- manifest[manifest$figure_id == figure_id, , drop = FALSE]
if (nrow(spec) == 0) {
  # Refuse rather than guess: an unknown figure id means the manifest is stale, and silently
  # defaulting would render a figure whose colour scale does not match the Python one.
  stop(sprintf("figure_id '%s' is not in FIGURE_R_MANIFEST.tsv; regenerate the manifest", figure_id))
}
spec <- as.list(spec[1, ])
if (!identical(spec$schema, "WIDE_MATRIX")) {
  stop(sprintf("figure '%s' has schema '%s'; use sapote_tidy_figure.R for that one",
               figure_id, spec$schema))
}
geometry <- if (nzchar(spec$geometry)) spec$geometry else "heatmap"

# ---- read ---------------------------------------------------------------------------------------
raw <- utils::read.csv(data_csv, stringsAsFactors = FALSE, check.names = FALSE, comment.char = "#")
if (ncol(raw) < 2 || nrow(raw) == 0) stop("sidecar needs a label column plus at least one series")

label_col <- names(raw)[1]
series    <- names(raw)[-1]
values    <- suppressWarnings(vapply(raw[series], as.numeric, numeric(nrow(raw))))
if (!is.matrix(values)) values <- matrix(values, nrow = nrow(raw), dimnames = list(NULL, series))
if (any(is.na(values))) {
  stop("non-numeric cell in a WIDE_MATRIX sidecar — this figure is not a matrix; check the manifest")
}

long <- data.frame(
  label  = rep(raw[[label_col]], times = length(series)),
  series = rep(series, each = nrow(raw)),
  value  = as.vector(values),
  stringsAsFactors = FALSE
)
# Row order is the sidecar's order (the Python renderer's own order). Reverse the factor so the
# first row plots at the TOP, matching matplotlib's imshow origin.
long$label  <- factor(long$label, levels = rev(unique(raw[[label_col]])))
long$series <- factor(long$series, levels = series)

# ---- colour scale --------------------------------------------------------------------------------
# The manifest records matplotlib/seaborn names, sometimes as "preferred|fallback" (the Python code
# writes `"rocket_r" if "rocket_r" in plt.colormaps() else "magma_r"`). viridisLite supplies every
# one of these, so the R figure uses the SAME palette rather than an approximation.
sapote_palette_option <- function(cmap) {
  preferred <- strsplit(cmap, "|", fixed = TRUE)[[1]]
  known <- c(viridis = "viridis", plasma = "plasma", cividis = "cividis", magma = "magma",
             inferno = "inferno", rocket = "rocket", mako = "mako", turbo = "turbo")
  for (name in preferred) {
    base <- sub("_r$", "", name)
    if (base %in% names(known)) {
      return(list(option = known[[base]], reverse = grepl("_r$", name)))
    }
  }
  # magma_r is the Python default for hmap(); use it when the manifest has no entry.
  list(option = "magma", reverse = TRUE)
}

is_zscore <- grepl("zscore", figure_id, fixed = TRUE)
cmap_spec <- sapote_palette_option(if (nzchar(spec$cmap)) spec$cmap else "magma_r")
cbar_lab  <- if (nzchar(spec$cbar_label)) spec$cbar_label else "count"
title     <- if (!is.na(title_arg)) title_arg else gsub("_", " ", sub("^[A-Za-z][0-9]+_", "", figure_id))

# ---- plot ----------------------------------------------------------------------------------------
if (geometry == "bubble") {
  # bubble_matrix(): size encodes the count, colour encodes the same or a second measure. With a
  # single sidecar column per series only the count is recoverable, so size and colour share it and
  # the caption says so — inventing a second channel would be a figure that claims more than its data.
  p <- ggplot(long, aes(x = series, y = label, size = value, colour = value)) +
    geom_point(alpha = 0.9, stroke = 0.4) +
    ggplot2::scale_size_area(max_size = 6, guide = "none") +
    ggplot2::scale_colour_viridis_c(option = cmap_spec$option,
                                    direction = if (cmap_spec$reverse) -1 else 1,
                                    name = cbar_lab) +
    ggplot2::labs(x = NULL, y = NULL, title = title,
                  caption = "Bubble size and colour both encode the plotted count.") +
    sapote_theme() +
    ggplot2::theme(plot.caption = ggplot2::element_text(size = 8, hjust = 0))
} else if (is_zscore) {
  # fig_census / F01: imshow(z, cmap="RdBu_r", vmin=-2, vmax=2) — a DIVERGING scale on a fixed
  # domain. Letting it rescale to the data would change what a colour means between runs.
  p <- ggplot(long, aes(x = series, y = label, fill = value)) +
    geom_tile(colour = "white", linewidth = 0.3) +
    ggplot2::scale_fill_distiller(palette = "RdBu", direction = -1, limits = c(-2, 2),
                                  oob = scales::squish, name = cbar_lab) +
    ggplot2::labs(x = NULL, y = NULL, title = title) +
    sapote_theme()
} else {
  # hmap()/heatmap() default to LogNorm, so counts spanning orders of magnitude stay legible. Zero
  # and negative cells are undefined on a log scale; matplotlib's LogNorm masks them, and trans =
  # "log10" would drop them silently, so shift to a pseudo-log domain and label with real values.
  p <- ggplot(long, aes(x = series, y = label, fill = value)) +
    geom_tile(colour = "white", linewidth = 0.3) +
    ggplot2::scale_fill_viridis_c(option = cmap_spec$option,
                                  direction = if (cmap_spec$reverse) -1 else 1,
                                  trans = scales::pseudo_log_trans(base = 10),
                                  name = cbar_lab) +
    ggplot2::labs(x = NULL, y = NULL, title = title) +
    sapote_theme()
}

# Cell annotations, as the Python renderers do (`ax.text(j, i, f"{int(M[i, j])}")`). The label sits
# INSIDE its own cell, which is the one place text on data is correct — it annotates that cell and
# nothing else — so contrast, not offset, is what keeps it readable.
if (geometry != "bubble") {
  annot <- long
  annot$shown <- ifelse(is.na(annot$value), "", format(round(annot$value), trim = TRUE))
  rng <- range(annot$value, na.rm = TRUE)
  mid <- if (is_zscore) 0 else mean(rng)
  annot$ink <- ifelse(annot$value > mid, "white", SAPOTE_INK)
  p <- p + geom_text(data = annot, aes(x = series, y = label, label = shown, colour = ink),
                     inherit.aes = FALSE, size = 8 / .pt, show.legend = FALSE) +
    ggplot2::scale_colour_identity()
}

p <- p + ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 30, hjust = 1))

paths <- sapote_save_pair(p, out_prefix, profile, sapote_height_in(nrow(raw)))
cat(paste(paths, collapse = "\n"), "\n", sep = "")
