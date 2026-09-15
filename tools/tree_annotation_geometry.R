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
