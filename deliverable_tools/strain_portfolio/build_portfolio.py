"""Private/local derived portfolio view. No scans, database copies or inferred activity.
Use explicit hash-pinned external source owners; emit only a JSON sidecar and offline HTML.
"""
import argparse, collections, hashlib, importlib.util, json, sqlite3, sys
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()

def checked(entry):
    p=Path(entry['path']).resolve(strict=True)
    if sha(p)!=entry['sha256']: raise ValueError('SOURCE_PIN_CHANGED')
    return p

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def identity(r):
    parts=[r[k] for k in ('strain','full_node','region','bgc_alias')]
    if not all(isinstance(x,str) and x.strip()==x and x for x in parts): raise ValueError('INCOMPLETE_IDENTITY')
    if r['exact_identity']!=' / '.join(parts): raise ValueError('IDENTITY_CONFLICT')
    return r['exact_identity']

def summarize(rows):
    groups={};seen=set()
    for r in rows:
        if r.get('population') != 'frozen45': raise ValueError('MIXED_POPULATION_HOLD')
        if not isinstance(r.get('run_id'),str) or len(r['run_id'])!=64: raise ValueError('RUN_ID_REQUIRED')
        for field in ['ks','c','a','exact_genes','linked_genes','boundary_genes']:
            if type(r.get(field)) is not int or r[field]<0: raise ValueError('MISSING_OR_INVALID_MEASUREMENT')
        if r['linked_genes']>r['exact_genes']: raise ValueError('DENOMINATOR_CONFLICT')
        key=(r['run_id'],identity(r))
        if key in seen: raise ValueError('DUPLICATE_RUN_LOCUS')
        seen.add(key)
        g=groups.setdefault((r['strain'],r['run_id']),dict(strain=r['strain'],run_id=r['run_id'],loci=0,families={},tailoring={},ks=0,c=0,a=0,exact_genes=0,linked_genes=0,boundary_genes=0,edge_loci=0,edge_known=0))
        g['loci']+=1
        for field in ['families','tailoring']:
            for v in set(r[field]):g[field][v]=g[field].get(v,0)+1
        for field in ['ks','c','a','exact_genes','linked_genes','boundary_genes']:g[field]+=r[field]
        if r['touches_source_edge'] is not None:g['edge_known']+=1;g['edge_loci']+=int(r['touches_source_edge'])
    return sorted(groups.values(),key=lambda g:(g['strain'],g['run_id']))

