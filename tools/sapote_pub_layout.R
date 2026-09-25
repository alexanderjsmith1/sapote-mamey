# Publication layout for Sapote figures (Alex, 2026-09-24).
# Top to bottom: the figure, white space, the PUBLIC caption, a thin rule, then small grey INTERNAL notes
# (tool versions, cutoffs, rulings applied, exclusions, data paths). The public caption is plain scientific
# English; jargon and paths live only in the notes. No governance wording anywhere on the page: run
# tools/figure_render_qc.py on the output folder, which checks the drawn text and CAPTION files.
#
# Usage:
#   source("tools/sapote_pub_layout.R")
#   p <- ggplot(...) + theme_pub()
#   save_pub(p, "FIG_035c_bgc_count_by_genus", "caption_public.md", "caption_internal.md", w = 7.5, h_body = 5)
# Writes <stem>.png (with caption), <stem>.pdf (with caption), <stem>_plot_only.png (for slides) and a
# caption file holding the public caption then the internal notes. The caption file defaults to
# CAPTION.md and refuses to overwrite one that belongs to another figure.
suppressPackageStartupMessages({ library(ggplot2); library(ggtext) })

PUB_INK <- "#17212E"; PUB_SUB <- "#54637A"; PUB_NOTE <- "#8A94A3"
PUB_FONT <- getOption("sapote.pub_font", "Arial")

.pub_read <- function(x) {
  if (is.null(x)) return("")
  txt <- if (length(x) == 1 && file.exists(x)) readLines(x, warn = FALSE) else x
  trimws(paste(txt, collapse = " "))
}

# Draw the PDF with the first device that can render the house font. On macOS only quartz() draws
# Arial (cairo_pdf and pdf() stop with "invalid font type"); elsewhere cairo usually can.
.pub_pdf <- function(fig, file, width, height) {
  devs <- list(
    quartz = function() grDevices::quartz(type = "pdf", file = file, width = width, height = height),
    cairo = function() grDevices::cairo_pdf(file, width = width, height = height),
    pdf = function() grDevices::pdf(file, width = width, height = height))
  if (!identical(Sys.info()[["sysname"]], "Darwin")) devs$quartz <- NULL
  if (!capabilities("cairo")) devs$cairo <- NULL
  errs <- character()
  for (d in names(devs)) {
    ok <- tryCatch({ devs[[d]](); print(fig); grDevices::dev.off(); TRUE },
                   error = function(e) { try(grDevices::dev.off(), silent = TRUE); errs[[d]] <<- conditionMessage(e); FALSE })
    if (ok) return(invisible(d))
  }
  unlink(file)
  stop("no PDF device could draw font '", PUB_FONT, "': ", paste(names(errs), errs, sep = ": ", collapse = "; "))
}

save_pub <- function(p, stem, public_md, internal_md = NULL, w, h_body, title_md = NULL,
                     caption_file = "CAPTION.md", outdir = ".") {
  cap_path <- file.path(outdir, caption_file)
  if (file.exists(cap_path) && !identical(readLines(cap_path, n = 1, warn = FALSE), paste0("# ", stem)))
    stop("caption file ", cap_path, " belongs to another figure; pass caption_file = 'CAPTION_", stem, ".md'")
  pub <- .pub_read(public_md)
  int <- .pub_read(internal_md)
  if (!nzchar(pub)) stop("public caption is empty for ", stem)
  dir.create(outdir, showWarnings = FALSE, recursive = TRUE)
  out <- function(ext) file.path(outdir, paste0(stem, ext))

  ggsave(out("_plot_only.png"), p, width = w, height = h_body, dpi = 300, bg = "white")
  cpl <- (w - 0.6) * 15
  h_cap <- 0.9 + 0.2 * ceiling(nchar(pub) / cpl) +
    if (nzchar(int)) 0.35 + 0.15 * ceiling(nchar(int) / (cpl * 1.35)) else 0
  rule <- paste0("<span style='color:#C9D0D9'>", strrep("─", 60), "</span>")
  cap <- paste0("<span style='font-size:9.5pt; color:", PUB_INK, "'><b>", pub, "</b></span>",
                if (nzchar(int)) paste0("<br><br>", rule, "<br><span style='font-size:6.8pt; color:", PUB_NOTE,
                                        "'>Internal notes: ", int, "</span>") else "")
  cap_theme <- theme(plot.caption = element_textbox_simple(family = PUB_FONT, lineheight = 1.3, hjust = 0,
                                                           margin = margin(t = 36, b = 6)),
                     plot.caption.position = "plot")
  # A patchwork figure gets one caption for the whole figure, not one under its last panel.
  fig <- if (inherits(p, "patchwork")) p + patchwork::plot_annotation(caption = cap, theme = cap_theme)
         else p + labs(caption = cap) + cap_theme
  ggsave(out(".png"), fig, width = w, height = h_body + h_cap, dpi = 300, bg = "white")
  .pub_pdf(fig, out(".pdf"), w, h_body + h_cap)

  md <- gsub("</?i>", "*", pub)
  writeLines(c(paste0("# ", stem), "", "## Caption", "",
               if (!is.null(title_md)) paste0("**", title_md, "** ", md) else md,
               if (nzchar(int)) c("", "## Internal notes", "", int)), cap_path)
  message("wrote ", stem)
  invisible(c(png = out(".png"), pdf = out(".pdf"), plot_only = out("_plot_only.png"), caption = cap_path))
}

theme_pub <- function(base = 11) {
  theme_minimal(base_size = base, base_family = PUB_FONT) +
    theme(plot.title = element_markdown(face = "bold", size = base + 3, colour = PUB_INK),
          plot.subtitle = element_markdown(size = base - 1.5, colour = PUB_SUB, lineheight = 1.2),
          axis.title = element_text(colour = PUB_SUB, size = base - 1), axis.text = element_text(colour = PUB_INK),
          # ggplot2 4.x sets the side elements explicitly, so markdown must be set on each side too
          axis.text.x.bottom = element_markdown(colour = PUB_INK, lineheight = 1.3),
          axis.text.y.left = element_markdown(colour = PUB_INK),
          panel.grid.minor = element_blank(), legend.text = element_markdown(size = base - 1.5),
          legend.title = element_text(size = base - 1, face = "bold"),
          plot.background = element_rect(fill = "white", colour = NA), plot.margin = margin(10, 14, 10, 10))
}
