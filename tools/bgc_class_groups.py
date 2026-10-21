#!/usr/bin/env python3
"""Portable paper figure renderer, preserving the original printed ggplot layout.

Input genome TSV: strain, genus, block. Data schemas are documented in --help.
All outputs are new; counts represent supplied data only. No biological inference.
"""

try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import argparse, csv, hashlib, json, math, shutil, subprocess, sys
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
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--genomes", required=True, type=Path, help="TSV: unique strain, genus, block; input block order is authoritative")
    parser.add_argument("--data",required=True,type=Path,help=SCHEMA)
    parser.add_argument("--totals",type=Path,help="B02 only: strain, genus, regions, contig_edge, pct_edge")
    parser.add_argument("--out",required=True,type=Path,help="new output directory")
    parser.add_argument("--layout",choices=LAYOUTS,default=LAYOUTS[0])
    parser.add_argument("--palette-set",choices=["moss","attine"])
    parser.add_argument("--anchor-group",default="Bryophyte",help="B01 moss layout selects classes from this group")
    parser.add_argument("--comparators",default="",help="B02 moss: comma-separated block labels placed last")
    parser.add_argument("--dpi",type=int,default=600)
    _mt_args(parser)
    parser.add_argument("--overflow",choices=["collapse","split","top"],default="collapse",help="when the rows need more than 8.5 in of panel: collapse classes below --collapse-below into one row, split into two side-by-side panels, or keep the --top-n classes")
    parser.add_argument("--collapse-below",type=int,default=5,help="regions; classes below this fold into one Other classes row")
    parser.add_argument("--top-n",type=int,default=20)
    args=parser.parse_args(argv)
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
    inputs=[args.genomes,args.data,palette_path,ROOT/"tools/sapote_pub_layout.R",ROOT/"tools/sapote_min_text.R",ROOT/"tools/_min_text_check.py"]
    prepared, numbers, totals=prepare(args,genomes,roster,rows)
    if args.totals: inputs.append(args.totals)
    if args.out.exists(): raise FileExistsError(args.out)
    if not shutil.which("Rscript"): raise RuntimeError("Rscript is required")
    args.out.mkdir(parents=True)
    write(args.out/"plot_data.tsv",prepared)
    if totals: write(args.out/"plot_totals.tsv",totals)
    write(args.out/(TOOL+"_numbers.tsv"),numbers)
    config={"layout":args.layout,"data":str((args.out/"plot_data.tsv").resolve()),
            "totals":str((args.out/"plot_totals.tsv").resolve()),"out":str((args.out/TOOL).resolve()),
            "bundle_layout":str((ROOT/"tools/sapote_pub_layout.R").resolve()),"dpi":args.dpi,"min_text_pt":args.min_text_pt,"print_width":args.print_width,"min_text_helper":str((ROOT/"tools/sapote_min_text.R").resolve()),"overflow":args.overflow,"collapse_below":args.collapse_below,"top_n":args.top_n,
            "anchor":args.anchor_group,"groups":list(dict.fromkeys(r["block"] for r in genomes)),
            "comparators":args.comparators.split(",") if args.comparators else [],
            "group_counts":{g:sum(r["block"]==g for r in genomes) for g in dict.fromkeys(r["block"] for r in genomes)}}
    (args.out/"render_config.json").write_text(json.dumps(config,indent=2))
    (args.out/"render.R").write_text(R_CODE)
    result=subprocess.run(["Rscript",str(args.out/"render.R"),str(args.out/"render_config.json")],capture_output=True,text=True)
    (args.out/"RENDER.log").write_text(result.stdout+result.stderr)
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    _mt_enforce(args.out/(TOOL+".pdf"),args.min_text_pt)
    for ext in [".png",".pdf"]: stamp_file(args.out/(TOOL+ext),TOOL)
    receipt={"tool":TOOL,"layout":args.layout,"palette_set":args.palette_set,"fallback_genera":sorted(unknown),"genomes":len(genomes),
             "inputs":[{"path":str(p.resolve()),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in inputs]}
    (args.out/"RUN_INFO.json").write_text(json.dumps(receipt,indent=2)+"\n")
    return 0

TOOL="bgc_class_groups"
SCHEMA="class-summary TSV: display, family, regions, genomes; moss additionally group"
COLUMNS=["display","family","regions","genomes"]
NUMERIC=["regions","genomes"]
LAYOUTS=["bee","moss","moss-comparators"]

def prepare(args,genomes,roster,rows):
    keys=[(r.get("group",""),r["display"]) for r in rows]
    if len(keys)!=len(set(keys)): raise ValueError("duplicate group/class summary")
    if args.layout == "bee": selected=[r.copy() | {"group":""} for r in rows if r["family"]!="Saccharide" and int(r["regions"])>=3]
    else:
        if any("group" not in r for r in rows): raise ValueError("moss B01 requires group")
        anchor=sorted([r for r in rows if r["group"]==args.anchor_group and r["family"]!="Saccharide" and int(r["regions"])>=3],key=lambda r:int(r["regions"]))
        order={r["display"]:i for i,r in enumerate(anchor)}
        groups=list(dict.fromkeys(r["block"] for r in genomes))
        selected=[r.copy() for r in rows if r["display"] in order and (args.layout=="moss-comparators" or r["group"]==args.anchor_group)]
        selected.sort(key=lambda r:(groups.index(r["group"]),order[r["display"]]))
        for r in selected:
            n=sum(g["block"]==r["group"] for g in genomes)
            if int(r["genomes"])>n: raise ValueError("class genome count exceeds group denominator")
            label=next((g.get("block_label") for g in genomes if g["block"]==r["group"] and g.get("block_label")),None)
            r["group"]=label or r["group"]+f" ({n} genomes)"
    if args.layout=="bee": selected.sort(key=lambda r:int(r["regions"]))
    if not selected: raise ValueError("no selected classes")
    if any(r["family"] not in {"PKS","NRPS","RiPP","Terpene","Other classes"} for r in selected): raise ValueError("unknown family")
    if args.layout=="bee" and any(int(r["genomes"])>len(genomes) for r in selected): raise ValueError("class genome count exceeds roster")
    return selected,selected,None

R_CODE='suppressPackageStartupMessages({library(dplyr);library(ggplot2);library(ggtext);library(jsonlite)})\ncfg <- fromJSON(commandArgs(TRUE)[1]); source(cfg$bundle_layout); source(cfg$min_text_helper)\nhas_chicklet <- requireNamespace("ggchicklet", quietly = TRUE)\nFAMCOL <- c(PKS = "#C44E52", NRPS = "#3C6E9F", RiPP = "#5E9A4E", Terpene = "#E0A030", `Other classes` = "#8C7AA9")\ns <- read.delim(cfg$data, stringsAsFactors=FALSE)\nW <- if(cfg$layout == "moss-comparators" || identical(cfg$overflow, "split")) 7 else 3.4\n# M5_452 min-text rules: one row per class at >= 1.5 x text height; too tall -> the card\'s overflow option (receipt + caption table)\nrows_of <- function(d, split = FALSE) { n <- length(unique(d$display)); if (split) ceiling(n / 2) else n }\ncfg$overflow_used <- "none"; overflow_rows <- NULL\nif (rows_of(s) * mt_pitch_in(cfg) > mt_max_panel_in(cfg)) {\n  pol <- cfg$overflow\n  if (cfg$layout == "moss-comparators" && pol != "split") stop("MIN_TEXT_TOO_TALL: the comparator layout supports --overflow split only", call. = FALSE)\n  if (pol == "collapse") {\n    small <- s %>% group_by(display) %>% summarise(r = max(regions), .groups = "drop") %>% filter(r < cfg$collapse_below) %>% pull(display)\n    overflow_rows <- s %>% filter(display %in% small)\n    other <- overflow_rows %>% group_by(group) %>% summarise(regions = sum(regions), .groups = "drop") %>%\n      mutate(display = sprintf("Other classes (%d classes, %d regions)", length(small), regions), family = "Other classes", genomes = NA)\n    s <- bind_rows(other, s %>% filter(!display %in% small))\n  } else if (pol == "top") {\n    keep <- s %>% group_by(display) %>% summarise(r = max(regions), .groups = "drop") %>% arrange(desc(r)) %>% head(cfg$top_n) %>% pull(display)\n    overflow_rows <- s %>% filter(!display %in% keep); s <- s %>% filter(display %in% keep)\n  }\n  cfg$overflow_used <- pol\n}\nif (!is.null(overflow_rows)) write.table(overflow_rows, paste0(cfg$out, "_overflow_classes.tsv"), sep = "\\t", row.names = FALSE, quote = FALSE)\ns$group <- factor(s$group, levels=unique(s$group))\ns$display <- factor(s$display, levels = unique(s$display))\ns$lab <- ifelse(is.na(s$genomes), as.character(s$regions), paste0(s$regions, " (", s$genomes, ")"))\nsplit <- identical(cfg$overflow_used, "split")\nif (split) { lv <- levels(s$display); s$half <- factor(ifelse(match(s$display, lv) > length(lv) / 2, "a", "b"), levels = c("a", "b")) }\nfams <- intersect(names(FAMCOL), unique(s$family))\np <- ggplot(s, aes(x = display, y = regions, fill = family)) +\n  (if (has_chicklet) ggchicklet::geom_chicklet(width = 0.6, radius = grid::unit(1, "pt"), colour = NA) else geom_col(width = 0.6, colour = NA)) +\n  geom_text(aes(label = lab), hjust = -0.08, size = 6 / .pt, colour = PUB_SUB, family = PUB_FONT) +\n  coord_flip(clip = "off") + scale_fill_manual(values = FAMCOL[fams], breaks = fams, name = NULL, guide = "none") +   # owner, 12 Oct: no colour legend\n  labs(x = NULL, y = "Regions carrying the class (genomes)") +\n  theme_pub(7) + theme(panel.grid.major.y = element_blank(),\n                       legend.position = "inside", legend.position.inside = c(0.98, 0.04), legend.justification = c(1, 0),\n                       legend.key.size = unit(7, "pt"), legend.key.spacing.y = unit(1, "pt"),\n                       axis.text.y = ggtext::element_markdown(size = 6), axis.text.y.left = ggtext::element_markdown(size = 6, margin = margin(r = 1)),\n                       axis.text.x.bottom = ggtext::element_markdown(size = 7), axis.title.x = element_text(size = 7),\n                       legend.text = ggtext::element_markdown(size = 7), plot.margin = margin(3, 4, 3, 2))\nif (cfg$layout == "moss-comparators") p <- p + facet_grid(. ~ group) + theme(strip.text=element_text(size=7,face="bold",colour=PUB_INK),legend.position.inside=c(0.995,0.04))\nif (split) p <- p + facet_wrap(~ half, nrow = 1, scales = "free_y") + theme(strip.text = element_blank())\nvmax <- max(s$regions)\nlim <- mt_value_limit(p, s$lab, vmax, cfg, if (split) W / 2 else W)   # value labels end inside the panel at the floor size\np <- p + scale_y_continuous(limits = c(0, lim), breaks = scales::breaks_pretty()(c(0, vmax)), expand = expansion(0))\ncfg$rows <- rows_of(s, split)\nmt_save(p, cfg$out, W, 4.2, cfg)\n'

if __name__ == "__main__": raise SystemExit(main())
