# Minimum printed text size for the bundle's R figure cards (M5_452_render_cards_min_text_8pt, 12 Oct 2026).
# docs/FIGURE_STYLE.md "Publication artwork gate": the smallest plot label, tick, legend or annotation is at least 8 pt at the declared
# physical width (SINGLE_COLUMN 3.5 in, DOUBLE_COLUMN 7.2 in). This helper never shrinks text. It
#   1. raises every theme text element and every text layer (geom_text/label, ggrepel, ggtext) below the floor to the floor;
#   2. draws at the declared print width, growing the canvas height by the extra fixed height the larger text needs;
#   3. draws an SVG check page (svglite) and measures every text box: text outside its clip area or two overlapping text boxes
#      fail closed (stop "MIN_TEXT_DOES_NOT_FIT"); stacked rows that collide grow the height (x1.08 per step, up to max_height 9.5 in);
#      it also fails closed when the panel area left at the print width falls below min_panel_frac of it.
# Use: source("tools/sapote_min_text.R"); mt_save(p, out_stem, w_design, h_design, cfg)
#   cfg: min_text_pt (8), print_width (3.5/7.2), dpi, rows (stacked text rows -> panel height = rows x 1.5 x text height),
#   max_panel_in (8.5; above it MIN_TEXT_TOO_TALL: the card applies its overflow option), max_height (9.5).
#   mt_value_limit() sizes the value axis so measured end-of-bar labels fit inside the panel.
# Writes <out_stem>.png and .pdf (via sapote_pub_layout.R .pub_pdf) and <out_stem>_min_text.json.

source(file.path(dirname(normalizePath(sys.frame(1)$ofile)), "sapote_stamp_required.R"))

# text colour lighter than near-black counts as grey: relative luminance > 0.04 (house ink #17212E = 0.015, house sub-ink #54637A = 0.12)
mt_light <- function(col) {
  if (is.null(col) || length(col) != 1 || is.na(col) || identical(col, "white") || identical(col, "#FFFFFF")) return(FALSE)
  v <- tryCatch(grDevices::col2rgb(col)[, 1] / 255, error = function(e) NULL); if (is.null(v)) return(FALSE)
  lum <- sum(c(0.2126, 0.7152, 0.0722) * v^2.2); lum > 0.04 && lum < 0.9
}
.mt_font <- function() if (exists("PUB_FONT")) get("PUB_FONT") else "Arial"   # cards that do not source sapote_pub_layout.R
.mt_text_layers <- c("GeomText", "GeomLabel", "GeomTextRepel", "GeomLabelRepel", "GeomRichText", "GeomTextBox")

