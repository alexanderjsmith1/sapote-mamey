#!/usr/bin/env python3
"""build_workflow_figure.py — Sapote-Mamey file-structure + data-flow diagram (manuscript Figure 1).

Schematic figures are a different category from data figures: the FIGURE_STYLE "no arrows / no callouts"
rule governs data plots (where annotation must not force regeneration); a workflow diagram's arrows ARE its
data. This renders the two-tier architecture and the flow from antiSMASH output to ranked leads.

Emits a Graphviz .dot (editable source, per the figure-data convention) and renders PNG + PDF.

Usage: python tools/build_workflow_figure.py --out-dir <dir>      # writes dot, renders png+pdf
       python tools/build_workflow_figure.py --out-dir <dir> --replot   # re-render from edited dot
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, subprocess
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _wbio import atomic_write_text

LEGACY_DOT = r'''digraph sapote_mamey {
  rankdir=TB; bgcolor="white"; splines=ortho; nodesep=0.35; ranksep=0.5;
  node [shape=box style="rounded,filled" fontname="DejaVu Sans" fontsize=11 penwidth=1.2];
  edge [color="#555555" penwidth=1.1 arrowsize=0.8];

  input [label="antiSMASH output\n(region GBK + region JSON)" fillcolor="#EEF2F5" color="#8888AA"];

  subgraph cluster_mamey {
    label="MAMEY  ·  deterministic Python (tools/)"; fontname="DejaVu Sans"; fontsize=12; style="rounded";
    color="#2E86AB"; penwidth=1.6; fontcolor="#2E86AB";
    extract [label="BGC extraction\n(edge-aware, corrected counts)" fillcolor="#D6EAF4"];
    bank    [label="JSON banks (cohort/)\nbgc · gene · deep · markers" fillcolor="#D6EAF4"];
    workbook[label="coded workbook\n(schema v1.2, A–H sheets)" fillcolor="#AED6E8"];
    extract -> bank -> workbook;
  }

  subgraph cluster_modules {
    label="analysis modules"; fontsize=12; style="rounded"; color="#7FB069"; penwidth=1.4; fontcolor="#5A8A45";
    norm  [label="fragmentation\nnormalization" fillcolor="#E8F3E0"];
    veto  [label="cross-reacting\nvetoes" fillcolor="#E8F3E0"];
    eco   [label="chitinase /\nsaccharide triage" fillcolor="#E8F3E0"];
    reg   [label="TFBS / SARP\ncoupling" fillcolor="#E8F3E0"];
    pan   [label="pan-BGC-ome /\nnovelty" fillcolor="#E8F3E0"];
    resc  [label="fragment-rescue\ntiers" fillcolor="#E8F3E0"];
  }

  subgraph cluster_sapote {
    label="SAPOTE  ·  judgment + claim-safety"; fontsize=12; style="rounded"; color="#B07AA1"; penwidth=1.6; fontcolor="#8E5A82";
    modeb [label="Mode B deep dives\n(CONFIRM / DOWNGRADE / DROP)" fillcolor="#F0E4EE"];
    rules [label="claim-safety rules\n(KCB=similarity; extract-level bioactivity)" fillcolor="#F0E4EE"];
  }

  score [label="four-axis priority scoring\n(chemistry · regulation · anchor · tier)" shape=box style="rounded,filled" fillcolor="#FCE8C8" color="#C8954A" penwidth=1.4];

  subgraph cluster_out {
    label="deliverables"; fontsize=12; style="rounded"; color="#999999"; penwidth=1.2;
    lead  [label="Lead_Board" fillcolor="#F2F2F2"];
    prio  [label="Priority_Leads\n(Class A–C)" fillcolor="#F2F2F2"];
    figs  [label="figures\n(+ source CSV, replot)" fillcolor="#F2F2F2"];
    synth [label="cross-strain\nsynthesis" fillcolor="#F2F2F2"];
  }

  input -> extract;
  workbook -> norm; workbook -> veto; workbook -> eco; workbook -> reg; workbook -> pan; workbook -> resc;
  norm -> score; veto -> modeb; eco -> score; reg -> score; pan -> score; resc -> score;
  modeb -> score; rules -> modeb; rules -> score [style=dashed];
  score -> lead -> prio; prio -> figs; pan -> synth [style=dashed]; prio -> synth;
}
'''

# Paper-ready diagrams (card 018c0f08_452_paper_flow_diagrams). Plain words only: no folder, module or schema names.
# Every box is an HTML table with a transparent padded border, so arrows stop a little short of the visible box.
# Group names sit to the left of their boxes as plain text, never on a frame line that an arrow crosses.
_INK, _PAD = "#4A5560", 6
_FILL = {"plain": "#F4F6F8", "extract": "#DCEAF2", "analysis": "#E6F0DF", "reading": "#F2E6EF", "decision": "#FFFFFF"}
_EDGE_INK = {"reading": "#7A4A70"}


def _esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<BR/>")


def _box(name, text, kind="plain"):
    ink = _EDGE_INK.get(kind, _INK)
    style = "ROUNDED"   # solid outlines everywhere (owner, 15 Oct: no dashes)
    return (f'  {name} [shape=plain label=<<TABLE BORDER="0" CELLPADDING="{_PAD}" CELLSPACING="0"><TR>'
            f'<TD BORDER="1" STYLE="{style}" BGCOLOR="{_FILL[kind]}" COLOR="{ink}" CELLPADDING="7">{_esc(text)}</TD>'
            f'</TR></TABLE>>];\n')


def _side(name, text):
    """A group name set as plain text; it sits at the left end of its row inside the group's frame."""
    return f'  {name} [shape=plaintext fontcolor="#4A5560" fontsize=11 label=<{_esc(text)}>];\n'


