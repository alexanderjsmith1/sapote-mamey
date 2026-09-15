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
  if (Sys.getenv("GG_STRIPS", "0") == "2") annotation_args <- c(annotation_args,"--require-geography")
  annotation_out <- suppressWarnings(system2(python,annotation_args,stdout=TRUE,stderr=TRUE))
  annotation_rc <- attr(annotation_out,"status")
  if (!is.null(annotation_rc) && annotation_rc != 0) stop(paste(annotation_out,collapse="\n"))
}
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
# GG_ITALIC: italicise the SPECIES (first two whitespace tokens = Genus species) and leave the
# bracketed source, the (T) marker and the (accession) upright (Alex, 2026-09-08: "species names
# are italicized."). plotmath + parse=TRUE; ggtext is not installed. Plain text when unset.
parse_labels <- FALSE
if (nzchar(Sys.getenv("GG_ITALIC"))) {
  .q <- function(x) encodeString(as.character(x), quote = '"')
  .italicize <- function(s) {
    s <- as.character(s)
    m <- regmatches(s, regexec("^(\\S+\\s+\\S+)(.*)$", s))[[1]]
    if (length(m) == 0) return(paste0("italic(", .q(s), ")"))
    if (nzchar(m[3])) paste0("italic(", .q(m[2]), ")*", .q(m[3])) else paste0("italic(", .q(m[2]), ")")
  }
  md$disp <- vapply(md$disp, .italicize, character(1))
  parse_labels <- TRUE
}
md <- md[md$tip %in% tr$tip.label, , drop = FALSE]
norm <- function(z) toupper(gsub("[-_ ]","",z)); md$focal <- norm(md$tip) %in% norm(focal)
n <- length(tr$tip.label)

palette_file <- file.path(script_dir, "phylo_display_palette.tsv")
if (!file.exists(palette_file)) stop("Shared phylogeny palette unavailable")
shared_palette <- read.delim(palette_file, quote="", stringsAsFactors=FALSE, check.names=FALSE)
cat_fixed <- setNames(shared_palette$color[shared_palette$field=="source"], shared_palette$value[shared_palette$field=="source"])
geo_fixed <- setNames(shared_palette$color[shared_palette$field=="geography"], shared_palette$value[shared_palette$field=="geography"])

cat_vals <- sort(unique(md$category[!is.na(md$category) & md$category != ""]))
cat_unknown <- setdiff(cat_vals, names(cat_fixed))
if (length(cat_unknown)) stop(paste0("ANNOTATION_SOURCE_PALETTE_UNSUPPORTED: ",paste(cat_unknown,collapse=", ")))
cat_pal <- cat_fixed

src_vals <- sort(unique(md$source[!is.na(md$source) & md$source != ""]))
src_unknown <- setdiff(src_vals,names(geo_fixed))
if (length(src_unknown)) stop(paste0("ANNOTATION_GEOGRAPHY_PALETTE_UNSUPPORTED: ",paste(src_unknown,collapse=", ")))
src_pal <- geo_fixed

lsize <- if (n > 120) 1.7 else if (n > 60) 2.0 else 2.4
if (nzchar(Sys.getenv("GG_LABEL_SIZE"))) lsize <- as.numeric(Sys.getenv("GG_LABEL_SIZE"))
xr      <- max(ape::node.depth.edgelength(tr), na.rm = TRUE)
if (!is.finite(xr) || xr <= 0) stop("Positive tree depth required")
# Gap between branch tip and the dotted leader/label, as a fraction of tree depth. Default 0.02
# unchanged; GG_LAB_OFFSET_FRAC widens it when labels read as touching the branch tips
# (Alex, 2026-09-08: "a little more space between the branches and the labels").
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

p <- ggtree(tr, size = tree_size, ladderize = TRUE) %<+% md +
  geom_tiplab(aes(label = ifelse(focal, NA, disp)), align = TRUE, linetype = "dotted", linesize = 0.2,
              size = lsize, offset = lab_off, parse = parse_labels) +
  geom_treescale(width = sb_len, x = 0.04 * xr, y = -0.12 * max(1, Ntip(tr) / 60), fontsize = max(2, lsize - 0.4),
                 linesize = 0.4, offset = 0.08 * max(1, Ntip(tr) / 60)) +
  ggtree::hexpand(hexp)
if (any(md$focal)) {
focal_face   <- Sys.getenv("GG_FOCAL_FACE", "plain")
focal_colour <- Sys.getenv("GG_FOCAL_COLOUR", "#000000")
  p <- p + geom_tiplab(aes(label = ifelse(focal, disp, NA)), align = TRUE,
                       linetype = NA, linesize = 0, colour = focal_colour,
                       fontface = focal_face, size = lsize, offset = lab_off, na.rm = TRUE, parse = parse_labels)
}

tip_order <- rev(ggtree::get_taxa_name(p))
mk_strip <- function(col, pal, title) {
  d <- data.frame(tip = md$tip, val = md[[col]], stringsAsFactors = FALSE)
  d$tip <- factor(d$tip, levels = tip_order)
  ggplot(d, aes(x = 0, y = tip, fill = val)) +
    geom_tile(width = 1, height = 1) +
    scale_fill_manual(values = pal, na.value = "#eeeeee", name = title, drop = FALSE) +
    labs(title = paste(strwrap(title, width=12), collapse="\n")) + theme_void() + theme(plot.title = element_text(size=8, hjust=0.5), legend.key.size = unit(3.4, "mm"), legend.text = element_text(size = 6),
                         legend.title = element_text(size = 7))
}
s_cat <- mk_strip("category", cat_pal, Sys.getenv("GG_STRIP1_TITLE", "Isolation source"))
s_src <- mk_strip("source",   src_pal, Sys.getenv("GG_STRIP2_TITLE", "Strain class"))