mt_floor <- function(p, min_pt) {
  log <- list()
  if (inherits(p, "patchwork")) {   # floor every member plot, then the outer plot
    p$patches$plots <- lapply(p$patches$plots, function(q) { r <- mt_floor(q, min_pt); log <<- c(log, attr(r, "mt_log")); r })
  }
  full <- ggplot2::complete_theme(p$theme)
  for (nm in names(ggplot2::get_element_tree())) {
    el <- tryCatch(ggplot2::calc_element(nm, full), error = function(e) NULL)
    if (is.null(el) || !inherits(el, "ggplot2::element_text") && !inherits(el, "element_text")) next
    if (is.null(el$size) || !is.numeric(el$size) || el$size >= min_pt) next
    log[[length(log) + 1]] <- list(element = nm, from_pt = el$size, to_pt = min_pt)
    if (!is.null(p$theme[[nm]])) { e <- p$theme[[nm]]; e$size <- min_pt; p$theme[[nm]] <- e }
    else { el$size <- min_pt; p$theme[[nm]] <- el }
  }
  # The owner (12 Oct): light-grey text is not acceptable in a publication figure -> black; axis titles keep >= 0.75 x text height
  # clear of the tick labels.
  for (nm in names(ggplot2::get_element_tree())) {
    el <- tryCatch(ggplot2::calc_element(nm, ggplot2::complete_theme(p$theme)), error = function(e) NULL)
    if (is.null(el) || !inherits(el, "ggplot2::element_text") && !inherits(el, "element_text")) next
    if (mt_light(el$colour)) {
      log[[length(log) + 1]] <- list(element = nm, colour_from = el$colour, colour_to = "black")
      if (!is.null(p$theme[[nm]])) { e <- p$theme[[nm]]; e$colour <- "black"; p$theme[[nm]] <- e } else { el$colour <- "black"; p$theme[[nm]] <- el }
    }
  }
  # page margins >= 5 pt on every side so no text sits within the 3 pt page-edge band of the collision gate
  pm <- grid::convertUnit(ggplot2::calc_element("plot.margin", ggplot2::complete_theme(p$theme)), "pt", valueOnly = TRUE)
  if (length(pm) == 4 && any(pm < 5)) p$theme$plot.margin <- ggplot2::margin(max(pm[1], 5), max(pm[2], 5), max(pm[3], 5), max(pm[4], 5))
  # an end tick label is centred on the panel edge: keep left/right page margins >= half its measured width + 3 pt
  if (!inherits(p, "patchwork")) {
    # numeric x axes only, and only the first and last labels (they sit on the panel edges); category labels are centred on bands
    # (fix 12 Oct 23:55: the widest category name had squeezed C02's panel until the host-group names collided)
    xl <- tryCatch(unlist(lapply(ggplot2::ggplot_build(p)$layout$panel_params, function(pp) {
      if (isTRUE(tryCatch(pp$x$is_discrete(), error = function(e) FALSE))) return(character(0))
      v <- pp$x$get_labels(); v <- v[!is.na(v) & nzchar(v)]; if (length(v)) v[c(1, length(v))] else character(0) })), error = function(e) NULL)
    xl <- xl[!is.na(xl) & nzchar(xl)]
    if (length(xl)) {
      half <- max(systemfonts::string_width(gsub("<[^>]+>", "", xl), family = .mt_font(), size = min_pt)) / 2 + 3
      pm <- grid::convertUnit(ggplot2::calc_element("plot.margin", ggplot2::complete_theme(p$theme)), "pt", valueOnly = TRUE)
      if (length(pm) == 4 && (pm[2] < half || pm[4] < half)) p$theme$plot.margin <- ggplot2::margin(pm[1], max(pm[2], half), pm[3], max(pm[4], half))
    }
  }
  gap <- 0.75 * min_pt
  for (nm in c("axis.title.x", "axis.title.x.bottom")) { e <- p$theme[[nm]]; if (is.null(e)) e <- ggplot2::calc_element(nm, ggplot2::complete_theme(p$theme))
    e$margin <- ggplot2::margin(t = gap); p$theme[[nm]] <- e }
  for (nm in c("axis.title.y", "axis.title.y.left")) { e <- p$theme[[nm]]; if (is.null(e)) e <- ggplot2::calc_element(nm, ggplot2::complete_theme(p$theme))
    e$margin <- ggplot2::margin(r = gap); p$theme[[nm]] <- e }
  for (i in seq_along(p$layers)) {
    L <- p$layers[[i]]
    if (!any(class(L$geom) %in% .mt_text_layers)) next
    if (!is.null(L$aes_params$colour) && mt_light(L$aes_params$colour)) {
      log[[length(log) + 1]] <- list(element = paste0("layer", i, ":colour"), colour_from = L$aes_params$colour, colour_to = "black")
      L$aes_params$colour <- "black"
    }
    s <- L$aes_params$size
    if (is.null(s)) s <- L$geom$default_aes$size
    if (is.numeric(s) && s * ggplot2::.pt < min_pt - 1e-9) {
      log[[length(log) + 1]] <- list(element = paste0("layer", i, ":", class(L$geom)[1]), from_pt = s * ggplot2::.pt, to_pt = min_pt)
      L$aes_params$size <- min_pt / ggplot2::.pt
    }
  }
  attr(p, "mt_log") <- log
  p
}

