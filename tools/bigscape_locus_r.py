#!/usr/bin/env python3
"""Render one explicitly selected, source-bound BiG-SCAPE pair through R.

Reads existing evidence; no search, clustering, all-pairs export or source copy.
Default images are a clean vector SVG and a captioned vector PDF; --preview-png
adds one native 300-DPI PNG. Requires an explicit single-run DB at this stage.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,sqlite3,subprocess,sys
from pathlib import Path
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # run as tools/<name>.py from the bundle root
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while block:=f.read(1024*1024):h.update(block)
    return h.hexdigest()

def read_only(path):return sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
def require_fresh(out):
    out=Path(out)
    if out.exists() or out.is_symlink():raise ValueError('output must be a new directory')
    if not out.parent.is_dir():raise ValueError('output parent must exist')

def checked_refresh(out,db,comparison):
    if out.is_symlink():raise ValueError('refresh output cannot be a symlink')
    path=out/'PROTOTYPE_RECEIPT.json'
    if not path.is_file() or path.is_symlink():raise ValueError('refresh requires a prior complete prototype receipt')
    previous=json.loads(path.read_text())
    if previous.get('status')!='COMPLETE':raise ValueError('refresh requires a complete prior render')
    expected=previous['source_bindings'][:2]
    actual=[{'path':str(db),'sha256':sha(db)},{'path':str(comparison),'sha256':sha(comparison)}]
    if expected!=actual:raise ValueError('refresh cannot change the database or selected comparison')
    for name,binding in previous['outputs'].items():
        p=out/name
        if Path(name).name!=name or p.is_symlink() or sha(p)!=binding['sha256']:raise ValueError('prior output differs from receipt; refresh refused')
    return previous

def span_coordinates(cds,start,stop,reverse=False):
    ordered=list(reversed(cds)) if reverse else list(cds)
    if not 0<=start<stop<=len(ordered):raise ValueError('invalid stored CDS span')
    selected=ordered[start:stop]
    return min(g['nt_start'] for g in selected),max(g['nt_stop'] for g in selected)

def write_tsv(path,rows,fields,replace=False):
    with path.open('w' if replace else 'x',encoding='utf-8',newline='') as f:
        w=_SafeDictWriter(f,fieldnames=fields,delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(rows)

def prepare(db,run_id,comparison,bundle):
    sys.path.insert(0,str(bundle))
    from mamey.figures.locus_comparison import validate,layout
    from mamey.figure_policy import preflight_chart_data
    try:
        from Bio import SeqIO
    except ImportError:  # no Biopython: the bundle's GenBank reader
        from mamey._gbk_shim import SeqIO
    spec=json.loads(comparison.read_text(encoding='utf-8'));validate(spec)
    if len(spec['tracks'])!=2:raise ValueError('exactly two tracks supported')
    bindings=[{'path':str(db),'sha256':sha(db)},{'path':str(comparison),'sha256':sha(comparison)}]
    source_by_name={}
    for source in spec['sources']:
        p=Path(source['path']);p=p if p.is_absolute() else comparison.parent/p
        p=p.resolve()
        if sha(p)!=source['sha256']:raise ValueError(f'source hash mismatch: {p.name}')
        bindings.append({'path':str(p),'sha256':source['sha256']})
        if p.suffix.lower() in ['.gbk','.gb','.genbank']:
            if p.name in source_by_name:raise ValueError('ambiguous source basename')
            source_by_name[p.name]=p
    c=read_only(db);c.row_factory=sqlite3.Row
    runs=[dict(r) for r in c.execute('select * from run')]
    if len(runs)!=1 or runs[0]['id']!=run_id:raise ValueError('requires one explicitly selected DB run; multi-run provenance is not inferred')
    run=runs[0]
    if not run.get('end_time'):raise ValueError('selected run is incomplete')
    records=[dict(r) for r in c.execute("select r.*,g.path from bgc_record r join gbk g on g.id=r.gbk_id where r.record_type='region'")]
    display,links=layout(spec);by={(r['track'],r['gene']):r for r in display}
    genes=[];tracks=[];selected=[]
    for ti,t in enumerate(spec['tracks']):
        matches=[]
        for record in records:
            p=source_by_name.get(Path(record['path']).name)
            if p is None:continue
            recs=list(SeqIO.parse(str(p),'genbank'))  # one record, as SeqIO.read requires
            if len(recs)!=1:raise ValueError(f'source GBK must hold exactly one record: {p.name}')
            rec=recs[0]
            region=next(f for f in rec.features if f.type=='region')
            feature_by_tag={f.qualifiers.get('locus_tag',[''])[0]:f for f in rec.features if f.type=='CDS'}
            if set(g['id'] for g in t['genes'])!=set(feature_by_tag):continue
            if any(int(feature_by_tag[g['id']].location.start)!=g['start'] or int(feature_by_tag[g['id']].location.end)!=g['end'] or feature_by_tag[g['id']].location.strand!=g['strand'] or hashlib.sha256(feature_by_tag[g['id']].qualifiers['translation'][0].rstrip('*').encode()).hexdigest()!=g['aa_sha256'] for g in t['genes']):continue
            # Strong binding includes the GBK stored in this DB, not filename alone.
            stored=Path(record['path']).resolve()
            if not stored.is_file() or sha(stored)!=sha(p):raise ValueError('DB source differs from supplied GBK')
            matches.append((record,p,rec,region,feature_by_tag))
        if len(matches)!=1:raise ValueError('track must resolve to one exact DB region with complete source/AA parity')
        record,p,rec,region,features=matches[0];selected.append(record)
        db_cds=[dict(x) for x in c.execute('select * from cds where gbk_id=? and nt_start>=? and nt_stop<=? order by nt_start,nt_stop,orf_num',(record['gbk_id'],record['nt_start'],record['nt_stop']))]
        source_cds={(g['start'],g['end'],g['strand'],g['aa_sha256']) for g in t['genes']}
        stored_cds={(x['nt_start'],x['nt_stop'],x['strand'],hashlib.sha256(x['aa_seq'].rstrip('*').encode()).hexdigest()) for x in db_cds}
        if source_cds!=stored_cds:raise ValueError('DB CDS coordinates/strands/proteins differ from source manifest')
        anchor=by[(t['id'],t['anchor_gene'])]['anchor_bp']
        # Raw-GBK references retain an explicitly unassigned alias; none is invented.
        identity=t['identity'];alias=identity.get('bgc','') if t['kind']=='bgc' else ''
        strain=identity.get('strain',t['label'])
        heading=f"{strain}\n{rec.id} / region{int(region.qualifiers['region_number'][0]):03}"
        if alias:heading+=' / '+alias
        if t['kind']=='reference' and identity['accession']!=t['label']:
            heading=f"{t['label']} [{identity['accession']}]\n{rec.id} / region{int(region.qualifiers['region_number'][0]):03}"
        tracks.append(dict(track=t['id'],heading=heading,strain=strain,full_node=rec.id,region=int(region.qualifiers['region_number'][0]),bgc_alias=alias,alias_state='SUPPLIED' if alias else 'NOT_ASSIGNED_IN_RAW_GBK',orientation=t['orientation'],anchor_gene=t['anchor_gene'],anchor_bp=anchor,offset_bp=t.get('offset_bp',0),source=str(p),source_sha256=sha(p),contig_edge=bool(record['contig_edge']),source_start=(0-anchor)*t['orientation']+t.get('offset_bp',0),source_end=(len(rec)-anchor)*t['orientation']+t.get('offset_bp',0),cds=db_cds))
        for order,g in enumerate(t['genes'],1):
            f=features[g['id']];r=by[(t['id'],g['id'])]
            genes.append(dict(track=t['id'],strain=strain,full_node=rec.id,region=tracks[-1]['region'],bgc_alias=alias,alias_state=tracks[-1]['alias_state'],locus_tag=g['id'],order=order,start=g['start'],end=g['end'],strand=g['strand'],length_aa=len(f.qualifiers['translation'][0].rstrip('*')),role=f.qualifiers.get('gene_kind',['other'])[0],gene_functions=' | '.join(f.qualifiers.get('gene_functions',[])),source_domains=' | '.join(f.qualifiers.get('sec_met_domain',[])),source=str(p),aa_sha256=g['aa_sha256'],display_start=r['display_start']/1000,display_end=r['display_end']/1000,display_strand=r['display_strand'],display_label=g['label']))
    aid,bid=[r['id'] for r in selected]
    edges=[dict(x) for x in c.execute('select d.* from distance d join edge_params e on e.id=d.edge_param_id where ((record_a_id=? and record_b_id=?) or (record_a_id=? and record_b_id=?)) and lower(e.weights)=lower(?) and lower(e.alignment_mode)=lower(?) and lower(e.extend_strategy)=lower(?)',(aid,bid,bid,aid,run['weights'],run['alignment_mode'],run['extend_strategy']))]
    if len(edges)!=1:raise ValueError('exact pair/edge-parameter association not unique')
    edge=edges[0];spans=[]
    for t,record in zip(tracks,selected):
        side='a' if record['id']==edge['record_a_id'] else 'b';reverse=side=='b' and bool(edge['reverse'])
        for kind in ['lcs','ext']:
            lo,hi=span_coordinates(t['cds'],edge[f'{kind}_{side}_start'],edge[f'{kind}_{side}_stop'],reverse)
            x=[((z-t['anchor_bp'])*t['orientation']+t['offset_bp'])/1000 for z in [lo,hi]]
            spans.append(dict(track=t['track'],kind=kind,native_start=lo,native_end=hi,display_start=min(x),display_end=max(x),stored_record_side=side,stored_reverse=bool(edge['reverse'])))
        del t['cds']
    c.close()
    plotted_links=[]
    for l in links:
        a,b=(by[tuple(l[k])] for k in ['a','b'])
        plotted_links.append(dict(track_a=l['a'][0],gene_a=l['a'][1],track_b=l['b'][0],gene_b=l['b'][1],identity_pct=l.get('identity_pct',''),a_start=a['display_start']/1000,a_end=a['display_end']/1000,b_start=b['display_start']/1000,b_end=b['display_end']/1000,evidence=l['evidence']))
    preflight=preflight_chart_data(genes,chart_kind='locus_map',numeric_fields=['start','end','length_aa'])
    return dict(genes=genes,links=plotted_links,spans=spans,tracks=tracks,run=run,edge=edge,bindings=bindings,preflight=preflight)

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--db',type=Path,required=True);ap.add_argument('--run-id',type=int,required=True)
    ap.add_argument('--comparison',type=Path,required=True);ap.add_argument('--bundle-root',type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument('--rscript',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--preview-png',action='store_true')
    ap.add_argument('--refresh',action='store_true',help='replace this prototype rendering in place after validating its complete prior receipt; never changes scientific inputs')
    a=ap.parse_args(argv)
    a.db=a.db.resolve();a.comparison=a.comparison.resolve();a.bundle_root=a.bundle_root.resolve();a.out=a.out.absolute()
    previous=checked_refresh(a.out,a.db,a.comparison) if a.refresh else None
    if previous and 'locus_plot_only.png' in previous['outputs']:a.preview_png=True
    if not a.refresh:require_fresh(a.out)
    data=prepare(a.db,a.run_id,a.comparison,a.bundle_root)
    if not a.refresh:a.out.mkdir()
    for name in ['genes','links','spans']:
        rows=data[name];fields=list(rows[0]) if rows else ['track_a','gene_a','track_b','gene_b','identity_pct','a_start','a_end','b_start','b_end','evidence']
        write_tsv(a.out/(name+'.tsv'),rows,fields,replace=a.refresh)
    caption=(f"The two rows show all {sum(1 for g in data['genes'] if g['track']==data['tracks'][0]['track'])} and {sum(1 for g in data['genes'] if g['track']==data['tracks'][1]['track'])} CDSs in the selected regions on a common kb scale. Arrows encode gene direction; fills follow source antiSMASH roles. Gray ribbons show {len(data['links'])} supplied protein correspondences. Dark and blue bars show the LCS and final comparable CDS envelopes stored by BiG-SCAPE. Gene numbers follow source order and resolve to full tags in genes.tsv. Whole-row orientation and translation preserve native spacing. These computational comparisons support inspection of gene organization; compound identity and production require separate evidence.")
    (a.out/'CAPTION.md').write_text('# Paired locus comparison\n\n'+caption+'\n',encoding='utf-8')
    config={'tracks':data['tracks'],'title':'NRPS locus comparison' if all('NRPS'==x for x in [data['run'].get('record_type','')]) else 'Locus comparison','subtitle':f"BiG-SCAPE {data['run']['alignment_mode']} / {data['run']['extend_strategy']}; D = {data['edge']['distance']:.4f}",'caption':caption,'bundle_root':str(a.bundle_root),'preview_png':a.preview_png,'width_in':7.2,'body_height_in':5.6,'min_font_pt':8}
    (a.out/'plot_config.json').write_text(json.dumps(config,indent=2)+'\n')
    renderer=Path(__file__).with_name('bigscape_locus_map.R');command=[str(a.rscript),str(renderer),str(a.out)]+(['--refresh'] if a.refresh else [])
    receipt={'status':'RUNNING','source_bindings':data['bindings'],'run_id':a.run_id,'stored_run_settings':data['run'],'pair_components':data['edge'],'preflight':data['preflight'],'command':command,'producer_sha256':sha(__file__),'R_renderer_sha256':sha(renderer),'bundle_root':str(a.bundle_root),'bundle_build_stamp':(a.bundle_root/'BUILD_STAMP.txt').read_text(),'borrowed_source_bindings':{str(p):sha(p) for p in [a.bundle_root/'tools/sapote_figure_theme.R',a.bundle_root/'tools/sapote_locus_map.R',a.bundle_root/'mamey/figures/locus_comparison.py',a.bundle_root/'mamey/figure_policy.py']},'identity_holds':[t['track']+': BGC alias not assigned in source' for t in data['tracks'] if not t['bgc_alias']],'scope':'Custom development prototype; no Mamey score, release approval or biological acceptance. DB read-only; no clustering/search or all-pairs export.'}
    path=a.out/'PROTOTYPE_RECEIPT.json';path.write_text(json.dumps(receipt,indent=2)+'\n')
    if previous:
        receipt['prior_renders']=previous.get('prior_renders',[])+[{'producer_sha256':previous['producer_sha256'],'R_renderer_sha256':previous['R_renderer_sha256'],'outputs':previous['outputs'],'action':'Explicit --refresh replaced declared prototype outputs after hash/input validation. Prior output hashes retained; no source data removed.'}]
        path.write_text(json.dumps(receipt,indent=2)+'\n')
    with (a.out/'R.log').open('w') as f:result=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
    receipt.update(returncode=result.returncode,status='COMPLETE' if result.returncode==0 else 'FAILED')
    if result.returncode==0:
        if not all(sha(x['path'])==x['sha256'] for x in data['bindings']):raise ValueError('source changed during render')
        receipt['outputs']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(a.out.iterdir()) if p.is_file() and p!=path}
    path.write_text(json.dumps(receipt,indent=2)+'\n')
    if result.returncode:raise RuntimeError('R rendering failed; retained R.log and partial outputs')
    print(json.dumps({'output':str(a.out),'files':len(receipt['outputs'])+1,'bytes':sum(x['bytes'] for x in receipt['outputs'].values())+path.stat().st_size,'genes':len(data['genes']),'links':len(data['links']),'distance':data['edge']['distance']}))
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,RuntimeError,FileNotFoundError,sqlite3.DatabaseError) as exc:
        sys.stderr.write(f'refused: {exc}\n');raise SystemExit(2)
