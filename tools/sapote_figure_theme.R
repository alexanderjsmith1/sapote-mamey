#!/usr/bin/env Rscript
# sapote_figure_theme.R — shared palette, theme, and label-placement helpers for the R figure
# templates. Source this from every Sapote-Mamey R script so the ggplot2/ggtree output matches the
# Python renderer instead of drifting into a second, prettier house style.
#
# The palette and the publication profiles below are TRANSCRIBED FROM mamey/figure_policy.py
# (COHORT_PALETTE, PUBLICATION_PROFILES). They are not free choices. Drift between the two is caught
# by tests/test_410_r_figure_templates.py, which parses THIS file and compares it against the Python
# constants — so if figure_policy.py changes, that test fails until this file is updated.
#
# Claim-safety: these templates render evidence coverage and phylogenetic neighbourhood. Neither is a
# product-identity claim. Captions are authored upstream and are not invented here.

# ---- palette: mamey/figure_policy.py::COHORT_PALETTE -------------------------------------------
SAPOTE_COHORT_PALETTE <- c(
  "BEE"                = "#0072B2",
  "WASP"               = "#56B4E9",
  "ATTINE"             = "#8C510A",
  "MOSS"               = "#009E73",
  "REFERENCE"          = "#666666",
  "EXTERNAL_BENCHMARK" = "#CC79A7",
  "UNRESOLVED"         = "#1A1A1A"
)

# Accent used for the assembly-state markers (matplotlib "#D55E00", Okabe-Ito vermillion).
SAPOTE_ACCENT <- "#D55E00"
SAPOTE_GRID   <- "#D9E1E8"
SAPOTE_INK    <- "#1A1A1A"

# ---- publication profiles: mamey/figure_policy.py::PUBLICATION_PROFILES -------------------------
SAPOTE_PROFILES <- list(
  SINGLE_COLUMN = list(width_in = 3.5, minimum_text_pt = 8.0, minimum_raster_dpi = 300),
  DOUBLE_COLUMN = list(width_in = 7.2, minimum_text_pt = 8.0, minimum_raster_dpi = 300)
)

sapote_profile <- function(name) {
  name <- toupper(name)
  if (!name %in% names(SAPOTE_PROFILES)) {
    stop(sprintf("unknown profile %s; expected one of %s",
                 name, paste(names(SAPOTE_PROFILES), collapse = ", ")))
  }
  SAPOTE_PROFILES[[name]]
}

# Figure height mirrors the Python renderer exactly: max(3.4, 0.62 * n_rows + 1.8).
sapote_height_in <- function(n_rows) max(3.4, 0.62 * n_rows + 1.8)

# Label wrap width mirrors the Python renderer: 34 (single column) / 68 (double column).
sapote_wrap <- function(profile) if (toupper(profile) == "SINGLE_COLUMN") 34 else 68

# ---- theme -------------------------------------------------------------------------------------
# Minimum text size is 8 pt in BOTH profiles and is a publication-QA floor, not a preference:
# validate_publication_artwork() rejects artwork below it. Nothing here may set a size under 8.
sapote_theme <- function(base_pt = 8) {
  if (base_pt < 8) stop("minimum_text_pt is 8.0; a smaller base size fails publication QA")
  ggplot2::theme_minimal(base_size = base_pt) +
    ggplot2::theme(
      text             = ggplot2::element_text(colour = SAPOTE_INK),
      axis.text        = ggplot2::element_text(size = base_pt, colour = SAPOTE_INK),
      axis.title       = ggplot2::element_text(size = base_pt),
      plot.title       = ggplot2::element_text(size = base_pt + 1, hjust = 0),
      panel.grid.major.y = ggplot2::element_blank(),
      panel.grid.minor   = ggplot2::element_blank(),
      panel.grid.major.x = ggplot2::element_line(colour = SAPOTE_GRID, linewidth = 0.3),
      legend.position    = "none"
    )
}

# ---- label placement ---------------------------------------------------------------------------
# House rule, universal across every Sapote-Mamey figure: a text label must never sit on top of the
# data it describes. Bar value labels are placed OUTSIDE the bar end; tree tip labels are offset off
# the branch. These helpers exist so no template re-decides that per figure.

# Offset for a value label drawn past the end of a horizontal bar, in data units.
sapote_bar_label_x <- function(value, max_value = 100, pad = 1, ceiling_at = 103) {
  pmin(value + pad, ceiling_at)
}

# Offset for the assembly-state marker, further out again so it never collides with the value label.
sapote_bar_marker_x <- function(value, pad = 9, ceiling_at = 111) {
  pmin(value + pad, ceiling_at)
}

# Horizontal nudge for a ggtree tip label, expressed as a fraction of total tree depth. ggtree draws
# tip labels at the tip coordinate by default, which puts the text on the branch line.
sapote_tip_nudge <- function(max_depth, fraction = 0.01) max_depth * fraction

sapote_wrap_labels <- function(x, width) {
  vapply(x, function(s) paste(strwrap(s, width = width), collapse = "\n"), character(1))
}

# ---- saving ------------------------------------------------------------------------------------
# Emits the same pair the Python renderer does (SVG + 300-dpi PNG) at the profile width.
sapote_save_pair <- function(plot, out_prefix, profile, height_in) {
  spec <- sapote_profile(profile)
  ggplot2::ggsave(paste0(out_prefix, ".svg"), plot,
                  width = spec$width_in, height = height_in, units = "in")
  ggplot2::ggsave(paste0(out_prefix, ".png"), plot,
                  width = spec$width_in, height = height_in, units = "in",
                  dpi = spec$minimum_raster_dpi)
  invisible(c(paste0(out_prefix, ".svg"), paste0(out_prefix, ".png")))
}
