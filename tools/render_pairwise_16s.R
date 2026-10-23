a <- commandArgs(TRUE); D <- a[1]; TOOLS <- a[2]; O <- a[3]
source(file.path(TOOLS,"sapote_pub_layout.R")); source(file.path(TOOLS,"sapote_min_text.R"))
suppressPackageStartupMessages({ library(dplyr) })
source(file.path(TOOLS,"sapote_pub_layout.R"))
PAL <- c(Streptomyces = "#2E8B84", Nocardia = "#7E5AA2", Micromonospora = "#C0973F", Actinomadura = "#4C78A8")
hp <- unlist(jsonlite::fromJSON(file.path(TOOLS,"../mamey/data/genus_palette.json"))$default); k <- intersect(names(PAL), names(hp)); PAL[k] <- hp[k]
d <- read.delim(file.path(D,"pairwise_16S_identity_overlap.tsv"), stringsAsFactors = FALSE) %>%
  filter(percent_identity != "NA", short_overlap == 0, genus_a == genus_b, genus_a %in% names(PAL)) %>%
  mutate(percent_identity = as.numeric(percent_identity), genus = factor(genus_a, levels = names(PAL)))
iso <- d %>% group_by(genus) %>% summarise(isol = n_distinct(c(a, b)), pairs = n(), .groups = "drop")
strip <- setNames(paste0("<i>", iso$genus, "</i><br><span style='font-size:8pt'>", iso$isol, " isolates, ",
                         format(iso$pairs, big.mark = ","), " pairs</span>"), iso$genus)
p <- ggplot(d, aes(x = percent_identity, fill = genus)) +
  geom_histogram(binwidth = 0.25, boundary = 100, colour = "white", linewidth = 0.1) +
  facet_wrap(~ genus, ncol = 2, scales = "free", labeller = labeller(genus = strip)) +
  scale_fill_manual(values = PAL, guide = "none") +
  scale_x_continuous(breaks = seq(92, 100, 4), labels = function(x) paste0(x, "%")) + coord_cartesian(xlim = c(92, 100)) +
  scale_y_continuous(breaks = function(l) unique(floor(scales::pretty_breaks(3)(l))), expand = expansion(mult = c(0, 0.05))) +
  labs(x = "Pairwise 16S rRNA gene identity", y = "Isolate pairs") +
  theme_pub(base = 6.5) + theme(strip.text = element_markdown(face = "bold", hjust = 0, size = 7, lineheight = 1.05, margin = margin(b = 3)),
                      axis.text = element_text(size = 6.5), axis.title = element_text(colour = PUB_INK, size = 7),
                      panel.grid.major.x = element_blank(), panel.spacing.x = unit(0.35, "cm"), panel.spacing.y = unit(0.3, "cm"),
                      axis.title.y = element_text(margin = margin(r = 4)), axis.title.x = element_text(margin = margin(t = 4)),
                      plot.margin = margin(3, 5, 3, 3))
out <- file.path(O,"pairwise_16s.png"); stopifnot(!file.exists(out))
mt_save(p,tools::file_path_sans_ext(out),3.4,3.05,list(min_text_pt=8,print_width=3.4,dpi=600))
