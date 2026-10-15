#!/usr/bin/env Rscript
# Draw T05 (dDDH with the closest type strain) and T06 (16S similarity against dDDH) from tygs_figures.py's data table.
# Drawing copied from the bee paper's Fig. 2A/2B script (fig_dDDH_PRINT.R and its moss copy moss_2AB_bee_identical.R):
# same marks, colours, error bars, reference lines and label backing. Changes for the bundle:
#   - every text element is 8 pt or larger at the printed size;
#   - no interpretive text on the canvas ("potential new species", the 16S/dDDH callout): it belongs in the caption;
#   - the T06 x range comes from the data (and keeps the 98.65% line in view), not a fixed 95-100%;
#   - genus colours come from mamey/data/genus_palette.json.
# Args: data.tsv palette.json outdir widthA widthB
suppressPackageStartupMessages({ library(ggplot2); library(dplyr); library(readr); library(ggrepel); library(ggtext); library(jsonlite) })
here <- dirname(normalizePath(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE))))
source(file.path(here, "sapote_pub_layout.R"))
source(file.path(here, "sapote_stamp_required.R"))
a <- commandArgs(TRUE); data <- a[1]; pal_file <- a[2]; out <- a[3]; WA <- as.numeric(a[4]); WB <- as.numeric(a[5])
KEY <- if (length(a) >= 6 && nzchar(a[6])) a[6] else "Genus (16S rRNA)"
PT <- 8
d <- read_tsv(data, show_col_types = FALSE, col_types = cols(.default = "c")) %>%
  mutate(across(c(d4, d4_ci_low, d4_ci_high, similarity_16s), as.numeric)) %>% arrange(d4)
pj <- fromJSON(pal_file); pal_all <- unlist(pj$default)
PSET <- if (length(a) >= 7) a[7] else ""
if (nzchar(PSET)) { if (is.null(pj$sets[[PSET]])) stop("PALETTE_SET_UNKNOWN: ", PSET); ov <- unlist(pj$sets[[PSET]]); pal_all[names(ov)] <- ov }
 fallback <- if (!is.null(pj$fallback)) pj$fallback else "#8C96A5"
gen <- sort(unique(d$genus)); pal <- setNames(ifelse(gen %in% names(pal_all), pal_all[gen], fallback), gen)
glab <- setNames(paste0("<i>", gen, "</i>"), gen)
d <- d %>% mutate(ts_md = if ("reference_label" %in% names(.) && any(!is.na(reference_label) & reference_label != ""))
                            reference_label else sub("^(\\S+) (\\S+)", "<i>\\1 \\2</i>", closest_type_strain),
                  lab_md = if ("row_label" %in% names(.)) row_label else paste0("<i>", genus, "</i> sp. ", isolate))
d$lab_md <- factor(d$lab_md, levels = d$lab_md)
AX <- theme(axis.title = element_text(size = PT, colour = PUB_INK), axis.title.x = element_markdown(size = PT, colour = PUB_INK, margin = margin(t = 3)),
            axis.text.x.bottom = element_markdown(size = PT, colour = PUB_INK), axis.text.y.left = element_markdown(size = PT, colour = PUB_INK),
            legend.text = element_markdown(size = PT), legend.title = element_text(size = PT, face = "bold"),
            legend.key.size = unit(8, "pt"), legend.margin = margin(0, 0, 0, 0), plot.margin = margin(5, 6, 5, 5))
