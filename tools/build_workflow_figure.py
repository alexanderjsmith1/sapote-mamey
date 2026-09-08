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

DOT = r'''digraph sapote_mamey {
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

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out-dir', default='.'); ap.add_argument('--replot', action='store_true')
    a=ap.parse_args(); os.makedirs(a.out_dir, exist_ok=True)
    dot=os.path.join(a.out_dir,'fig_workflow.dot')
    if not a.replot:
        atomic_write_text(dot, DOT)
    if not os.path.exists(dot):
        emit(f"  no {dot} to render"); return
    for fmt in ('png','pdf'):
        out=os.path.join(a.out_dir,f'fig_workflow.{fmt}')
        try:
            subprocess.run(['dot',f'-T{fmt}','-Gdpi=160',dot,'-o',out],check=True)
            emit(f"  fig_workflow.{fmt} rendered")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            emit(f"  [warn] could not render {fmt} (graphviz 'dot' needed): {e}")
    emit(f"  editable source: {dot} (edit + --replot to regenerate)")

if __name__=='__main__': main()
