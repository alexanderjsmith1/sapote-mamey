"""Adapt edge totals to the public_genome_families two-part display schema.

Only a format adapter: regions -> families, interior -> in_public, edge ->
not_in_public. These legacy renderer column names do not mean families here.
The original edge-rule receipt is required and copied into the output receipt.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools._figure_route_common import table,unique,write_table,receipt,output_dir

def convert(totals,genomes):
    ts=unique(totals,'strain');gs=unique(genomes,'strain')
    if ts.keys()!=gs.keys():raise ValueError('edge totals and genome roster differ')
    out=[]
    for g in genomes:
        t=ts[g['strain']]
        n,e=int(t['regions']),int(t['contig_edge'])
        if n<0 or not 0<=e<=n or t['genus']!=g['genus']:raise ValueError('invalid edge counts or genus mismatch')
        out.append(dict(strain=g['strain'],genus=g['genus'],families=n,in_public=n-e,not_in_public=e))
    return out

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('totals','genomes','edge-receipt','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args(argv); info=json.loads(a.edge_receipt.read_text())
    if not info.get('rule'):raise ValueError('missing edge-rule provenance')
    rows=convert(table(a.totals,['strain','genus','regions','contig_edge']),table(a.genomes,['strain','genus']))
    out=output_dir(a.out);write_table(out/'plot_data.tsv',rows,['strain','genus','families','in_public','not_in_public'])
    receipt(out,'edge_plot_data',[a.totals,a.genomes,a.edge_receipt,Path(__file__)],
            {'edge_rule':info['rule'],'renderer_column_meanings':{'families':'regions','in_public':'interior','not_in_public':'edge'}},figures=False)
    return 0
if __name__=='__main__':raise SystemExit(main())
