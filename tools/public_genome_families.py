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
    parser.add_argument("--x-title",default=None,
                        help="B04: x-axis title, drawn in the ink colour; \\n breaks a line (default: the original wording)")
    parser.add_argument("--source-tags",choices=["grey","ink"],default="grey",
                        help="B04: colour of the '(source)' tag after each isolate name: grey (original) or ink")
    parser.add_argument("--count-labels",choices=["of-total","none"],default="of-total",
                        help="B04: print 'N of M' (not found in public genomes, of all families) beside each bar, or nothing")
    parser.add_argument("--part-labels",default=None,
                        help="B04: the two legend names, 'found|not found' (default: 'Found in public genomes|Not found in public genomes'); "
                             "for a reference-only genus, e.g. 'In 2 or more genomes of the genus|In this genome only' (M5_452_b04_reference_row_labels)")
    parser.add_argument("--overflow",choices=["pages"],default=None,
                        help="when the genome rows need more than 8.5 in of panel at --min-text-pt: draw full-width pages with the rows split "
                             "across them (<out>_page1, _page2, ...; labels unchanged). Without it a too-tall page is refused (MIN_TEXT_TOO_TALL). "
                             "m5_452_public_genome_families_overflow_pages")
    parser.add_argument("--row-order",choices=["sorted","input"],default="sorted",
                        help="sorted (default): rows by genus, block, strain; input: rows in --genomes order (e.g. genome-tree tip order)")
    _mt_args(parser)
    args=parser.parse_args(argv)
    parts=args.part_labels.split("|") if args.part_labels else ["Found in public genomes","Not found in public genomes"]
    if len(parts)!=2 or not all(x.strip() for x in parts) or parts[0]==parts[1]: raise ValueError("--part-labels needs two different non-empty names separated by |")
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
    if args.row_order=="input":   # m5_452_public_genome_families_overflow_pages: keep the --genomes row order
        rank={r["strain"]:i for i,r in enumerate(genomes)}; prepared=sorted(prepared,key=lambda r:rank[r["strain"]])
    if args.totals: inputs.append(args.totals)
    if args.out.exists(): raise FileExistsError(args.out)
    if not shutil.which("Rscript"): raise RuntimeError("Rscript is required")
    args.out.mkdir(parents=True)
    write(args.out/"plot_data.tsv",prepared)
    if totals: write(args.out/"plot_totals.tsv",totals)
    write(args.out/(TOOL+"_numbers.tsv"),numbers)
    config={"layout":args.layout,"data":str((args.out/"plot_data.tsv").resolve()),
            "totals":str((args.out/"plot_totals.tsv").resolve()),"out":str((args.out/TOOL).resolve()),
            "bundle_layout":str((ROOT/"tools/sapote_pub_layout.R").resolve()),"dpi":args.dpi,"min_text_pt":args.min_text_pt,"print_width":args.print_width,"min_text_helper":str((ROOT/"tools/sapote_min_text.R").resolve()),
            "anchor":args.anchor_group,"x_title":args.x_title.replace("\\n","\n") if args.x_title else None,"count_labels":args.count_labels,"part_labels":parts,"source_tags":args.source_tags,"overflow":args.overflow,"row_order":args.row_order,"groups":list(dict.fromkeys(r["block"] for r in genomes)),
            "comparators":args.comparators.split(",") if args.comparators else [],
            "group_counts":{g:sum(r["block"]==g for r in genomes) for g in dict.fromkeys(r["block"] for r in genomes)}}
    (args.out/"render_config.json").write_text(json.dumps(config,indent=2))
    (args.out/"render.R").write_text(R_CODE)
    result=subprocess.run(["Rscript",str(args.out/"render.R"),str(args.out/"render_config.json")],capture_output=True,text=True)
    (args.out/"RENDER.log").write_text(result.stdout+result.stderr)
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    pages_file=args.out/(TOOL+"_pages.json")
    stems=[TOOL+f"_page{i}" for i in range(1,json.loads(pages_file.read_text())["pages"]+1)] if pages_file.exists() else [TOOL]
    for stem in stems:
        _mt_enforce(args.out/(stem+".pdf"),args.min_text_pt)
        for ext in [".png",".pdf"]: stamp_file(args.out/(stem+ext),TOOL)
    receipt={"tool":TOOL,"layout":args.layout,"palette_set":args.palette_set,"fallback_genera":sorted(unknown),"genomes":len(genomes),"row_order":args.row_order,"overflow":args.overflow,"pages":len(stems),
             "inputs":[{"path":str(p.resolve()),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in inputs]}
    (args.out/"RUN_INFO.json").write_text(json.dumps(receipt,indent=2)+"\n")
    return 0

TOOL="public_genome_families"
SCHEMA="TSV: strain, genus, families, in_public, not_in_public"
COLUMNS=["strain","genus","families","in_public","not_in_public"]
NUMERIC=["families","in_public","not_in_public"]
LAYOUTS=["bee","moss"]

def prepare(args,genomes,roster,rows):
    if len({r["strain"] for r in rows})!=len(rows): raise ValueError("duplicate family strain")
    if {r["strain"] for r in rows}!=set(roster): raise ValueError("family table and roster differ")
    for r in rows:
        g=roster[r["strain"]]
        if r["genus"]!=g["genus"]: raise ValueError("genus mismatch")
        if int(r["in_public"])+int(r["not_in_public"])!=int(r["families"]): raise ValueError("family parts do not sum")
        r["host_group"]=g["block"]
        r["label"]=(g.get("label") or "").replace("\\n","<br>")   # M5_452_b04_reference_row_labels: optional verbatim row label
    return rows, rows, None

R_CODE='suppressPackageStartupMessages({library(dplyr);library(ggplot2);library(ggtext);library(jsonlite)})\ncfg <- fromJSON(commandArgs(TRUE)[1]); source(cfg$bundle_layout)\nINK <- "#17212E"; SUB <- "#54637A"; FONT <- "Arial"\nTAGC <- if (identical(cfg$source_tags, "ink")) INK else SUB\nHOST_ORDER <- c(cfg$groups, "")\nd <- read.delim(cfg$data,stringsAsFactors=FALSE)\nd$host_group[is.na(d$host_group)] <- ""\nif (!identical(cfg$row_order, "input")) d <- d %>% arrange(genus, match(host_group, HOST_ORDER), strain)   # input: --genomes order (m5_452_public_genome_families_overflow_pages)\nd$lab <- paste0("<i>", d$genus, "</i> sp. <b>", d$strain, "</b>",\n                ifelse(d$host_group != "", paste0(" <span style=\'color:", TAGC, "\'>(", d$host_group, ")</span>"), ""))\nif ("label" %in% names(d)) { ov <- !is.na(d$label) & d$label != ""; d$lab[ov] <- d$label[ov] }   # M5_452_b04_reference_row_labels\nd$key <- factor(d$strain, levels = rev(d$strain))\nlong <- bind_rows(d %>% transmute(key, genus, part = cfg$part_labels[1], n = in_public),\n                  d %>% transmute(key, genus, part = cfg$part_labels[2], n = not_in_public)) %>%\n  mutate(part = factor(part, levels = cfg$part_labels))\nbuild <- function(d, long) ggplot(long, aes(y = key, x = n)) +\n  geom_col(aes(fill = part), width = 0.6, position = position_stack(reverse = TRUE)) +\n  (if (identical(cfg$count_labels, "none")) NULL else geom_text(data = d, aes(y = key, x = families, label = paste0(not_in_public, " of ", families)), inherit.aes = FALSE,\n            hjust = -0.12, size = 6 / .pt, colour = INK, family = FONT)) +\n  scale_fill_manual(values = setNames(c("#C9D0D9", "#2E8B84"), cfg$part_labels), name = NULL) +\n  scale_y_discrete(labels = setNames(d$lab, d$strain)) +\n  scale_x_continuous(breaks = c(0, 10, 20, 30, 40), expand = expansion(mult = c(0, 0.5))) +   # original breaks; wider right margin for the counts (8 pt: 0.36 -> 0.5)\n  labs(x = if (is.null(cfg$x_title)) "Gene cluster families\\n(label: not found in\\npublic genomes, of all)" else cfg$x_title, y = NULL) +\n  theme_minimal(base_size = 7, base_family = FONT) +\n  theme(panel.grid.minor = element_blank(), panel.grid.major.y = element_blank(),\n        axis.title = element_text(size = 7, colour = if (is.null(cfg$x_title)) SUB else INK, lineheight = 1.05, hjust = 0.5), axis.text = element_text(colour = INK, size = 7),\n        axis.text.y.left = element_markdown(size = 6.5, colour = INK, margin = margin(r = 1)), legend.position = "bottom",\n        legend.text = element_text(size = 7), legend.key.size = unit(7, "pt"), legend.margin = margin(0, 0, 0, 0),\n        legend.box.spacing = unit(2, "pt"), legend.justification = "right", plot.margin = margin(2, 4, 2, 1),\n        plot.background = element_rect(fill = "white", colour = NA))\np <- build(d, long)\nH <- if(cfg$layout == "bee") 3.75 else 1.75\nsource(cfg$min_text_helper); W0 <- if (is.null(cfg$print_width)) 3.4 else as.numeric(cfg$print_width); vmax <- max(d$families)\nlim <- if (identical(cfg$count_labels, "none")) vmax * 1.04 else mt_value_limit(p, paste0(d$not_in_public, " of ", d$families), vmax, cfg, W0)   # measured label room\nxs <- scale_x_continuous(breaks = scales::breaks_pretty()(c(0, vmax)), limits = c(0, lim), expand = expansion(0))   # m5_452_public_genome_families_axis_breaks: as tools/bgc_class_groups.py (was fixed 0-40)\np <- p + xs + coord_cartesian(clip = "off")\n# m5_452_public_genome_families_overflow_pages: rows beyond the panel go to further full-width pages; a row takes one text line per label line\nlines <- max(lengths(regmatches(d$lab, gregexpr("<br>", d$lab, fixed = TRUE)))) + 1\ncfg$overflow_used <- "none"\nif (identical(cfg$overflow, "pages") && nrow(d) * lines * mt_pitch_in(cfg) > mt_max_panel_in(cfg)) {\n  per <- floor(mt_max_panel_in(cfg) / (mt_pitch_in(cfg) * lines)); np <- ceiling(nrow(d) / per); per <- ceiling(nrow(d) / np)\n  pg <- split(seq_len(nrow(d)), ceiling(seq_len(nrow(d)) / per)); out0 <- cfg$out; cfg$overflow_used <- "pages"\n  for (i in seq_along(pg)) {\n    dd <- d[pg[[i]], ]; dd$key <- droplevels(dd$key); ll <- long %>% filter(key %in% dd$key) %>% mutate(key = droplevels(key))\n    cfg$rows <- nrow(dd) * lines; cfg$out <- paste0(out0, "_page", i)\n    mt_save(build(dd, ll) + xs + coord_cartesian(clip = "off"), cfg$out, W0, H, cfg)\n  }\n  writeLines(jsonlite::toJSON(list(pages = length(pg), rows_per_page = unname(lengths(pg)), lines_per_row = lines, strains = lapply(pg, function(ix) d$strain[ix])), auto_unbox = TRUE, pretty = TRUE), paste0(out0, "_pages.json"))\n} else { cfg$rows <- nrow(d); mt_save(p,cfg$out,W0,H,cfg) }\n'

if __name__ == "__main__": raise SystemExit(main())
