# Validate the actual built strip, not only its source geom_tile() arguments.
validate_annotation_strip <- function(plot, tip_order, expected_values, palette) {
  if (anyDuplicated(tip_order) || length(tip_order) != length(expected_values))
    stop("ANNOTATION_IDENTITY: invalid tip/value roster")
  built <- ggplot2::ggplot_build(plot)$data[[1]]
  n <- length(tip_order)
  if (nrow(built) != n || anyDuplicated(built$y) || any(!is.finite(built$y)) ||
      !setequal(as.numeric(built$y), seq_len(n))) stop("ANNOTATION_ROWS: non-bijective strip")
  if (any(!is.finite(built$ymin)) || any(!is.finite(built$ymax)) ||
      any(abs((built$ymax-built$ymin)-1)>1e-8) ||
      any(abs((built$ymax+built$ymin)/2-built$y)>1e-8))
    stop("ANNOTATION_GEOMETRY: each cell must occupy exactly one tip row")
  expected <- unname(palette[as.character(expected_values)])
  expected[is.na(expected_values) | expected_values==""] <- "#eeeeee"
  if (anyNA(expected)) stop("ANNOTATION_PALETTE: missing category colour")
  actual <- built$fill[match(seq_len(n),as.numeric(built$y))]
  same <- vapply(seq_len(n),function(i) identical(grDevices::col2rgb(actual[i]),grDevices::col2rgb(expected[i])),logical(1))
  if (!all(same)) stop("ANNOTATION_COLOUR: strip colours differ from joined tip values")
  data.frame(tip=tip_order,y=seq_len(n),value=expected_values,fill=actual)
}

# v9.7.444: every panel of a tree + strips figure must span one y range, or strip cells sit off their tips.
# aplot draws the tree over [scale-bar y, n + 0.6]; a strip left on its default range [0.4, n + 0.6] has rows
# slightly shorter than the tree's, and its cells drift off their tips toward the bottom of the tree.
validate_panel_ranges <- function(combined) {
  pw <- aplot::as.patchwork(combined)
  yr <- lapply(c(list(pw), pw$patches$plots), function(g)
    tryCatch(ggplot2::ggplot_build(g)$layout$panel_params[[1]]$y.range, error = function(e) NULL))
  yr <- Filter(Negate(is.null), yr)
  shown <- vapply(yr, function(r) paste(format(round(r, 4), nsmall = 4), collapse = ".."), "")
  if (length(yr) < 2 || any(vapply(yr, function(r) max(abs(r - yr[[1]])) > 1e-6, logical(1))))
    stop("ANNOTATION_PANEL_RANGE_MISMATCH: ", paste(shown, collapse = " vs "))
  shown
}
