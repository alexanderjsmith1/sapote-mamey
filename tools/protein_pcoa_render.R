# Draw one protein-class PCoA panel with ggplot2 + ggrepel. Called by tools/protein_pcoa_render.py, never by hand:
#   Rscript protein_pcoa_render.R <spec.json> <output prefix> <stamp>
# The spec is one JSON file written for this run (points, labels, legend text, class tag, colour, stamp). The script refuses a
# spec whose stamp differs from the one it was given, writes <prefix>.pdf/.svg/.png, then <prefix>.stamp so the caller can check
# that these files came from this run. Labels repel from each other and from every cohort point, with thin leader lines.
suppressMessages({library(ggplot2); library(ggrepel); library(jsonlite)})
grDevices::pdf(NULL)   # a null device for incidental graphics calls, so R never leaves an Rplots.pdf in the working folder
a <- commandArgs(TRUE); spec <- fromJSON(a[1]); prefix <- a[2]; stamp <- a[3]
if (!identical(spec$stamp, stamp)) stop("stamp mismatch: refusing to draw a spec from another run")
pts <- as.data.frame(spec$points)
lv <- intersect(c("ref", "mibig", "iso_low", "iso_mid", "iso_high", "iso_unknown"), unique(pts$layer))   # only layers with points
pts$layer <- factor(pts$layer, levels = lv); pts <- pts[order(pts$layer), ]
leg <- spec$legend; col <- spec$colour; midf <- if (is.null(spec$mid_fill)) "white" else spec$mid_fill
labs <- unlist(c(ref = leg$ref, mibig = leg$mibig, iso_low = leg$iso_low, iso_mid = leg$iso_mid, iso_high = leg$iso_high, iso_unknown = leg$iso_unknown))[lv]
pts$ps <- ifelse(pts$layer %in% c("ref", "mibig"), 0.28 * sqrt(3 + 1.5 * sqrt(pts$size)), 1.9)
g <- ggplot(pts, aes(x, y)) +
  geom_point(aes(colour = layer, fill = layer, shape = layer, size = ps, alpha = layer), stroke = 0.45) +
  scale_size_identity() +
  scale_colour_manual(values = c(ref = "#b5b5b5", mibig = "#3a78b5", iso_low = "black", iso_mid = col, iso_high = col, iso_unknown = "#555555"), labels = labs, breaks = lv, name = NULL) +
  scale_fill_manual(values = c(ref = "#b5b5b5", mibig = "#3a78b5", iso_low = col, iso_mid = midf, iso_high = "white", iso_unknown = "white"), labels = labs, breaks = lv, name = NULL) +
  scale_shape_manual(values = c(ref = 16, mibig = 16, iso_low = 21, iso_mid = 21, iso_high = 21, iso_unknown = 23), labels = labs, breaks = lv, name = NULL) +
  scale_alpha_manual(values = c(ref = .7, mibig = .7, iso_low = 1, iso_mid = 1, iso_high = 1, iso_unknown = 1), labels = labs, breaks = lv, name = NULL) +
  guides(colour = guide_legend(override.aes = list(size = unname(c(ref = 2.2, mibig = 2.2, iso_low = 2.4, iso_mid = 2.4, iso_high = 2.4, iso_unknown = 2.4)[lv]),
                                                   stroke = unname(c(ref = 0, mibig = 0, iso_low = .45, iso_mid = .7, iso_high = .9, iso_unknown = .9)[lv])))) +
  annotate("text", x = -Inf, y = Inf, label = spec$tag, hjust = -0.04, vjust = 1.4, fontface = "bold", size = 9 / .pt) +
  scale_y_continuous(expand = expansion(mult = c(.03, .10))) +   # headroom so the class tag sits clear of the points
  labs(x = spec$xlab, y = spec$ylab) + theme_classic(base_size = 9) +
  theme(legend.position = "bottom", legend.direction = "vertical", legend.justification = "left", legend.text = element_text(size = 8),
        legend.key.height = unit(10, "pt"), axis.line = element_line(linewidth = .4), axis.ticks = element_line(linewidth = .4))
