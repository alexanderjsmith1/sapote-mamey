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
lv <- intersect(c("ref", "mibig", "iso_low", "iso_high"), unique(pts$layer))   # only layers with points
pts$layer <- factor(pts$layer, levels = lv); pts <- pts[order(pts$layer), ]
leg <- spec$legend; col <- spec$colour
labs <- c(ref = leg$ref, mibig = leg$mibig, iso_low = leg$iso_low, iso_high = leg$iso_high)[lv]
pts$ps <- ifelse(pts$layer %in% c("ref", "mibig"), 0.28 * sqrt(3 + 1.5 * sqrt(pts$size)), 1.9)
g <- ggplot(pts, aes(x, y)) +
  geom_point(aes(colour = layer, fill = layer, shape = layer, size = ps, alpha = layer), stroke = 0.45) +
  scale_size_identity() +
  scale_colour_manual(values = c(ref = "#b5b5b5", mibig = "#3a78b5", iso_low = "black", iso_high = col), labels = labs, breaks = lv, name = NULL) +
  scale_fill_manual(values = c(ref = "#b5b5b5", mibig = "#3a78b5", iso_low = col, iso_high = "white"), labels = labs, breaks = lv, name = NULL) +
  scale_shape_manual(values = c(ref = 16, mibig = 16, iso_low = 21, iso_high = 21), labels = labs, breaks = lv, name = NULL) +
  scale_alpha_manual(values = c(ref = .7, mibig = .7, iso_low = 1, iso_high = 1), labels = labs, breaks = lv, name = NULL) +
  guides(colour = guide_legend(override.aes = list(size = unname(c(ref = 2.2, mibig = 2.2, iso_low = 2.4, iso_high = 2.4)[lv]),
                                                   stroke = unname(c(ref = 0, mibig = 0, iso_low = .45, iso_high = .9)[lv])))) +
  annotate("text", x = -Inf, y = Inf, label = spec$tag, hjust = -0.04, vjust = 1.4, fontface = "bold", size = 9 / .pt) +
  scale_y_continuous(expand = expansion(mult = c(.03, .10))) +   # headroom so the class tag sits clear of the points
  labs(x = spec$xlab, y = spec$ylab) + theme_classic(base_size = 9) +
  theme(legend.position = "bottom", legend.direction = "vertical", legend.justification = "left", legend.text = element_text(size = 7.5),
        legend.key.height = unit(10, "pt"), axis.line = element_line(linewidth = .4), axis.ticks = element_line(linewidth = .4))
lab <- if (length(spec$labels)) as.data.frame(spec$labels) else data.frame(x = numeric(0), y = numeric(0), label = character(0))
if (nrow(lab)) {
  iso <- pts[pts$layer %in% c("iso_low", "iso_high"), c("x", "y")]; iso$label <- ""   # empty labels keep text off the points
  g <- g + geom_text_repel(data = rbind(lab[, c("x", "y", "label")], iso), aes(x, y, label = label), inherit.aes = FALSE, size = 2.1,
    min.segment.length = 0, segment.size = .25, segment.colour = "#555555", box.padding = .4, point.padding = .2,
    force = 3, force_pull = .5, max.overlaps = Inf, max.iter = 20000, seed = 1)
}
w <- 7; h <- 7.2
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