.mt_grob <- function(p) if (inherits(p, "patchwork")) patchwork::patchworkGrob(p) else ggplot2::ggplotGrob(p)
.mt_fixed <- function(u) sum(grid::convertUnit(u[grid::unitType(u) != "null"], "in", valueOnly = TRUE))   # sum/grob units count; pure null (panels) do not


# Text boxes drawn by svglite (x/y/anchor/rotation/font-size/textLength, in pt) and the clip rectangle each sits under.
mt_text_boxes <- function(svg) {
  doc <- xml2::read_xml(svg); xml2::xml_ns_strip(doc)
  clips <- list()
  for (cp in xml2::xml_find_all(doc, "//clipPath")) {
    r <- xml2::xml_find_first(cp, "./rect")
    clips[[xml2::xml_attr(cp, "id")]] <- as.numeric(vapply(c("x", "y", "width", "height"), function(k) xml2::xml_attr(r, k), ""))
  }
  out <- list()
  vb <- as.numeric(strsplit(xml2::xml_attr(doc, "viewBox"), " ")[[1]])   # page box in pt
  for (t in xml2::xml_find_all(doc, "//text")) {
    txt <- xml2::xml_text(t); if (!nzchar(trimws(txt))) next
    st <- xml2::xml_attr(t, "style"); fs <- as.numeric(sub(".*font-size: *([0-9.]+)px.*", "\\1", st))
    w <- as.numeric(sub("px", "", xml2::xml_attr(t, "textLength"))); anc <- xml2::xml_attr(t, "text-anchor"); if (is.na(anc)) anc <- "start"
    a0 <- switch(anc, start = 0, middle = -w / 2, end = -w)
    tr <- xml2::xml_attr(t, "transform"); ang <- 0
    if (!is.na(tr)) {
      xy <- as.numeric(strsplit(sub(".*translate\\(([^)]*)\\).*", "\\1", tr), ",")[[1]])
      if (grepl("rotate", tr)) ang <- as.numeric(sub(".*rotate\\(([^)]*)\\).*", "\\1", tr))
    } else xy <- as.numeric(c(xml2::xml_attr(t, "x"), xml2::xml_attr(t, "y")))
    lx <- c(a0, a0 + w, a0 + w, a0); ly <- c(-0.72 * fs, -0.72 * fs, 0.21 * fs, 0.21 * fs)   # Arial cap/descender
    th <- ang * pi / 180; gx <- xy[1] + lx * cos(th) - ly * sin(th); gy <- xy[2] + lx * sin(th) + ly * cos(th)
    cid <- NA; anc_g <- xml2::xml_find_first(t, "ancestor::g[@clip-path][1]")
    if (!inherits(anc_g, "xml_missing")) cid <- sub("url\\(#(.*)\\)", "\\1", xml2::xml_attr(anc_g, "clip-path"))
    out[[length(out) + 1]] <- data.frame(text = substr(txt, 1, 40), size = fs, x0 = min(gx), x1 = max(gx), y0 = min(gy), y1 = max(gy),
                                         angle = ang, clip = cid, stringsAsFactors = FALSE)
  }
  b <- do.call(rbind, out)
  # halo copies (ggrepel bg.colour / shadowtext draw one label several times, offset by bg.r): keep one per text and place
  cx <- (b$x0 + b$x1) / 2; cy <- (b$y0 + b$y1) / 2; dup <- rep(FALSE, nrow(b))
  for (i in seq_len(nrow(b))[-1]) {
    j <- which(!dup[seq_len(i - 1)] & b$text[seq_len(i - 1)] == b$text[i] & b$size[seq_len(i - 1)] == b$size[i] &
               abs(cx[seq_len(i - 1)] - cx[i]) < 1.5 & abs(cy[seq_len(i - 1)] - cy[i]) < 1.5)
    if (length(j)) dup[i] <- TRUE
  }
  b <- b[!dup, ]
  # ggtext/gridtext draws rich labels word by word: merge words on one baseline (same clip, angle, size) into one line box
  b <- b[order(b$clip, b$angle, round(b$y1, 1), b$x0), ]; keep <- rep(TRUE, nrow(b))
  for (i in seq_len(nrow(b))[-1]) {
    k <- max(which(keep[seq_len(i - 1)]))
    if (identical(b$clip[i], b$clip[k]) && b$angle[i] == 0 && b$angle[k] == 0 && abs(b$y1[i] - b$y1[k]) < 0.05 &&
        b$size[i] == b$size[k] && b$x0[i] - b$x1[k] >= 0.1 * b$size[i] && b$x0[i] - b$x1[k] < 0.5 * b$size[i] && b$x0[i] >= b$x0[k] &&
        !(grepl("^[-0-9.,%]+$", b$text[i]) && grepl("[-0-9.,%]+$", b$text[k]))) {   # words are a space apart; numbers (ticks) never merge (fix 12 Oct 23:40)
      b$x1[k] <- max(b$x1[k], b$x1[i]); b$text[k] <- substr(paste(b$text[k], b$text[i]), 1, 40); keep[i] <- FALSE
    }
  }
  b <- b[keep, ]; attr(b, "clips") <- clips; attr(b, "page") <- vb; b
}

