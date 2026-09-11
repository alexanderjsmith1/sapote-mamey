#!/usr/bin/env Rscript
# ggtree_placement_bioassay.R — variant of ggtree_placement.R that draws a MEASURED wet-lab
# bioassay strip (anti-Candida / anti-MRSA) beside each QUERY tip, in the same spirit as
# tree_bioassay.py's overlay on a plain genome/MLSA tree, but on an EPA-ng placement tree.
# Same inputs as every other ggtree_placement*.R variant: the annotation TSV produced by
# build_placement_ggtree_inputs.py --bioassay-table (v9.7.423). Reference/type-strain tips never
# carry this strip -- bioassay_status/anti_candida/anti_mrsa are blank on them by construction.
#
# CLAIM CEILING (stricter than the host/origin overlays): this is MEASURED, CRUDE-EXTRACT,
# STRAIN-LEVEL activity. It is NOT attributed to any specific BGC, is not a purified-compound
# result, and is not a structure claim. It says only "this strain's extract did/did not inhibit
# the test organism." Judgment deferred.
#
# Usage:
#   Rscript ggtree_placement_bioassay.R <pruned.nwk> <annotation.tsv> <out_prefix> [withloc|noloc]
# Emits <out_prefix>.pdf and <out_prefix>.png.
#
# Claim-safety: 16S is an anchor / neighbourhood, not a species call; judgment deferred.

suppressPackageStartupMessages({
  library(ape); library(ggtree); library(ggplot2); library(treeio)
})

RESULT_COLOR <- c(positive = "#2e8b57", negative = "#d9d9d9", not_tested = "#ffffff", not_recorded = "#9ebcda")
RESULT_LABEL <- c(positive = "positive", negative = "negative", not_tested = "not tested", not_recorded = "not recorded")

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) stop("Usage: ggtree_placement_bioassay.R <nwk> <tsv> <out_prefix> [withloc|noloc]")
nwk <- args[1]; tsv <- args[2]; out <- args[3]
locmode <- ifelse(length(args) >= 4, args[4], "withloc")

tr  <- read.tree(nwk)
ann <- read.delim(tsv, sep = "\t", quote = "", stringsAsFactors = FALSE, check.names = FALSE)
if (!all(c("bioassay_status", "anti_candida", "anti_mrsa") %in% names(ann))) {
  stop(paste0("BIOASSAY_ANNOTATION_MISSING: annotation TSV has no bioassay_status/anti_candida/",
              "anti_mrsa columns -- re-run build_placement_ggtree_inputs.py with --bioassay-table (v9.7.423+)."))
}

qcol <- if (locmode == "noloc") "label_noloc" else "label_withloc"
ann$show <- ifelse(ann$kind == "query", ann[[qcol]], ann$ref_label)
ann$lab_q <- ifelse(ann$kind == "query", ann$show, NA)
ann$lab_r <- ifelse(ann$kind == "reference", ann$show, NA)

n     <- length(tr$tip.label)
q_n   <- sum(ann$kind == "query", na.rm = TRUE)
r_n   <- sum(ann$kind == "reference", na.rm = TRUE)
lsize <- if (n > 140) 1.9 else if (n > 60) 2.3 else 2.8
group <- sub("_placement.*$", "", basename(out)); group <- sub("_ggtree.*$", "", group)

if (anyDuplicated(ann$tip) || !setequal(ann$tip, tr$tip.label)) stop("BIOASSAY_TIP_BINDING: tree and annotations must match one to one")
xr    <- max(ape::node.depth.edgelength(tr), na.rm = TRUE)
if (!is.finite(xr) || xr <= 0) xr <- 1
q_off <- 0.058 * xr      # query labels clear the two bioassay dots + the query point
r_off <- 0.008 * xr

