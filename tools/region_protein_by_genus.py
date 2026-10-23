#!/usr/bin/env python3
"""Render supplied assembly-level predicted-region amino-acid totals by genus.

No sequence analysis is performed. Uses the M5 PCoA page-default minimum-text
helpers alongside the publication layout. Candidate renderer only.
"""
import argparse
import csv
import hashlib
import json
import math
import platform
from pathlib import Path
import shutil
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mamey.csv_safety import SafeDictWriter
from mamey.figure_policy import preflight_chart_data, assert_no_banned_figure_text
from mamey.figure_stamp import stamp_file
from tools._min_text_check import enforce

TOOL = "region_protein_by_genus"
# height grows with the number of genus rows: ROW_IN per row plus FRAME_IN for the axis, title and margins. Each row
# carries an isolate label tier above and below it (LABEL_OFFSET rows from the row line). A smaller --print-height
# than MIN_ROW_IN per row is refused, so rows are never squeezed back together.
ROW_IN = 0.62
FRAME_IN = 1.1
MIN_ROW_IN = 0.5
LABEL_OFFSET = 0.42


def print_height(n_rows, requested=None):
    """Page height in inches for n_rows genus rows; a requested height must leave MIN_ROW_IN per row."""
    auto = max(3.0, ROW_IN * n_rows + FRAME_IN)
    if requested is None:
        return round(auto, 2)
    floor = MIN_ROW_IN * n_rows + FRAME_IN
    if not math.isfinite(requested) or requested < floor:
        raise ValueError(f"--print-height {requested} in leaves less than {MIN_ROW_IN} in per row for {n_rows} rows "
                         f"(at least {floor:.2f} in)")
    return requested
FIELDS = ["strain", "genus", "amino_acids", "missing_CDS_lengths"]
# comparators: named public genomes drawn as labelled points (no box), e.g. the nearest genera of an isolate placed only
# to family. name is set in italics and strain_label in roman; open = yes draws an open symbol (e.g. a fragmented
# assembly, explained in the caption). They count in the row's n and never in its box. label = no draws the point without
# a label (several fragmented assemblies within a few thousand amino acids cannot all be labelled at 8 pt; the caption
# names them). Optional; default yes.
COMPARATOR_FIELDS = ["name", "strain_label", "open", "label"]

def validate(rows):
    preflight = preflight_chart_data(rows, chart_kind="scatter", numeric_fields=["amino_acids"])
    seen = set()
    for row in rows:
        if not set(FIELDS).issubset(row):
            raise ValueError("missing input fields")
        if not row["strain"].strip() or not row["genus"].strip():
            raise ValueError("blank identity")
        if row["strain"] in seen:
            raise ValueError("duplicate assembly")
        seen.add(row["strain"])
        value = float(row["amino_acids"])
        if value <= 0 or not math.isfinite(value) or value != int(value):
            raise ValueError("amino_acids must be a positive integer")
        if float(row["missing_CDS_lengths"]) != 0:
            raise ValueError("missing CDS lengths require a hold")
        if "role" in row and row["role"] not in ("isolate", "reference", "comparator"):
            raise ValueError("role must be isolate, reference or comparator")
        if row.get("role") == "comparator":
            if not (row.get("name") or "").strip():
                raise ValueError(f"comparator {row['strain']} needs a name (the italic part of its label)")
            if (row.get("open") or "no") not in ("yes", "no"):
                raise ValueError("open must be yes or no")
    assert_no_banned_figure_text([r["genus"] for r in rows], figure_id=TOOL)
    return preflight

