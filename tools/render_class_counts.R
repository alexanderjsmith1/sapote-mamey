a <- commandArgs(TRUE); D <- a[1]; TOOLS <- a[2]; O <- a[3]
source(file.path(TOOLS,"sapote_pub_layout.R")); source(file.path(TOOLS,"sapote_min_text.R"))
suppressPackageStartupMessages({ library(dplyr); library(ggchicklet) })
source(file.path(TOOLS,"sapote_pub_layout.R"))
FAMCOL <- c(PKS = "#C44E52", NRPS = "#3C6E9F", RiPP = "#5E9A4E", Terpene = "#E0A030", `Other classes` = "#8C7AA9")
s <- read.delim(file.path(D,"fig_016d_class_summary.tsv"), stringsAsFactors = FALSE) %>%
  filter(family != "Saccharide", regions >= 3) %>% arrange(regions)
s$display <- factor(s$display, levels = s$display)
s$lab <- paste0(s$regions, " (", s$genomes, ")")
fams <- intersect(names(FAMCOL), unique(s$family))
p <- ggplot(s, aes(x = display, y = regions, fill = family)) +
  geom_chicklet(width = 0.74, radius = grid::unit(1, "pt"), colour = NA) +
  geom_text(aes(label = lab), hjust = -0.08, size = 6 / .pt, colour = PUB_SUB, family = PUB_FONT) +
  coord_flip() + scale_fill_manual(values = FAMCOL[fams], breaks = fams, name = NULL, guide = guide_legend(ncol = 1)) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.24))) +
  labs(x = NULL, y = "Regions carrying the class (genomes)") +
  theme_pub(7) + theme(panel.grid.major.y = element_blank(),
                       legend.position = "inside", legend.position.inside = c(0.98, 0.04), legend.justification = c(1, 0),
                       legend.key.size = unit(7, "pt"), legend.key.spacing.y = unit(1, "pt"),
                       axis.text.y = ggtext::element_markdown(size = 6), axis.text.y.left = ggtext::element_markdown(size = 6, margin = margin(r = 1)),
                       axis.text.x.bottom = ggtext::element_markdown(size = 7), axis.title.x = element_text(size = 7),
                       legend.text = ggtext::element_markdown(size = 7), plot.margin = margin(3, 4, 3, 2))
out <- file.path(O,"class_counts.png")
stopifnot(!file.exists(out))
mt_save(p,tools::file_path_sans_ext(out),3.4,4.2,list(min_text_pt=8,print_width=3.4,dpi=600))
