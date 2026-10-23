"""Run-of-record overview from precomputed tables; does not fit BiG-SLiCE.

Input folder: panelA_data.tsv, panelB_isolate.tsv, panelB_background.tsv.
The three category shares must sum to their supplied per-collection denominator;
all five original categories are accepted. Thresholds 0.6 and 0.8 and the plotting
bin width 0.025 retain their producing definitions. No fact-sheet counts ship.
"""
import argparse
from collections import defaultdict
from pathlib import Path
import shutil,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools._figure_route_common import ROOT,bind,table,number,output_dir,execute,receipt
CATS={'reference_family','isolate_only_shared','isolate_only_alone','beyond_0.6_to_0.8','beyond_0.8'}
def validate(data):
    rows=table(data/'panelA_data.tsv',['collection','category','regions','total_regions'])
    groups=defaultdict(list)
    for r in rows:groups[r['collection']].append(r)
    if set(groups)!={'bee_wasp','moss','attine'}:raise ValueError('unexpected/missing collections')
    for coll,rs in groups.items():
        if len(rs)!=len(CATS) or {r['category'] for r in rs}!=CATS:raise ValueError('missing/duplicate categories')
        totals={int(r['total_regions']) for r in rs}
        if len(totals)!=1 or next(iter(totals))<=0 or any(int(r['regions'])<0 for r in rs) or sum(int(r['regions']) for r in rs)!=next(iter(totals)):
            raise ValueError('category denominator mismatch')
    iso=table(data/'panelB_isolate.tsv',['collection','strain','contig','region','distance'])
    bg=table(data/'panelB_background.tsv',['source','distance'])
    for r in iso+bg:number(r['distance'],0,1.1)
    for coll,rs in groups.items():
        if sum(r['collection']==coll for r in iso)!=int(rs[0]['total_regions']):raise ValueError('isolate roster count mismatch')
    if any(r['collection'] not in groups for r in iso):raise ValueError('unknown isolate collection')
    if sorted(round(float(r['distance']),6) for r in iso)!=sorted(round(float(r['distance']),6) for r in bg if r['source']=='isolate'):
        raise ValueError('background isolate distances differ')
    return groups

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(argv);validate(a.data_dir);rscript=shutil.which('Rscript')
    if not rscript:raise RuntimeError('Rscript required')
    script=ROOT/'tools/render_bigslice_overview.R'
    inputs=[a.data_dir/f for f in ('panelA_data.tsv','panelB_isolate.tsv','panelB_background.tsv')]+[script,ROOT/'tools/sapote_pub_layout.R',ROOT/'tools/sapote_min_text.R',Path(__file__)]
    bind(inputs);out=output_dir(a.out)
    execute([rscript,str(script),str(a.data_dir.resolve()),str(ROOT/'tools'),str(out.resolve())],out/'render.log')
    from mamey.figure_stamp import stamp_file
    for f in out.iterdir():
        if f.suffix in ('.pdf','.png','.svg'):stamp_file(f,'bigslice_overview_figure')
    receipt(out,'bigslice_overview_figure',inputs,{'fitting':'NOT_EXECUTED','thresholds':[0.6,0.8],'histogram_bin_width':0.025})
    return 0
if __name__=='__main__':raise SystemExit(main())
