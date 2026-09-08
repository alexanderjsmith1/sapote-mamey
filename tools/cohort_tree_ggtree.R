#!/usr/bin/env Rscript
# cohort_tree_ggtree.R — ggtree template for the cohort PHYLOGENOMIC tree (the GToTree concatenated
# single-copy-gene tree), rooted on a declared outgroup.
#
# Companion to tools/ggtree_placement.R, which renders a different thing: an EPA-ng 16S *placement*.
# This one renders the whole-genome cohort tree produced by the phylo arm
# (`<cohort>/phylo_tree/gtotree_out/gtotree_out.tre`).
#
# Usage:
#   Rscript cohort_tree_ggtree.R <tree.tre> <out_prefix> [annotation.tsv] [outgroup_tip] [profile]
#
#     annotation.tsv : optional, tab-separated, columns `identity` and `cohort` (and optionally
#                      `role` and `display_label`). `cohort` keys the shared palette so the tree
#                      colours match every other Sapote-Mamey figure.
#     outgroup_tip   : optional tip name to root on. When omitted the tree is used as read — it is
#                      NOT midpoint-rooted silently, because an unstated rooting is an unstated
#                      phylogenetic claim.
#     profile        : SINGLE_COLUMN (default) or DOUBLE_COLUMN.
#
# Emits <out_prefix>.svg and <out_prefix>.png at 300 dpi.
#
# Claim-safety: a concatenated-marker tree is a NEIGHBOURHOOD, not a species assignment and not a
# product claim. Node support is drawn as-is; a well-supported node is evidence about topology only.

suppressPackageStartupMessages({
  library(ggplot2); library(ape); library(ggtree)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: cohort_tree_ggtree.R <tree.tre> <out_prefix> [annotation.tsv] [outgroup_tip] [profile]")
}
tree_path  <- args[1]
out_prefix <- args[2]
ann_path   <- if (length(args) >= 3 && nzchar(args[3])) args[3] else NA_character_
outgroup   <- if (length(args) >= 4 && nzchar(args[4])) args[4] else NA_character_
profile    <- if (length(args) >= 5) toupper(args[5]) else "SINGLE_COLUMN"

source(file.path(dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])),
                 "sapote_figure_theme.R"))

# ---- read -------------------------------------------------------------------------------------
# read.tree tolerates the trailing newline GToTree writes. (The Python arm's own Newick guard has a
# regex bug on exactly that newline — see PHYLO_PIPELINE_AUDIT_V409.md — so this template reads the
# file the phylo arm produced even where the Python gate currently refuses it.)
tr <- ape::read.tree(tree_path)
if (is.null(tr)) stop(sprintf("could not parse a Newick tree from %s", tree_path))
if (length(tr$tip.label) < 3) stop("a tree with fewer than 3 tips is not renderable as a cohort tree")

if (!is.na(outgroup)) {
  if (!outgroup %in% tr$tip.label) {
    stop(sprintf("outgroup tip %s is not in the tree; tips are: %s",
                 outgroup, paste(tr$tip.label, collapse = ", ")))
  }
  tr <- ape::root(tr, outgroup = outgroup, resolve.root = TRUE)
}

# ---- annotation -------------------------------------------------------------------------------
tip_df <- data.frame(identity = tr$tip.label, stringsAsFactors = FALSE)
tip_df$cohort <- "UNRESOLVED"
tip_df$display_label <- tip_df$identity

if (!is.na(ann_path)) {
  ann <- utils::read.delim(ann_path, sep = "\t", quote = "", stringsAsFactors = FALSE,
                           check.names = FALSE)
  if (!"identity" %in% names(ann)) stop("annotation.tsv needs an `identity` column")
  unmatched <- setdiff(tr$tip.label, ann$identity)
  if (length(unmatched)) {
    # Loud, not silent: an unannotated tip would otherwise render grey and read as a REFERENCE.
    warning(sprintf("tips with no annotation row (rendered UNRESOLVED): %s",
                    paste(unmatched, collapse = ", ")))
  }
  idx <- match(tip_df$identity, ann$identity)
  if ("cohort" %in% names(ann)) {
    matched <- !is.na(idx)
    tip_df$cohort[matched] <- ann$cohort[idx[matched]]
  }
  if ("display_label" %in% names(ann)) {
    lab <- ann$display_label[idx]
    tip_df$display_label <- ifelse(is.na(lab) | !nzchar(lab), tip_df$identity, lab)
  }
}

unknown <- setdiff(unique(tip_df$cohort), names(SAPOTE_COHORT_PALETTE))
if (length(unknown)) {
  stop(sprintf("cohort value(s) with no palette entry: %s — add them to figure_policy.py first",
               paste(unknown, collapse = ", ")))
}

# ---- plot -------------------------------------------------------------------------------------
# Tip labels are nudged OFF the branch end (house rule: text never sits on the data). The x limit is
# expanded so the longest label cannot be clipped at the panel edge.
max_depth <- max(ape::node.depth.edgelength(tr))
nudge     <- sapote_tip_nudge(max_depth)
longest   <- max(nchar(tip_df$display_label))

p <- ggtree(tr, linewidth = 0.4) %<+% tip_df +
  geom_tippoint(aes(colour = cohort), size = 1.4) +
  geom_tiplab(aes(label = display_label, colour = cohort),
              size = 8 / .pt, nudge_x = nudge, hjust = 0) +
  scale_colour_manual(values = SAPOTE_COHORT_PALETTE, drop = FALSE) +
  ggtree::geom_treescale(width = signif(max_depth / 5, 1), fontsize = 8 / .pt, linesize = 0.3) +
  ggplot2::xlim(0, max_depth * (1 + 0.035 * longest)) +
  ggplot2::labs(caption = paste0(
    "Concatenated single-copy marker tree",
    if (!is.na(outgroup)) paste0(" · rooted on ", outgroup) else " · rooting as supplied",
    " · branch lengths are substitutions per site.",
    " Phylogenetic neighbourhood, not a species assignment."
  )) +
  sapote_theme() +
  ggplot2::theme(axis.text = ggplot2::element_blank(),
                 axis.title = ggplot2::element_blank(),
                 panel.grid = ggplot2::element_blank(),
                 plot.caption = ggplot2::element_text(size = 8, hjust = 0))

# Node support, when the tree carries it. Drawn to the upper-LEFT of the node so the number never
# overlaps the branch it annotates. GToTree/FastTree write support as node labels in [0,1].
if (!is.null(tr$node.label) && any(nzchar(tr$node.label))) {
  support <- suppressWarnings(as.numeric(tr$node.label))
  support_df <- data.frame(node = (length(tr$tip.label) + 1):(length(tr$tip.label) + tr$Nnode),
                           support = support, stringsAsFactors = FALSE)
  # Root has no meaningful support; very low values are noise on a 4-taxon tree.
  support_df <- support_df[!is.na(support_df$support), , drop = FALSE]
  if (nrow(support_df)) {
    p <- p %<+% support_df +
      geom_nodelab(aes(label = ifelse(is.na(support), "", sprintf("%.2f", support))),
                   size = 8 / .pt, hjust = 1.15, vjust = -0.5, colour = SAPOTE_INK)
  }
}

paths <- sapote_save_pair(p, out_prefix, profile, sapote_height_in(length(tr$tip.label)))
cat(paste(paths, collapse = "\n"), "\n", sep = "")
