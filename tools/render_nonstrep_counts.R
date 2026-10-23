a <- commandArgs(TRUE); D <- a[1]; TOOLS <- a[2]; O <- a[3]
source(file.path(TOOLS,"sapote_pub_layout.R")); source(file.path(TOOLS,"sapote_min_text.R"))
suppressPackageStartupMessages({ library(ggplot2); library(dplyr); library(readxl); library(ggtext) })
INK <- "#17212E"; SUB <- "#54637A"; FONT <- "Arial"
hp <- unlist(jsonlite::fromJSON(file.path(TOOLS,"../mamey/data/genus_palette.json"))$default)
s1 <- read.delim(file.path(D,"genus_16s.tsv"),check.names=FALSE,stringsAsFactors=FALSE)
g <- trimws(sub(" sp\\.?$", "", s1$`Genus (16S)`))
g <- g[!is.na(g) & grepl("^[A-Z][a-z]+$", g)]                # drops "No 16S" and "No 16S sequence"
n_all <- length(g); n_strep <- sum(g == "Streptomyces")
d <- as.data.frame(table(genus = g[g != "Streptomyces"]), stringsAsFactors = FALSE) %>% arrange(desc(Freq), genus)
stopifnot(n_all == n_strep + sum(d$Freq))   # the counts in the Results text
d$genus <- factor(d$genus, levels = d$genus)
pal <- setNames(ifelse(d$genus %in% names(hp), hp[as.character(d$genus)], "#8C96A5"), d$genus)
base <- function(p) p + scale_fill_manual(values = pal, guide = "none") +
  scale_y_continuous(limits = c(0, 25), breaks = seq(0, 25, 5), expand = expansion(mult = c(0, 0.02))) +
  labs(x = NULL, y = "Isolates (16S rRNA gene)") + theme_minimal(base_size = 7, base_family = FONT) +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1, size = 7, colour = INK, face = "italic"), axis.text.y = element_text(size = 7, colour = INK),
        axis.title.y = element_text(size = 7, colour = SUB), panel.grid.major.x = element_blank(), panel.grid.minor = element_blank(),
        plot.background = element_rect(fill = "white", colour = NA), plot.margin = margin(4, 4, 2, 16))
lab <- setNames(paste0("<i>", levels(d$genus), "</i>"), levels(d$genus))
pA <- base(ggplot(d, aes(genus, Freq, fill = genus)) + geom_col(width = 0.72) +
  geom_text(aes(label = Freq), vjust = -0.4, size = 2.3, colour = SUB, family = FONT) + 
  annotate("richtext", x = nrow(d), y = 24.5, hjust = 1, vjust = 1, size = 2.5, family = FONT, colour = INK, fill = NA, label.colour = NA,
           label = paste0("<i>Streptomyces</i>: ", n_strep, " isolates (not shown)")))
d2 <- rbind(data.frame(genus = "Streptomyces", Freq = n_strep), d %>% mutate(genus = as.character(genus)))
d2$genus <- factor(d2$genus, levels = d2$genus); d2$h <- pmin(d2$Freq, 25)
pal2 <- c(Streptomyces = unname(hp["Streptomyces"]), pal)
lab2 <- setNames(paste0("<i>", levels(d2$genus), "</i>"), levels(d2$genus))
pB <- ggplot(d2, aes(genus, h, fill = genus)) + geom_col(width = 0.72) +
  geom_text(data = subset(d2, Freq <= 25), aes(label = Freq), vjust = -0.4, size = 2.3, colour = SUB, family = FONT) +
  annotate("segment", x = 0.58, xend = 1.42, y = 20.2, yend = 21.2, colour = "white", linewidth = 1.6) +
  annotate("segment", x = 0.58, xend = 1.42, y = 21.4, yend = 22.4, colour = "white", linewidth = 1.6) +
  annotate("text", x = 1.48, y = 23.8, label = as.character(n_strep), hjust = 0, size = 2.3, colour = SUB, family = FONT) +
  scale_fill_manual(values = pal2, guide = "none") +
  scale_y_continuous(limits = c(0, 25), breaks = seq(0, 25, 5), expand = expansion(mult = c(0, 0.02))) +
  labs(x = NULL, y = "Isolates (16S rRNA gene)") + theme_minimal(base_size = 7, base_family = FONT) +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, vjust = 1, size = 7, colour = INK, face = "italic"), axis.text.y = element_text(size = 7, colour = INK),
        axis.title.y = element_text(size = 7, colour = SUB), panel.grid.major.x = element_blank(), panel.grid.minor = element_blank(),
        plot.background = element_rect(fill = "white", colour = NA), plot.margin = margin(4, 4, 2, 16))
for (x in list(list("1C_candidate_A_Streptomyces_in_note_v2.png", pA), list("1C_candidate_B_Streptomyces_broken_bar_v2.png", pB))) {
  stopifnot(!file.exists(file.path(O,x[[1]]))); mt_save(x[[2]],file.path(O,tools::file_path_sans_ext(x[[1]])),3.4,3.05,list(min_text_pt=8,print_width=3.4,dpi=600))
}

