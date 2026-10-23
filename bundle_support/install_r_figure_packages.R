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
# .452: every package the shipped R scripts load, including R code embedded in Python tools
# (tests/test_452_ci_installs_r.py keeps this list complete).
cran <- c("ggplot2","dplyr","tidyr","scales","patchwork","ape","phangorn","ggrepel","aplot","ggtext","svglite","jsonlite","systemfonts","xml2","ragg","png","readxl")
bioc <- c("ggtree","treeio")
# Optional: not on CRAN (MIT). tools/bgc_class_groups.py draws rounded bars with it and plain bars without it.
# Fetched as a source archive pinned to one commit, not through the GitHub API, which refuses anonymous tokens
# (HTTP 401 on CI). A failed optional install is reported, never fatal.
github <- c(ggchicklet = "https://codeload.github.com/hrbrmstr/ggchicklet/tar.gz/64c468dd0900153be1690dbfc5cfb35710da8183")
have <- function(p) requireNamespace(p, quietly = TRUE)
# Figure groups. Only "core" is required by default; each other group adds one figure family, and a missing one is
# reported, not fatal. --require trees,bioassay (or --require all) makes those groups required too.
# Keep in step with R_FIGURE_GROUPS in mamey/optional_r.py (tests/test_456_r_figure_groups.py checks both).
groups <- list(
  core     = c("ggplot2","ggtext","jsonlite","scales","dplyr","patchwork","ggrepel","svglite","systemfonts","xml2"),
  trees    = c("ape","ggtree","treeio","aplot","phangorn"),
  bioassay = c("tidyr","png"),
  extras   = c("ragg","ggchicklet","readxl"))
req_i <- match("--require", args)
required <- if (!is.na(req_i) && req_i < length(args)) strsplit(args[req_i + 1], ",", fixed = TRUE)[[1]] else character()
if ("all" %in% required) required <- names(groups)
required <- unique(c("core", required))
unknown <- setdiff(required, names(groups))
if (length(unknown)) stop("--require: unknown group(s): ", paste(unknown, collapse = ", "), "; groups are ", paste(names(groups), collapse = ", "))
check_only <- "--check" %in% commandArgs(trailingOnly = TRUE)
if (!check_only && !offline) {
  miss <- cran[!vapply(cran, have, TRUE)]
  if (length(miss)) install.packages(miss, repos = "https://cloud.r-project.org")
  bm <- bioc[!vapply(bioc, have, TRUE)]
  if (length(bm)) tryCatch({ if (!have("BiocManager")) install.packages("BiocManager", repos = "https://cloud.r-project.org")
                             BiocManager::install(bm, ask = FALSE, update = FALSE) },
                           error = function(e) message("Bioconductor packages not installed: ", conditionMessage(e)))
  gm <- names(github)[!vapply(names(github), have, TRUE)]
  for (g in gm) tryCatch({ tgz <- tempfile(fileext = ".tar.gz"); download.file(github[[g]], tgz, mode = "wb")
                           install.packages(tgz, repos = NULL, type = "source") },
                         error = function(e) message("optional package ", g, " not installed: ", conditionMessage(e)))
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
      if (grepl("\\.zip$", z)) {
        d <- tempfile(); dir.create(d); unzip(z, exdir = d)
        roots <- c(d, list.dirs(d, recursive = FALSE))
        src <- roots[file.exists(file.path(roots, "DESCRIPTION"))]
        if (length(src) != 1L)
          stop("--from ZIP must contain exactly one top-level R package with DESCRIPTION: ", basename(z))
      }
      ok <- tryCatch({ install.packages(src, repos = NULL, type = "source"); TRUE }, warning = function(w) FALSE)
      if (!ok) failed <- c(failed, z)
    }
    if (!length(failed) || length(failed) == length(pending)) break
    pending <- failed
  }
  if (length(failed)) message("Not installed from --from (missing dependencies or build errors): ",
                              paste(basename(failed), collapse = ", "))
}
for (g in names(groups)) for (p in groups[[g]])
  cat(sprintf("%-9s %-12s %s\n", g, p, if (have(p)) as.character(packageVersion(p)) else if (g %in% required) "MISSING" else "not installed (optional)"))

missing <- unlist(lapply(required, function(g) groups[[g]][!vapply(groups[[g]], have, TRUE)]))
if (length(missing)) quit(status=2)
