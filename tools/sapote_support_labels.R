# Support labels for genome trees: anchored at the node, white halo, and a y-only ggrepel nudge only where two labels collide.
# Sourced by render_max4_tree.R (MAX4_SUPPORT_HALO=1) and by the moss S9 renderer copy.
#
# support_halo_layers(nd, small_pt, x_per_pt, y_per_pt, ...) returns a list of ggplot layers.
#   nd        data.frame with x, y (node position, data units) and label (the printed number).
#   small_pt  text size in pt.
#   x_per_pt, y_per_pt  data units per pt on the drawn page. They are only used to find collisions and to cap the nudge;
#             the anchor itself is set in text units (hjust, vjust), so the gap is exact in pt.
# Anchor: the label's right edge sits GAP_X pt left of the node, its baseline GAP_Y pt above the branch line.
# Halo: ggrepel's bg.colour / bg.r, as in tools/tygs_figures.R (T05); branch lines pass under the halo, never through digits.
# Collisions: label boxes (digit width 0.556 em, cap height 0.716 em, Arial/Helvetica) that come within PAD pt (1.6, two
#   halo reaches) of each other
#   form a group. Each group gets its own geom_text_repel layer: direction 'y', ylim limited to MAX_NUDGE pt beyond the
#   group's own boxes, nearby branch lines as empty-label points (sampled every 0.5 pt) to keep the labels off them, a short grey leader to the node, seed and max.iter fixed and max.time = Inf, so reruns are identical.
# Every other label is drawn with ggrepel too (for the halo) but with force 0 and max.iter 0: it does not move.
# Branch lines (segs: x0, y0, x1, y1 in data units; tree_segments() builds them from ggtree data): when the default box would
#   cross a branch line, the label goes just below the branch (still left of the node), or else just right of the node,
#   whichever is clear first. With no clear spot it stays at the default, behind its halo. The caption must say so.
#   "Clear" means no branch line within `clear` pt (0.8, the halo's reach at bg.r 0.12) and no tip symbol (pts: x, y and
#   radius in pt) touching the box. Two labels on one row with a vertical branch line between them and a gap of at most
#   ambig_gap pt (4) count as colliding too: side by side across a line, a reader cannot tell which node each number labels.
tree_segments <- function(td) {
  e <- td[!is.na(td$parent) & td$parent != td$node, ]
  par_x <- td$x[match(e$parent, td$node)]
  h <- data.frame(x0 = par_x, y0 = e$y, x1 = e$x, y1 = e$y)
  inn <- td[!td$isTip, ]
  v <- do.call(rbind, lapply(seq_len(nrow(inn)), function(i) { k <- td$y[td$parent == inn$node[i] & td$node != inn$node[i]]
    if (!length(k)) NULL else data.frame(x0 = inn$x[i], y0 = min(k), x1 = inn$x[i], y1 = max(k)) }))
  rbind(h, v)
}
# Data units per pt of the tree panel (panel 1, leftmost) on the final W x H page: the panel's laid-out size from the
# patchwork gtable, and the data ranges ggplot actually drew (scale expansion included). Exact, so collision and
# clearance tests in pt match the SVG. Needs an open graphics device for text metrics (the caller opens a null device of
# the page size and closes it); this helper never opens or saves one.
tree_panel_scale <- function(fig, tree_plot, W, H) {
  if (grDevices::dev.cur() == 1) stop('tree_panel_scale: open a null device of the page size first')
  g <- patchwork::patchworkGrob(fig)
  size <- function(units, total) { isnull <- grid::unitType(units) == 'null'
    val <- vapply(seq_along(units), function(i) if (isnull[i]) 0 else grid::convertUnit(units[i], 'in', valueOnly = TRUE), 0)
    nul <- vapply(seq_along(units), function(i) if (isnull[i]) as.numeric(units[i]) else 0, 0)
    ifelse(isnull, (total - sum(val)) * nul / sum(nul), val) }
  pr <- g$layout[grepl('^panel', g$layout$name), ]; pr <- pr[order(pr$l, pr$t), ][1, ]
  pw <- sum(size(g$widths, W)[pr$l:pr$r]); ph <- sum(size(g$heights, H)[pr$t:pr$b])
  pp <- ggplot2::ggplot_build(tree_plot)$layout$panel_params[[1]]
  c(x_per_pt = diff(pp$x.range) / (pw * 72), y_per_pt = diff(pp$y.range) / (ph * 72), panel_w_in = pw, panel_h_in = ph)
}