tree_tip_y <- p$data$y[match(tip_order,p$data$label)]
if (anyNA(tree_tip_y) || any(abs(tree_tip_y-seq_along(tip_order))>1e-8))
  stop("ANNOTATION_TREE_ALIGNMENT: strip order differs from plotted tree tips")
category_audit <- validate_annotation_strip(s_cat,tip_order,md$category[match(tip_order,md$tip)],cat_pal)
source_audit <- validate_annotation_strip(s_src,tip_order,md$source[match(tip_order,md$tip)],src_pal)
write.table(data.frame(category_audit,geography=source_audit$value,geography_fill=source_audit$fill),
            paste0(out,".annotation_audit.tsv"),sep="\t",quote=FALSE,row.names=FALSE)
n_strips <- Sys.getenv("GG_STRIPS", "0")
if (!n_strips %in% c("0", "1", "2")) stop("GG_STRIPS must be 0, 1 or 2")
combined <- if (n_strips == "0") {
  p
} else if (n_strips == "1") {
  s_cat |> insert_left(p, width = 13)
} else {
  s_src |> insert_left(s_cat, width = 1) |> insert_left(p, width = 13)
}

per_tip <- if (n > 800) 0.085 else if (n > 300) 0.105 else 0.14
# GG_PER_TIP overrides vertical density (inches/tip) so the SAME tree can be emitted at several
# densities without dropping tips (Alex, 2026-09-08: "3 figures always at different densities").
if (nzchar(Sys.getenv("GG_PER_TIP"))) per_tip <- as.numeric(Sys.getenv("GG_PER_TIP"))
h <- max(5, per_tip * n + 1.5)
w <- if (n > 600) 22 else if (n > 250) 19 else if (n > 120) 16 else 12
# SEXTANT_422e: panel width was chosen from the TIP COUNT alone. Once reference tips carry the
# deposited organism (SEXTANT_422a) the labels roughly doubled in length, and on the 2026-09-09
# re-render they ran off the panel -- "(NR_025113.1", "(NR_0" -- so the accession, the one part of
# the tip that makes it checkable, was the part that got clipped. Widen for the longest label
# actually being drawn. Character width in inches is approximated from the ggplot point size.
.lab_chars <- suppressWarnings(max(nchar(as.character(md$disp)), na.rm = TRUE))
if (!is.finite(.lab_chars)) .lab_chars <- 0
# ggplot `size` is font height in mm; mean glyph advance is about half that. 0.019 in per
# character per size unit is measured back from the labels that were still clipping at 0.0072,
# which widened nothing at all (103 chars x 2.4 gave 1.8 in for a label needing ~4.7 in).
.lab_in <- .lab_chars * lsize * 0.019
w <- max(w, 6 + .lab_in + 2.5)              # tree + labels + the two heatmap strips
if (nzchar(Sys.getenv("GG_FIG_WIDTH"))) w <- as.numeric(Sys.getenv("GG_FIG_WIDTH"))
figid <- Sys.getenv("GG_FIGID")
if (!nzchar(figid)) figid <- basename(out)
mth <- Sys.getenv("GG_METHODS")
writeLines(c(if (nzchar(mth)) mth else "Methods not supplied.", display_note),
           paste0(out, ".methods.txt"))
final <- combined; h_total <- h
if (nzchar(mth)) {
  # v9.7.418: wrap the WHOLE caption (figure id + methods) at a width derived from the panel width.
  # Previously only the methods text was wrapped (at 125) and the id was prepended afterwards, so the
  # first line overran the 12-in panel and the claim-safety clause was clipped ("...not a spe").
  # v9.7.422: patchwork aligns this caption strip to the PANEL region, not the full figure width
  # (the legend column sits outside it), so wrapping at w*9 overran and clipped the caption at the
  # panel edge. Wrap to the panel share instead; GG_CAPTION_WRAP overrides.
  cap_w <- max(48, floor(w * 5.3))
  if (nzchar(Sys.getenv("GG_CAPTION_WRAP"))) cap_w <- as.numeric(Sys.getenv("GG_CAPTION_WRAP"))
  caption_text <- if (identical(figid, "-")) mth else paste0(figid, "  |  ", mth)
  mthw <- paste(strwrap(caption_text, width = cap_w), collapse = "\n")
  nlines <- length(strsplit(mthw, "\n")[[1]])
  cap <- ggplot() +
    annotate("text", x = 0, y = 1, label = mthw, hjust = 0, vjust = 1, size = 3.6, colour = "grey20", lineheight = 1.2) +
    scale_x_continuous(limits = c(0, 1), expand = c(0, 0)) +
    scale_y_continuous(limits = c(0, 1), expand = c(0, 0)) +
    theme_void() + theme(plot.margin = margin(2, 6, 2, 6))
  caph <- 0.30 * nlines + 0.6
  plot_body <- if (n_strips == "0") combined else aplot::as.patchwork(combined)
  final <- plot_body / cap + patchwork::plot_layout(heights = c(h, caph))
  h_total <- h + caph
}
ggsave(paste0(out, ".pdf"), final, width = w, height = h_total, limitsize = FALSE)
ggsave(paste0(out, ".png"), final, width = w, height = h_total, dpi = 200, limitsize = FALSE)
cat(sprintf("wrote %s.{pdf,png}  tips=%d focal=%d categories=%d sources=%d\n",
            out, n, sum(md$focal), length(unique(na.omit(md$category))), length(src_vals)))

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
