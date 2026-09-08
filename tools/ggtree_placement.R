#!/usr/bin/env Rscript
# ggtree_placement.R — render an EPA-ng 16S placement (pruned newick + annotation TSV) with ggtree.
# AS queries in red (bold) with host [+ region] + GenBank accession; type-strain references in blue.
# Inputs are produced by build_placement_ggtree_inputs.py (<group>_pruned.nwk, <group>_ggtree_annotation.tsv).
#
# Usage:
#   Rscript ggtree_placement.R <pruned.nwk> <annotation.tsv> <out_prefix> [withloc|noloc]
# Emits <out_prefix>.pdf and <out_prefix>.png. Location labels are already normalised to a bare
# region in the TSV (label_withloc / label_noloc); pick with the 4th arg.
#
# Claim-safety: 16S is an anchor / neighbourhood, not a species call; judgment deferred.

suppressPackageStartupMessages({
  library(ape); library(ggtree); library(ggplot2); library(treeio)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) stop("Usage: ggtree_placement.R <nwk> <tsv> <out_prefix> [withloc|noloc]")
nwk <- args[1]; tsv <- args[2]; out <- args[3]
locmode <- ifelse(length(args) >= 4, args[4], "withloc")

tr  <- read.tree(nwk)
ann <- read.delim(tsv, sep = "\t", quote = "", stringsAsFactors = FALSE, check.names = FALSE)

# choose the query label column; references always use ref_label
qcol <- if (locmode == "noloc") "label_noloc" else "label_withloc"
ann$show <- ifelse(ann$kind == "query", ann[[qcol]], ann$ref_label)
if (!("origin" %in% names(ann))) ann$origin <- NA
# split labels into two columns so we can style queries vs references independently
ann$lab_q <- ifelse(ann$kind == "query", ann$show, NA)
ann$lab_r <- ifelse(ann$kind == "reference", ann$show, NA)

n     <- length(tr$tip.label)
q_n   <- sum(ann$kind == "query", na.rm = TRUE)
r_n   <- json_ref <- sum(ann$kind == "reference", na.rm = TRUE)
lsize <- if (n > 140) 1.9 else if (n > 60) 2.3 else 2.8
group <- sub("_placement.*$", "", basename(out)); group <- sub("_ggtree.*$", "", group)

# Label offsets. The query tip point is centred ON the tip, so a tiplab drawn with no offset starts
# at the same x and the dot collides with the first letter of the strain id. Offsets are expressed
# as a fraction of the tree's own depth (substitutions/site), NOT in absolute units, so they hold
# whatever the branch-length scale of a given genus turns out to be.
xr    <- max(ape::node.depth.edgelength(tr), na.rm = TRUE)
q_off <- 0.020 * xr      # query labels clear the host/query point
r_off <- 0.008 * xr      # reference labels get the same breathing room, visually consistent

p <- ggtree(tr, size = 0.32) %<+% ann +
  # reference tips (blue)
  geom_tiplab(aes(label = lab_r), color = "#1f4e79", size = lsize, na.rm = TRUE,
              align = FALSE, linesize = 0, offset = r_off) +
  # query tips (red, bold) + a red point at the tip
  geom_tippoint(aes(subset = (kind == "query")), color = "#c00000", size = 0.9, na.rm = TRUE) +
  geom_tiplab(aes(label = lab_q), color = "#c00000", fontface = "bold", size = lsize,
              na.rm = TRUE, align = FALSE, linesize = 0, offset = q_off) +
  geom_tippoint(aes(subset = (kind == "reference" & !is.na(origin) & origin != ""), color = origin),
                size = 1.4, na.rm = TRUE) +
  scale_color_manual(name = "Isolation source",
    values = c("soil"="#7a5230","soil/rock"="#b08d57","plant"="#2ca02c","lichen"="#66c2a5","marine"="#4aa3c7",
               "insect-associated"="#8856a7","clinical/animal"="#d94801","other"="#969696",
               "unresolved"="#d9d9d9"), na.translate = FALSE) +
  guides(color = guide_legend(override.aes = list(size = 3), order = 2)) +
  ggtree::hexpand(0.52) +                                   # room for long tip labels
  # Caption is overridable per caller (GG_TITLE / GG_SUB env) so a fungal 18S IQ-TREE is not
  # mislabelled with the bacterial 16S/EPA-ng default.
  labs(title = { t <- Sys.getenv("GG_TITLE");
                 if (nzchar(t)) sprintf(t, q_n, r_n)
                 else sprintf("%s 16S phylogenetic placement (EPA-ng) — %d AS queries (red) on a %d type-strain RAxML-NG (GTR+G, 10 BS) backbone",
                              tools::toTitleCase(gsub("_", " ", group)), q_n, r_n) },
       subtitle = { s <- Sys.getenv("GG_SUB");
                    if (nzchar(s)) s
                    else sprintf("query-pruned to nearest-neighbour clades; labels %s (paper strain table); ggtree | 16S = anchor/neighbourhood, not a species call; judgment deferred",
                                 if (locmode == "noloc") "host + accession" else "host + region + accession") }) +
  theme_tree2() +
  theme(plot.title = element_text(size = 8), plot.subtitle = element_text(size = 6.5),
        plot.margin = margin(6, 6, 6, 6))

# GG_METHODS: an optional methods block rendered as a left-aligned caption BELOW the tree, so the
# figure carries its own methods (every tree must travel with its methods). Wrapped to page width.
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
cat(sprintf("wrote %s.{pdf,png}  tips=%d queries=%d refs=%d locmode=%s\n", out, n, q_n, r_n, locmode))