def build(config):
    if config['population']!='frozen45':raise ValueError('POPULATION_UNSUPPORTED_NO_SILENT_MERGE')
    paths={k:checked(v) for k,v in config['sources'].items()}
    for e in config['owner_files']:checked(e)
    owner=load('portfolio_architecture_owner',paths['architecture_reader'])
    db=paths['architecture_db'];manifest=json.loads(paths['architecture_manifest'].read_text())
    if paths['architecture_manifest']!=db.parent/'RELEASE_MANIFEST.json':raise ValueError('OWNER_MANIFEST_PATH_CONFLICT')
    first=owner.read(db,limit=500);source_rows=first['rows'];offset=first['next_offset']
    while offset is not None:
        page=owner.read(db,limit=500,offset=offset);source_rows+=page['rows'];offset=page['next_offset']
    c=sqlite3.connect(db.as_uri()+'?mode=ro&immutable=1',uri=True);c.row_factory=sqlite3.Row
    try:
        genes={r['locus_key']:dict(r) for r in c.execute("SELECT locus_key,sum(membership='EXACT_REGION') exact_genes,sum(membership='EXACT_REGION' AND bound_feature_count>0) linked_genes,sum(membership='OVERLAPPING_BOUNDARY_CONTEXT') boundary_genes FROM gene GROUP BY locus_key")}
        lengths={(r['strain'],r['contig']):r['record_length'] for r in c.execute('SELECT strain,contig,record_length FROM source_record')}
        source={r['strain']:dict(r) for r in c.execute('SELECT * FROM source')}
        contigs={r['strain']:r['n'] for r in c.execute('SELECT strain,count(distinct contig) n FROM source_record GROUP BY strain')}
        profile=dict(c.execute('SELECT * FROM section_profile').fetchone())
        if hashlib.sha256(profile['contract_text'].encode()).hexdigest()!=profile['profile_sha256']:raise ValueError('PROFILE_HASH_CONFLICT')
        # No section completion mapping is authored by this view.
    finally:c.close()
    rows=[]
    for raw in source_rows:
        identity(raw);cap=json.loads(raw['capacity_json']);g=genes.get(raw['locus_key'])
        if g is None:raise ValueError('GENE_ROSTER_UNBOUND')
        length=lengths.get((raw['strain'],raw['full_node']))
        rows.append(dict(population='frozen45',coordinate_convention='WHOLE_RECORD_1_BASED_INCLUSIVE',evidence_state='OBSERVED_SOURCE_ANNOTATIONS',other_channel_states='NOT_ASSESSED_BY_THIS_VIEW',strain=raw['strain'],run_id=source[raw['strain']]['source_sha256'],full_node=raw['full_node'],region=raw['region'],bgc_alias=raw['bgc_alias'],exact_identity=raw['exact_identity'],locus_key=raw['locus_key'],families=json.loads(raw['products_json']),tailoring=cap['tailoring'],ks=raw['canonical_ks'],c=raw['canonical_c'],a=raw['canonical_a'],exact_genes=g['exact_genes'],linked_genes=g['linked_genes'],boundary_genes=g['boundary_genes'],touches_source_edge=(raw['start']<=1 or raw['end']>=length) if length else None,source_record_length=length,start=raw['start'],end=raw['end'],source_member=raw['source_member'],source_member_sha256=raw['source_member_sha256'],source_file=source[raw['strain']]['source_locator'],source_sha256=source[raw['strain']]['source_sha256'],raw_broad_counts=json.loads(raw['broad_counts_json']),capacity_heuristic=cap['capacity'],capacity_evidence=cap['evidence'],hold='Capacity/tailoring are owner heuristics; edge contact is source geometry, not a fragmentation diagnosis. Parent links do not validate function. Module-domain links remain unadmitted.'))
    sys.path.insert(0,str(paths['wetlab_adapter'].parent))
    wet=load('portfolio_wetlab_adapter',paths['wetlab_adapter']);mp=paths['wetlab_manifest'];wm=json.loads(mp.read_text())
    if wm['binding']['census_sha256']!=manifest['binding']['census_sha256']:raise ValueError('CENSUS_CONFLICT')
    if wm['binding']['full50_profile_sha256']!=profile['profile_sha256']:raise ValueError('CONTRACT_CONFLICT')
    with wet.frozen(mp.parent,mp,wm,'database') as w:
        applicability={r['strain']:dict(r) for r in w.execute('SELECT * FROM strain_applicability')}
        assays=[dict(r) for r in w.execute("SELECT r.record_id,r.strain,r.binding_state,r.sheet,r.row_number,r.raw_json,r.raw_sha256,s.path source_file,s.sha256 source_sha256,s.quality FROM source_record r JOIN source s USING(source_id) WHERE r.binding_state='EXACT_SOURCE_STRAIN_LABEL' AND r.strain IS NOT NULL ORDER BY r.strain,r.record_id")]
        for r in assays:
            r['raw_values']=json.loads(r.pop('raw_json'));r['observations']=[dict(x) for x in w.execute('SELECT endpoint_raw,value_raw_json,unit_raw,organism_raw,assay_raw,measurement_state,replicate_state,concentration_state,date_state,missing_metadata_json FROM observation WHERE record_id=?',(r['record_id'],))]
            r['hold']='Strain/fraction context only. Primary assay validation and replicate semantics unresolved; no locus attribution. Derivative sources may overlap.'
    portfolios=summarize(rows)
    for p in portfolios:
        p['source_contigs']=contigs[p['strain']];p['wetlab']=applicability[p['strain']]
        p['wetlab_records']=[r for r in assays if r['strain']==p['strain']]
    if len(rows)!=first['total'] or len(portfolios)!=45:raise ValueError('FROZEN_DENOMINATOR_CONFLICT')
    for e in config['sources'].values():checked(e)
    return dict(schema='strain_portfolio/1',population='frozen45',population_hold='current44base and current46runs are not included; no finalized extension was admitted for this build.',source_version=manifest['binding']['bundle_version'],source_status=manifest['status'],model_provenance=manifest['binding']['model_provenance'],profile={k:v for k,v in profile.items() if k!='contract_text'},section_mapping='No exact50 completion mapping asserted; source contract hash verified.',sources=config,denominator=dict(strains=len(set(r['strain'] for r in rows)),runs=len(portfolios),loci=len(rows),exact_gene_occurrences=sum(r['exact_genes'] for r in rows)),rules={'families':'Distinct source product label presence per locus; multilabel counts overlap. These are pathway-class annotations, not GCF assignments or products.','machinery':'Sum canonical coordinate-deduplicated aSDomain KS, C, A counts within source loci; cross-locus overlap is not deduplicated.','tailoring':'Distinct existing-owner tailoring label presence per locus; heuristic annotation only.','readiness':'Exact-region gene occurrences with any explicit domain-parent link / all exact-region gene occurrences. Not overall evidence completeness.','fragmentation':'Distinct source-record contigs and locus edge contacts / loci with known source record length. Not assembly N50 or proof of truncation.','wetlab':'Exact source strain labels only; records and raw endpoints, no pooled effect size or activity inference.'},portfolios=portfolios,loci=rows)

