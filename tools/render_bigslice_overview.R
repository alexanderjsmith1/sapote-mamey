suppressPackageStartupMessages({ library(ggplot2); library(patchwork); library(scales) })
a <- commandArgs(TRUE); D <- a[1]; TOOLS <- a[2]; O <- a[3]
source(file.path(TOOLS, "sapote_pub_layout.R"))
rd <- function(f) read.delim(file.path(D, f), check.names = FALSE, stringsAsFactors = FALSE)
COLL <- c(bee_wasp = "Bee/wasp", moss = "Moss", attine = "Attine")
COH  <- c(bee_wasp = "#C9A227", moss = "#2E7D4F", attine = "#8C4A2F")
CATS <- c("reference_family", "isolate_only_shared", "isolate_only_alone", "beyond_0.6_to_0.8", "beyond_0.8")
CATLAB <- c("In a family with a reference or database genome", "In an AS-only family, 2+ regions", "Alone in its family",
            "Beyond 0.6, up to 0.8, from every family", "Beyond 0.8 from every family")
CATCOL <- c("#BDBDBD", "#0072B2", "#56B4E9", "#D55E00", "#6B2D00")
TXT <- c("#17212E", "#FFFFFF", "#17212E", "#FFFFFF", "#FFFFFF")
BASE <- 10

A <- rd("panelA_data.tsv")
A$collection <- factor(A$collection, levels = rev(names(COLL)))
A$category <- factor(A$category, levels = rev(CATS))                       # stack order: reference family at the left
A$frac <- A$regions / A$total_regions
A$lab <- ifelse(A$frac >= 0.045, format(A$regions, big.mark = ","), "")
A$txt <- TXT[match(as.character(A$category), CATS)]
glab <- setNames(sprintf("%s<br>(n = %s)", COLL, format(tapply(A$total_regions, A$collection, max)[names(COLL)], big.mark = ",")), names(COLL))
pa <- ggplot(A, aes(frac, collection, fill = category)) +
  geom_col(width = 0.68, colour = "white", linewidth = 0.3) +
  geom_text(aes(label = lab, colour = category), position = position_stack(vjust = 0.5), size = 3.0, family = PUB_FONT, show.legend = FALSE) +
  scale_colour_manual(values = setNames(TXT, CATS)) +
  scale_fill_manual(NULL, values = setNames(CATCOL, CATS), labels = setNames(CATLAB, CATS), breaks = CATS) +
  scale_x_continuous("Share of regions", labels = percent, expand = expansion(mult = c(0, 0.01))) +
  scale_y_discrete(NULL, labels = glab) +
  guides(fill = guide_legend(nrow = 3, byrow = TRUE)) +
  theme_pub(BASE) + theme(legend.position = "top", legend.justification = "left", legend.key.size = unit(0.35, "cm"),
                          panel.grid.major.y = element_blank(), axis.text.y.left = ggtext::element_markdown(lineheight = 1.0, colour = PUB_INK))

I <- rd("panelB_isolate.tsv"); G <- rd("panelB_background.tsv")
I$collection <- factor(COLL[I$collection], levels = COLL)
BW <- 0.025; brk <- seq(0, 1.1, by = BW)
bin <- function(x) { h <- hist(pmin(x, 1.1 - 1e-9), breaks = brk, plot = FALSE, right = FALSE); data.frame(x = h$mids, f = h$counts / length(x)) }
bgd <- bin(G$distance)
bgall <- do.call(rbind, lapply(COLL, function(cl) cbind(bgd, collection = cl)))
cd <- do.call(rbind, lapply(names(COLL), function(k) cbind(bin(I$distance[I$collection == COLL[k]]), collection = COLL[k])))
bgall$collection <- factor(bgall$collection, levels = COLL); cd$collection <- factor(cd$collection, levels = COLL)
fillv <- setNames(COH, COLL)
pb <- ggplot() +
  geom_col(data = bgall, aes(x, f), width = BW, fill = "#BDBDBD", colour = NA) +
  geom_col(data = cd, aes(x, f, fill = collection), width = BW, alpha = 0.85, colour = NA) +
  geom_step(data = bgall, aes(x - BW/2, f), direction = "hv", colour = "#555555", linewidth = 0.3) +
  geom_vline(xintercept = 0.6, linetype = "dashed", linewidth = 0.4, colour = PUB_INK) +
  geom_vline(xintercept = 0.8, linetype = "dotted", linewidth = 0.5, colour = PUB_INK) +
  scale_fill_manual(values = fillv, guide = "none") +
  facet_wrap(~collection, ncol = 1, strip.position = "top") +
  scale_x_continuous("Distance to the nearest family centroid", breaks = seq(0, 1.0, 0.2), expand = expansion(mult = c(0.01, 0.01))) +
  scale_y_continuous("Fraction of regions per bin", labels = percent_format(accuracy = 1)) +
  coord_cartesian(xlim = c(0, 1.1)) +
  theme_pub(BASE) + theme(strip.text = element_text(hjust = 0, face = "bold", size = 9, colour = PUB_INK), panel.spacing.y = unit(0.35, "lines"))

fig <- (pa / pb) + plot_layout(heights = c(1.0, 2.1)) + plot_annotation(tag_levels = "a")
source(file.path(TOOLS,"sapote_min_text.R"))
mt_save(fig,file.path(O,"bigslice_overview"),6.5,7.4,list(min_text_pt=8,print_width=6.5,dpi=600))
