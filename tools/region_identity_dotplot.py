"""Promoted per-gene identity dot plot using an explicit assembly grouping record.

No assembly identity is inferred from matching genome length. --assembly-map is
TSV(genome_id, assembly_key, focus), focus yes/no. It binds the reviewed duplicate
map; --genes is TSV(query_id, label, best_streptomyces_identity). --hits uses the
original query/subject/identity first-three-column format. The subject genome key
is its first pipe-delimited token, as in the producing script.
"""
import argparse
from collections import defaultdict
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools._figure_route_common import bind,number,output_dir,receipt,save,table,unique,write_table

def prepare(map_path, genes_path, hits_path):
    mapping=unique(table(map_path,['genome_id','assembly_key','focus']),'genome_id')
    states=defaultdict(set)
    for r in mapping.values():
        if not r['assembly_key'].strip() or r['focus'] not in ('yes','no'):raise ValueError('invalid assembly grouping')
        states[r['assembly_key']].add(r['focus'])
    if any(len(x)!=1 for x in states.values()):raise ValueError('conflicting focus state in an assembly group')
    genes=table(genes_path,['query_id','label','best_streptomyces_identity']); unique(genes,'query_id')
    allowed={g['query_id'] for g in genes}; best=defaultdict(dict)
    with Path(hits_path).open() as stream:
        for line in stream:
            if not line.strip():continue
            parts=line.rstrip('\n').split('\t')
            if len(parts)<3:raise ValueError('malformed hit row')
            q,s,pid=parts[:3]; value=number(pid,0,100); genome=s.split('|')[0]
            if q not in allowed:raise ValueError('hit query absent from gene table')
            if genome not in mapping:raise ValueError('hit genome absent from reviewed assembly map')
            key=mapping[genome]['assembly_key'];best[q][key]=max(best[q].get(key,0),value)
    for g in genes:
        if g['best_streptomyces_identity']:number(g['best_streptomyces_identity'],0,100)
    return genes,best,{k:next(iter(v)) for k,v in states.items()}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('assembly-map','genes','hits','out'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--identity-record',type=Path,required=True,help='single-row TSV strain,contig,region,bgc_alias')
    a=p.parse_args(argv);genes,best,states=prepare(a.assembly_map,a.genes,a.hits)
    identity=table(a.identity_record,['strain','contig','region','bgc_alias'])
    if len(identity)!=1:raise ValueError('one bound locus record required')
    from mamey.figure_theme import apply_theme,exact_locus_identity
    r=identity[0]; locus=exact_locus_identity(r['strain'],r['contig'],r['region'],r['bgc_alias'])
    bind([a.assembly_map,a.genes,a.hits,a.identity_record,Path(__file__)])
    out=output_dir(a.out)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    apply_theme(plt,profile='manuscript')
    # Geometry, colours and marker meanings retained from the producing dot plot.
    plt.rcParams.update({'font.size':8,'figure.facecolor':'white','savefig.facecolor':'white'})
    fig,ax=plt.subplots(figsize=(6.5,max(4.6,len(genes)*.3)))
    rows=[]; n=len(genes); act,focus,ref='#4C78A8','#163344','#1B7837'
    for i,g in enumerate(genes):
        y=n-1-i;hits=best[g['query_id']]
        other=sorted(v for k,v in hits.items() if states[k]=='no'); focal=sorted(v for k,v in hits.items() if states[k]=='yes')
        ax.scatter(other,[y+.14+(k%3-1)*.07 for k in range(len(other))],s=9,facecolor='white',edgecolor=act,linewidth=.6)
        ax.scatter(focal,[y-.02]*len(focal),s=16,color=focus)
        if g['best_streptomyces_identity']:
            ax.scatter([float(g['best_streptomyces_identity'])],[y-.2],s=18,color=ref,marker='s')
        ax.text(101,y,str(len(hits)),ha='left',va='center',fontsize=8)
        for key,value in sorted(hits.items()):
            rows.append(dict(query_id=g['query_id'],assembly_key=key,focus=states[key],identity=value))
    ax.set_yticks(range(n));ax.set_yticklabels([g['label'] or g['query_id'] for g in reversed(genes)],fontsize=8)
    # Keep every supplied hit visible; source search thresholds belong in the receipt.
    lo=min([48]+[v for hits in best.values() for v in hits.values()]+[float(g['best_streptomyces_identity']) for g in genes if g['best_streptomyces_identity']])
    ax.set_xlim(max(0,lo-1),100);ax.set_ylim(-.6,n-.4);ax.set_xlabel('Amino-acid identity (%)')
    ax.text(101,n-.3,'genomes',ha='left',va='bottom',fontsize=8)
    for s in ('top','right'):ax.spines[s].set_visible(False)
    ax.grid(axis='x',color='#e5e5e5',linewidth=.6);ax.set_axisbelow(True)
    ax.legend(handles=[Line2D([],[],marker='o',ls='',mfc='white',mec=act,ms=4,label='other comparison genomes'),
                       Line2D([],[],marker='o',ls='',color=focus,ms=4.5,label='focal reference group'),
                       Line2D([],[],marker='s',ls='',color=ref,ms=4.5,label='best Streptomyces genome')],
              loc='lower center',bbox_to_anchor=(.45,1.02),ncol=3,frameon=False,fontsize=8)
    fig.tight_layout();save(fig,out/'identity_dotplot','region_identity_dotplot');plt.close(fig)
    write_table(out/'DRAWN.tsv',rows,['query_id','assembly_key','focus','identity'])
    receipt(out,'region_identity_dotplot',[a.assembly_map,a.genes,a.hits,a.identity_record,Path(__file__)],
            {'locus':locus,'assembly_grouping':'operator-supplied reviewed record; no length-based inference',
             'library_entries':len(table(a.assembly_map,['genome_id'])),'assembly_groups':len(states)})
    return 0
if __name__=='__main__':raise SystemExit(main())