# Problems: text outside its clip rectangle (clipped) and pairs of overlapping text boxes (colliding/touching), tolerance tol pt.
mt_text_problems <- function(b, tol = 0.25, clip_tol = 1) {
  clips <- attr(b, "clips"); clipped <- character(0); clipped_x <- FALSE
  for (i in seq_len(nrow(b))) {
    r <- clips[[b$clip[i]]]; if (is.null(r)) next
    cx <- b$x0[i] < r[1] - clip_tol || b$x1[i] > r[1] + r[3] + clip_tol
    cy <- b$y0[i] < r[2] - clip_tol || b$y1[i] > r[2] + r[4] + clip_tol
    pg <- attr(b, "page"); edge <- 3   # pt: text keeps >= 3 pt from the page edge (M3 review, 12 Oct)
    if (!is.null(pg) && (b$x0[i] < pg[1] + edge || b$x1[i] > pg[1] + pg[3] - edge)) cx <- TRUE
    if (!is.null(pg) && (b$y0[i] < pg[2] + edge - 1 || b$y1[i] > pg[2] + pg[4] - edge + 1)) cy <- TRUE
    if (cx || cy) clipped <- c(clipped, b$text[i])
    if (cx) clipped_x <- TRUE   # left/right clipping cannot be fixed by a taller canvas
  }
  o <- order(b$x0); b <- b[o, ]; hits <- list(); stack_only <- TRUE
  for (i in seq_len(nrow(b))) {
    j <- i + 1
    while (j <= nrow(b) && b$x0[j] < b$x1[i] - tol) {
      if (b$y0[j] < b$y1[i] - tol && b$y0[i] < b$y1[j] - tol) {
        hits[[length(hits) + 1]] <- paste0(b$text[i], " | ", b$text[j])
        ox <- min(b$x1[i], b$x1[j]) - max(b$x0[i], b$x0[j]); oy <- min(b$y1[i], b$y1[j]) - max(b$y0[i], b$y0[j])
        if (!(b$angle[i] == 0 && b$angle[j] == 0 && oy < ox)) stack_only <- FALSE   # only vertical stacking is fixable by height
      }
      j <- j + 1
    }
  }
  list(clipped = unique(clipped), overlaps = unlist(hits), height_fixable = !clipped_x && stack_only && (length(hits) > 0 || length(clipped) > 0))
}


