a <- commandArgs(TRUE); D <- a[1]; TOOLS <- a[2]; O <- a[3]
source(file.path(TOOLS,"sapote_pub_layout.R")); source(file.path(TOOLS,"sapote_min_text.R"))
suppressPackageStartupMessages({ library(dplyr); library(patchwork) })
source(file.path(TOOLS,"sapote_pub_layout.R"))
m <- read.delim(file.path(D,"cross_001b_matrix.tsv"), stringsAsFactors = FALSE)
m$family[m$family == "Terpene"] <- "Other classes"   # one-column group: its strip label would not fit
t <- read.delim(file.path(D,"cross_001b_genome_totals.tsv"), stringsAsFactors = FALSE)
gord <- m %>% distinct(strain, genus) %>% count(genus) %>% arrange(desc(n), genus) %>% pull(genus)
FAMS <- c("PKS", "NRPS", "RiPP", "Other classes")
cls_ord <- m %>% group_by(display, family) %>% summarise(tot = sum(count), .groups = "drop") %>%
  mutate(family = factor(family, levels = FAMS)) %>% arrange(family, desc(tot)) %>% pull(display)
m <- m %>% mutate(genus = factor(genus, levels = gord), family = factor(family, levels = FAMS),
                  display = factor(display, levels = cls_ord),
                  lab = paste0("<i>", genus, "</i> sp. ", strain))
rowlab <- m %>% distinct(strain, lab) %>% { setNames(.$lab, .$strain) }
sord <- m %>% distinct(strain, genus) %>% arrange(genus, strain) %>% pull(strain)
m$strain <- factor(m$strain, levels = rev(sord))
m$bin <- factor(ifelse(m$count >= 6, "6 or more", as.character(m$count)), levels = c(as.character(0:5), "6 or more"))
BINCOL <- setNames(colorRampPalette(c("#F4F6F9", "#3C6E9F"))(7), levels(m$bin))

render <- function(RL, EW, W, H, OUT) {
CELL <- 2.1   # mm = 6 pt
p1 <- ggplot(m, aes(x = display, y = strain, fill = bin)) +
  geom_tile(colour = "white", linewidth = 0.25) +
  geom_text(aes(label = count, colour = count == 0), show.legend = FALSE, size = CELL, family = PUB_FONT) +
  scale_colour_manual(values = c(`TRUE` = "#AEB6C1", `FALSE` = PUB_INK), guide = "none") +
  scale_fill_manual(values = BINCOL, drop = FALSE, name = "Regions", guide = guide_legend(nrow = 1)) +
  scale_y_discrete(labels = RL) +
  facet_grid(genus ~ family, scales = "free", space = "free", switch = "y") +
  labs(x = NULL, y = NULL) + theme_pub(7) +
  theme(axis.text.x.bottom = element_markdown(angle = 90, hjust = 1, vjust = 0.5, size = 7, colour = PUB_INK),
        axis.text.y.left = element_markdown(size = 7, colour = PUB_INK), panel.grid = element_blank(), panel.spacing = unit(1.5, "pt"),
        strip.text.y.left = element_blank(), strip.text.x = element_text(face = "bold", size = 7.5), strip.placement = "outside",
        legend.position = "bottom", legend.key.width = unit(0.7, "cm"), legend.key.height = unit(0.25, "cm"),
        legend.text = element_markdown(size = 7), legend.title = element_text(size = 7, face = "bold"),
        legend.justification = "left", plot.margin = margin(2, 1, 2, 2))
t$strain <- factor(t$strain, levels = rev(sord)); t$genus <- factor(t$genus, levels = gord)
p2 <- ggplot(t, aes(x = pct_edge, y = strain)) + geom_col(fill = "#B8BFC9", width = 0.7) +
  geom_text(aes(label = paste0(pct_edge, "%")), hjust = -0.12, size = CELL, colour = PUB_INK, family = PUB_FONT) +
  facet_grid(genus ~ "On a\ncontig edge", scales = "free_y", space = "free_y") +
  scale_x_continuous(limits = c(0, 150), breaks = c(0, 100), labels = function(x) paste0(x, "%")) +
  labs(x = NULL, y = NULL) + theme_pub(7) +
  theme(axis.text.y.left = element_blank(), axis.text.x = element_text(size = 7, colour = PUB_INK), panel.grid = element_blank(),
        panel.spacing = unit(1.5, "pt"),
        strip.text.y = element_text(face = "bold.italic", size = 7, angle = 0, hjust = 0, vjust = 0.5, colour = PUB_INK, margin = margin(l = 3, r = 1)),
        strip.text.x = element_text(face = "bold", size = 7.5), plot.margin = margin(2, 2, 2, 1))
body <- (p1 | p2) + plot_layout(widths = c(10, EW))
  mt_save(body,file.path(O,tools::file_path_sans_ext(OUT)),W,H,list(min_text_pt=8,print_width=W,dpi=600))
}

short <- setNames(names(rowlab), names(rowlab))   # AS number only; the genus is in the right-hand strip
render(short, 2.1, 7.0, 6.2, "CROSS_001b_class_heatmap_bee_wasp_genomes_PRINT.png")
render(rowlab, 1.7, 9.4, 6.8, "CROSS_001b_class_heatmap_bee_wasp_genomes_PRINT_LANDSCAPE.png")
