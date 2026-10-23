# M5_452 (owner, 12 Oct 2026: "make your figures look like the bee figures"; "this should all be bundle features"). Draws a page of protein
# PCoA / TriMap / t-SNE panels in the bee Fig. S9 print style, called by tools/protein_pcoa_render.py --page, never by hand:
#   Rscript protein_pcoa_page.R <page_spec.json> <output prefix> <stamp>
# Style values copied from the bee re-plot kit's render_pcoa_print.R (BEE_PROTEIN_PCOA_REPLOT_KIT_2026-09-29): reference #b5b5b5 and
# MIBiG #3a78b5 (alpha .7); cohort tiers < low: fill #b2182b, edge black; low-mid: fill #f4a582, edge #d6604d; >= mid: fill white,
# edge #d6604d; point area law 0.17*sqrt(3 + 1.5*sqrt(n)) for centroids, 1.25 for cohort points; bold panel tag top-left; repelled
# labels with #555555 leaders (size .25); one shared legend for the page; theme_classic. M5_452 v2: label positions come placed from
# tools/protein_pcoa_render.py (bee greedy placement on the final page geometry), drawn as given; panel limits are fixed (coord_cartesian). Text is raised to the min-text floor and the
# page is saved through tools/sapote_min_text.R mt_save (8 pt floor, SVG collision/clip gate, PDF + PNG), plus an SVG.
suppressMessages({library(ggplot2); library(jsonlite); library(patchwork)})
grDevices::pdf(NULL)
# panels: a list; points and labels: column vectors
a <- commandArgs(TRUE); page <- fromJSON(a[1], simplifyVector = TRUE, simplifyDataFrame = FALSE); prefix <- a[2]; stamp <- a[3]
if (!identical(page$stamp, stamp)) stop("stamp mismatch: refusing to draw a spec from another run")
.pg <- list(page = page, prefix = prefix, stamp = stamp)   # dot names survive helpers that clear the workspace
source(page$min_text$layout); source(page$min_text$helper)
page <- .pg$page; prefix <- .pg$prefix; stamp <- .pg$stamp; mt <- page$min_text; fs <- mt$min_text_pt
lv <- c("ref", "mibig", "iso_low", "iso_mid", "iso_high")
if (is.null(page$legend$mibig)) lv <- setdiff(lv, "mibig")   # no MIBiG point on the page: no MIBiG key
if (!is.null(page$legend$iso_unknown)) lv <- c(lv, "iso_unknown")
COL <- c(ref = "#b5b5b5", mibig = "#3a78b5", iso_low = "black", iso_mid = "#d6604d", iso_high = "#d6604d", iso_unknown = "#555555")
FILL <- c(ref = "#b5b5b5", mibig = "#3a78b5", iso_low = "#b2182b", iso_mid = "#f4a582", iso_high = "white", iso_unknown = "white")
panel <- function(sp) {
  pts <- as.data.frame(lapply(sp$points, unlist), stringsAsFactors = FALSE); pts$layer <- factor(pts$layer, levels = lv); pts <- pts[order(pts$layer), ]
  rps <- if (is.null(page$ref_point_scale)) 1 else as.numeric(page$ref_point_scale)   # --ref-point-scale (opt-in)
  cps <- if (is.null(page$cohort_point_scale)) 1 else as.numeric(page$cohort_point_scale)   # --cohort-point-scale (opt-in)
  pts$ps <- ifelse(pts$layer %in% c("ref", "mibig"), rps * 0.17 * sqrt(3 + 1.5 * sqrt(pts$size)), 1.25 * cps)
  labs <- unlist(page$legend)[lv]
  if (isTRUE(page$legend_slot)) labs <- sub(", best", ",\nbest", labs, fixed = TRUE)   # 018c0f08_458: legend in a grid slot, two lines
  g <- ggplot(pts, aes(x, y)) +
    geom_point(aes(colour = layer, fill = layer, shape = layer, size = ps, alpha = layer), stroke = 0.35, show.legend = TRUE) + scale_size_identity() +
    scale_colour_manual(values = COL, labels = labs, breaks = lv, drop = FALSE, name = NULL) +
    scale_fill_manual(values = FILL, labels = labs, breaks = lv, drop = FALSE, name = NULL) +
    scale_shape_manual(values = c(ref = 16, mibig = 16, iso_low = 21, iso_mid = 21, iso_high = 21, iso_unknown = 23), labels = labs, breaks = lv, drop = FALSE, name = NULL) +
    scale_alpha_manual(values = c(ref = .7, mibig = .7, iso_low = 1, iso_mid = 1, iso_high = 1, iso_unknown = 1), labels = labs, breaks = lv, drop = FALSE, name = NULL) +
    guides(colour = guide_legend(ncol = 1, override.aes = list(size = unname(c(ref=2.2, mibig=2.2, iso_low=2.4, iso_mid=2.4, iso_high=2.4, iso_unknown=2.4)[lv]),
                                                                  stroke = unname(c(ref=0, mibig=0, iso_low=.45, iso_mid=.6, iso_high=.9, iso_unknown=.9)[lv])))) +
    annotate("text", x = -Inf, y = Inf, label = sp$tag, hjust = -0.04, vjust = 1.4, fontface = "bold", size = fs / .pt) +
    coord_cartesian(xlim = unlist(sp$xlim), ylim = unlist(sp$ylim), expand = FALSE) +   # limits from the renderer (PAGE_EXPAND)
    labs(x = sp$xlab, y = sp$ylab) + theme_classic(base_size = fs) +
    theme(axis.text = element_text(size = fs, colour = "black"), axis.line = element_line(linewidth = .3), axis.ticks = element_line(linewidth = .3),
          legend.text = element_text(size = fs), legend.key.height = unit(10, "pt"))
  lab <- if (length(sp$labels$label)) as.data.frame(lapply(sp$labels, unlist), stringsAsFactors = FALSE) else NULL
  if (!is.null(lab) && nrow(lab)) {   # placed labels: leader from the point edge (sx, sy) to the label anchor (x, y)
    g <- g + geom_segment(data = lab, aes(x = sx, y = sy, xend = x, yend = y), inherit.aes = FALSE, colour = page$leader_colour, linewidth = .25)
    if (isTRUE(page$label_box)) {   # 018c0f08_458 --label-over-reference: text on a borderless white box so it reads over grey/blue centroids
      g <- g + geom_label(data = lab, aes(x = x, y = y, label = label, hjust = hjust, vjust = vjust, fontface = face), inherit.aes = FALSE,
                          size = fs / .pt, fill = grDevices::adjustcolor("white", alpha.f = 0.85), label.size = 0,
                          label.padding = unit(0.8, "pt"), label.r = unit(0, "pt"))
    } else {
      g <- g + geom_text(data = lab, aes(x = x, y = y, label = label, hjust = hjust, vjust = vjust, fontface = face), inherit.aes = FALSE,
                         size = fs / .pt)
    }
  }
  if (grepl("^t-SNE", sp$xlab)) {   # t-SNE axes carry no tick numbers: t-SNE coordinates have no units or scale (candidate card)
    g <- g + theme(axis.text = element_blank(), axis.ticks = element_blank())
  }
  mt_floor(g, fs)
}
ps <- lapply(page$panels, panel)
if (!is.null(page$tags) && length(ps) > 1) {   # m5_452_protein_pcoa_multiset_grid: one legend per grid page, from the panel with the most point
  keep <- which.max(sapply(page$panels, function(sp) length(unique(unlist(sp$points$layer)))))   # kinds (a set without a tier would split it)
  ps[-keep] <- lapply(ps[-keep], function(g) g + guides(colour = "none", fill = "none", shape = "none", alpha = "none"))
}
nr <- ceiling(length(page$panels) / page$ncol); extra_in <- 1.0
if (isTRUE(page$legend_slot) && length(ps) < nr * page$ncol) {   # 018c0f08_458 --legend-in-empty-slot: the shared legend fills the first empty slot
  ps <- c(ps, list(guide_area())); extra_in <- 0.15
}
pg <- wrap_plots(ps, ncol = page$ncol) + plot_layout(guides = "collect") +
  plot_annotation(tag_levels = if (is.null(page$tags)) "a" else list(unlist(page$tags))) & theme(   # m5_452_protein_pcoa_multiset_grid: page$tags continue the letters across grid pages
                                            legend.position = "bottom", legend.direction = "vertical", legend.justification = "left",
                                            plot.tag = element_text(face = "bold", size = fs))