# ---- layout rules (M3/owner review of the first 8 pt B01, 12 Oct) -------------------------------------------------------------
mt_min_pt <- function(cfg) if (is.null(cfg$min_text_pt)) 8 else as.numeric(cfg$min_text_pt)
mt_print_width <- function(cfg, w) if (!is.null(cfg$print_width)) as.numeric(cfg$print_width) else if (w <= 3.5) 3.5 else 7.2
# row pitch >= 1.5 x the text height: 1.5 x 8 pt = 12 pt = 0.167 in per stacked text row
mt_pitch_in <- function(cfg) 1.5 * mt_min_pt(cfg) / 72
mt_max_panel_in <- function(cfg) if (is.null(cfg$max_panel_in)) 8.5 else as.numeric(cfg$max_panel_in)
# Room for end-of-bar value labels: measure the widest label (Arial, at the floor) and extend the value axis so the data end at
# panel_width - label_width - padding. Returns the axis upper limit in data units. Never shrinks the text.
mt_value_limit <- function(p, labels, vmax, cfg, w, pad_pt = 4) {
  W <- mt_print_width(cfg, w); minpt <- mt_min_pt(cfg)
  pdf(NULL); on.exit(dev.off(), add = TRUE)
  fw <- .mt_fixed(.mt_grob(mt_floor(p, minpt))$widths)
  lw <- max(systemfonts::string_width(as.character(labels), family = .mt_font(), size = minpt)) / 72 + pad_pt / 72
  panel <- W - fw
  if (panel - lw <= 0.25 * panel)
    stop(sprintf("MIN_TEXT_DOES_NOT_FIT: value labels need %.2f in of a %.2f in panel", lw, panel), call. = FALSE)
  vmax * panel / (panel - lw)
}

# Axis upper limit so labels starting at data positions `starts` (left-aligned) end inside the panel: lim >= start/(1 - (lw+pad)/panel).
mt_start_limit <- function(p, starts, labels, cfg, w, min_limit, pad_pt = 4) {
  W <- mt_print_width(cfg, w); minpt <- mt_min_pt(cfg)
  pdf(NULL); on.exit(dev.off(), add = TRUE)
  panel <- W - .mt_fixed(.mt_grob(mt_floor(p, minpt))$widths)
  lw <- systemfonts::string_width(gsub("<[^>]+>", "", as.character(labels)), family = .mt_font(), size = minpt, italic = FALSE) / 72 + pad_pt / 72
  frac <- 1 - lw / panel
  if (any(frac <= 0.2)) stop("MIN_TEXT_DOES_NOT_FIT: a label is wider than 80% of the panel", call. = FALSE)
  max(min_limit, max(starts / frac))
}

# M5_452 page: the PDF mt_save would write first (same text floor, width and grown height), without the SVG gate.
mt_probe <- function(p, out, w, h, cfg) {
  min_pt <- if (is.null(cfg$min_text_pt)) 8 else as.numeric(cfg$min_text_pt)
  W <- if (!is.null(cfg$print_width)) as.numeric(cfg$print_width) else if (w <= 3.5) 3.5 else 7.2
  pdf(NULL); on.exit(dev.off(), add = TRUE)
  fh0 <- .mt_fixed(.mt_grob(p)$heights); q <- mt_floor(p, min_pt); fh1 <- .mt_fixed(.mt_grob(q)$heights)
  H <- h + max(0, fh1 - fh0)
  .pub_pdf(q, paste0(out, ".pdf"), W, H)
  sapote_stamp_files_required(paste0(out, ".pdf"), "sapote_min_text_probe")
  invisible(H)
}