def render(data):
    template=Path(__file__).with_name('portfolio_template.html').read_text()
    return template.replace('__PORTFOLIO_DATA__',json.dumps(data,sort_keys=True,separators=(',',':')).replace('<','\\u003c').replace('&','\\u0026'))

def write_outputs(data,output):
    """Additive, resumable per-run partitions: verify an existing file, never replace it."""
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    def put(name,raw):
        p=output/name;p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists():
            if p.read_bytes()!=raw:raise ValueError('OUTPUT_CONFLICT_USE_NEW_ROOT')
        else:
            with p.open('xb') as f:f.write(raw)
        return {'path':name,'sha256':sha(p),'bytes':p.stat().st_size}
    entries=[]
    for portfolio in data['portfolios']:
        rows=[r for r in data['loci'] if r['run_id']==portfolio['run_id'] and r['strain']==portfolio['strain']]
        name='partitions/'+hashlib.sha256((portfolio['strain']+portfolio['run_id']).encode()).hexdigest()+'.json'
        entries.append(put(name,json.dumps({'portfolio':portfolio,'loci':rows},sort_keys=True).encode()))
    entries.append(put('portfolio.json',json.dumps(data,indent=2,sort_keys=True).encode()))
    entries.append(put('START_HERE.html',render(data).encode()))
    put('BUILD_RECEIPT.json',json.dumps({'schema':'portfolio_build_receipt/1','partitions':len(data['portfolios']),'files':entries,'builder_sha256':sha(__file__),'template_sha256':sha(Path(__file__).with_name('portfolio_template.html')),'denominator':data['denominator'],'source_pins':data['sources'],'state':'MECHANICAL_CANDIDATE_NOT_SCIENTIFIC_ACCEPTANCE'},indent=2).encode())

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--source-root',type=Path);a=p.parse_args()
    config=json.loads(a.config.read_text())
    source_root=(a.source_root or a.config.parent).resolve(strict=True)
    for e in list(config['sources'].values())+config['owner_files']:
        path=Path(e['path'])
        if not path.is_absolute():e['path']=str((source_root/path).resolve(strict=True))
    output=a.output.resolve()
    for e in list(config['sources'].values())+config['owner_files']:
        if Path(e['path']).resolve().is_relative_to(output):raise ValueError('INPUT_OUTPUT_OVERLAP')
    data=build(config)
    write_outputs(data,a.output)
    print(json.dumps(data['denominator']))
if __name__=='__main__':main()
