#!/usr/bin/env Rscript
# sapote_locus_map.R — ggplot2 gene-arrow renderer for the BGC locus maps.
#
# Reads `<BGC>_locus_map_data.csv` / `<contig>_kcb_locusmap_data.csv`, the sidecar the Python locus
# renderers emit. One row per gene, with the full exact-locus identity in `panel`:
#
#     panel   Actinomadura_rifamycini / AULB01000003.1 / region001 / BGC001 · NRPS
#     ...     locus_tag, order, start, end, strand, length_aa, role, gene_functions,
#             label_displayed, selected_comparator, comparator_accession, comparator_compound,
#             subject_gene, pct_identity, pct_coverage, blast_score, evalue,
#             domain_tokens, hmm_tokens, module_tokens, motif_tokens, displayed_evidence_summary
#
# Usage:
#   Rscript sapote_locus_map.R <locus_data.csv> <out_prefix> [profile] [title]
#
# Claim-safety, and it is load-bearing here: the `panel` string is the exact-locus identity
# (strain / full node-or-contig / region / BGC alias) and is printed VERBATIM as the subtitle. It is
# never shortened, re-derived or reformatted — a truncated node is a different locus. A comparator
# is a similarity anchor, never a product identity, and gene ROLE is an antiSMASH annotation, not a
# demonstrated function.

suppressPackageStartupMessages({
  library(ggplot2)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) stop("Usage: sapote_locus_map.R <locus_data.csv> <out_prefix> [profile] [title]")
data_csv   <- args[1]
out_prefix <- args[2]
profile    <- if (length(args) >= 3) toupper(args[3]) else "DOUBLE_COLUMN"
title_arg  <- if (length(args) >= 4) args[4] else NA_character_

here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1]))
source(file.path(here, "sapote_figure_theme.R"))

REQUIRED <- c("panel", "locus_tag", "order", "start", "end", "strand", "role", "label_displayed")
df <- utils::read.csv(data_csv, stringsAsFactors = FALSE, check.names = FALSE, comment.char = "#")
missing <- setdiff(REQUIRED, names(df))
if (length(missing)) stop(sprintf("locus sidecar is missing: %s", paste(missing, collapse = ", ")))
if (nrow(df) == 0) stop("locus sidecar has no genes")

panels <- unique(df$panel)
if (length(panels) != 1) {
  stop(sprintf("expected exactly one locus panel, found %d: %s",
               length(panels), paste(panels, collapse = " | ")))
}
identity <- panels[1]
if (!grepl("^[^/]+ / [^/]+ / [^/]+ / ", identity)) {
  # A malformed identity is a HOLD, not something to paper over with a prettier label.
  stop(sprintf("panel is not a full strain / node / region / BGC identity: %s", identity))
}

df$start <- as.numeric(df$start); df$end <- as.numeric(df$end)
df$order <- as.numeric(df$order)
df$.strand <- ifelse(df$strand == "-", -1, 1)

# antiSMASH gene roles. Colours follow the Okabe-Ito set the rest of the bundle uses, so the map is
# readable in greyscale and to colour-blind readers.
ROLE_COLOURS <- c(
  "biosynthetic"            = "#0072B2",
  "biosynthetic-additional" = "#56B4E9",
  "transport"               = "#009E73",
  "regulatory"              = "#E69F00",
  "resistance"              = "#D55E00",
  "other"                   = "#BBBBBB"
)
df$.role <- ifelse(df$role %in% names(ROLE_COLOURS), df$role, "other")

# ---- arrow geometry --------------------------------------------------------------------------------
# Each gene is a polygon: a rectangle with a triangular head at the 3' end, so strand is readable
# from the shape and not only from colour. Head length is capped at a third of the gene so short
# genes stay visible as arrows rather than collapsing to a spike.
span <- max(df$end) - min(df$start)
body_h <- 0.30
head_h <- 0.46

arrow_poly <- function(i) {
  s <- df$start[i]; e <- df$end[i]; dir <- df$.strand[i]
  head_len <- min((e - s) / 3, span * 0.012)
  if (dir > 0) {
    xs <- c(s, e - head_len, e, e - head_len, s)
  } else {
    xs <- c(e, s + head_len, s, s + head_len, e)
  }
  ys <- c(-body_h, -body_h, 0, body_h, body_h)
  data.frame(id = df$locus_tag[i], x = xs, y = ys, role = df$.role[i], stringsAsFactors = FALSE)
}
polys <- do.call(rbind, lapply(seq_len(nrow(df)), arrow_poly))

p <- ggplot() +
  ggplot2::geom_hline(yintercept = 0, colour = "#999999", linewidth = 0.3) +
  ggplot2::geom_polygon(data = polys, aes(x = x, y = y, group = id, fill = role),
                        colour = SAPOTE_INK, linewidth = 0.18) +
  ggplot2::scale_fill_manual(values = ROLE_COLOURS, name = "antiSMASH role") +
  ggplot2::scale_x_continuous(labels = function(v) sprintf("%.0f kb", v / 1000)) +
  ggplot2::labs(
    x = NULL, y = NULL,
    title = if (!is.na(title_arg)) title_arg else "Locus map",
    subtitle = identity,   # verbatim exact-locus identity — never abbreviated
    caption = paste("Gene roles are antiSMASH annotations, not demonstrated functions.",
                    "Any comparator shown is a similarity anchor, not a product identity.")
  ) +
  sapote_theme() +
  ggplot2::theme(
    axis.text.y = ggplot2::element_blank(),
    panel.grid.major.x = ggplot2::element_line(colour = SAPOTE_GRID, linewidth = 0.3),
    legend.position = "bottom",
    plot.subtitle = ggplot2::element_text(size = 8, family = "mono"),
    plot.caption  = ggplot2::element_text(size = 8, hjust = 0)
  )

# ---- gene labels -----------------------------------------------------------------------------------
# House rule: text never sits on the data. Labels go BELOW the arrow track, alternating two rows so
# neighbouring genes cannot collide, and only for genes the Python renderer marked label_displayed.
shown <- df[toupper(df$label_displayed) == "YES", , drop = FALSE]
if (nrow(shown)) {
  shown$.x <- (shown$start + shown$end) / 2
  shown$.y <- ifelse(seq_len(nrow(shown)) %% 2 == 0, -0.72, -1.02)
  p <- p + ggplot2::geom_text(data = shown, aes(x = .x, y = .y, label = locus_tag),
                              size = 8 / .pt, colour = SAPOTE_INK)
}
p <- p + ggplot2::ylim(-1.3, 0.9)

height <- max(3.4, 2.6 + 0.02 * nrow(df))
paths <- sapote_save_pair(p, out_prefix, profile, height)
cat(paste(paths, collapse = "\n"), "\n", sep = "")