if (isTRUE(page$legend_slot)) pg <- pg & theme(legend.key.spacing.y = unit(5, "pt"))   # 018c0f08_458: two-line entries kept apart
if (isTRUE(page$probe)) {   # M5_452 trial PDF at the final size, no gates (the renderer reads the panel frames from it)
  mt_probe(pg, prefix, mt$print_width, page$panel_height * nr + extra_in, list(min_text_pt = fs, print_width = mt$print_width))
} else {
  rec <- mt_save(pg, prefix, mt$print_width, page$panel_height * nr + extra_in, list(min_text_pt = fs, print_width = mt$print_width, dpi = 600, min_panel_frac = 0.2))
  ggsave(paste0(prefix, ".svg"), pg, width = mt$print_width, height = rec$height_in)
  ggsave(paste0(prefix, "_plot_only.png"), pg, width = mt$print_width, height = rec$height_in, dpi = 300, bg = "white")
}
sapote_stamp_files_required(paste0(prefix, if (isTRUE(page$probe)) ".pdf" else c(".png", "_plot_only.png", ".pdf", ".svg")), "protein_pcoa_page")
if (!isTRUE(page$probe)) {
  namespaces <- sort(loadedNamespaces())
  execution <- list(schema="sapote-mamey.r-page-execution.v1", stamp=stamp,
    scope="CURRENT_RENDER_PROCESS", renderer="tools/protein_pcoa_page.R",
    labeler="BEE_GREEDY_PRINT_POINT_PLACEMENT_AND_R_GEOM_TEXT",
    numeric_fit_execution="NOT_EXECUTED_BY_THIS_RENDERER",
    r_version=R.version.string, platform=R.version$platform,
    loaded_namespace_versions=setNames(lapply(namespaces,function(n) as.character(getNamespaceVersion(n))),namespaces),
    session_info=capture.output(sessionInfo()))
  jsonlite::write_json(execution,paste0(prefix,"_runtime.json"),auto_unbox=TRUE,pretty=TRUE)
}
writeLines(stamp, paste0(prefix, ".stamp"))