if (!is.null(spec$source_style)) {   # M5_452_pcoa_source_style: reference-only figure, outlined points, shape by source, boxed legend
  ss <- spec$source_style
  pts <- pts[order(pts$layer != "mibig"), ]; g$data <- pts   # MIBiG drawn first, reference points on top
  ol <- function(v) if (is.null(v)) "black" else v   # outline colours are options (card 018c0f08_452_pcoa_source_style_colour_options)
  g <- g + scale_colour_manual(values = c(ref = ol(ss$ref_outline), mibig = ol(ss$mibig_outline)), labels = labs, breaks = lv, name = NULL) +
    scale_fill_manual(values = c(ref = ss$ref_fill, mibig = ss$mibig_fill), labels = labs, breaks = lv, name = NULL) +
    scale_shape_manual(values = c(ref = 21, mibig = 24), labels = labs, breaks = lv, name = NULL) +
    scale_alpha_manual(values = c(ref = 1, mibig = 1), labels = labs, breaks = lv, name = NULL) +
    guides(colour = guide_legend(override.aes = list(size = 2.4, stroke = .35))) +
    theme(legend.box.background = element_rect(colour = "black", linewidth = .3), legend.box.margin = margin(3, 3, 3, 3))
}
lab <- if (length(spec$labels)) as.data.frame(spec$labels) else data.frame(x = numeric(0), y = numeric(0), label = character(0))
if (nrow(lab)) {
  iso <- pts[pts$layer %in% c("iso_low", "iso_mid", "iso_high", "iso_unknown"), c("x", "y")]; iso$label <- ""   # empty labels keep text off the points
  g <- g + geom_text_repel(data = rbind(lab[, c("x", "y", "label")], iso), aes(x, y, label = label), inherit.aes = FALSE, size = 8 / .pt,
    min.segment.length = 0, segment.size = .25, segment.colour = "#555555", box.padding = .4, point.padding = .2,
    force = 3, force_pull = .5, max.overlaps = Inf, max.iter = 20000, seed = 1)
}
w <- 7; h <- 7.2
if (!is.null(spec$min_text)) {   # M5_452: floor all text, refuse colliding/clipped labels, save PNG + PDF through the shared helpers
  mt <- spec$min_text; source(mt$layout); source(mt$helper)
  rec <- mt_save(g, prefix, mt$print_width, h * mt$print_width / w, list(min_text_pt = mt$min_text_pt, print_width = mt$print_width, dpi = 600))
  ggsave(paste0(prefix, ".svg"), mt_floor(g, mt$min_text_pt), width = mt$print_width, height = rec$height_in)
  writeLines(stamp, paste0(prefix, ".stamp")); quit(save = "no", status = 0)
}
# cairo_pdf embeds editable text, but on a Mac without XQuartz capabilities("cairo") is TRUE and drawing text still fails
# ("failed to load cairo DLL" is only a warning and no file appears); so draw text into a scratch file first and trust cairo only
# when that file exists and is not empty, then Quartz on a Mac, then base pdf.
cairo_ok <- local({
  f <- tempfile(fileext = ".pdf")
  ok <- tryCatch(suppressWarnings({ grDevices::cairo_pdf(f); grid::grid.text("x"); grDevices::dev.off(); TRUE }),
                 error = function(e) FALSE)
  while (grDevices::dev.cur() > 1) grDevices::dev.off()
  isTRUE(ok) && file.exists(f) && isTRUE(file.info(f)$size > 0)
})
pdf_device <- if (cairo_ok) grDevices::cairo_pdf else if (Sys.info()[["sysname"]] == "Darwin")
  function(filename, width, height, ...) grDevices::quartz(file = filename, type = "pdf", width = width, height = height) else grDevices::pdf
# a Quartz device that cannot open (no window server, sandbox) must still end in base pdf, never in a missing PDF
pdf_ok <- tryCatch({ ggsave(paste0(prefix, ".pdf"), g, width = w, height = h, device = pdf_device); TRUE },
                   error = function(e) FALSE)
while (grDevices::dev.cur() > 1) grDevices::dev.off()
if (!pdf_ok || !isTRUE(file.info(paste0(prefix, ".pdf"))$size > 0))
  ggsave(paste0(prefix, ".pdf"), g, width = w, height = h, device = grDevices::pdf)
ggsave(paste0(prefix, ".svg"), g, width = w, height = h)
ggsave(paste0(prefix, ".png"), g, width = w, height = h, dpi = 600)
writeLines(stamp, paste0(prefix, ".stamp"))
