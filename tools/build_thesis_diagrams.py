#!/usr/bin/env python3
"""build_thesis_diagrams.py — chain-of-events and cause-and-effect diagrams for the thesis chapter.

Two Graphviz diagrams (schematic figures; the no-arrows FIGURE_STYLE rule does not apply — arrows are the
content):
  1. fig_dev_chain     — how Sapote-Mamey developed: each problem discovered drove a specific solution.
  2. fig_causeeffect   — two real test-case paths through the pipeline (the enediyne veto, and a Class-A
                         lead's journey), showing the decisions and their effects.

Emits editable .dot sources + PNG + PDF for each. Usage:
  python tools/build_thesis_diagrams.py --out-dir <dir>            # write dots, render
  python tools/build_thesis_diagrams.py --out-dir <dir> --replot   # re-render from edited dots
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, subprocess
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _wbio import atomic_write_text

DEV_CHAIN = r'''digraph dev_chain {
  rankdir=TB; bgcolor="white"; nodesep=0.3; ranksep=0.42; fontname="DejaVu Sans";
  node [shape=box style="rounded,filled" fontname="DejaVu Sans" fontsize=10 penwidth=1.1 width=2.6];
  edge [color="#666666" penwidth=1.1 arrowsize=0.7 fontname="DejaVu Sans" fontsize=8];

  node [fillcolor="#FBE3E0" color="#C0392B"];  // problems
  p1 [label="antiSMASH detects BGCs\nbut does not prioritize them"];
  p2 [label="raw BGC counts inflated by\nassembly fragmentation"];
  p3 [label="corrected count still confounded\nacross strains of uneven quality"];
  p4 [label="single markers cross-react\n(hglE→enediyne; sugar genes→saccharide)"];
  p5 [label="which candidates are real?\nover-claiming risk"];
  p6 [label="how to rank what survives?"];
  p7 [label="how novel is the chemistry?"];

  node [fillcolor="#E1EEF6" color="#2E86AB"];  // solutions
  s1 [label="Mamey: deterministic\nedge-aware BGC extraction"];
  s2 [label="corrected-count formula\nInterior + ½Edge + ¼FC"];
  s3 [label="fragmentation-robust normalization\n(ectoine+NAPAA denominator)"];
  s4 [label="cross-reacting-family vetoes\n+ saccharide triage (1285→18)"];
  s5 [label="Sapote: Mode B deep dives\n+ locked claim-safety rules"];
  s6 [label="four-axis priority scoring\n→ Class A–C"];
  s7 [label="pan-BGC-ome / novelty\n(41% dark; not saturated)"];

  node [shape=box style="rounded,filled" fillcolor="#FCE8C8" color="#C8954A" width=3.0];
  out [label="ranked, fragmentation-corrected,\nclaim-safe shortlist  →  6 Class-A leads + manuscript"];

  p1->s1 [label=" drove"]; p2->s2 [label=" drove"]; p3->s3 [label=" drove"];
  p4->s4 [label=" drove"]; p5->s5 [label=" drove"]; p6->s6 [label=" drove"]; p7->s7 [label=" drove"];
  s1->p2 [style=dashed label=" revealed"]; s2->p3 [style=dashed label=" revealed"];
  s3->p4 [style=dashed]; s4->p5 [style=dashed]; s5->p6 [style=dashed]; s6->p7 [style=dashed];
  s7->out; s6->out;
}
'''

CAUSE_EFFECT = r'''digraph cause_effect {
  rankdir=TB; bgcolor="white"; nodesep=0.32; ranksep=0.4; fontname="DejaVu Sans"; compound=true;
  node [shape=box style="rounded,filled" fontname="DejaVu Sans" fontsize=10 penwidth=1.1];
  edge [color="#666666" penwidth=1.1 arrowsize=0.7 fontname="DejaVu Sans" fontsize=8];

  subgraph cluster_ene {
    label="Test case 1 — enediyne veto"; fontsize=12; color="#C0392B"; style="rounded"; fontcolor="#C0392B";
    e0 [label="~20 enediyne-marked regions\n(raw signal)" fillcolor="#EEF2F5"];
    e1 [label="check for hglE glycolipid KS\nat the same locus" fillcolor="#FFF6E0"];
    e2 [label="8 carry hglE →\nFALSE POSITIVE → VETOED" fillcolor="#FBE3E0" color="#C0392B"];
    e3 [label="12 candidates (no hglE)" fillcolor="#E8F3E0"];
    e4 [label="Mode B: ene_KS E-value,\n~1900-aa PKSE, UnbV accessory" fillcolor="#F0E4EE"];
    e5 [label="2 CONFIRMED genuine:\nSID-XXX (lidamycin), SID-XXX (neocarzinostatin)" fillcolor="#D6EAD6" color="#27AE60"];
    e0->e1; e1->e2 [label=" hglE present"]; e1->e3 [label=" hglE absent"]; e3->e4; e4->e5;
  }

  subgraph cluster_lead {
    label="Test case 2 — a Class-A lead's path (SID-XXX/BGC024)"; fontsize=12; color="#2E86AB"; style="rounded"; fontcolor="#2E86AB";
    l0 [label="BGC024 detected\n(trans-AT PKS-NRPS)" fillcolor="#EEF2F5"];
    l1 [label="KCB anchor: cycloheximide\n(similarity, not ID)" fillcolor="#FFF6E0"];
    l2 [label="Mode B deep dive → CONFIRM\n(chemistry holds)" fillcolor="#F0E4EE"];
    l3 [label="TFBS coupling → SARP present\n(actively-regulated pathway)" fillcolor="#E8F3E0"];
    l4 [label="four-axis score:\nchemistry ∩ SARP ∩ KCB ∩ tier" fillcolor="#FCE8C8" color="#C8954A"];
    l5 [label="→ CLASS A lead" fillcolor="#D6EAD6" color="#27AE60"];
    l6 [label="but 142 contigs (fragmented)\n→ contig-rescue: re-sequencing target" fillcolor="#FBE3E0" color="#C0392B"];
    l0->l1->l2->l3->l4->l5; l5->l6 [label=" caveat"];
  }
}
'''

def render(dot_text, base, out_dir, replot):
    dot=os.path.join(out_dir, base+'.dot')
    if not replot: atomic_write_text(dot, dot_text)
    if not os.path.exists(dot): emit(f"  no {dot}"); return
    for fmt in ('png','pdf'):
        try:
            subprocess.run(['dot',f'-T{fmt}','-Gdpi=150',dot,'-o',os.path.join(out_dir,f'{base}.{fmt}')],check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            emit(f"  [warn] {base}.{fmt}: {e}"); return
    emit(f"  {base}: png+pdf (+ editable {base}.dot)")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out-dir', default='.'); ap.add_argument('--replot', action='store_true')
    a=ap.parse_args(); os.makedirs(a.out_dir, exist_ok=True)
    render(DEV_CHAIN, 'fig_dev_chain', a.out_dir, a.replot)
    render(CAUSE_EFFECT, 'fig_causeeffect', a.out_dir, a.replot)

if __name__=='__main__': main()
