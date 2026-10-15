# Required metadata stamping for shared R export points. Reuse the bundle stamper
# in a private environment so loading it does not replace the caller's theme.
.sapote_required_tools_dir <- dirname(normalizePath(sys.frame(1)$ofile))
sapote_stamp_files_required <- local({
  stamper <- new.env(parent = globalenv())
  source(file.path(.sapote_required_tools_dir, "sapote_figure_theme.R"), local = stamper)
  function(paths, tool) {
    if (!length(paths) || any(!file.exists(paths)))
      stop("FIGURE_STAMP_REQUIRED: output file missing", call. = FALSE)
    if (!isTRUE(stamper$sapote_stamp_files(paths, tool)))
      stop("FIGURE_STAMP_REQUIRED: renderer metadata could not be written", call. = FALSE)
    invisible(TRUE)
  }
})