support_halo_layers <- function(nd, small_pt, x_per_pt, y_per_pt, colour = 'grey35', gap_x = 1, gap_y = 1.2,
                                pad = 1.6, max_nudge = 4, seed = 1L, max_iter = 20000L, halo_r = 0.12, leader = '#595959', segs = NULL,
                                pts = NULL, clear = 0.8, ambig_gap = 4) {
  if (!requireNamespace('ggrepel', quietly = TRUE)) stop('MAX4_SUPPORT_HALO needs the ggrepel package')
  if (!nrow(nd)) return(list())
  w_pt <- nchar(nd$label) * 0.556 * small_pt; h_pt <- 0.716 * small_pt
  nd$hj <- 1 + gap_x / w_pt          # right edge gap_x pt left of the node
  nd$vj <- -gap_y / h_pt             # baseline gap_y pt above the node's y
  # boxes in pt, relative to an arbitrary origin; y grows upwards, as in the data
  bx1 <- nd$x / x_per_pt - gap_x; bx0 <- bx1 - w_pt; by0 <- nd$y / y_per_pt + gap_y; by1 <- by0 + h_pt
  # Placement, greedy, deepest nodes first. Candidates in order: left-above (the default), left-below (top gap_y pt under the
  # branch line), right-centre (left edge gap_x pt right of the node). Take the first candidate clear of branch lines and of
  # labels already placed; else the first clear of lines (a later nudge separates the labels); else left-above, behind the halo.
  nd$side <- 'left-above'
  ambig <- function(a, b) FALSE   # replaced below when branch lines are supplied
  if (!is.null(segs) && nrow(segs)) {
    sx0 <- pmin(segs$x0, segs$x1) / x_per_pt; sx1 <- pmax(segs$x0, segs$x1) / x_per_pt
    sy0 <- pmin(segs$y0, segs$y1) / y_per_pt; sy1 <- pmax(segs$y0, segs$y1) / y_per_pt
    # a box hits when a branch line comes within `clear` pt (the halo's reach) or a tip symbol (pts: x, y, r_pt) overlaps it
    px <- if (is.null(pts)) numeric(0) else pts$x / x_per_pt; py <- if (is.null(pts)) numeric(0) else pts$y / y_per_pt; pr <- if (is.null(pts)) numeric(0) else pts$r_pt
    hits <- function(b) any(sx0 < b[3] + clear & sx1 > b[1] - clear & sy0 < b[4] + clear & sy1 > b[2] - clear) ||
      any(px + pr > b[1] - clear & px - pr < b[3] + clear & py + pr > b[2] - clear & py - pr < b[4] + clear)
    placed <- list()
    vx <- sx0[sx0 == sx1]; vy0 <- sy0[sx0 == sx1]; vy1 <- sy1[sx0 == sx1]   # vertical branch lines
    # two labels side by side with a vertical line between them read as one label: same row (y within 1 pt), gap <= ambig_gap
    ambig <- function(a, b) { if (a[1] > b[1]) { t <- a; a <- b; b <- t }; g <- b[1] - a[3]
      if (g < 0 || g > ambig_gap || a[2] > b[4] + 1 || b[2] > a[4] + 1) return(FALSE)
      lo <- max(a[2], b[2]) - 1; hi <- min(a[4], b[4]) + 1; any(vx >= a[3] & vx <= b[1] & vy0 < hi & vy1 > lo) }
    near <- function(b) any(vapply(placed, function(q) (b[1] < q[3] + pad && q[1] < b[3] + pad && b[2] < q[4] + pad && q[2] < b[4] + pad) || ambig(b, q), TRUE))
    for (i in order(-nd$x)) {
      X <- nd$x[i] / x_per_pt; Y <- nd$y[i] / y_per_pt; w <- w_pt[i]
      cand <- list(`left-above` = list(b = c(X - gap_x - w, Y + gap_y, X - gap_x, Y + gap_y + h_pt), hj = 1 + gap_x / w, vj = -gap_y / h_pt),
                   `left-below` = list(b = c(X - gap_x - w, Y - gap_y - h_pt, X - gap_x, Y - gap_y), hj = 1 + gap_x / w, vj = 1 + gap_y / h_pt),
                   `right-centre` = list(b = c(X + gap_x, Y - h_pt / 2, X + gap_x + w, Y + h_pt / 2), hj = -gap_x / w, vj = 0.5))
      ok_line <- !vapply(cand, function(cc) hits(cc$b), TRUE); free <- ok_line & !vapply(cand, function(cc) near(cc$b), TRUE)
      k <- if (any(free)) which(free)[1] else if (any(ok_line)) which(ok_line)[1] else 1L
      cc <- cand[[k]]; nd$side[i] <- names(cand)[k]; nd$hj[i] <- cc$hj; nd$vj[i] <- cc$vj
      bx0[i] <- cc$b[1]; by0[i] <- cc$b[2]; bx1[i] <- cc$b[3]; by1[i] <- cc$b[4]; placed[[length(placed) + 1]] <- cc$b } }
  n <- nrow(nd); grp <- seq_len(n)
  find <- function(i) { while (grp[i] != i) i <- grp[i]; i }
  for (i in seq_len(n - 1)) for (j in (i + 1):n)
    if ((bx0[i] < bx1[j] + pad && bx0[j] < bx1[i] + pad && by0[i] < by1[j] + pad && by0[j] < by1[i] + pad) ||
        ambig(c(bx0[i], by0[i], bx1[i], by1[i]), c(bx0[j], by0[j], bx1[j], by1[j]))) grp[find(j)] <- find(i)
  g <- vapply(seq_len(n), find, 0L); sizes <- table(g); nd$group <- ifelse(sizes[as.character(g)] > 1, g, 0L)
  # a label whose spot still meets a line or symbol (no candidate was clear) gets the same y search, as a group of one
  blocked <- if (exists('hits', inherits = FALSE)) vapply(seq_len(n), function(i) hits(c(bx0[i], by0[i], bx1[i], by1[i])), TRUE) else rep(FALSE, n)
  nd$group[blocked & nd$group == 0L] <- n + which(blocked & nd$group == 0L)
  fixed <- nd[nd$group == 0, ]
  layers <- list()
  if (nrow(fixed)) layers[[1]] <- ggrepel::geom_text_repel(data = fixed, ggplot2::aes(x = x, y = y, label = label), size = small_pt / ggplot2::.pt,
      hjust = fixed$hj, vjust = fixed$vj, colour = colour, bg.colour = 'white', bg.r = halo_r, force = 0, force_pull = 0, max.iter = 0,
      max.time = Inf, seed = seed, segment.colour = NA, max.overlaps = Inf, box.padding = 0, point.padding = 0, inherit.aes = FALSE)
  # Collision groups: exhaustive y search. Each label may take any of the three spots and a y offset of -max_nudge..max_nudge
  # in 0.1 pt steps; the combination with the smallest cost (total |offset| in pt, +0.5 for leaving the chosen spot) that
  # clears every branch line and keeps labels pad pt apart wins; ties go to the first in a fixed order. With no clean
  # combination, the labels keep their spots and only the label-label clearance is solved. ggrepel then draws each label at
  # its solved offset (nudge_y, force 0) with the halo and a short leader to the node. Deterministic: no random step.
  hits_b <- if (exists('hits', inherits = FALSE)) hits else function(b) FALSE
  sep <- function(B) { m <- nrow(B); if (m < 2) return(TRUE); for (u in 1:(m - 1)) for (v in (u + 1):m)
    if ((B[u, 1] < B[v, 3] + pad && B[v, 1] < B[u, 3] + pad && B[u, 2] < B[v, 4] + pad && B[v, 2] < B[u, 4] + pad) ||
        ambig(B[u, ], B[v, ])) return(FALSE); TRUE }
  steps <- seq(-max_nudge, max_nudge, by = 0.1); steps <- steps[order(abs(steps), steps)]
  nd$dy <- 0
  for (k in setdiff(unique(nd$group), 0L)) {
    ii <- which(nd$group == k)
    opts <- lapply(ii, function(i) { X <- nd$x[i] / x_per_pt; Y <- nd$y[i] / y_per_pt; w <- w_pt[i]
      base <- list(`left-above` = c(X - gap_x - w, Y + gap_y, X - gap_x, Y + gap_y + h_pt), `left-below` = c(X - gap_x - w, Y - gap_y - h_pt, X - gap_x, Y - gap_y),
                   `right-centre` = c(X + gap_x, Y - h_pt / 2, X + gap_x + w, Y + h_pt / 2))
      o <- expand.grid(side = names(base), dy = steps, stringsAsFactors = FALSE)
      o$cost <- abs(o$dy) + ifelse(o$side == nd$side[i], 0, 0.5)
      o$b <- lapply(seq_len(nrow(o)), function(r) base[[o$side[r]]] + c(0, o$dy[r], 0, o$dy[r]))
      o$line_ok <- !vapply(o$b, hits_b, TRUE); o[order(o$cost), ] })
    best <- NULL
    for (need_lines in c(TRUE, FALSE)) {
      keep <- if (length(ii) == 1) 300 else if (length(ii) == 2) 120 else if (length(ii) == 3) 25 else 8   # caps the joint search at about 15,000 rows
      cand <- lapply(opts, function(o) { if (need_lines) o <- o[o$line_ok, ]; head(o, keep) })
      if (any(vapply(cand, nrow, 0L) == 0)) next
      idx <- expand.grid(lapply(cand, function(o) seq_len(nrow(o)))); cost <- Reduce(`+`, lapply(seq_along(cand), function(j) cand[[j]]$cost[idx[[j]]]))
      for (r in order(cost, seq_along(cost))) { B <- do.call(rbind, lapply(seq_along(cand), function(j) cand[[j]]$b[[idx[r, j]]]))
        if (sep(B)) { best <- lapply(seq_along(cand), function(j) cand[[j]][idx[r, j], ]); break } }
      if (!is.null(best)) break }
    if (is.null(best)) next
    for (j in seq_along(ii)) { i <- ii[j]; o <- best[[j]]; sd <- o$side
      nd$side[i] <- sd; nd$dy[i] <- o$dy; w <- w_pt[i]
      nd$hj[i] <- if (sd == 'right-centre') -gap_x / w else 1 + gap_x / w
      nd$vj[i] <- switch(sd, `left-above` = -gap_y / h_pt, `left-below` = 1 + gap_y / h_pt, `right-centre` = 0.5) }
  }
  moved <- nd[nd$group != 0, ]
  if (nrow(moved)) layers[[length(layers) + 1]] <- ggrepel::geom_text_repel(data = moved, ggplot2::aes(x = x, y = y, label = label), size = small_pt / ggplot2::.pt,
      hjust = moved$hj, vjust = moved$vj, nudge_y = moved$dy * y_per_pt, colour = colour, bg.colour = 'white', bg.r = halo_r, force = 0, force_pull = 0,
      max.iter = max_iter, max.time = Inf, seed = seed, box.padding = 0, point.padding = 0, point.size = 0, min.segment.length = grid::unit(1, 'pt'),
      segment.colour = leader, segment.size = 0.2, max.overlaps = Inf, inherit.aes = FALSE)
  attr(layers, 'groups') <- length(setdiff(unique(nd$group), 0L)); attr(layers, 'nudged') <- sum(nd$group != 0 & nd$dy != 0); attr(layers, 'side') <- table(factor(nd$side, c('left-above', 'left-below', 'right-centre')))
  attr(layers, 'table') <- nd
  layers
}
