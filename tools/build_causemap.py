#!/usr/bin/env python3
"""build_causemap.py — chain-of-events / cause-effect diagrams (thesis-oriented).

Two schematic maps, rendered via Graphviz (PNG + PDF), each with an editable .dot source:
  - development : how Sapote-Mamey's rules arose — observation -> problem -> diagnosis -> rule, chained
                  across the project (the methodology cause-effect map for a thesis methods chapter).
  - testcase    : a real strain's path through the pipeline with decision points and outcomes
                  (default SID-XXX, a fragmented Class-A trans-AT lead — the contig-rescue worked example).

Schematic figures are exempt from the FIGURE_STYLE no-arrows rule (the arrows are the content).

Usage: python tools/build_causemap.py --which development --out-dir <dir>
       python tools/build_causemap.py --which testcase    --out-dir <dir>
       python tools/build_causemap.py --which all         --out-dir <dir>
       python tools/build_causemap.py --out-dir <dir> --replot   # re-render edited .dot files
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, subprocess
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _wbio import atomic_write_text

DEVELOPMENT = r'''digraph development {
  rankdir=LR; bgcolor="white"; nodesep=0.3; ranksep=0.7; fontname="DejaVu Sans";
  node [shape=box style="rounded,filled" fontname="DejaVu Sans" fontsize=10 penwidth=1.1];
  edge [color="#555555" arrowsize=0.8];
  // node classes: observation (grey), problem (red-ish), rule/solution (green)
  // 1 fragmentation
  o1 [label="raw antiSMASH counts" fillcolor="#ECECEC"];
  p1 [label="counts track assembly\ncontiguity, not biology" fillcolor="#F6D7D2"];
  r1 [label="corrected-count formula\nInterior + ½Edge + ¼FC" fillcolor="#D6EAD8"];
  o1->p1->r1;
  // 2 enediyne / hglE
  o2 [label="raw enediyne signal ~10× high" fillcolor="#ECECEC"];
  p2 [label="prevalent hglE glycolipid\ndomain mimics ene_KS" fillcolor="#F6D7D2"];
  r2 [label="hglE veto + ene_KS/PKSE/UnbV\nconfirmation → 2 genuine" fillcolor="#D6EAD8"];
  o2->p2->r2;
  // 3 single-marker cross-reaction (general rule)
  p3 [label="single markers cross-react\nbetween classes" fillcolor="#F6D7D2"];
  r3 [label="VETO rule: a marker must beat the\nnearest cross-reacting family at the locus" fillcolor="#D6EAD8"];
  p2->p3->r3;
  // 4 NAPAA
  o4 [label="NAPAA (ε-poly-L-lysine)\nubiquitous" fillcolor="#ECECEC"];
  r4 [label="exclude NAPAA from\necological/comparative claims" fillcolor="#D6EAD8"];
  o4->r4;
  // 5 saccharide
  o5 [label="saccharide = largest class\n(1285 regions)" fillcolor="#ECECEC"];
  p5 [label="mostly tailoring/machinery,\nnot standalone products" fillcolor="#F6D7D2"];
  r5 [label="saccharide triage (→18) +\nomit saccharide-only from headline" fillcolor="#D6EAD8"];
  o5->p5->r5; r4->r5 [style=dashed label="same logic" fontsize=8];
  // 6 normalization
  p6 [label="counts not comparable across\nstrains of differing assembly" fillcolor="#F6D7D2"];
  r6 [label="fragmentation-robust normalization\n(ectoine+NAPAA denominator)" fillcolor="#D6EAD8"];
  r1->p6->r6;
  // 7 judgment / claim-safety
  p7 [label="need judgment + guardrails\n(overclaim risk)" fillcolor="#F6D7D2"];
  r7 [label="two-tier split: Mamey (deterministic)\n+ Sapote (Mode B + claim-safety)" fillcolor="#D6EAD8"];
  r3->p7->r7;
  // 8 convergence
  r8 [label="four-axis priority scoring\n→ Class-A leads" fillcolor="#CDE7D0" penwidth=1.6];
  r2->r8; r6->r8; r7->r8; r5->r8 [style=dashed];
  { rank=same; r2; r3; }
}
'''

TESTCASE = r'''digraph testcase {
  rankdir=TB; bgcolor="white"; nodesep=0.3; ranksep=0.45; fontname="DejaVu Sans";
  node [shape=box style="rounded,filled" fontname="DejaVu Sans" fontsize=10 penwidth=1.1 fillcolor="#EEF3F6"];
  edge [color="#555555" arrowsize=0.8];
  t  [label="SID-XXX — 142 contigs (fragmented draft)" fillcolor="#E4ECF2"];
  a  [label="antiSMASH: BGC024 detected\n(trans-AT PKS-NRPS, edge fragments)"];
  f  [label="fragment-rescue: 348 megasynthase fragments\nat contig edges; EFLS 1232; tier B" fillcolor="#FBEEDD"];
  v  [shape=diamond label="marker beats nearest\ncross-reacting family?" fillcolor="#FCEFD6"];
  vp [label="trans-AT signature holds\n(not an hglE/cross-react artefact)" fillcolor="#E6F4EA"];
  m  [shape=diamond label="Mode B deep dive" fillcolor="#FCEFD6"];
  mc [label="CONFIRM: trans-AT PKS-NRPS hybrid\n(cycloheximide-anchored)" fillcolor="#E6F4EA"];
  reg[label="regulatory coupling: SARP activator present" fillcolor="#EAF1F8"];
  pr [label="four-axis score → CLASS A" fillcolor="#CDE7D0" penwidth=1.6];
  rs [label="PREDICTION: long-read re-sequencing reassembles\nthe split megasynthase into one contiguous cluster" fillcolor="#F3E8F0"];
  t->a->f->v; v->vp [label="yes" fontsize=9]; vp->m; m->mc [label="CONFIRM" fontsize=9]; mc->reg->pr; f->rs [style=dashed]; pr->rs;
}
'''

ENEDIYNE = r'''digraph enediyne {
  rankdir=TB; bgcolor="white"; nodesep=0.35; ranksep=0.5; fontname="DejaVu Sans";
  node [shape=box style="rounded,filled" fontname="DejaVu Sans" fontsize=10 penwidth=1.1];
  edge [color="#555555" arrowsize=0.8];
  sig [label="enediyne signal fires (ene_KS-like marker)\n~12 raw candidate regions" fillcolor="#ECECEC"];
  d1 [shape=diamond label="hglE/hglD glycolipid domain\nat the same locus?" fillcolor="#FCEFD6"];
  dh [label="DROP — false enediyne\nPREV-001 glycolipid cross-reaction\n(SID-XXX / BGC046)" fillcolor="#F6D2CC"];
  d2 [shape=diamond label="iterative PKSE megasynthase (~1900 aa)\n+ warhead / accessory genes (UnbV, SgcJ/EcaC)?" fillcolor="#FCEFD6"];
  ds [label="DROP — false enediyne\nsmall modular PKS, no warhead\n(SID-XXX/BGC010, 994 aa; SID-XXX/BGC018)" fillcolor="#F6D2CC"];
  cf [label="CONFIRM — genuine enediyne\nSID-XXX/BGC048 (lidamycin; ene_KS + SgcJ/EcaC)\nSID-XXX/BGC003 (neocarzinostatin; ene_KS E=1.6e-257, 1948 aa PKSE)" fillcolor="#D6EAD8" penwidth=1.6];
  out [label="net: ~12 raw → 2 genuine  (≈10× over-call corrected)" fillcolor="#EDEDED" penwidth=1.4];
  sig->d1;
  d1->dh [label="yes" fontsize=9 color="#C0392B"];
  d1->d2 [label="no" fontsize=9];
  d2->ds [label="no" fontsize=9 color="#C0392B"];
  d2->cf [label="yes" fontsize=9 color="#2E7D32"];
  dh->out [style=dashed]; ds->out [style=dashed]; cf->out [style=dashed];
}
'''

REJECTIONS = r'''digraph rejections {
  rankdir=LR; bgcolor="white"; nodesep=0.25; ranksep=0.8; fontname="DejaVu Sans";
  node [shape=box style="rounded,filled" fontname="DejaVu Sans" fontsize=10 penwidth=1.1];
  edge [color="#555555" arrowsize=0.7];
  hub [label="Mode B deep dive\ncorrectly REJECTS 5 of 35 candidates\n(specificity, not just hits)" fillcolor="#E4ECF2" penwidth=1.6];
  r1 [label="SID-XXX / BGC046\nfalse enediyne — hglE glycolipid\ncross-reaction (PREV-001)" fillcolor="#F6D2CC"];
  r2 [label="SID-XXX / BGC010\nfalse enediyne — small modular PKS\n(994 aa), no PKSE/accessory" fillcolor="#F6D2CC"];
  r3 [label="SID-XXX / BGC018\nfalse enediyne — KCB c-1027 whole-genome\nonly, no warhead machinery" fillcolor="#F6D2CC"];
  r4 [label="SID-XXX / BGC043\nfalse nucleoside — trehalose/glycogen\nprimary metabolism" fillcolor="#F6D2CC"];
  r5 [label="SID-XXX / BGC039\nglyco locus, not modular PKS —\nsingle KS; T1PKS + size overstated" fillcolor="#F6D2CC"];
  hub->r1; hub->r2; hub->r3; hub->r4; hub->r5;
}
'''

MAPS={'development':DEVELOPMENT,'testcase':TESTCASE,'enediyne':ENEDIYNE,'rejections':REJECTIONS}

def render(name, dot_text, out_dir, replot):
    dot=os.path.join(out_dir,f'causemap_{name}.dot')
    if not replot: atomic_write_text(dot, dot_text)
    if not os.path.exists(dot): emit(f"  no {dot}"); return
    for fmt in ('png','pdf'):
        try:
            subprocess.run(['dot',f'-T{fmt}','-Gdpi=160',dot,'-o',os.path.join(out_dir,f'causemap_{name}.{fmt}')],check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            emit(f"  [warn] {name} {fmt}: {e}"); return
    emit(f"  causemap_{name}.png/.pdf rendered (+ editable .dot)")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--which', default='all', choices=['development','testcase','enediyne','rejections','all'])
    ap.add_argument('--out-dir', default='.'); ap.add_argument('--replot', action='store_true')
    a=ap.parse_args(); os.makedirs(a.out_dir,exist_ok=True)
    todo=MAPS if a.which=='all' else {a.which:MAPS[a.which]}
    for name,txt in todo.items(): render(name,txt,a.out_dir,a.replot)

if __name__=='__main__': main()
