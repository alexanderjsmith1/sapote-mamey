#!/usr/bin/env Rscript
# Rectangular phylogram with exact metadata joins and optional titled annotation strips.

suppressPackageStartupMessages({
  library(ape); library(ggtree); library(ggplot2); library(aplot); library(treeio); library(patchwork)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) stop("Usage: ggtree_rect_heatmap.R <nwk> <metadata.tsv> <out_prefix> [focal_csv]")
nwk <- args[1]; tsv <- args[2]; out <- args[3]
focal <- if (length(args) >= 4 && nzchar(args[4])) strsplit(args[4], ",")[[1]] else character(0)

script_arg <- grep("^--file=", commandArgs(), value = TRUE)
if (length(script_arg) != 1) stop("Cannot bind renderer location")
script_path <- sub("^--file=", "", script_arg)
if (!file.exists(script_path)) script_path <- gsub("~+~", " ", script_path, fixed=TRUE)
script_dir <- dirname(normalizePath(script_path, mustWork=TRUE))
checker <- file.path(script_dir, "tree_sanity_check.py")
python <- Sys.getenv("SAPOTE_PYTHON", Sys.which("python3"))
if (!file.exists(checker) || !nzchar(python)) stop("Tree checker or Python unavailable")
if (nzchar(Sys.getenv("GG_SKIP_GUARD")) || nzchar(Sys.getenv("GG_GATE_EXEMPTION")))
  stop("Unbound guard overrides are not supported; provide a validated analysis tree")
gate_tree <- Sys.getenv("GG_GATE_TREE", nwk)
display_receipt <- Sys.getenv("GG_DISPLAY_RECEIPT")
display_sha <- Sys.getenv("GG_DISPLAY_RECEIPT_SHA256")
gate_args <- c(shQuote(nwk))
if (nzchar(display_receipt)) {
  checker <- file.path(script_dir, "gate_stem_aware.py")
  if (!file.exists(checker) || !nzchar(display_sha)) stop("Verified display receipt and checker required")
  gate_args <- c(gate_args, "--metadata", shQuote(tsv), "--receipt", shQuote(display_receipt),
                 "--receipt-sha256", shQuote(display_sha))
  if (nzchar(Sys.getenv("GG_GATE_TREE"))) gate_args <- c(gate_args, "--parent", shQuote(gate_tree))
} else if (normalizePath(gate_tree, mustWork=TRUE) != normalizePath(nwk, mustWork=TRUE)) {
  stop("A distinct analysis parent requires a hash-bound display receipt")
} else if (nzchar(display_sha)) {
  stop("Display receipt hash requires a receipt")
}
if (nzchar(Sys.getenv("GG_LOCKED_ROOT_RECEIPT"))) {   # .452: registry-LOCKED outgroup root edge, from a hash-bound receipt
  if (!nzchar(display_receipt)) stop("Locked root edge requires a bound display receipt")
  gate_args <- c(gate_args, "--locked-root-receipt", shQuote(Sys.getenv("GG_LOCKED_ROOT_RECEIPT")),
                 "--locked-root-receipt-sha256", shQuote(Sys.getenv("GG_LOCKED_ROOT_RECEIPT_SHA256")))
}
diagnostic_receipt <- Sys.getenv("GG_DIAGNOSTIC_ROOTING_RECEIPT")
if (nzchar(diagnostic_receipt)) {
  if (!nzchar(display_receipt)) stop("Diagnostic requires a bound display receipt")
  gate_args <- c(gate_args, "--diagnostic-rooting-receipt", shQuote(diagnostic_receipt),
                 "--diagnostic-rooting-sha256", shQuote(Sys.getenv("GG_DIAGNOSTIC_ROOTING_SHA256")))
}
gate_out <- suppressWarnings(system2(python, c(shQuote(checker), gate_args), stdout=TRUE, stderr=TRUE))
gate_rc <- attr(gate_out, "status"); if (is.null(gate_rc)) gate_rc <- 0
if (gate_rc != 0) { cat(paste(gate_out, collapse="\n"), "\n", file=stderr()); quit(status=gate_rc) }

display_note <- grep("^DISPLAY_NOTE: ", gate_out, value=TRUE)
display_note <- sub("^DISPLAY_NOTE: ", "", display_note)
if (nzchar(display_receipt) && any(file.exists(paste0(out, c(".pdf", ".png", ".session.txt", ".render_receipt.json", ".methods.txt")))))
  stop("Bound display render outputs already exist; use a new output prefix")

source(file.path(script_dir, "tree_annotation_geometry.R"))
if (Sys.getenv("GG_STRIPS", "0") != "0") {
  annotation_gate <- file.path(script_dir, "tree_annotation_gate.py")
  annotation_args <- c(shQuote(annotation_gate),shQuote(tsv))
  if (Sys.getenv("GG_STRIP_KIND","source") == "activity") annotation_args <- c(annotation_args,"--activity")
  if (Sys.getenv("GG_STRIPS", "0") == "2") annotation_args <- c(annotation_args,"--require-geography")
  if (Sys.getenv("GG_BLANK_MISSING", "0") == "1") annotation_args <- c(annotation_args,"--allow-blank-reference")
  annotation_out <- suppressWarnings(system2(python,annotation_args,stdout=TRUE,stderr=TRUE))
  annotation_rc <- attr(annotation_out,"status")
  if (!is.null(annotation_rc) && annotation_rc != 0) stop(paste(annotation_out,collapse="\n"))
}
activity_spec <- jsonlite::fromJSON(Sys.getenv("GG_ACTIVITY_SPEC", "[]"))
split_activity <- is.data.frame(activity_spec) && nrow(activity_spec) > 0
tr <- read.tree(nwk)
md <- read.delim(tsv, sep = "\t", quote = "", stringsAsFactors = FALSE, check.names = FALSE)
if (!all(c("tip", "label") %in% names(md))) stop("Metadata requires tip and label columns")
if (length(focal) == 0 && "role" %in% names(md))
  focal <- md$tip[tolower(md$role) == "query"]
if (anyDuplicated(tr$tip.label) || anyDuplicated(md$tip)) stop("Duplicate tip identity")
if (!setequal(tr$tip.label, md$tip)) stop("Tree and metadata tip sets must match exactly")
if (any(is.na(md$label) | !nzchar(trimws(md$label)))) stop("Missing display labels")
if (any(grepl("(unnamed)", md$label, fixed=TRUE))) stop("Unresolved display labels")
for (c in c("category", "source")) if (!c %in% names(md)) md[[c]] <- NA
if (is.null(tr$edge.length) || any(!is.finite(tr$edge.length)) || any(tr$edge.length < 0)) stop("Valid branch lengths required")
md$disp <- ifelse(is.na(md$label) | md$label == "", md$tip, md$label); md$label <- NULL
# .452 GG_LOCKED_ROOT_EDGE: the gate (run above, on the unshortened tree) exempted the ingroup half of the root edge to
# a registry-LOCKED outgroup. Draw both root edges short (display only), with a break mark and the true length printed.
locked_edge <- suppressWarnings(as.numeric(Sys.getenv("GG_LOCKED_ROOT_EDGE")))
root_break <- NULL
if (is.finite(locked_edge)) {
  .root <- Ntip(tr) + 1
  .re <- which(tr$edge[, 1] == .root)
  .og <- which(tolower(tr$tip.label) %in% tolower(tr$tip.label[grepl("outgroup", tr$tip.label, ignore.case = TRUE)]))
  if (length(.re) != 2 || length(.og) != 1 || !any(tr$edge[.re, 2] == .og)) stop("LOCKED_ROOT_EDGE_SHAPE")
  .stem <- .re[tr$edge[.re, 2] != .og]
  .in_depth <- max(ape::node.depth.edgelength(tr)[seq_len(Ntip(tr))][-.og]) - tr$edge.length[.stem]
  .short <- 0.25 * .in_depth
  tr$edge.length[.re] <- .short
  root_break <- list(stem_node = tr$edge[.stem, 2], x = .short / 2, label = sprintf("%.2f", locked_edge))
}
md$disp_plain <- md$disp
# GG_ITALIC: italicise the SPECIES (first two whitespace tokens = Genus species) and leave the
# bracketed source, the (T) marker and the (accession) upright (owner, 2026-09-08: "species names
# are italicized."). plotmath + parse=TRUE; ggtext is not installed. Plain text when unset.
parse_labels <- FALSE
if (nzchar(Sys.getenv("GG_ITALIC"))) {
  .q <- function(x) encodeString(as.character(x), quote = '"')
  # v9.7.444: italicise Genus species only; 'sp.' and everything after stay upright (a genus-only isolate label).
  # GG_FOCAL_FACE=bold draws focal (isolate) labels bold / bold-italic inside the same expression.
  .italicize <- function(s, bold = FALSE) {
    w <- strsplit(as.character(s), " ", fixed = TRUE)[[1]]
    k <- if (length(w) >= 2 && w[2] != "sp." && grepl("^[a-z]", w[2])) 2 else 1
    it <- paste(w[seq_len(k)], collapse = " ")
    rest <- if (length(w) > k) paste0(" ", paste(w[-seq_len(k)], collapse = " ")) else ""
    e <- paste0(if (bold) "bolditalic(" else "italic(", .q(it), ")")
    if (nzchar(rest)) e <- paste0(e, "*", if (bold) paste0("bold(", .q(rest), ")") else .q(rest))
    e
  }
  .bold_focal <- Sys.getenv("GG_FOCAL_FACE", "plain") == "bold"
  .is_focal <- toupper(gsub("[-_ ]", "", md$tip)) %in% toupper(gsub("[-_ ]", "", focal))
  md$disp <- mapply(.italicize, md$disp, .bold_focal & .is_focal, USE.NAMES = FALSE)
  parse_labels <- TRUE
}
md <- md[md$tip %in% tr$tip.label, , drop = FALSE]
norm <- function(z) toupper(gsub("[-_ ]","",z)); md$focal <- norm(md$tip) %in% norm(focal)
n <- length(tr$tip.label)
# v9.7.444 option 1: reference cells with no deposited value are left blank (no fill, no legend entry).
blank_missing <- Sys.getenv("GG_BLANK_MISSING", "0") == "1"
if (blank_missing) for (c in c("category", "source")) {
  v <- trimws(as.character(md[[c]])); miss <- is.na(v) | tolower(v) %in% c("", "not recorded", "n/a", "na", "none", "unknown", "missing")
  md[[c]][miss & !md$focal] <- NA
}

palette_file <- file.path(script_dir, "phylo_display_palette.tsv")
if (!file.exists(palette_file)) stop("Shared phylogeny palette unavailable")
shared_palette <- read.delim(palette_file, quote="", stringsAsFactors=FALSE, check.names=FALSE)
cat_fixed <- setNames(shared_palette$color[shared_palette$field=="source"], shared_palette$value[shared_palette$field=="source"])
geo_field <- if (Sys.getenv("SAPOTE_GEOGRAPHY_LEVEL") == "country") "country" else "geography"   # v9.7.444
geo_fixed <- setNames(shared_palette$color[shared_palette$field==geo_field], shared_palette$value[shared_palette$field==geo_field])
# v9.7.444: GG_STRIP_KIND=activity draws both strips from the shared 'activity' palette (measured Candida / MRSA
# activity on query tips; reference and outgroup cells stay blank because they were not part of the screen).
if (Sys.getenv("GG_STRIP_KIND","source") == "activity") {
  # .452: GG_ACTIVITY_PALETTE picks the palette field: default "activity" (red / dark grey / grey, unchanged) or
  # "calm" ("activity_calm": dark blue / blue-grey / pale grey; moss Fig. S1b, owner, 13 Oct). The split-strip states
  # (+, −, n.t.) take the same three colours, in the palette's row order: active, tested inactive, not tested.
  act_field <- switch(Sys.getenv("GG_ACTIVITY_PALETTE", "default"), default = "activity", calm = "activity_calm",
                      stop("ACTIVITY_PALETTE_UNKNOWN: ", Sys.getenv("GG_ACTIVITY_PALETTE")))
  act_fixed <- setNames(shared_palette$color[shared_palette$field==act_field], shared_palette$value[shared_palette$field==act_field])
  if (length(act_fixed) != 3) stop("ACTIVITY_PALETTE_UNAVAILABLE")
  if (split_activity) act_fixed <- c(act_fixed, setNames(unname(act_fixed), c("+","−","n.t.")))
  if (split_activity) {
    observed_activity <- unique(unlist(md[activity_spec$column],use.names=FALSE))
    act_fixed <- act_fixed[names(act_fixed) %in% union(observed_activity,c("+","−","n.t."))]
  }
  cat_fixed <- act_fixed; geo_fixed <- act_fixed
}

cat_vals <- sort(unique(md$category[!is.na(md$category) & md$category != ""]))
cat_unknown <- setdiff(cat_vals, names(cat_fixed))
if (length(cat_unknown)) stop(paste0("ANNOTATION_SOURCE_PALETTE_UNSUPPORTED: ",paste(cat_unknown,collapse=", ")))
cat_pal <- cat_fixed

src_vals <- sort(unique(md$source[!is.na(md$source) & md$source != ""]))
src_unknown <- setdiff(src_vals,names(geo_fixed))
if (length(src_unknown)) stop(paste0("ANNOTATION_GEOGRAPHY_PALETTE_UNSUPPORTED: ",paste(src_unknown,collapse=", ")))
src_pal <- geo_fixed

print_mode <- nzchar(Sys.getenv("GG_PRINT_WIDTH"))
print_width <- suppressWarnings(as.numeric(Sys.getenv("GG_PRINT_WIDTH", "7.2")))
if (!is.finite(print_width) || print_width < 4 || print_width > 40) stop("PRINT_WIDTH_INVALID")
min_pt <- 8
lsize <- min_pt * 25.4 / 72.27
if (nzchar(Sys.getenv("GG_LABEL_SIZE"))) lsize <- max(lsize, as.numeric(Sys.getenv("GG_LABEL_SIZE")))
xr      <- max(ape::node.depth.edgelength(tr), na.rm = TRUE)
if (!is.finite(xr) || xr <= 0) stop("Positive tree depth required")
# Gap between branch tip and the dotted leader/label, as a fraction of tree depth. Default 0.02
# unchanged; GG_LAB_OFFSET_FRAC widens it when labels read as touching the branch tips
# (owner, 2026-09-08: "a little more space between the branches and the labels").
lab_off <- as.numeric(Sys.getenv("GG_LAB_OFFSET_FRAC", "0.02")) * xr

sb_raw  <- 0.10 * xr
sb_pow  <- 10 ^ floor(log10(sb_raw))
sb_len  <- (c(1, 2, 5, 10)[which.min(abs(c(1, 2, 5, 10) * sb_pow - sb_raw))]) * sb_pow
tree_size <- as.numeric(Sys.getenv("GG_TREE_LWD", "0.3"))

# Horizontal room reserved for the aligned tip labels, as a fraction of tree depth.
# The /200 divisor under-reserved: on the real attine Pseudonocardiaceae panel the longest
# reference labels were truncated mid-accession where the heatmap strip begins ("(NR_18" ...).
# Calibrated to /90 against that panel and re-checked on moss; GG_HEXPAND (which
# placement_display.py already sets, and which this renderer previously ignored) raises the floor.
hexp <- max(0.38, max(nchar(md$disp, type = "width")) * lsize / 90)
hexp_env <- Sys.getenv("GG_HEXPAND")
if (nzchar(hexp_env)) hexp <- max(hexp, as.numeric(hexp_env))
hexp_exact <- Sys.getenv("GG_HEXPAND_EXACT")
if (nzchar(hexp_exact)) {
  hexp <- as.numeric(hexp_exact)
  if (!is.finite(hexp) || hexp < 0.05 || hexp > 2) stop("GG_HEXPAND_EXACT must be between 0.05 and 2")
}

# v9.7.444 GG_FIT_LABELS: reserve exactly the measured label width, so the tree fills the panel and the strips sit
# right after the labels (the character-count estimate above over-reserves on short labels).
fit_labels <- TRUE
if (fit_labels) {
  grDevices::pdf(NULL)
  .lab_w_in <- max(vapply(seq_len(nrow(md)), function(i) grid::convertWidth(grid::grobWidth(grid::textGrob(if (parse_labels) parse(text=md$disp[i]) else md$disp_plain[i],
    gp = grid::gpar(fontsize = lsize * 72.27 / 25.4, fontface = if (isTRUE(md$focal[i])) 2 else 1))), "inches", valueOnly = TRUE), 0))
  .scale_w_in <- grid::convertWidth(grid::grobWidth(grid::textGrob(format(sb_len), gp=grid::gpar(fontsize=lsize*72.27/25.4))),"inches",valueOnly=TRUE)
  invisible(grDevices::dev.off())
  .n_str <- if (split_activity) nrow(activity_spec) else 2 + nzchar(Sys.getenv("GG_STRIP3_COL"))
  .fig_w <- if (print_mode) print_width else if (nzchar(Sys.getenv("GG_FIG_WIDTH"))) as.numeric(Sys.getenv("GG_FIG_WIDTH")) else 4.8 + .lab_w_in + 0.3 + 0.5 * .n_str + 1.7
  print_width <- .fig_w
  .panel_in <- (.fig_w - 0.55) * 13 / (13 + .n_str)  # tree panel share next to 1-unit strips; ~1.7 in legend column
  .g <- (.lab_w_in + 0.25) / .panel_in
  if (!is.finite(.g) || .g >= 0.9) stop("FIT_LABELS: labels do not fit the requested width")
  hexp <- (.g + 0.02) / (1 - .g)
  cat(sprintf("FIT_LABELS: label %.2f in, figure %.2f in, tree panel %.2f in, hexpand %.3f\n", .lab_w_in, .fig_w, .panel_in, hexp))
}

# v9.7.444: one y range for the tree and the strips. aplot draws the tree panel over [scale-bar y, n + 0.6] (measured:
# [-0.12, 22.6] for 22 tips) but the strips over their default [0.4, n + 0.6], so every strip row was ~2 % shorter than
# a tree row and cells drifted up to half a row off their tips by the bottom. The strips now get the tree's range.
y_lo <- -0.12 * max(1, Ntip(tr) / 60)
p <- ggtree(tr, size = tree_size, ladderize = TRUE) %<+% md +
  geom_tiplab(aes(label = ifelse(focal, NA, disp)), align = TRUE, linetype = "dotted", linesize = 0.2,
              size = lsize, offset = lab_off, parse = parse_labels) +
  ggtree::hexpand(hexp)
if (!is.null(root_break)) {
  .y <- p$data$y[p$data$node == root_break$stem_node]
  p <- p + annotate("text", x = root_break$x, y = .y, label = "//", size = lsize, fontface = "bold", angle = 0) +
    annotate("text", x = root_break$x, y = .y, label = root_break$label, size = lsize, vjust = -0.9, colour = "grey25")
  cat("LOCKED_ROOT_EDGE: drawn shortened with a break mark;", root_break$label, "\n")
}
if (any(md$focal)) {
focal_face   <- Sys.getenv("GG_FOCAL_FACE", "plain")
focal_colour <- Sys.getenv("GG_FOCAL_COLOUR", "#000000")
  p <- p + geom_tiplab(aes(label = ifelse(focal, disp, NA)), align = TRUE,
                       linetype = NA, linesize = 0, colour = focal_colour,
                       fontface = focal_face, size = lsize, offset = lab_off, na.rm = TRUE, parse = parse_labels)
}

# v9.7.444 GG_SUPPORT_MIN: print internal-node support (the tree's node labels, e.g. RAxML-NG Felsenstein bootstrap)
# at or above the threshold; lower values and unlabelled nodes stay blank.
sup_min <- suppressWarnings(as.numeric(Sys.getenv("GG_SUPPORT_MIN")))
if (is.finite(sup_min)) {
  .nd <- p$data[!p$data$isTip, ]
  .nd$sup <- suppressWarnings(as.numeric(sub("/.*$", "", .nd$label)))
  .nd <- .nd[is.finite(.nd$sup) & .nd$sup >= sup_min, ]
  # m5_452 GG_SUPPORT_MAX: values at or above it stay blank (e.g. 100 for "100 unlabelled"); unset = unchanged.
  sup_max <- suppressWarnings(as.numeric(Sys.getenv("GG_SUPPORT_MAX")))
  if (is.finite(sup_max)) .nd <- .nd[.nd$sup < sup_max, ]
  # m5_452 GG_SUPPORT_POS: where each number sits. "left" (default) = sealed placement, up and left of the node.
  # "right" = just right of the node, centred between its child branches. "auto" = per node, the first of five places whose
  # text box crosses no line: right, up-left (sealed), down-left, up-right, down-right. Lines = branches, node verticals and the
  # dotted tip-label leaders. Box size from the text at print size; tips drawn >= 0.18 in apart, so the height estimate is
  # generous. A node with no clear place keeps the place with fewest crossings and is reported as SUPPORT_LABEL_COLLISION.
  sup_pos <- Sys.getenv("GG_SUPPORT_POS", "left")
  .places <- list(right = c(-0.12, 0.5), left = c(1.15, -0.35), left_below = c(1.15, 1.35),
                  right_above = c(-0.12, -0.35), right_below = c(-0.12, 1.35))           # hjust, vjust
  .side <- rep(if (sup_pos == "right") "right" else "left", nrow(.nd))
  if (sup_pos == "auto" && nrow(.nd)) {
    .pd <- p$data; .xu <- xr * (1 + hexp) / .panel_in; .yu <- 1 / 0.18
    .ch <- .pd[.pd$parent != .pd$node, ]; .tp <- .pd[.pd$isTip, ]
    .seg <- rbind(
      data.frame(x0 = .pd$x[match(.ch$parent, .pd$node)], x1 = .ch$x, y0 = .ch$y, y1 = .ch$y),                         # branches
      do.call(rbind, lapply(split(.ch, .ch$parent), function(k)                                                      # node verticals
        data.frame(x0 = .pd$x[.pd$node == k$parent[1]], x1 = .pd$x[.pd$node == k$parent[1]], y0 = min(k$y), y1 = max(k$y)))),
      data.frame(x0 = .tp$x, x1 = max(.tp$x) + lab_off, y0 = .tp$y, y1 = .tp$y))                                     # tip leaders
    grDevices::pdf(NULL)
    .wh <- t(vapply(as.character(round(.nd$sup)), function(t) { g <- grid::textGrob(t, gp = grid::gpar(fontsize = lsize * 72.27 / 25.4))
      c(grid::convertWidth(grid::grobWidth(g), "inches", TRUE), grid::convertHeight(grid::grobHeight(g), "inches", TRUE)) }, numeric(2)))
    invisible(grDevices::dev.off())
    .hits <- function(bx) sum(pmax(.seg$x0, .seg$x1) >= bx[1] & pmin(.seg$x0, .seg$x1) <= bx[2] &
                              pmax(.seg$y0, .seg$y1) >= bx[3] & pmin(.seg$y0, .seg$y1) <= bx[4])
    .clash <- rep(FALSE, nrow(.nd))
    for (i in seq_len(nrow(.nd))) {
      w <- (.wh[i, 1] + 0.03) * .xu; h <- (.wh[i, 2] + 0.03) * .yu; x <- .nd$x[i]; y <- .nd$y[i]
      hk <- vapply(.places, function(hv) { x0 <- x - hv[1] * w; y0 <- y - hv[2] * h; .hits(c(x0, x0 + w, y0, y0 + h)) }, numeric(1))
      .side[i] <- names(hk)[which.min(hk)]                                       # first place with the fewest crossings
      if (min(hk) > 0) cat("SUPPORT_LABEL_COLLISION: node", .nd$node[i], "support", round(.nd$sup[i]), "crosses", min(hk), "line(s)\n")
      .clash[i] <- min(hk) > 0
    }
    # m5_452 GG_SUPPORT_UNPLACED=omit: a number with no clear place is not drawn; its value and clade (first and last tip label
    # in drawing order) are printed as SUPPORT_NOT_DRAWN for the caption. Default (unset or "draw"): drawn at the fewest crossings.
    if (Sys.getenv("GG_SUPPORT_UNPLACED", "draw") == "omit" && any(.clash)) {
      .kids <- split(.pd$node[.pd$parent != .pd$node], .pd$parent[.pd$parent != .pd$node])
      .tips_of <- function(k) { out <- c(); todo <- k
        while (length(todo)) { h <- todo[1]; todo <- todo[-1]; ch <- .kids[[as.character(h)]]
          if (is.null(ch)) out <- c(out, h) else todo <- c(todo, ch) }
        out }
      for (i in which(.clash)) {
        tt <- .pd[.pd$node %in% .tips_of(.nd$node[i]), ]; tt <- tt[order(-tt$y), ]
        nm <- md$disp_plain[match(tt$label[c(1, nrow(tt))], md$tip)]
        cat("SUPPORT_NOT_DRAWN:", round(.nd$sup[i]), "| clade from", nm[1], "to", nm[2], "|", nrow(tt), "tips\n")
      }
      .nd <- .nd[!.clash, ]; .side <- .side[!.clash]
    }
    cat("SUPPORT_POS auto:", paste0(round(.nd$sup), "=", .side, collapse = " "), "\n")
  }
  .nd$hj <- vapply(.side, function(s) .places[[s]][1], numeric(1)); .nd$vj <- vapply(.side, function(s) .places[[s]][2], numeric(1))
  # White backing, no border: branch lines behind a number cannot cut through it (seen on crowded basal nodes).
  if (nrow(.nd)) p <- p + geom_label(data = .nd, aes(x = x, y = y, label = round(sup), hjust = hj, vjust = vj), inherit.aes = FALSE,
                                     size = lsize, colour = "grey25",
                                     fill = "white", border.colour = NA, label.padding = grid::unit(0.04, "lines"))
  cat("SUPPORT_LABELS:", nrow(.nd), "nodes >=", sup_min, if (is.finite(sup_max)) paste("and <", sup_max) else "", "\n")
}
band_col <- Sys.getenv("GG_FOCAL_BAND")
if (nzchar(band_col) && any(md$focal)) {
  .td <- p$data[p$data$isTip, ]; .fy <- .td$y[.td$label %in% md$tip[md$focal]]
  .band <- geom_rect(data = data.frame(ymin = .fy - 0.5, ymax = .fy + 0.5), inherit.aes = FALSE,
                     aes(xmin = max(.td$x) + lab_off * 0.5, xmax = Inf, ymin = ymin, ymax = ymax), fill = band_col, colour = NA)
  p$layers <- c(list(.band), p$layers)   # under the tree and the labels
}
tip_order <- rev(ggtree::get_taxa_name(p))
strip_layer <- if (nzchar(band_col)) 2L else 1L
strip_title <- function(title) {
  raw <- gsub("*", "", title, fixed=TRUE)
  title_set <- c(Sys.getenv("GG_STRIP1_TITLE","Isolation source"),Sys.getenv("GG_STRIP2_TITLE","Strain class"))
  lines <- strwrap(raw,width=8)
  count <- max(length(lines),vapply(title_set,function(t) length(strwrap(gsub("*","",t,fixed=TRUE),width=8)),0L))
  lines <- c(lines,rep("&nbsp;",count-length(lines)))
  if (grepl("*Candida*",title,fixed=TRUE)) lines <- gsub("Candida","<i>Candida</i>",lines,fixed=TRUE)
  paste(lines,collapse="<br>")
}
mk_strip <- function(col, pal, title, face = "plain") {   # v9.7.444: face, e.g. italic for a genus title (Candida)
  d <- data.frame(tip = md$tip, val = md[[col]], stringsAsFactors = FALSE)
  d$tip <- factor(d$tip, levels = tip_order)
  # y limits pinned to the tree's tip order: a band layer holding only isolate rows would otherwise train the discrete
  # scale first and move every cell to another row (the colour audit catches this).
  g <- ggplot(d, aes(x = 0, y = tip, fill = val)) + scale_y_discrete(limits = tip_order, expand = expansion(add = c(1 - y_lo, 0.6)))
  if (nzchar(band_col)) g <- g + geom_tile(data = d[md$focal, , drop = FALSE], aes(x = 0, y = tip), inherit.aes = FALSE,
                                           width = 1.3, height = 1, fill = band_col)
  g <- g +
    # v9.7.444: a thin white outline separates adjacent cells that share a value (they merged into one tall block);
    # the cell geometry the alignment audit checks is unchanged.
    geom_tile(width = if (nzchar(band_col)) 0.8 else 1, height = 1, colour = "white", linewidth = 0.5,
              show.legend = if (Sys.getenv("GG_STRIP_KIND","source") == "activity") TRUE else NA) +   # keys for unused levels too
    # v9.7.444 trial: activity strips share one full scale, so a strip with no "active" cell (e.g. Candida on a small
    # genus) still merges into one Activity legend instead of drawing a second, shorter one.
    scale_fill_manual(values = pal, limits = if (Sys.getenv("GG_STRIP_KIND","source") == "activity" && (col %in% c("category", "source") || split_activity)) names(pal) else NULL,
                      na.value = if (blank_missing) "white" else "#eeeeee", name = if (Sys.getenv("GG_STRIP_KIND","source") == "activity" && (col %in% c("category", "source") || split_activity)) "Activity" else title, drop = FALSE, na.translate = !blank_missing) +
    # v9.7.444 trial (Alex 2026-09-27): a title with *italic* markup ("*Candida* sp.") is drawn as markdown, unwrapped
    labs(title = strip_title(title)) + theme_void() +
    theme(plot.title=ggtext::element_markdown(size=8,hjust=0.5),legend.key.size=unit(3.4,"mm"),
          legend.text=element_text(size=8),legend.title=element_text(size=8))
  if (split_activity) {
    d$state_label <- ifelse(d$val %in% c("+","−","n.t."), d$val, "")
    g <- g + geom_text(data=d,aes(x=0,y=tip,label=state_label),inherit.aes=FALSE,size=lsize,
                      colour=ifelse(d$val %in% c("+","−"),"white","black"),na.rm=TRUE)
  }
  g
}
s_cat <- mk_strip("category", cat_pal, Sys.getenv("GG_STRIP1_TITLE", "Isolation source"), Sys.getenv("GG_STRIP1_FACE", "plain"))
s_src <- mk_strip("source",   src_pal, Sys.getenv("GG_STRIP2_TITLE", "Strain class"), Sys.getenv("GG_STRIP2_FACE", "plain"))

tree_tip_y <- p$data$y[match(tip_order,p$data$label)]
if (anyNA(tree_tip_y) || any(abs(tree_tip_y-seq_along(tip_order))>1e-8))
  stop("ANNOTATION_TREE_ALIGNMENT: strip order differs from plotted tree tips")
category_audit <- validate_annotation_strip(s_cat,tip_order,md$category[match(tip_order,md$tip)],cat_pal,layer=strip_layer)
source_audit <- validate_annotation_strip(s_src,tip_order,md$source[match(tip_order,md$tip)],src_pal,layer=strip_layer)
activity_plots <- list()
if (split_activity) {
  activity_titles <- lapply(activity_spec$label,function(label) strwrap(label,width=10))
  title_lines <- max(lengths(activity_titles))
  activity_audits <- list()
  for (j in seq_len(nrow(activity_spec))) {
    col <- activity_spec$column[j]
    if (!col %in% names(md)) stop("ACTIVITY_COLUMN_MISSING")
    md[[col]][is.na(md[[col]]) | md[[col]] == ""] <- NA
    title <- paste(c(activity_titles[[j]],rep("&nbsp;",title_lines-length(activity_titles[[j]]))),collapse="<br>")
    for (word in c("C.","albicans","auris")) title <- gsub(word,paste0("<i>",word,"</i>"),title,fixed=TRUE)
    g <- mk_strip(col,act_fixed,title)
    # All strip headings occupy the same height, including the unknown-species heading.
    g <- g + labs(title=title) + theme(plot.title=ggtext::element_markdown(size=8,hjust=0.5))
    activity_plots[[j]] <- g
    audit <- validate_annotation_strip(g,tip_order,md[[col]][match(tip_order,md$tip)],act_fixed,layer=strip_layer)
    activity_audits[[j]] <- data.frame(audit,strip=activity_spec$label[j],column=col)
  }
  write.table(do.call(rbind,activity_audits),paste0(out,".activity_audit.tsv"),sep="\t",quote=FALSE,row.names=FALSE,na="")
}
write.table(data.frame(category_audit,geography=source_audit$value,geography_fill=source_audit$fill),
            paste0(out,".annotation_audit.tsv"),sep="\t",quote=FALSE,row.names=FALSE)
n_strips <- Sys.getenv("GG_STRIPS", "0")
if (!n_strips %in% c("0", "1", "2")) stop("GG_STRIPS must be 0, 1 or 2")
# v9.7.444 GG_STRIP3_COL: an optional third strip (e.g. host group) from a metadata column, palette field of the same name
strip3_col <- Sys.getenv("GG_STRIP3_COL")
if (nzchar(strip3_col)) {
  if (!strip3_col %in% names(md)) stop("GG_STRIP3_COL column missing from metadata: ", strip3_col)
  s3_pal <- setNames(shared_palette$color[shared_palette$field == strip3_col], shared_palette$value[shared_palette$field == strip3_col])
  v3 <- md[[strip3_col]]; v3[is.na(v3) | trimws(v3) == ""] <- NA; md[[strip3_col]] <- v3
  unk3 <- setdiff(unique(na.omit(v3)), names(s3_pal)); if (length(unk3)) stop("STRIP3_PALETTE_UNSUPPORTED: ", paste(unk3, collapse = ", "))
  s_3 <- mk_strip(strip3_col, s3_pal, Sys.getenv("GG_STRIP3_TITLE", strip3_col))
  s3_audit <- validate_annotation_strip(s_3, tip_order, md[[strip3_col]][match(tip_order, md$tip)], s3_pal, layer = strip_layer)
}
# Page windows use the same tree coordinates, root and branches. No tip is pruned.
# Remove labels outside each window before drawing, rather than merely clipping text.
w <- print_width
mth <- Sys.getenv("GG_METHODS")
figid <- Sys.getenv("GG_FIGID")
if (!nzchar(figid)) figid <- basename(out)
writeLines(c(if (nzchar(mth)) gsub("*", "", mth, fixed=TRUE) else "Methods not supplied.", display_note), paste0(out, ".methods.txt"))
caption_text <- if (identical(figid, "-")) mth else paste0(figid, " | ", mth)
cap_w <- max(48, floor(w * 5.3))
if (print_mode) cap_w <- max(25, floor(13 * w))
if (nzchar(Sys.getenv("GG_CAPTION_WRAP"))) cap_w <- suppressWarnings(as.numeric(Sys.getenv("GG_CAPTION_WRAP")))
if (!is.finite(cap_w) || cap_w < 1) stop("CAPTION_WRAP_INVALID")
caption_lines <- if (nzchar(mth)) strwrap(caption_text, width=cap_w) else character()
caph <- if (length(caption_lines)) length(caption_lines)*0.14+0.25 else 0
if (caph > 4) stop("CAPTION_TOO_LONG_FOR_PRINT_PAGE")
rows_per_page <- max(1L, floor((9 - caph - 1.3) / 0.18))
page_groups <- split(rev(tip_order), ceiling(seq_along(tip_order)/rows_per_page))
page_count <- length(page_groups)
page_plots <- list()
page_rows <- list()
page_files <- character()
for (i in seq_along(page_groups)) {
  shown <- page_groups[[i]]
  ys <- tree_tip_y[match(shown, tip_order)]
  bottom <- min(ys)-1.25; top <- max(ys)+0.6
  pp <- p
  pp$data <- pp$data[!pp$data$isTip | pp$data$label %in% shown, , drop=FALSE]
  # Support numbers have independent layer data; trim these to the same window.
  pp$layers <- lapply(pp$layers, function(layer) {
    layer <- unserialize(serialize(layer, NULL))
    if (inherits(layer$data, "data.frame") && "y" %in% names(layer$data))
      layer$data <- layer$data[layer$data$y >= min(ys)-0.5 & layer$data$y <= top,,drop=FALSE]
    layer
  })
  # m5_452 GG_SCALE_OFFSET: scale-bar label distance from its line (tree y units; default 0.12 as sealed). A short bar
  # under a longer label ran through the label (Fig. 5 Actinomadura, 0.05); a larger offset lifts the label clear.
  scale_offset <- suppressWarnings(as.numeric(Sys.getenv("GG_SCALE_OFFSET", "0.12"))); if (!is.finite(scale_offset)) scale_offset <- 0.12
  # m5_452 GG_SCALE_PAGES=last: on a multi-page tree the scale bar is drawn on the last page only (on earlier pages the root lines run
  # through its corner; seen on the 76-genome Fig. 5 tree). Default (unset or "all"): every page, as sealed.
  pp <- pp + coord_cartesian(ylim=c(bottom, top), clip="on", expand=FALSE)
  if (Sys.getenv("GG_SCALE_PAGES", "all") != "last" || i == page_count)
    pp <- pp + geom_treescale(width=sb_len, x=max(0.04*xr, (.scale_w_in/2+0.12)*xr*(1+hexp)/.panel_in-sb_len/2), y=min(ys)-0.95,
                   fontsize=lsize, linesize=0.4, offset=scale_offset)
  page_strip <- function(g) {
    g$data <- g$data[as.character(g$data$tip) %in% shown,,drop=FALSE]
    g + coord_cartesian(ylim=c(bottom, top), clip="on", expand=FALSE) + theme(legend.position="none")
  }
  sc <- page_strip(s_cat); ss <- page_strip(s_src)
  combined <- if (split_activity) {
    strips <- lapply(activity_plots,page_strip)
    panel <- strips[[length(strips)]]
    if (length(strips)>1) for (j in rev(seq_len(length(strips)-1))) panel <- insert_left(panel,strips[[j]],width=1)
    insert_left(panel,pp,width=13)
  } else if (n_strips == "0") pp else if (n_strips == "1") sc |> insert_left(pp,width=13) else {
    if (nzchar(strip3_col)) page_strip(s_3) |> insert_left(ss,width=1) |> insert_left(sc,width=1) |> insert_left(pp,width=13)
    else ss |> insert_left(sc,width=1) |> insert_left(pp,width=13)
  }
  if (n_strips != "0") cat("PANEL_Y_RANGES:", paste(validate_panel_ranges(combined), collapse=" | "), "\n")
  body <- if (n_strips == "0") combined else aplot::as.patchwork(combined)
  legend_grob <- function(g) {
    # Text/grob measurement must never open the default disk device.
    grDevices::pdf(NULL)
    measurement_device <- grDevices::dev.cur()
    on.exit(if (measurement_device %in% grDevices::dev.list()) grDevices::dev.off(measurement_device), add=TRUE)
    gt <- ggplotGrob(g + theme(legend.position="bottom",legend.text=element_text(size=8),legend.title=element_text(size=8)))
    gt$grobs[[which(gt$layout$name == "guide-box-bottom")]]
  }
  if (n_strips != "0") {
    leg <- wrap_elements(full=legend_grob(if (split_activity) activity_plots[[1]] else s_cat))
    if (Sys.getenv("GG_STRIP_KIND","source") != "activity" && n_strips == "2")
      leg <- leg / wrap_elements(full=legend_grob(s_src))
    body <- wrap_plots(list(body,leg),ncol=1,heights=c(1,0.10))
  }
  body_h <- max(2.6, length(shown)*0.18+1.3)
  final <- body
  if (length(caption_lines)) {
    cap_layer <- if (Sys.getenv("GG_CAPTION_MD") == "1")
      ggtext::geom_richtext(data=data.frame(x=0,y=1,label=paste(caption_lines,collapse="<br>")),aes(x=x,y=y,label=label),hjust=0,vjust=1,size=lsize,lineheight=1.1,fill=NA,label.colour=NA,label.padding=grid::unit(0,"pt")) else
      annotate("text",x=0,y=1,label=paste(caption_lines,collapse="\n"),hjust=0,vjust=1,size=lsize,lineheight=1.1)
    cap <- ggplot() + cap_layer +
      scale_x_continuous(limits=c(0,1),expand=c(0,0)) + scale_y_continuous(limits=c(0,1),expand=c(0,0)) + theme_void() + theme(plot.margin=margin(2,6,2,6))
    final <- wrap_plots(list(body,cap),ncol=1,heights=c(body_h,caph))
  }
  # Publication default: pagination belongs in the sidecar; draw only on explicit opt-in.
  if (identical(Sys.getenv("GG_PAGE_TITLE"), "1"))
  final <- final + plot_annotation(title=sprintf("Page %d of %d",i,page_count), theme=theme(plot.title=element_text(size=8)))
  h_total <- min(9, body_h+caph+0.2)
  page_plots[[i]] <- final
  page_prefix <- if (page_count > 1) paste0(out,"_page",i) else out
  ggsave(paste0(page_prefix,".pdf"),final,width=w,height=h_total,limitsize=FALSE)
  ggsave(paste0(page_prefix,".png"),final,width=w,height=h_total,dpi=300,limitsize=FALSE)
  page_files <- c(page_files,paste0(page_prefix,c(".pdf",".png")))
  page_rows[[i]] <- list(page=i,tips=shown,width_in=w,height_in=h_total,minimum_font_pt=min_pt,pdf=basename(paste0(page_prefix,".pdf")),png=basename(paste0(page_prefix,".png")))
}
if (page_count > 1) {
  grDevices::pdf(paste0(out,".pdf"),width=w,height=9,onefile=TRUE)
  for (figure in page_plots) print(figure)
  invisible(grDevices::dev.off())
  if (!file.copy(paste0(out,"_page1.png"),paste0(out,".png"),overwrite=FALSE)) stop("PAGE_PREVIEW_EXISTS")
  page_files <- c(page_files,paste0(out,c(".pdf",".png")))
}
# stamp_file is required before binding any render receipt.
stamp_rc <- system2(python,c(shQuote(file.path(script_dir,"placement_stamp.py")),"--print-width",as.character(w),shQuote(page_files)))
if (stamp_rc != 0) stop("PLACEMENT_STAMP_FAILED")
jsonlite::write_json(list(schema="placement-pages-v1",page_titles=identical(Sys.getenv("GG_PAGE_TITLE"), "1"),root_policy=Sys.getenv("GG_ROOT_POLICY", "preserve_supplied"),diagnostic_only=nzchar(diagnostic_receipt),pages=page_rows,preview="first page",tip_count=n),paste0(out,".pages.json"),auto_unbox=TRUE,pretty=TRUE)
cat(sprintf("wrote %s: %d pages at %.2f in, minimum 8 pt; %d tips\n",out,page_count,w,n))

capture.output(sessionInfo(), file=paste0(out, ".session.txt"))

if (nzchar(display_receipt)) {
  bind_out <- suppressWarnings(system2(python,
    c(shQuote(checker), gate_args, "--render-prefix", shQuote(out)), stdout=TRUE, stderr=TRUE))
  bind_rc <- attr(bind_out, "status"); if (is.null(bind_rc)) bind_rc <- 0
  if (bind_rc != 0) {
    cat(paste(bind_out, collapse="\n"), "\n", file=stderr())
    stop("Render binding failed; generated graphics remain unverified")
  }
}