R_CODE = r'''
suppressPackageStartupMessages({library(ggplot2); library(ggtext); library(jsonlite); library(ggrepel)})
cfg <- fromJSON(commandArgs(TRUE)[1]); source(cfg$bundle_layout); source(cfg$min_text_helper)
d <- read.delim(cfg$data, stringsAsFactors=FALSE, check.names=FALSE)
has_role <- "role" %in% names(d)
if (!has_role) d$role <- "reference"
genera <- if (length(cfg$row_order)) cfg$row_order else sort(unique(d$genus)); d$value <- d$amino_acids/1000
d$position <- NA_real_; boxes <- list()
for (i in seq_along(genera)) {
  ix <- which(d$genus == genera[i] & d$role == "reference"); ix <- ix[order(d$value[ix],d$strain[ix])]
  d$position[d$genus == genera[i] & d$role %in% c("isolate", "comparator")] <- i
  if (length(ix)) {   # fixed jitter from each genome's ID: reproducible, and no rank-ordered slope that reads as a trend
    # (with or without a role column; a genus with no public genomes keeps its isolate diamond and draws no points or box)
    h <- sapply(d$strain[ix], function(z) { u <- utf8ToInt(z); sum(u * seq_along(u) * 7919) %% 1000 }) / 999
    d$position[ix] <- i - 0.2 + 0.4 * h
  }
  v <- d$value[ix]
  if(length(v)>=3) {
    q <- quantile(v,c(0.25,0.5,0.75),type=7,names=FALSE); iq <- q[3]-q[1]
    inside <- v[v >= q[1]-1.5*iq & v <= q[3]+1.5*iq]
    boxes[[length(boxes)+1]] <- data.frame(y=i,q1=q[1],median=q[2],q3=q[3],low=min(inside),high=max(inside))
  }
}
p <- ggplot(d,aes(x=value,y=position)) + theme_pub(8) +
  theme(panel.grid.major.y=element_blank(),legend.position="none",axis.text=element_text(size=8,colour="black"),
        axis.text.y.left=element_markdown(size=8,colour="black"),axis.text.x.bottom=element_markdown(size=8,colour="black"),
        axis.title.x=element_text(size=8,colour="black"),plot.margin=margin(8,10,8,8))
if(length(boxes)) {
 b <- do.call(rbind,boxes)
 p <- p + geom_segment(data=b,aes(x=low,xend=high,y=y,yend=y),inherit.aes=FALSE,colour=PUB_SUB) +
  geom_segment(data=b,aes(x=low,xend=low,y=y-0.12,yend=y+0.12),inherit.aes=FALSE,colour=PUB_SUB) +
  geom_segment(data=b,aes(x=high,xend=high,y=y-0.12,yend=y+0.12),inherit.aes=FALSE,colour=PUB_SUB) +
  geom_rect(data=b,aes(xmin=q1,xmax=q3,ymin=y-0.225,ymax=y+0.225),inherit.aes=FALSE,fill="white",colour=PUB_SUB) +
  geom_segment(data=b,aes(x=median,xend=median,y=y-0.225,yend=y+0.225),inherit.aes=FALSE,colour=PUB_INK)
 write.table(b,paste0(cfg$out,"_box_summary.tsv"),sep="\t",quote=FALSE,row.names=FALSE)
}
write.table(d[,c("strain","genus","role","value","position")],paste0(cfg$out,"_point_positions.tsv"),sep="\t",quote=FALSE,row.names=FALSE)
n_ref <- sapply(genera,function(g)sum(d$genus==g & d$role %in% c("reference","comparator")))
if (has_role) {
  iso <- d[d$role=="isolate",]
  # isolate labels: plain text in two tiers, alternating above and below the row by value within each genus, so a
  # genus with several isolates spreads its labels over both sides instead of one crowded line
  iso <- iso[order(iso$genus, iso$value), ]
  tier <- ave(iso$value, iso$genus, FUN = function(v) seq_along(v))
  iso$nudge <- ifelse(tier %% 2 == 1, cfg$label_offset, -cfg$label_offset)
  cmp <- d[d$role=="comparator",]
  if (nrow(cmp)) {
    cmp <- cmp[order(cmp$genus, cmp$value), ]
    cmp$strain_label[is.na(cmp$strain_label)] <- ""
    if (is.null(cmp$label)) cmp$label <- "yes"
    cmpl <- cmp[cmp$label != "no", ]                  # label = no: point drawn, label left to the caption
    ctier <- ave(cmpl$value, cmpl$genus, FUN = function(v) seq_along(v))
    cmpl$nudge <- ifelse(ctier %% 2 == 1, cfg$label_offset, -cfg$label_offset)
    # a row shared with an isolate: every comparator label goes to the side the isolate labels do not start on, so the
    # two label layers (repelled separately) cannot meet,
    # in two staggered tiers below the row (alternating by value)
    shared <- cmpl$genus %in% iso$genus
    cmpl$nudge[shared] <- ifelse(ctier[shared] %% 2 == 1, -cfg$label_offset, -2 * cfg$label_offset)
    cmpl$lab <- ifelse(nzchar(cmpl$strain_label), sprintf('italic("%s")~"%s"', cmpl$name, cmpl$strain_label),
                       sprintf('italic("%s")', cmpl$name))
    p <- p + geom_point(data=cmp,shape=21,size=2.4,stroke=.6,colour=PUB_SUB,
                        fill=ifelse(cmp$open=="yes","white",PUB_SUB)) +
      geom_text_repel(data=cmpl,aes(label=lab),parse=TRUE,size=cfg$min_text_pt/.pt,family=PUB_FONT,colour=PUB_SUB,
                      seed=7,nudge_y=cmpl$nudge,direction="x",min.segment.length=0,segment.colour="#6B7483",
                      segment.size=.3,box.padding=.25,point.padding=.3)
  }
  p <- p + geom_point(data=d[d$role=="reference",],size=1,colour="#9AA3AE") +
    geom_point(data=iso,shape=23,size=2.8,fill=PUB_INK,colour="white",stroke=.4) +
    geom_text_repel(data=iso,aes(label=strain),size=cfg$min_text_pt/.pt,fontface="bold",family=PUB_FONT,colour=PUB_INK,
                    seed=7,nudge_y=iso$nudge,direction="x",min.segment.length=0,segment.colour="#6B7483",
                    segment.size=.3,box.padding=.25,point.padding=.3)
  ylab <- paste0("<i>",genera,"</i> ",ifelse(n_ref>0,paste0("(n = ",n_ref,")"),"(no public genomes)"))
  # room for the staggered comparator tiers under a shared row (ggrepel drops a label that falls outside the panel)
  extra <- if (nrow(cmp) && any(cmp$genus %in% iso$genus)) 2 * cfg$label_offset else 0
} else {
  extra <- 0
  p <- p + geom_point(size=1,colour="#9AA3AE")   # same reference points and italic genus labels as the role path
  ylab <- paste0("<i>",genera,"</i> (n = ",sapply(genera,function(g)sum(d$genus==g)),")")
}
p <- p +
 scale_y_reverse(breaks=seq_along(genera),labels=ylab,
                 limits=c(length(genera)+0.75+extra,0.25)) +
 labs(y=NULL,x="Protein encoded in predicted regions, thousand amino acids\n(saccharide-only regions excluded)")
cfg$rows <- length(genera)
mt_save(p,cfg$out,cfg$print_width,cfg$print_height,cfg)

# Capture the session that actually produced the plot, after graphics namespaces loaded.
ns <- sort(loadedNamespaces())
runtime <- list(schema_version="sapote.r-render-runtime.v1", R_version=R.version.string,
                platform=R.version$platform, R_home=R.home(), locale=Sys.getlocale(),
                packages=setNames(lapply(ns,function(n) list(
                  version=as.character(getNamespaceVersion(n)),
                  path=if(n=="base") file.path(R.home("library"),"base") else getNamespaceInfo(asNamespace(n),"path"))),ns),
                session_info=capture.output(sessionInfo()))
writeLines(toJSON(runtime,auto_unbox=TRUE,pretty=TRUE),cfg$runtime_receipt)
'''

