#!/usr/bin/env Rscript
# Install the R packages the bundle's figure renderers need. Online: CRAN + Bioconductor.
# Offline: --from <dir> installs every package archive (.tar.gz or .zip source) found in a directory
# the operator supplies. No third-party package source is shipped in this bundle.
# Usage: Rscript install_r_figure_packages.R [--check] [--from <dir>]
args <- commandArgs(trailingOnly = TRUE)
from_i <- match("--from", args)
from_dir <- if (!is.na(from_i) && from_i < length(args)) args[from_i + 1] else NA
if (!is.na(from_i) && (is.na(from_dir) || startsWith(from_dir, "--")))
  stop("--from needs a directory of package archives; refusing to fall back to an online install")
offline <- !is.na(from_dir)
cran <- c("ggplot2","dplyr","tidyr","scales","patchwork","ape","ggrepel")
bioc <- c("ggtree","treeio")
have <- function(p) requireNamespace(p, quietly = TRUE)
check_only <- "--check" %in% commandArgs(trailingOnly = TRUE)
if (!check_only && !offline) {
  miss <- cran[!vapply(cran, have, TRUE)]
  if (length(miss)) install.packages(miss, repos = "https://cloud.r-project.org")
  bm <- bioc[!vapply(bioc, have, TRUE)]
  if (length(bm)) { if (!have("BiocManager")) install.packages("BiocManager", repos = "https://cloud.r-project.org"); BiocManager::install(bm, ask = FALSE, update = FALSE) }
} else if (!check_only) {
  if (!dir.exists(from_dir)) stop("--from directory not found: ", from_dir)
  archives <- list.files(from_dir, pattern = "\\.(tar\\.gz|zip)$", full.names = TRUE)
  if (!length(archives)) stop("--from directory holds no .tar.gz or .zip package archives: ", from_dir)
  # repos = NULL resolves no dependencies, and list.files() order is alphabetical (ggplot2 before
  # scales, ggtree before treeio). Retry the failures until a pass installs nothing new.
  pending <- archives
  repeat {
    failed <- character()
    for (z in pending) {
      src <- z
      if (grepl("\\.zip$", z)) { d <- tempfile(); dir.create(d); unzip(z, exdir = d); src <- list.dirs(d, recursive = FALSE)[1] }
      ok <- tryCatch({ install.packages(src, repos = NULL, type = "source"); TRUE }, warning = function(w) FALSE)
      if (!ok) failed <- c(failed, z)
    }
    if (!length(failed) || length(failed) == length(pending)) break
    pending <- failed
  }
  if (length(failed)) message("Not installed from --from (missing dependencies or build errors): ",
                              paste(basename(failed), collapse = ", "))
}
for (p in c(cran, bioc)) cat(sprintf("%-10s %s\n", p, if (have(p)) as.character(packageVersion(p)) else "MISSING"))

missing <- c(cran, bioc)[!vapply(c(cran, bioc), have, TRUE)]
if (length(missing)) quit(status=2)
