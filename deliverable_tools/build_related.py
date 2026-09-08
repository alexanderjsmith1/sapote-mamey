"""Build a bounded private comparison sidecar using pinned existing evidence readers.
Usage: python -B build_related.py CONFIG.json NEW_OUTPUT_DIRECTORY
No alignment, clustering, annotation scan, or orthology inference is performed.
"""
import argparse, collections, hashlib, importlib.util, json, sys, zipfile, re
from pathlib import Path
sys.dont_write_bytecode = True
ADMITTED = 'SOURCE_CONTENT_AND_CENSUS_LOCUS_BOUND_CONTEXT'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
def identity(row):
    parts=[row.get(k) for k in ('strain','full_node','region','bgc_alias')]
    if any(not isinstance(v,str) or not v.strip() or v!=v.strip() for v in parts): raise ValueError('COMPLETE_IDENTITY_HOLD')
    text=' / '.join(parts)
    if row.get('exact_identity',text)!=text: raise ValueError('IDENTITY_CONFLICT')
    return text

def eligible(m,run):
    return m['state']==ADMITTED and bool(run['end_time']) and m['database_sha256']==run['database_sha256'] and m['run_id']==run['run_id']

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def validate_detail(locus,genes,roster):
    identity(locus)
    exact=[g for g in genes if g['membership']=='EXACT_REGION']
    observed=[(g['locus_tag'],g['protein_sha256']) for g in exact]
    expected=[(g['locus_tag'],g['protein_sha256']) for g in roster]
    if collections.Counter(observed)!=collections.Counter(expected): raise ValueError('PROTEIN_ROSTER_CONFLICT')
    if any(g['end']<g['start'] for g in genes): raise ValueError('GENE_GEOMETRY_HOLD')
    return {'exact_identity':identity(locus),'exact_genes':len(exact),'roster_match':True,'boundary_context_genes':len(genes)-len(exact)}