_HEAD = ('  bgcolor="white"; nodesep=0.3; ranksep=0.45; fontname="Helvetica";\n'
         '  node [fontname="Helvetica" fontsize=11];\n'
         f'  edge [color="{_INK}" penwidth=1.0 arrowsize=0.7 fontname="Helvetica" fontsize=10];\n')

WORKFLOW_DOT = ("digraph workflow {\n  rankdir=TB; compound=true;\n" + _HEAD
    + _box("input", "antiSMASH archive of one genome")
    + '  subgraph cluster_x { label=""; style="rounded"; color="#C9D6DE"; penwidth=0.8;\n'
    + _side("lx", "Fixed\nextraction")
    + _box("pkg", "Checksummed package:\nregions, genes and domains", "extract")
    + _box("cnt", "Region counts with contig-edge status", "extract")
    + '  rx [shape=plaintext label=<Fixed<BR/>extraction> fontcolor="white" fontsize=11];\n'
    + '  {rank=same; lx; pkg; rx;} lx -> pkg -> rx [style=invis];\n  }\n'
    + '  subgraph cluster_a { label=""; style="rounded"; color="#CFDCC7"; penwidth=0.8;\n'
    + _side("la", "Analyses")
    + _box("gr", "Reference genes\nsearched genome-wide", "analysis")
    + _box("sp", "Split pathways\nacross contigs", "analysis")
    + _box("hb", "Protein homology\nbound to genes", "analysis")
    + _box("fam", "Gene cluster families\nin other genomes", "analysis")
    + _box("ps", "Protein space", "analysis")
    + _box("tx", "Relatedness and\nphylogeny", "analysis")
    + '  ra [shape=plaintext label=<Analyses> fontcolor="white" fontsize=11];\n'
    + '  {rank=same; la; gr; sp; hb; ra;} la -> gr -> sp -> hb -> ra [style=invis];\n'
      '  {rank=same; fam; ps; tx;} fam -> ps -> tx [style=invis];\n'
      '  gr -> fam [style=invis]; sp -> ps [style=invis]; hb -> tx [style=invis];\n  }\n'
    + _box("read", "Reading each cluster: class-level;\nsimilarity is not identity", "reading")
    + _box("out", "Figures with their data and run records")
    + "  input -> pkg; pkg -> cnt;\n"
      "  cnt -> sp [lhead=cluster_a];\n"
      "  ps -> read [ltail=cluster_a]; read -> out;\n}\n")

GAP_RESCUE_DOT = ("digraph gap_rescue {\n  rankdir=TB;\n" + _HEAD
    + _box("ref", "Characterized reference cluster (MIBiG):\nits protein sequences")
    + _box("srch", "Search every protein of the draft genome\n(match: >= 30% identity over >= 50% of the protein)")
    + _box("asg", "Assign each reference gene its best genome protein\n(clear: >= 35% identity and a bitscore\n>= 1.2 x that of the next candidate)")
    + _box("where", "Where is each gene?", "decision")
    + _box("inr", "In the region") + _box("same", "Elsewhere on\nthe same contig")
    + _box("oth", "On another contig") + _box("none", "Not found")
    + _box("cnt", "Count reference genes found (N of M)\nand distinct genome proteins (K)", "extract")
    + _box("rep", "Report clusters more than 70% complete", "analysis")
    + "  ref -> srch -> asg -> where; where -> inr; where -> same; where -> oth; where -> none;\n"
      "  {inr same oth} -> cnt; cnt -> rep;\n}\n")

SPLIT_PATHWAY_DOT = ("digraph split_pathway {\n  rankdir=TB;\n" + _HEAD
    + _box("two", "Two regions that end at contig edges")
    + _box("hom", "Proof 1, homology: both match adjacent parts\nof the same characterized cluster")
    + _box("log", "Proof 2, biosynthetic logic: their domains\ncomplete one assembly line")
    + _box("both", "Both proofs?", "decision")
    + _box("pair", "Candidate split pathway\n(linked by homology; the DNA is not joined)", "analysis")
    + _box("hold", "Not paired")
    + _box("chk", "Check against the closest complete public genome:\none similar intact region there?", "extract")
    + '  two -> hom; two -> log; hom -> both; log -> both; both -> pair [label="  yes"]; both -> hold [label="  no"]; pair -> chk;\n}\n')

FIGURES = {"workflow": WORKFLOW_DOT, "gap-rescue": GAP_RESCUE_DOT, "split-pathway": SPLIT_PATHWAY_DOT, "legacy": LEGACY_DOT}
DOT = WORKFLOW_DOT   # the default is the paper-ready workflow diagram

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out-dir', default='.'); ap.add_argument('--replot', action='store_true')
    ap.add_argument('--figure', choices=sorted(FIGURES), default='workflow',
                    help="workflow (paper Figure 1, default), gap-rescue or split-pathway method diagrams, or legacy (the old design)")
    a=ap.parse_args(); os.makedirs(a.out_dir, exist_ok=True)
    stem = 'fig_workflow' if a.figure == 'workflow' else 'fig_' + a.figure.replace('-', '_')
    dot=os.path.join(a.out_dir,stem+'.dot')
    if not a.replot:
        atomic_write_text(dot, FIGURES[a.figure])
    if not os.path.exists(dot):
        emit(f"  no {dot} to render"); return
    for fmt in ('png','pdf'):
        out=os.path.join(a.out_dir,f'{stem}.{fmt}')
        try:
            subprocess.run(['dot',f'-T{fmt}','-Gdpi=600',dot,'-o',out],check=True)
            emit(f"  {stem}.{fmt} rendered")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            emit(f"  [warn] could not render {fmt} (graphviz 'dot' needed): {e}")
    emit(f"  editable source: {dot} (edit + --replot to regenerate)")

if __name__=='__main__': main()
