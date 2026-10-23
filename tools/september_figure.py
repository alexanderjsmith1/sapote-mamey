"""Portable entry point for the September counts, pairwise 16S and class panels.

--kind chooses the promoted producing script. --data-dir contains the original
named input TSVs; no Excel table is guessed. Nonstreptomyces counts accept
'genus_16s.tsv' with the recorded 'Genus (16S)' column. Heatmap needs both matrix
and totals. Rendering always uses bundle publication/minimum-text helpers.
"""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools._figure_route_common import bind,execute,output_dir,receipt,ROOT
FILES={'nonstrep_counts':['genus_16s.tsv'],'pairwise_16s':['pairwise_16S_identity_overlap.tsv'],
       'class_counts':['fig_016d_class_summary.tsv'],'class_heatmap':['cross_001b_matrix.tsv','cross_001b_genome_totals.tsv']}
def main(argv=None):
    import shutil
    from mamey.figure_stamp import stamp_file
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kind',choices=FILES,required=True);p.add_argument('--data-dir',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args(argv)
    script=ROOT/'tools'/('render_'+a.kind+'.R')
    inputs=[a.data_dir/f for f in FILES[a.kind]]+[script,ROOT/'tools/sapote_pub_layout.R',ROOT/'tools/sapote_min_text.R',ROOT/'mamey/data/genus_palette.json']
    bind(inputs);rs=shutil.which('Rscript')
    if not rs:raise RuntimeError('Rscript is required')
    out=output_dir(a.out)
    execute([rs,str(script),str(a.data_dir.resolve()),str(ROOT/'tools'),str(out.resolve())],out/'render.log')
    for f in out.iterdir():
        if f.suffix in ('.pdf','.png','.svg'):stamp_file(f,'september_'+a.kind)
    receipt(out,'september_'+a.kind,inputs)
    return 0
if __name__=='__main__':raise SystemExit(main())