def build(config,out):
    cfg=json.loads(Path(config).read_text());sources=cfg['sources']
    if cfg['population']!='frozen45':raise ValueError('POPULATION_NOT_SUPPORTED_NO_IMPLICIT_MERGE')
    for k,s in sources.items():
        if sha(s['path'])!=s['sha256']:raise ValueError('SOURCE_HASH_HOLD:'+k)
        if k in ('bigscape','architecture') and any(Path(s['path']+x).exists() for x in ('-wal','-journal')):raise ValueError('LIVE_DATABASE_HOLD')
    out=Path(out).resolve()
    binding={'config_sha256':sha(config),'builder_sha256':sha(__file__),'template_sha256':sha(Path(__file__).with_name('related_view.html'))}
    if out.exists():
        if not (out/'RESUME_BINDING.json').exists() or json.loads((out/'RESUME_BINDING.json').read_text())!=binding:raise ValueError('RESUME_BINDING_HOLD')
        if (out/'SELF_AUDIT.json').exists():raise ValueError('SEALED_OUTPUT_USE_NEW_ROOT')
    else:out.mkdir(parents=True)
    (out/'RESUME_BINDING.json').write_text(json.dumps(binding,indent=2))
    (out/'partitions').mkdir(exist_ok=True)
    br=load(sources['bigscape_reader']['path'],'existing_family_reader');ar=load(sources['architecture_reader']['path'],'existing_architecture_reader')
    r=br.Reader(sources['bigscape']['path'],sources['bigscape']['sha256'])
    try:
        manifest=json.loads(Path(sources['bigscape_manifest']['path']).read_text())
        if manifest['database_sha256']!=sources['bigscape']['sha256']:raise ValueError('MANIFEST_HOLD')
        profile=json.loads(r.rows("SELECT value FROM metadata WHERE key='profile'")[0]['value'])
        with zipfile.ZipFile(sources['baseline']['path']) as z: contract=z.read(profile['member'])
        if hashlib.sha256(contract).hexdigest()!=profile['profile_sha256'] or profile['code_zip_sha256']!=sources['baseline']['sha256']:raise ValueError('CONTRACT_HOLD')
        sections=r.sections()
        required=[(int(n),t.strip()) for n,t in re.findall(r'^\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*$',contract.decode(),re.M)]
        if [(s['number'],s['requirement']) for s in sections]!=required or [n for n,t in required]!=list(range(1,51)):raise ValueError('SECTION_MAPPING_CONFLICT')
        if r.rows('PRAGMA foreign_key_check'):raise ValueError('FOREIGN_KEY_HOLD')
        runs={(x['database_sha256'],x['run_id']):x for x in r.rows('SELECT * FROM run')}
        loci={}
        for offset in range(0,manifest['counts']['locus'],1000):
            for x in r.coverage(1000,offset):identity(x);loci[x['locus_key']]=x
        members=r.rows('SELECT m.*,f.run_id,f.cutoff,f.bin_label,f.member_count,f.membership_sha256 FROM locus_membership m JOIN family f USING(database_sha256,qualified_family_id)')
        seen=set();assignments=collections.defaultdict(set)
        for m in members:
            mk=(m['locus_key'],m['database_sha256'],m['qualified_family_id'],m['record_id'])
            if mk in seen:raise ValueError('DUPLICATE_MEMBERSHIP_HOLD')
            seen.add(mk)
            if m['locus_key'] not in loci:raise ValueError('MEMBERSHIP_LOCUS_UNBOUND')
            if m['state']==ADMITTED:assignments[(m['locus_key'],m['database_sha256'],m['run_id'],m['cutoff'])].add(m['qualified_family_id'])
        if any(len(v)>1 for v in assignments.values()):raise ValueError('FAMILY_CONFLICT_HOLD')
        for m in members:m['exact_identity']=identity(loci[m['locus_key']])
        groups=collections.defaultdict(list);held=0
        for m in members:
            if eligible(m,runs[(m['database_sha256'],m['run_id'])]):groups[(m['database_sha256'],m['qualified_family_id'])].append(m)
            else:held+=1
        groups={k:v for k,v in groups.items() if len({m['locus_key'] for m in v})>1}
        # Fixed cutoff selection is explicit; no merging across cutoff or run.
        choices=sorted([(k,v) for k,v in groups.items() if v[0]['cutoff']=='0.3'],key=lambda kv:(max(loci[m['locus_key']]['region_nt'] for m in kv[1]),kv[0]))
        count=min(int(cfg.get('family_count',5)),len(choices))
        if count<1:raise ValueError('NO_ADMITTED_COMPARISON_PAIR')
        picks=[choices[round(i*(len(choices)-1)/max(1,count-1))] for i in range(count)]
        families=[];keys=[]
        for k,ms in picks:
            ordered=sorted({m['locus_key'] for m in ms},key=lambda x:(loci[x]['region_nt'],identity(loci[x])))
            pair=[ordered[0],ordered[-1]];keys.extend(pair)
            families.append({'database_sha256':k[0],'qualified_family_id':k[1],'run':runs[(k[0],ms[0]['run_id'])],'cutoff':ms[0]['cutoff'],'bin':ms[0]['bin_label'],'selected':pair,'selected_identities':[identity(loci[k]) for k in pair],'admitted_census_members':len(ordered),'source_family_members':ms[0]['member_count'],'membership_sha256':ms[0]['membership_sha256'],'memberships':[m for m in ms if m['locus_key'] in pair],'rule':'Exact bound membership + recorded run end; same database/run/cutoff/family. Two length extremes selected; no alignment.'})
        negatives=[]
        for state in sorted({l['coverage_state'] for l in loci.values()}-{'BOUND_LOCUS_CONTEXT_AVAILABLE'}):
            l=sorted((l for l in loci.values() if l['coverage_state']==state),key=identity)[0]
            negatives.append({'locus':l,'hold':state,'raw_memberships':[m for m in members if m['locus_key']==l['locus_key']]})
        details={};audit=[]
        for key in dict.fromkeys(keys):
            cached=out/'partitions'/('__'.join(re.sub(r'[^A-Za-z0-9_.-]','_',loci[key][k]) for k in ('strain','full_node','region','bgc_alias'))+'.json')
            checksum=cached.with_suffix('.sha256')
            if cached.exists():
                if not checksum.exists() or checksum.read_text().strip()!=sha(cached):raise ValueError('PARTITION_TAMPER_HOLD')
                saved=json.loads(cached.read_text());details[key]=saved['detail'];audit.append(saved['audit']);continue
            l=loci[key];ident=identity(l);detail=r.locus(l['strain'],l['full_node'],l['region'],l['bgc_alias'])
            ap=ar.read(sources['architecture']['path'],ident,limit=1);al=ap['locus']
            if al['source_member_sha256']!=l['source_member_sha256']:raise ValueError('SOURCE_MEMBER_CONFLICT')
            def pages(kind):
                result=[];offset=0
                while True:
                    page=ar.read(sources['architecture']['path'],ident,kind,500,offset);result.extend(page['rows'])
                    if page['next_offset'] is None:return result
                    offset=page['next_offset']
            genes=pages('genes');features=pages('features')
            check=validate_detail(l,genes,detail['genes']);audit.append(check)
            for f in features:
                f['binding']=json.loads(f['binding_json']);f['holds']=f['binding'].get('holds',[])
            details[key]={'locus':l,'architecture_locus':al,'genes':genes,'features':features,'memberships':detail['memberships'],'run_cutoff_coverage':detail['run_cutoff_coverage'],'boundary':'Contig-edge/fragmentation state not supplied by this view. Region-overlapping CDS are boundary context, not biological absence.','rule':'Exact four-part identity and source-member hash equality; exact gene tag/protein multiset equality. Coordinates retained in whole-record 1-based inclusive frame.'}
            cached.write_text(json.dumps({'detail':details[key],'audit':check},separators=(',',':')))
            checksum.write_text(sha(cached)+'\n')
            if len(audit)==5:(out/'FIRST_FIVE_AUDIT.json').write_text(json.dumps({'status':'PASS','checks':audit,'limits':'Source binding and geometry checks; no scientific validation'},indent=2))
        data={'schema':'related_bgc_differences/1','population':'frozen45','summary':{'census_loci':len(loci),'admitted_pair_families_all_cutoffs':len(groups),'held_membership_rows':held,'shown_families':len(families),'shown_loci':len(details)},'sources':sources,'families':families,'details':details,'negative_cases':negatives,'sections':sections,'contract':{'sha256':profile['profile_sha256'],'member':profile['member'],'bundle':profile['bundle_version']},'holds':['Private candidate evidence; owner/catalog and scientific acceptance pending','Current44base and 46runs not joined','External/reference members lack complete admitted cohort identity and architecture; reference arrangement comparison held','No orthology or biological absence inference','No domain-manifest or section-completeness hold cleared']}
        (out/'view.json').write_text(json.dumps(data,separators=(',',':')))
        template=Path(__file__).with_name('related_view.html').read_text()
        payload=json.dumps(data,separators=(',',':')).replace('<','\\u003c')
        (out/'index.html').write_text(template.replace('__DATA__',payload))
        if not all(sha(s['path'])==s['sha256'] for s in sources.values()):raise ValueError('SOURCE_CHANGED_DURING_BUILD')
        (out/'SELF_AUDIT.json').write_text(json.dumps({'status':'PASS_SOURCE_BINDING','checks':audit,'source_hashes_rechecked':all(sha(s['path'])==s['sha256'] for s in sources.values()),'summary':data['summary'],'limits':data['holds']},indent=2))
        return data['summary']
    finally:r.close()
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('config');p.add_argument('output');a=p.parse_args();print(json.dumps(build(a.config,a.output),indent=2))