def row_order_list(text, genera):
    """--row-order as a list; it must name every genus once. None keeps the alphabetical default ([])."""
    if text is None:
        return []
    order = [g.strip() for g in text.split(",") if g.strip()]
    if sorted(order) != sorted(genera) or len(set(order)) != len(order):
        raise ValueError(f"--row-order must name each genus once: missing {sorted(set(genera) - set(order))}, "
                         f"unknown {sorted(set(order) - set(genera))}")
    return order


def read_r_runtime(path):
    """A successful figure must carry the generating R session, never an inferred version."""
    runtime = json.loads(path.read_text())
    if (runtime.get("schema_version") != "sapote.r-render-runtime.v1"
            or not runtime.get("R_version") or not runtime.get("session_info")
            or not runtime.get("packages", {}).get("ggplot2", {}).get("version")):
        raise ValueError("missing executed R/ggplot2 runtime receipt")
    return runtime


def labels_not_drawn(rows, svg_text):
    """Labels the figure must carry (every isolate; every comparator whose label is not 'no') that are absent from the
    drawn SVG text. A comparator label is italic name + roman strain label, written as separate text runs, so its strain
    label (or its name when it has none) is the part looked for."""
    import html
    drawn = " | ".join(html.unescape(t) for t in re.findall(r">([^<]*)</text>", svg_text))
    want = []
    for r in rows:
        if r.get("role") == "isolate":
            want.append(r["strain"])
        elif r.get("role") == "comparator" and (r.get("label") or "yes") != "no":
            want.append((r.get("strain_label") or "").strip() or r["name"])
    return [w for w in want if w not in drawn]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", required=True, type=Path, help="TSV: " + ", ".join(FIELDS) + "; optional role (isolate or reference): "
                    "boxes are then drawn from references and isolates are labelled diamonds")
    ap.add_argument("--caption", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--min-text-pt", type=float, default=8)
    ap.add_argument("--print-width", type=float, default=7.2)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--row-order", default=None, help="genus rows top to bottom, comma-separated; must name every "
                    "genus in --data once (default: alphabetical)")
    ap.add_argument("--print-height", type=float, default=None, help="page height in inches (default: grows with the "
                    f"number of genus rows, {ROW_IN} in per row plus {FRAME_IN} in; at least {MIN_ROW_IN} in per row)")
    a = ap.parse_args(argv)
    if a.min_text_pt < 8 or not math.isfinite(a.min_text_pt) or a.print_width <= 0 or not math.isfinite(a.print_width) or a.dpi < 300:
        raise ValueError("publication gate requires >=8 pt, positive finite width and >=300 dpi")
    with a.data.open(newline="") as f:
        rows = list(csv.DictReader(f,delimiter="\t"))
    preflight = validate(rows)
    height = print_height(len({r["genus"] for r in rows}), a.print_height)
    row_order = row_order_list(a.row_order, {r["genus"] for r in rows})
    caption = a.caption.read_text()
    if not caption.strip(): raise ValueError("empty caption")
    dependencies = [ROOT/"tools/sapote_pub_layout.R", ROOT/"tools/sapote_min_text.R", ROOT/"tools/_min_text_check.py"]
    for path in dependencies:
        if not path.is_file(): raise FileNotFoundError(path)
    if a.out.exists(): raise FileExistsError(a.out)
    rscript = shutil.which("Rscript")
    if not rscript: raise RuntimeError("Rscript is required")
    rscript = str(Path(rscript).resolve())
    a.out.mkdir(parents=True)
    data = a.out/"plot_data.tsv"
    with data.open("w",newline="") as f:
        cols = FIELDS + (["role"] if rows and "role" in rows[0] else [])   # optional role: isolate, reference, comparator
        if any(r.get("role") == "comparator" for r in rows):
            cols += COMPARATOR_FIELDS
            rows = [{**r, "strain_label": r.get("strain_label") or "", "open": r.get("open") or "no",
                     "label": r.get("label") or "yes"} for r in rows]
        w = SafeDictWriter(f,fieldnames=cols,delimiter="\t"); w.writeheader()
        w.writerows([{k:r[k] for k in cols} for r in rows])
    cfg = dict(data=str(data.resolve()),out=str((a.out/TOOL).resolve()),bundle_layout=str(dependencies[0]),
               min_text_helper=str(dependencies[1]),min_text_pt=a.min_text_pt,print_width=a.print_width,dpi=a.dpi,
               runtime_receipt=str((a.out/"R_RUNTIME.json").resolve()),
               print_height=height,label_offset=LABEL_OFFSET,row_order=row_order)
    (a.out/"render_config.json").write_text(json.dumps(cfg,indent=2))
    (a.out/"render.R").write_text(R_CODE)
    (a.out/"PREFLIGHT.json").write_text(json.dumps(preflight,indent=2))
    command = [rscript,str(a.out/"render.R"),str(a.out/"render_config.json")]
    result = subprocess.run(command,capture_output=True,text=True)
    (a.out/"RENDER.log").write_text(result.stdout+result.stderr)
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    runtime = read_r_runtime(a.out/"R_RUNTIME.json")
    check = enforce(a.out/(TOOL+".pdf"),a.min_text_pt)
    missing = labels_not_drawn(rows, (a.out/(TOOL+"_text_check.svg")).read_text())
    if missing:   # ggrepel drops a label that falls outside the panel without an error; the min-text check cannot see it
        raise RuntimeError(f"LABEL_NOT_DRAWN: {missing}; outputs kept as an incomplete attempt")
    for ext in [".png",".pdf"]: stamp_file(a.out/(TOOL+ext),TOOL)
    shutil.copyfile(a.out/(TOOL+"_text_check.svg"),a.out/(TOOL+".svg"))
    stamp_file(a.out/(TOOL+".svg"),TOOL)
    (a.out/(TOOL+"_CAPTION.md")).write_text(caption)
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    receipt = dict(renderer_status="STAGED_B03_CARD_NOT_SEALED_450",tool=TOOL,assemblies=len(rows),
                   inputs=[dict(path=str(p.resolve()),sha256=digest(p)) for p in [a.data,a.caption,Path(__file__),*dependencies]],
                   min_text=check,preflight=preflight,
                   execution=dict(python_version=platform.python_version(),python_executable=sys.executable,
                                  command=command,rscript_sha256=digest(Path(rscript)),
                                  R_version=runtime["R_version"],ggplot2_version=runtime["packages"]["ggplot2"]["version"],
                                  artifacts=[dict(path=p.name,sha256=digest(p)) for p in
                                             [a.out/"R_RUNTIME.json",a.out/"render.R",a.out/"render_config.json"]]))
    (a.out/"RUN_INFO.json").write_text(json.dumps(receipt,indent=2)+"\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