# T05: one row per genome
lab_chars <- nchar(gsub("<[^>]+>", "", sub("<br>.*$", "", d$ts_md)))   # first line of each label, markup removed
xmax <- max(114, max(d$d4_ci_high + 2 + 1.75 * lab_chars))   # room for each type-strain name right of its point
pA <- ggplot(d, aes(y = lab_md)) +
  geom_vline(xintercept = 70, linetype = "dashed", colour = "#6B7483", linewidth = 0.3) +
  geom_errorbarh(aes(xmin = d4_ci_low, xmax = d4_ci_high), height = 0.35, colour = "#8A94A3", linewidth = 0.3) +
  geom_point(aes(x = d4, fill = genus), shape = 21, size = 2.1, colour = PUB_INK, stroke = 0.35) +
  # every type-strain name sits right of its interval (the bee script put names left of points at or above 70%, which clipped
  # long names against the row labels); the x axis is extended past 100% to make room
  geom_richtext(aes(x = pmax(d4_ci_high, d4) + 1.5, label = ts_md), hjust = 0, size = PT / .pt, fill = "white", lineheight = 1.05,
                label.colour = NA, colour = PUB_SUB, label.padding = unit(0.3, "pt"), label.r = unit(0, "pt")) +
  scale_fill_manual(values = pal, breaks = gen, labels = glab, name = KEY) +
  scale_x_continuous(limits = c(0, xmax), breaks = seq(0, 100, 10), labels = function(v) paste0(v, "%"), expand = expansion(0)) +
  scale_y_discrete(expand = expansion(add = c(0.6, 0.8))) +
  labs(x = "Digital DNA-DNA hybridisation (dDDH, formula d4) with the closest type strain", y = NULL) +
  guides(fill = guide_legend(nrow = 2, override.aes = list(size = 2.2))) +
  theme_pub(base = PT) + AX + theme(legend.position = "bottom", panel.grid.major.y = element_blank())
HA <- 1.4 + (if (any(grepl("<br>", d$ts_md)) || any(grepl("<br>", as.character(d$lab_md)))) 0.36 else 0.22) * nrow(d)   # two-line reference or row labels need taller rows
for (dev in c("png", "pdf")) {
  f <- file.path(out, paste0("T05_dDDH_closest_type_strain.", dev))
  if (dev == "png") ggsave(f, pA, width = WA, height = HA, dpi = 600, bg = "white") else { grDevices::quartz(type = "pdf", file = f, width = WA, height = HA); print(pA); invisible(dev.off()) }
  sapote_stamp_files_required(f, "tygs_figures")
}
# T06: 16S similarity against dDDH, genomes with a 16S value
b <- d %>% filter(!is.na(similarity_16s))
if (nrow(b)) {
  xl <- c(min(b$similarity_16s, 98.65) - 0.2, max(b$similarity_16s, 100) + 0.1)
  pB <- ggplot(b, aes(similarity_16s, d4, fill = genus)) +
    geom_hline(yintercept = 70, linetype = "dashed", colour = "#6B7483", linewidth = 0.3) +
    geom_vline(xintercept = 98.65, linetype = "dashed", colour = "#6B7483", linewidth = 0.3) +
    geom_point(shape = 21, size = 1.9, colour = PUB_INK, stroke = 0.35) +
    geom_text_repel(aes(label = isolate), size = PT / .pt, fontface = "bold", family = PUB_FONT, colour = PUB_INK, bg.colour = "white", bg.r = 0.12,
                    seed = 11, box.padding = 0.3, point.padding = 0.15, min.segment.length = 0, segment.colour = "#6B7483", segment.size = 0.25,
                    force = 8, max.time = 60, max.iter = 100000, max.overlaps = Inf) +
    scale_fill_manual(values = pal, breaks = gen, labels = glab, name = KEY) +
    scale_x_continuous(labels = function(v) paste0(v, "%")) + coord_cartesian(xlim = xl) +
    scale_y_continuous(limits = c(0, 100), breaks = seq(0, 100, 25), labels = function(v) paste0(v, "%")) +
    labs(x = "16S rRNA gene similarity to the closest type strain", y = "dDDH (d4) with the closest type strain") +
    guides(fill = guide_legend(nrow = 3, title.position = "top", override.aes = list(size = 2))) +
    theme_pub(base = PT) + AX + theme(legend.position = "bottom")
  for (dev in c("png", "pdf")) {
    f <- file.path(out, paste0("T06_16S_vs_dDDH.", dev))
    if (dev == "png") ggsave(f, pB, width = WB, height = 4.2, dpi = 600, bg = "white") else { grDevices::quartz(type = "pdf", file = f, width = WB, height = 4.2); print(pB); invisible(dev.off()) }
    sapote_stamp_files_required(f, "tygs_figures")
  }
}
cat("drew T05", if (nrow(b)) "and T06" else "(no 16S values: T06 not drawn)", "\n")