# One row per (tip, organism) so a single geom_point can carry both dots at fixed x-offsets past
# the tip, coloured by result. Reference tips are excluded entirely -- MEASURED activity belongs
# to this project's own isolates, never to a public comparator (blank columns already enforce
# this upstream; the explicit filter here is a second, independent guard against a future TSV that
# forgets to blank them).
q_ids <- ann$tip[ann$kind == "query" & !is.na(ann$bioassay_status) & ann$bioassay_status != ""]
norm_result <- function(v) {
  v <- tolower(trimws(ifelse(is.na(v), "", v)))
  v[v == ""] <- "not_recorded"
  if (any(!v %in% names(RESULT_COLOR))) stop("BIOASSAY_ANNOTATION_VALUE: unsupported result; use positive, negative, not_tested or blank")
  v
}
dots <- data.frame()
if (length(q_ids) > 0) {
  sub <- ann[ann$tip %in% q_ids, c("tip", "anti_candida", "anti_mrsa")]
  dots <- rbind(
    data.frame(tip = sub$tip, organism = "anti-Candida", result = norm_result(sub$anti_candida), off = 1),
    data.frame(tip = sub$tip, organism = "anti-MRSA",    result = norm_result(sub$anti_mrsa),    off = 2)
  )
}

p <- ggtree(tr, size = 0.32) %<+% ann +
  geom_tiplab(aes(label = lab_r), color = "#1f4e79", size = lsize, na.rm = TRUE,
              align = FALSE, linesize = 0, offset = r_off) +
  geom_tiplab(aes(label = lab_q), color = "#c00000", fontface = "bold", size = lsize,
              na.rm = TRUE, align = FALSE, linesize = 0, offset = q_off) +
  ggtree::hexpand(0.58)

if (nrow(dots) > 0) {
  tipxy <- p$data[match(dots$tip, p$data$label), c("x", "y")]
  dots$x <- tipxy$x + dots$off * (0.018 * xr)
  dots$y <- tipxy$y
  p <- p + geom_point(data = dots, aes(x = x, y = y, fill = result), shape = 22, size = 2.6,
                       color = "grey40", stroke = 0.25, inherit.aes = FALSE) +
    scale_fill_manual(name = "Bioassay result",
      values = RESULT_COLOR, labels = RESULT_LABEL, breaks = names(RESULT_COLOR))
}

p <- p +
  labs(title = { t <- Sys.getenv("GG_TITLE");
                 if (nzchar(t)) sprintf(t, q_n, r_n)
                 else sprintf("%s - bioassay overlay (%d query tips, %d reference tips)",
                              tools::toTitleCase(gsub("_", " ", group)), q_n, r_n) },
       subtitle = { s <- Sys.getenv("GG_SUB");
                    if (nzchar(s)) s else "Squares from left to right: Candida, MRSA" }) +
  theme_tree2() +
  theme(plot.title = element_text(size = 8), plot.subtitle = element_text(size = 6.5),
        plot.margin = margin(6, 6, 6, 6))

mth <- Sys.getenv("GG_METHODS")
if (nzchar(mth)) {
  mth <- paste(strwrap(mth, width = 135), collapse = "\n")
  p <- p + labs(caption = mth) +
       theme(plot.caption = element_text(hjust = 0, size = 9, colour = "grey20", lineheight = 1.15, margin = margin(t = 14)))
}
h <- max(4, 0.135 * n + 1.5); w <- if (n > 140) 14 else 12
if (nzchar(mth)) h <- h + 0.13 * (lengths(regmatches(mth, gregexpr("\n", mth)))[[1]] + 1) + 1.4
ggsave(paste0(out, ".pdf"), p, width = w, height = h, limitsize = FALSE)
ggsave(paste0(out, ".png"), p, width = w, height = h, dpi = 200, limitsize = FALSE)
cat(sprintf("wrote %s.{pdf,png}  tips=%d queries=%d refs=%d bioassay_dots=%d locmode=%s\n",
            out, n, q_n, r_n, nrow(dots), locmode))