mt_save <- function(p, out, w, h, cfg) {
  min_pt <- if (is.null(cfg$min_text_pt)) 8 else as.numeric(cfg$min_text_pt)
  W <- if (!is.null(cfg$print_width)) as.numeric(cfg$print_width) else if (w <= 3.5) 3.5 else 7.2
  frac <- if (is.null(cfg$min_panel_frac)) 0.35 else as.numeric(cfg$min_panel_frac)
  pdf(NULL); on.exit(dev.off(), add = TRUE)            # text measurement device
  g0 <- .mt_grob(p); fh0 <- .mt_fixed(g0$heights); fw0 <- .mt_fixed(g0$widths)
  q <- mt_floor(p, min_pt); log <- attr(q, "mt_log")
  g1 <- .mt_grob(q); fh1 <- .mt_fixed(g1$heights); fw1 <- .mt_fixed(g1$widths)
  H <- h + max(0, fh1 - fh0)   # grow the height by the extra fixed height the larger text needs; width stays the print width
  if (!is.null(cfg$rows)) {   # stacked text rows: panel height from the row count at >= 1.5 x text height (never shrink text)
    need <- as.numeric(cfg$rows) * mt_pitch_in(cfg)
    if (need > mt_max_panel_in(cfg))
      stop(sprintf("MIN_TEXT_TOO_TALL: %d rows at %.3f in need a %.2f in panel (> %.2f in); choose an overflow option",
                   as.integer(cfg$rows), mt_pitch_in(cfg), need, mt_max_panel_in(cfg)), call. = FALSE)
    H <- max(H, fh1 + need + 0.04)
  }
  panel_w <- W - fw1; panel_h <- H - fh1
  rec <- list(min_text_pt = min_pt, print_width_in = W, rows = if (is.null(cfg$rows)) NA else cfg$rows, row_pitch_in = mt_pitch_in(cfg),
              overflow = if (is.null(cfg$overflow_used)) NA else cfg$overflow_used, design_width_in = w, design_height_in = h, height_in = H,
              fixed_width_in = fw1, fixed_height_in = fh1, panel_width_in = panel_w, panel_height_in = panel_h,
              min_panel_frac = frac, floored = log)
  writeLines(jsonlite::toJSON(rec, auto_unbox = TRUE, pretty = TRUE, digits = 4), paste0(out, "_min_text.json"))
  if (panel_w < frac * W || panel_h < frac * (h - fh0))
    stop(sprintf("MIN_TEXT_DOES_NOT_FIT: at %.1f pt and %.2f in wide the panel keeps %.2f in of %.2f in (needs >= %.0f%%)",
                 min_pt, W, panel_w, W, 100 * frac), call. = FALSE)
  # Collision and clipping check on the drawn page; grow the height while the only problem is stacked rows.
  Hmax <- if (is.null(cfg$max_height)) 9.5 else as.numeric(cfg$max_height); svg <- paste0(out, "_text_check.svg")
  repeat {
    svglite::svglite(svg, width = W, height = H); print(q); invisible(dev.off())
    sapote_stamp_files_required(svg, "sapote_min_text_check")
    pr <- mt_text_problems(mt_text_boxes(svg))
    if (length(pr$clipped) == 0 && length(pr$overlaps) == 0) break
    if (pr$height_fixable && H * 1.08 <= Hmax) { H <- H * 1.08; next }   # stacked rows or top/bottom clipping only
    rec$height_in <- H; rec$clipped_text <- head(pr$clipped, 20); rec$overlapping_text <- head(pr$overlaps, 20)
    writeLines(jsonlite::toJSON(rec, auto_unbox = TRUE, pretty = TRUE, digits = 4), paste0(out, "_min_text.json"))
    stop(sprintf("MIN_TEXT_DOES_NOT_FIT: %d clipped text item(s) [%s], %d overlapping pair(s) [%s] at %.1f pt, %.2f x %.2f in",
                 length(pr$clipped), paste(head(pr$clipped, 3), collapse = "; "), length(pr$overlaps),
                 paste(head(pr$overlaps, 3), collapse = "; "), min_pt, W, H), call. = FALSE)
  }
  rec$height_in <- H; rec$clipped_text <- list(); rec$overlapping_text <- list()
  writeLines(jsonlite::toJSON(rec, auto_unbox = TRUE, pretty = TRUE, digits = 4), paste0(out, "_min_text.json"))
  ggplot2::ggsave(paste0(out, ".png"), q, width = W, height = H, dpi = cfg$dpi, bg = "white")
  .pub_pdf(q, paste0(out, ".pdf"), W, H)
  sapote_stamp_files_required(paste0(out, c(".png", ".pdf")), "sapote_min_text")
  invisible(rec)
}
