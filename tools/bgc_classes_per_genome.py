#!/usr/bin/env python3
"""Portable paper figure renderer, preserving the original printed ggplot layout.

Input genome TSV: strain, genus, block, and optionally row_note. Data schemas are documented in --help.
Moss layout: each row is labelled with its genus (and its row_note in brackets, when given); --row-labels per-block
restores one label per block.
All outputs are new; counts represent supplied data only. No biological inference.
"""

try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import argparse, csv, hashlib, html, json, math, shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.figure_stamp import stamp_file
from tools._min_text_check import add_args as _mt_args, enforce as _mt_enforce
ROOT = Path(__file__).resolve().parents[1]

def table(path, columns):
    with Path(path).open(newline="", encoding="utf-8") as fh:
        reader=csv.DictReader(fh, delimiter="\t")
        if not set(columns).issubset(reader.fieldnames or []):
            raise ValueError(f"{path}: required columns {columns}")
        rows=list(reader)
    if not rows: raise ValueError(f"{path}: empty table")
    return rows

def write(path, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        writer=_SafeDictWriter(fh,fieldnames=list(rows[0]),delimiter="\t")
        writer.writeheader(); writer.writerows(rows)

def numeric(rows, columns):
    for row in rows:
        for col in columns:
            value=float(row[col])
            if not math.isfinite(value) or value < 0: raise ValueError(f"invalid {col}: {row[col]}")
            if col != "pct_edge" and value != int(value): raise ValueError(f"noninteger {col}")

def main(argv=None):
    pre=argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    pre.add_argument("--layout-config", type=Path, default=ROOT/"mamey/data/bgc_class_layouts.json")
    preliminary,_=pre.parse_known_args(argv)
    settings=json.loads(preliminary.layout_config.read_text())
    layouts=settings["layouts"]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout-config", type=Path, default=preliminary.layout_config)
    parser.add_argument("--genomes", required=True, type=Path, help="TSV: unique strain, genus, block, optional row_note; input block order is authoritative")
    parser.add_argument("--data",required=True,type=Path,help=SCHEMA)
    parser.add_argument("--totals",type=Path,help="B02 only: strain, genus, regions, contig_edge, pct_edge")
    parser.add_argument("--out",required=True,type=Path,help="new output directory")
    parser.add_argument("--layout",choices=list(layouts),default=settings["default"])
    parser.add_argument("--palette-set",choices=sorted(json.loads((ROOT/"mamey/data/genus_palette.json").read_text())["sets"]))
    parser.add_argument("--anchor-group",default=settings.get("anchor_group_default",""),help="optional anchor block from the input table")
    parser.add_argument("--comparators",default="",help="comma-separated block labels placed last in grouped layouts")
    parser.add_argument("--dpi",type=int,default=600)
    parser.add_argument("--italic-row-notes",nargs="*",default=[],help="grouped layout: row_note values that are genus names, set in italics (explicit list; default none)")
    parser.add_argument("--row-labels",choices=["each-row","per-block"],default="each-row",help="grouped layout: label every row with its genus and row_note (default), or one label per block")
    _mt_args(parser)
    parser.add_argument("--orientation",choices=["strains-as-rows","classes-as-rows"],default="strains-as-rows",help="classes-as-rows draws strains as columns so two-digit counts fit their tiles at the text floor")
    args=parser.parse_args(argv)
    layout_spec=layouts[args.layout]
    if layout_spec.get("mode") not in ("grouped","standard"):
        parser.error("layout mode must be grouped or standard")
    needed=["width","edge_width"] + (["height_base","row_height"] if layout_spec["mode"]=="grouped" else ["height"])
    if any(not isinstance(layout_spec.get(k),(int,float)) or not math.isfinite(layout_spec[k]) or layout_spec[k]<=0 for k in needed):
        parser.error("layout dimensions must be positive finite numbers")
    if args.dpi < 72: raise ValueError("dpi must be >=72")
    genomes=table(args.genomes,["strain","genus","block"])
    roster={r["strain"]:r for r in genomes}
    if len(roster)!=len(genomes): raise ValueError("duplicate genome strain")
    palette_path=ROOT/"mamey/data/genus_palette.json"
    palette=json.loads(palette_path.read_text())
    colors=palette["default"].copy()
    colors.update(palette.get("sets",{}).get(args.palette_set,{}))
    unknown={r["genus"] for r in genomes}-set(colors)
    # Palette contract (mamey/data/genus_palette.json "about"): unknown genera use the fallback colour. These class renderers draw no
    # genus colour, so unknown genera are recorded in the receipt, not refused (M5_452_class_renderers_palette_fallback, 13 Oct 2026).
    rows=table(args.data,COLUMNS)
    numeric(rows,NUMERIC)
    inputs=[args.layout_config,args.genomes,args.data,palette_path,ROOT/"tools/sapote_pub_layout.R",ROOT/"tools/sapote_min_text.R",ROOT/"tools/_min_text_check.py"]
    prepared, numbers, totals=prepare(args,genomes,roster,rows)
    if args.totals: inputs.append(args.totals)
    if args.out.exists(): raise FileExistsError(args.out)
    if not shutil.which("Rscript"): raise RuntimeError("Rscript is required")
    args.out.mkdir(parents=True)
    write(args.out/"plot_data.tsv",prepared)
    if totals: write(args.out/"plot_totals.tsv",totals)
    write(args.out/(TOOL+"_numbers.tsv"),numbers)
    config={"layout":args.layout,"layout_spec":layout_spec,"data":str((args.out/"plot_data.tsv").resolve()),
            "totals":str((args.out/"plot_totals.tsv").resolve()),"out":str((args.out/TOOL).resolve()),
            "bundle_layout":str((ROOT/"tools/sapote_pub_layout.R").resolve()),"dpi":args.dpi,"min_text_pt":args.min_text_pt,"print_width":args.print_width,"min_text_helper":str((ROOT/"tools/sapote_min_text.R").resolve()),"orientation":args.orientation,
            "anchor":args.anchor_group,"groups":list(dict.fromkeys(r["block"] for r in genomes)),
            "comparators":args.comparators.split(",") if args.comparators else [],
            "row_labels":row_labels(genomes,set(args.italic_row_notes)) if args.row_labels=="each-row" else None,"italic_row_notes":sorted(set(args.italic_row_notes)),
            "group_counts":{g:sum(r["block"]==g for r in genomes) for g in dict.fromkeys(r["block"] for r in genomes)}}
    (args.out/"render_config.json").write_text(json.dumps(config,indent=2))
    (args.out/"render.R").write_text(R_CODE)
    result=subprocess.run(["Rscript",str(args.out/"render.R"),str(args.out/"render_config.json")],capture_output=True,text=True)
    (args.out/"RENDER.log").write_text(result.stdout+result.stderr)
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    _mt_enforce(args.out/(TOOL+".pdf"),args.min_text_pt)
    for ext in [".png",".pdf"]: stamp_file(args.out/(TOOL+ext),TOOL)
    receipt={"tool":TOOL,"layout":args.layout,"palette_set":args.palette_set,"fallback_genera":sorted(unknown),"genomes":len(genomes),"row_labels":args.row_labels,
             "inputs":[{"path":str(p.resolve()),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in inputs]}
    (args.out/"RUN_INFO.json").write_text(json.dumps(receipt,indent=2)+"\n")
    return 0

TOOL="bgc_classes_per_genome"
SCHEMA="complete matrix TSV: strain, genus, display, family, count; explicit zeros required"
COLUMNS=["strain","genus","display","family","count"]
NUMERIC=["count"]
LAYOUTS=list(json.loads((ROOT/"mamey/data/bgc_class_layouts.json").read_text())["layouts"])

def row_labels(genomes,italic_notes=()):
    """Right-hand label for every row: the genus in italics, then the genome table's row_note in brackets. A row_note
    named in italic_notes (an explicit list of genus names, e.g. host ant genera) is set in italics too."""
    out={}
    for r in genomes:
        note=(r.get("row_note") or "").strip()
        shown=f"<i>{html.escape(note)}</i>" if note in italic_notes else html.escape(note)
        g=html.escape(r['genus']); out[r["strain"]]=(g if r['genus'].endswith(("aceae", "aceae bacterium")) else f"<i>{g}</i>")+(f" ({shown})" if note else "")   # family names stay roman
    return out

def prepare(args,genomes,roster,rows):
    if not args.totals: raise ValueError("B02 requires --totals")
    totals=table(args.totals,["strain","genus","regions","contig_edge","pct_edge"])
    numeric(totals,["regions","contig_edge","pct_edge"])
    if len({r["strain"] for r in totals})!=len(totals) or {r["strain"] for r in totals}!=set(roster): raise ValueError("totals roster mismatch")
    if {r["strain"] for r in rows}!=set(roster): raise ValueError("class roster mismatch")
    keys=[(r["strain"],r["display"]) for r in rows]
    if len(keys)!=len(set(keys)): raise ValueError("duplicate class cell")
    classes={r["display"] for r in rows}
    if len(rows)!=len(classes)*len(roster): raise ValueError("class matrix must explicitly include zero cells")
    for r in rows+totals:
        if r["genus"]!=roster[r["strain"]]["genus"]: raise ValueError("genus mismatch")
        r["group"]=roster[r["strain"]]["block"]
    for r in totals:
        if int(r["contig_edge"])>int(r["regions"]) or float(r["pct_edge"])>100: raise ValueError("invalid edge totals")
        expected=100*int(r["contig_edge"])/int(r["regions"]) if int(r["regions"]) else 0
        if abs(float(r["pct_edge"])-expected)>0.51: raise ValueError("pct_edge inconsistent with counts")
    fams={"PKS","NRPS","RiPP","Terpene","Other classes"}
    if any(r["family"] not in fams for r in rows): raise ValueError("unknown class family")
    for cl in classes:
        if len({r["family"] for r in rows if r["display"]==cl})!=1: raise ValueError("class family differs across genomes")
    numbers=[dict(strain=r["strain"],genus=r["genus"],kind="class_count",display=r["display"],value=r["count"]) for r in rows]
    numbers += [dict(strain=r["strain"],genus=r["genus"],kind=k,display="",value=r[k]) for r in totals for k in ["regions","contig_edge","pct_edge"]]
    return rows,numbers,totals

R_CODE='suppressPackageStartupMessages({library(dplyr);library(ggplot2);library(ggtext);library(jsonlite)})\ncfg <- fromJSON(commandArgs(TRUE)[1]); source(cfg$bundle_layout)\nlibrary(patchwork)\nm <- read.delim(cfg$data,stringsAsFactors=FALSE)\nif(cfg$layout_spec$mode == "grouped") {\ncomp <- cfg$comparators\nm$family[m$family == "Terpene"] <- "Other classes"\nt <- read.delim(cfg$totals,stringsAsFactors=FALSE)\ncore <- m %>% filter(!group %in% comp) %>% distinct(strain, group) %>% count(group) %>% arrange(desc(n), group) %>% pull(group)\ngord <- c(core, comp)\nstrip_lab <- function(g) sub("^([A-Za-z]+)( \\\\((.*)\\\\))?$", "*\\\\1*", g) %>%\n  paste0(ifelse(grepl("\\\\(", g), paste0(" (", sub(".*\\\\((.*)\\\\)", "\\\\1", g), ")"), ""))\nFAMS <- c("PKS", "NRPS", "RiPP", "Other classes")\ncls_ord <- m %>% group_by(display, family) %>% summarise(tot = sum(count), .groups = "drop") %>%\n  mutate(family = factor(family, levels = FAMS)) %>% arrange(family, desc(tot)) %>% pull(display)\nglev <- strip_lab(gord)\nm <- m %>% mutate(group = factor(strip_lab(group), levels = glev), family = factor(family, levels = FAMS),\n                  display = factor(display, levels = cls_ord))\nsord <- m %>% distinct(strain, group) %>% arrange(group, as.integer(sub("AS-", "", strain))) %>% pull(strain)\nm$strain <- factor(m$strain, levels = rev(sord))\nm$bin <- factor(ifelse(m$count >= 6, "6 or more", as.character(m$count)), levels = c(as.character(0:5), "6 or more"))\nBINCOL <- setNames(colorRampPalette(c("#F4F6F9", "#3C6E9F"))(7), levels(m$bin))\nCELL <- 2.1\np1 <- ggplot(m, aes(x = display, y = strain, fill = bin)) +\n  geom_tile(colour = "white", linewidth = 0.25) +\n  geom_text(aes(label = count, colour = count == 0), show.legend = FALSE, size = CELL, family = PUB_FONT) +\n  scale_colour_manual(values = c(`TRUE` = "#AEB6C1", `FALSE` = PUB_INK), guide = "none") +\n  scale_fill_manual(values = BINCOL, drop = FALSE, name = "Regions", guide = guide_legend(nrow = 1)) +\n  facet_grid(group ~ family, scales = "free", space = "free", switch = "y") +\n  labs(x = NULL, y = NULL) + theme_pub(7) +\n  theme(axis.text.x.bottom = element_markdown(angle = 90, hjust = 1, vjust = 0.5, size = 7, colour = PUB_INK),\n        axis.text.y.left = element_markdown(size = 7, colour = PUB_INK), panel.grid = element_blank(), panel.spacing = unit(1.5, "pt"),\n        strip.text.y.left = element_blank(), strip.text.x = element_text(face = "bold", size = 7.5), strip.placement = "outside",\n        legend.position = "bottom", legend.key.width = unit(0.7, "cm"), legend.key.height = unit(0.25, "cm"),\n        legend.text = element_markdown(size = 7), legend.title = element_text(size = 7, face = "bold"),\n        legend.justification = "left", plot.margin = margin(2, 1, 2, 2))\nt$strain <- factor(t$strain, levels = rev(sord)); t$group <- factor(strip_lab(t$group), levels = glev)\np2 <- ggplot(t, aes(x = pct_edge, y = strain)) + geom_col(fill = "#B8BFC9", width = 0.7) +\n  geom_text(aes(label = paste0(pct_edge, "%")), hjust = -0.12, size = CELL, colour = PUB_INK, family = PUB_FONT) +\n  facet_grid(group ~ "On a\\ncontig edge", scales = "free_y", space = "free_y") +\n  scale_x_continuous(limits = c(0, 150), breaks = c(0, 100), labels = function(x) paste0(x, "%")) +\n  labs(x = NULL, y = NULL) + theme_pub(7) +\n  theme(axis.text.y.left = element_blank(), axis.text.x = element_text(size = 7, colour = PUB_INK), panel.grid = element_blank(),\n        panel.spacing = unit(1.5, "pt"),\n        strip.text.y = element_markdown(face = "bold", size = 7, angle = 0, hjust = 0, vjust = 0.5, colour = PUB_INK,\n                                        margin = margin(l = 3, r = 1)),\n        strip.text.x = element_text(face = "bold", size = 7.5), plot.margin = margin(2, 2, 2, 1))\nif (!is.null(cfg$row_labels)) {   # every row carries its genus label (and row_note), not one label per block\n  p2 <- p2 + scale_y_discrete(position = "right", labels = unlist(cfg$row_labels)) +\n    theme(strip.text.y = element_blank(), axis.text.y.right = element_markdown(face = "bold", size = 7, colour = PUB_INK, hjust = 0, margin = margin(l = 3)))\n}\nbody <- (p1 | p2) + plot_layout(widths = c(10, cfg$layout_spec$edge_width))\nn <- length(sord); H <- cfg$layout_spec$height_base + cfg$layout_spec$row_height * n\nsource(cfg$min_text_helper); mt_save(body,cfg$out,cfg$layout_spec$width,H,cfg)\n} else {\nm$family[m$family == "Terpene"] <- "Other classes"   # one-column group: its strip label would not fit\nt <- read.delim(cfg$totals, stringsAsFactors = FALSE)\ngord <- m %>% distinct(strain, genus) %>% count(genus) %>% arrange(desc(n), genus) %>% pull(genus)\nFAMS <- c("PKS", "NRPS", "RiPP", "Other classes")\ncls_ord <- m %>% group_by(display, family) %>% summarise(tot = sum(count), .groups = "drop") %>%\n  mutate(family = factor(family, levels = FAMS)) %>% arrange(family, desc(tot)) %>% pull(display)\nm <- m %>% mutate(genus = factor(genus, levels = gord), family = factor(family, levels = FAMS),\n                  display = factor(display, levels = cls_ord),\n                  lab = paste0("<i>", genus, "</i> sp. ", strain))\nrowlab <- m %>% distinct(strain, lab) %>% { setNames(.$lab, .$strain) }\nsord <- m %>% distinct(strain, genus) %>% arrange(genus, strain) %>% pull(strain)\nm$strain <- factor(m$strain, levels = rev(sord))\nm$bin <- factor(ifelse(m$count >= 6, "6 or more", as.character(m$count)), levels = c(as.character(0:5), "6 or more"))\nBINCOL <- setNames(colorRampPalette(c("#F4F6F9", "#3C6E9F"))(7), levels(m$bin))\nsource(cfg$min_text_helper)\n# Tile counts must fit inside their tiles at the text floor (M5_452 min-text card): measured Arial width vs tile width.\ntile_fit <- function(body, W, share, ncol, nfacet, digits) {\n  minpt <- if (is.null(cfg$min_text_pt)) 8 else as.numeric(cfg$min_text_pt)\n  Wp <- if (!is.null(cfg$print_width)) as.numeric(cfg$print_width) else if (W <= 3.5) 3.5 else 7.2\n  pdf(NULL); on.exit(dev.off(), add = TRUE)\n  fw <- .mt_fixed(.mt_grob(mt_floor(body, minpt))$widths)\n  tile <- ((Wp - fw) * share - (nfacet - 1) * 1.5 / 72) / ncol\n  need <- (systemfonts::string_width(strrep("8", digits), family = PUB_FONT, size = minpt) / 72 + 1.5 / 72)\n  cat(sprintf("tile_fit: tile %.3f in, %d-digit count at %.1f pt needs %.3f in\\n", tile, digits, minpt, need))\n  if (need > tile) stop(sprintf("MIN_TEXT_DOES_NOT_FIT: tiles are %.3f in wide at %.2f in; a %d-digit count at %.1f pt needs %.3f in. Use --orientation classes-as-rows.", tile, Wp, digits, minpt, need), call. = FALSE)\n}\n\nrender_rows <- function(W, OUT) {   # classes as rows, strains as columns (standard layout): tiles wide enough for two digits\n  mr <- m %>% mutate(display = factor(display, levels = rev(cls_ord)), strain = factor(as.character(strain), levels = sord))\n  p1 <- ggplot(mr, aes(x = strain, y = display, fill = bin)) + geom_tile(colour = "white", linewidth = 0.25) +\n    geom_text(aes(label = count, colour = count == 0), show.legend = FALSE, size = 2.1, family = PUB_FONT) +\n    scale_colour_manual(values = c(`TRUE` = "#AEB6C1", `FALSE` = PUB_INK), guide = "none") +\n    scale_fill_manual(values = BINCOL, drop = FALSE, name = "Regions", guide = guide_legend(nrow = 1)) +\n    facet_grid(family ~ genus, scales = "free", space = "free") + labs(x = NULL, y = NULL) + theme_pub(7) +\n    theme(axis.text.x.bottom = element_markdown(angle = 90, hjust = 1, vjust = 0.5, size = 7, colour = PUB_INK),\n          axis.text.y.left = element_markdown(size = 7, colour = PUB_INK), panel.grid = element_blank(), panel.spacing = unit(1.5, "pt"),\n          strip.text.x = element_text(face = "bold.italic", size = 7, angle = 90, hjust = 0, colour = PUB_INK),\n          strip.text.y = element_text(face = "bold", size = 7.5, angle = 270, colour = PUB_INK),\n          legend.position = "bottom", legend.key.width = unit(0.7, "cm"), legend.key.height = unit(0.25, "cm"),\n          legend.text = element_markdown(size = 7), legend.title = element_text(size = 7, face = "bold"), legend.justification = "left",\n          plot.margin = margin(2, 2, 2, 2))\n  tr <- t %>% mutate(strain = factor(as.character(strain), levels = sord), genus = factor(genus, levels = gord))\n  p0 <- ggplot(tr, aes(x = strain, y = pct_edge)) + geom_col(fill = "#B8BFC9", width = 0.7) +\n    geom_text(aes(label = paste0(pct_edge, "%")), angle = 90, hjust = -0.15, size = 2.1, colour = PUB_INK, family = PUB_FONT) +\n    facet_grid(. ~ genus, scales = "free_x", space = "free_x") +\n    scale_y_continuous(limits = c(0, 175), breaks = c(0, 100), labels = function(x) paste0(x, "%"), expand = expansion(0)) +\n    labs(x = NULL, y = "On a contig edge") + theme_pub(7) +\n    theme(axis.text.x = element_blank(), axis.text.x.bottom = element_blank(), axis.ticks.x = element_blank(), panel.grid = element_blank(), panel.spacing = unit(1.5, "pt"), strip.text = element_blank(),\n          axis.title.y = element_text(size = 7, angle = 0, vjust = 0.5, hjust = 1), plot.margin = margin(2, 2, 0, 2))\n  ncls <- nlevels(m$display); H <- 1.9 + mt_pitch_in(cfg) * ncls\n  body <- (p0 / p1) + plot_layout(heights = c(0.11 * ncls / 4, ncls * mt_pitch_in(cfg)))\n  tile_fit(body, W, 1, length(sord), length(gord), max(nchar(as.character(m$count))))\n  mt_save(body, sub(".png$", "", OUT), W, H, cfg); cat("wrote",OUT,"\n")\n}\n\nrender <- function(RL, EW, W, H, OUT) {\nCELL <- 2.1   # mm = 6 pt\np1 <- ggplot(m, aes(x = display, y = strain, fill = bin)) +\n  geom_tile(colour = "white", linewidth = 0.25) +\n  geom_text(aes(label = count, colour = count == 0), show.legend = FALSE, size = CELL, family = PUB_FONT) +\n  scale_colour_manual(values = c(`TRUE` = "#AEB6C1", `FALSE` = PUB_INK), guide = "none") +\n  scale_fill_manual(values = BINCOL, drop = FALSE, name = "Regions", guide = guide_legend(nrow = 1)) +\n  scale_y_discrete(labels = RL) +\n  facet_grid(genus ~ family, scales = "free", space = "free", switch = "y") +\n  labs(x = NULL, y = NULL) + theme_pub(7) +\n  theme(axis.text.x.bottom = element_markdown(angle = 90, hjust = 1, vjust = 0.5, size = 7, colour = PUB_INK),\n        axis.text.y.left = element_markdown(size = 7, colour = PUB_INK), panel.grid = element_blank(), panel.spacing = unit(1.5, "pt"),\n        strip.text.y.left = element_blank(), strip.text.x = element_text(face = "bold", size = 7.5), strip.placement = "outside",\n        legend.position = "bottom", legend.key.width = unit(0.7, "cm"), legend.key.height = unit(0.25, "cm"),\n        legend.text = element_markdown(size = 7), legend.title = element_text(size = 7, face = "bold"),\n        legend.justification = "left", plot.margin = margin(2, 1, 2, 2))\nt$strain <- factor(t$strain, levels = rev(sord)); t$genus <- factor(t$genus, levels = gord)\np2 <- ggplot(t, aes(x = pct_edge, y = strain)) + geom_col(fill = "#B8BFC9", width = 0.7) +\n  geom_text(aes(label = paste0(pct_edge, "%")), hjust = -0.12, size = CELL, colour = PUB_INK, family = PUB_FONT) +\n  facet_grid(genus ~ "On a\\ncontig edge", scales = "free_y", space = "free_y") +\n  scale_x_continuous(limits = c(0, 150), breaks = c(0, 100), labels = function(x) paste0(x, "%")) +\n  labs(x = NULL, y = NULL) + theme_pub(7) +\n  theme(axis.text.y.left = element_blank(), axis.text.x = element_text(size = 7, colour = PUB_INK), panel.grid = element_blank(),\n        panel.spacing = unit(1.5, "pt"),\n        strip.text.y = element_text(face = "bold.italic", size = 7, angle = 0, hjust = 0, vjust = 0.5, colour = PUB_INK, margin = margin(l = 3, r = 1)),\n        strip.text.x = element_text(face = "bold", size = 7.5), plot.margin = margin(2, 2, 2, 1))\nbody <- (p1 | p2) + plot_layout(widths = c(10, EW))\n  tile_fit(body, W, 10 / (10 + EW), nlevels(m$display), length(levels(m$family)), max(nchar(as.character(m$count))))\n  mt_save(body, sub(".png$", "", OUT), W, H, cfg); cat("wrote",OUT,"\\n")\n}\n\nif(cfg$layout_spec$labels == "strain" && identical(cfg$orientation, "classes-as-rows")) render_rows(7.2, paste0(cfg$out,".png")) else\nif(cfg$layout_spec$labels == "strain") render(setNames(names(rowlab),names(rowlab)),cfg$layout_spec$edge_width,cfg$layout_spec$width,cfg$layout_spec$height,paste0(cfg$out,".png"))\nelse render(rowlab,cfg$layout_spec$edge_width,cfg$layout_spec$width,cfg$layout_spec$height,paste0(cfg$out,".png"))\n}\n'

if __name__ == "__main__": raise SystemExit(main())
