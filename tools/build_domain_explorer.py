"""Read-only projection of the existing architecture owner; no biological scans.

CLI requires explicit source/reader/output paths. Only derived JSON/HTML is written.
"""
from pathlib import Path
import argparse, collections, hashlib, importlib.util, json, sqlite3

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''): h.update(block)
    return h.hexdigest()

def identity(row):
    parts=[row[x] for x in ('strain','full_node','region','bgc_alias')]
    if not all(isinstance(x,str) and x.strip() for x in parts): raise ValueError('IDENTITY_HOLD')
    if row['exact_identity']!=' / '.join(parts): raise ValueError('IDENTITY_CONFLICT')
    return row['exact_identity']

def arrangements(features, strand):
    """Exact coordinate/label duplicates collapse; unresolved overlaps hold order."""
    unique={ (f['start'],f['end'],f['domain']):f for f in features }
    fs=sorted(unique.values(),key=lambda f:(f['start'],f['end'],f['domain']))
    labels=sorted({f['domain'] for f in fs})
    holds=[]
    if strand not in (-1,1): holds.append('STRAND_UNBOUND')
    if any(b['start']<=a['end'] for a,b in zip(fs,fs[1:])): holds.append('OVERLAPPING_DOMAIN_INTERVALS_ORDER_HELD')
    ordered=[f['domain'] for f in (fs if strand==1 else fs[::-1])]
    return labels,ordered,holds,len(features)-len(fs)

def parent_matches(feature, parent, gene):
    return (feature['strain']==gene['strain'] and feature['contig']==gene['contig']
            and parent['locus_tag']==gene['tag'] and parent['protein_sha256']==gene['protein_sha256']
            and gene['start']==parent['cds_start'] and gene['end']==parent['cds_end']
            and gene['strand']==parent['strand'] and feature['strand']==gene['strand'])

def build(database, reader, output, template, pilot=False, population=None, expected_census=None):
    database=Path(database).resolve(); reader=Path(reader).resolve(); output=Path(output).resolve()
    manifest_path=database.parent/'RELEASE_MANIFEST.json'; manifest=json.loads(manifest_path.read_text())
    if expected_census is None or manifest['binding']['census_sha256']!=expected_census: raise ValueError('POPULATION_BINDING_HOLD')
    if sha(reader)!=manifest['reader_sha256']: raise ValueError('READER_MANIFEST_HOLD')
    spec=importlib.util.spec_from_file_location('architecture_owner',reader); owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
    # Reuse the owner admission gate before a compact SQL projection, avoiding
    # repeated full-file hashing for every gene or locus detail page.
    admitted=owner.read(database,limit=1)
    if not population or not population.strip():raise ValueError('POPULATION_LABEL_REQUIRED')
    source_hash=sha(database)
    resume_binding=dict(database_sha256=source_hash,reader_sha256=sha(reader),manifest_sha256=sha(manifest_path),builder_sha256=sha(__file__),template_sha256=sha(template),population=population,expected_census=expected_census,pilot=pilot)
    if output.exists() and any(output.iterdir()):
        receipt=json.loads((output/'SOURCE_MANIFEST.json').read_text())
        if receipt.get('resume_binding')!=resume_binding: raise ValueError('RESUME_INPUT_HOLD_USE_NEW_OUTPUT')
        if sha(output/'data.json')!=receipt['data_sha256'] or sha(output/'index.html')!=receipt['html_sha256']: raise ValueError('RESUME_OUTPUT_TAMPER')
        return json.loads((output/'data.json').read_text())
    c=sqlite3.connect(database.as_uri()+'?mode=ro&immutable=1',uri=True);c.row_factory=sqlite3.Row
    if c.execute('pragma foreign_key_check').fetchall():raise ValueError('FOREIGN_KEY_HOLD')
    if c.execute('select count(*) from gene g left join locus l using(locus_key) where l.locus_key is null').fetchone()[0]:raise ValueError('ORPHAN_GENE_HOLD')
    loci=[dict(r) for r in c.execute('select * from locus order by exact_identity')]
    for l in loci: identity(l); l['classes']=json.loads(l.pop('products_json'));l['genus']=None
    if pilot:
        # Five different source strains, real records only.
        chosen=[];seen=set()
        for l in loci:
            if l['strain'] not in seen: chosen.append(l);seen.add(l['strain'])
            if len(chosen)==5:break
        loci=chosen
    keys={l['locus_key']:i for i,l in enumerate(loci)}
    genes={}; excluded=collections.Counter();gene_occurrences=0
    for raw in c.execute('select g.*,l.strain,l.full_node from gene g join locus l using(locus_key)'):
        g=dict(raw)
        if g['locus_key'] not in keys:continue
        if g['membership']!='EXACT_REGION':excluded['boundary_context_gene_occurrences']+=1;continue
        gene_occurrences+=1
        key=(g['strain'],g['full_node'],g['locus_tag'],g['start'],g['end'],g['strand'],g['protein_sha256'])
        if key not in genes:genes[key]=dict(strain=g['strain'],contig=g['full_node'],tag=g['locus_tag'],start=g['start'],end=g['end'],strand=g['strand'],protein_sha256=g['protein_sha256'],loci=set(),features=collections.defaultdict(list))
        genes[key]['loci'].add(keys[g['locus_key']])
    lookup=collections.defaultdict(list)
    for key,g in genes.items():lookup[(g['strain'],g['contig'],g['tag'],g['protein_sha256'])].append(g)
    versions=collections.Counter(); raw_feature_count=0; held_features=[]
    for row in c.execute('select * from feature order by strain,feature_order'):
        f=dict(row)
        if f['feature_type'] not in ('aSDomain','PFAM_domain'):excluded['other_feature_surfaces']+=1;continue
        binding=json.loads(f['binding_json'])
        if binding['state']!='SOURCE_PROTEIN_AND_GEOMETRY_BOUND' or binding['holds'] or len(binding['parents'])!=1:
            excluded['unbound_or_conflicting_domain_features']+=1
            held_features.append({k:f[k] for k in ('strain','contig','feature_order','feature_type','domain','start','end','source_member','source_member_sha256','source_feature_indices_json','binding_json')})
            continue
        parent=binding['parents'][0]
        matches=lookup.get((f['strain'],f['contig'],parent['locus_tag'],parent['protein_sha256']),[])
        matches=[g for g in matches if parent_matches(f,parent,g)]
        if len(matches)!=1:excluded['outside_exact_population_or_parent_conflict']+=1;continue
        if not f['domain'] or f['frame']!='WHOLE_RECORD_1_BASED_INCLUSIVE':excluded['label_or_frame_hold']+=1;continue
        if not matches[0]['start']<=f['start']<=f['end']<=matches[0]['end']:excluded['containment_hold']+=1;continue
        raw_feature_count+=1;versions[(f['feature_type'],f['database_name'])]+=1
        matches[0]['features'][f['feature_type']].append({k:f[k] for k in ('feature_order','start','end','strand','domain','database_name','bitscore','evalue_raw','source_member','source_member_sha256','source_feature_indices_json','source_location','qualifiers_sha256')})
    patterns={};evidence=[];coverage={ch:set() for ch in ('aSDomain','PFAM_domain')};missing=collections.Counter()
    for g in genes.values():
        for channel in coverage:
            fs=g['features'].get(channel,[])
            if not fs:missing[channel]+=1;continue
            coverage[channel].update(g['loci'])
            labels,ordered,holds,duplicates=arrangements(fs,g['strand'])
            excluded['exact_duplicate_domain_records']+=duplicates
            if len(fs)<2:continue
            item={k:v for k,v in g.items() if k!='features'};item['loci']=sorted(item['loci']);item.update(channel=channel,features=fs,holds=holds,combination=labels,ordered=ordered)
            ei=len(evidence);evidence.append(item)
            for mode,pattern in [('combination',labels),('ordered',ordered)]:
                if mode=='ordered' and holds:excluded['protein_channel_order_holds']+=1;continue
                if len(pattern)<2:continue
                pk=(channel,mode,tuple(pattern))
                if pk not in patterns:patterns[pk]=dict(channel=channel,mode=mode,labels=pattern,evidence=[])
                patterns[pk]['evidence'].append(ei)
    profile=dict(c.execute('select * from section_profile').fetchone())
    if hashlib.sha256(profile['contract_text'].encode()).hexdigest()!=profile['profile_sha256']:raise ValueError('CONTRACT_HASH_HOLD')
    section_rows=[dict(r) for r in c.execute('select * from section_relevance where section_number in (24,32,44,50) order by section_number')]
    if len(section_rows)!=4 or any(r['profile_sha256']!=profile['profile_sha256'] or r['requirement'] not in profile['contract_text'] for r in section_rows):raise ValueError('SECTION_MAPPING_HOLD')
    sources=[dict(r) for r in c.execute('select * from source order by strain')]
    c.close()
    if source_hash!=sha(database):raise ValueError('SOURCE_CHANGED_DURING_BUILD')
    data=dict(schema='observed_domain_explorer/1',population=population+(' / five-strain pilot subset' if pilot else ''),loci=loci,evidence=evidence,patterns=list(patterns.values()),coverage={k:sorted(v) for k,v in coverage.items()},sources=sources,source=dict(database=str(database),database_sha256=source_hash,manifest_sha256=sha(manifest_path),reader=str(reader),reader_sha256=sha(reader),status=manifest['status']),counts=dict(loci=len(loci),strains=len({l['strain'] for l in loci}),physical_genes=len(genes),gene_occurrences=gene_occurrences,overlapping_gene_memberships=gene_occurrences-len(genes),admitted_features=raw_feature_count,missing_channel_genes=dict(missing),exclusions=dict(excluded)),annotation_databases=[dict(channel=k[0],raw_database=k[1],features=v) for k,v in sorted(versions.items())],contract=dict(profile_sha256=profile['profile_sha256'],bundle_version=profile['bundle_version'],member=profile['member'],mapping='No exact50 section mapping claimed by this explorer'),holds=['Genus taxonomy unbound; genus stratification disabled','Annotation versions and detection sensitivity can confound rarity','No biological absence inference from missing annotation','Rarity is not novelty; no novelty score','Candidate evidence only; scientific and release acceptance pending'])
    output.mkdir(parents=True,exist_ok=True)
    data['held_features']=held_features
    data['contract']['mapping']='Verified against source-bound exact50 contract; partial supporting evidence only'
    data['contract']['sections']=[dict(section=r['section_number'],requirement=r['requirement'],owner_relation=r['relation'],widget_relation='PARTIAL_SUPPORT_ONLY',limits='Within-protein annotation patterns and prevalence only; not homology/comparator distance, module chemistry, a complete gene table or section completion') for r in section_rows]
    data['observation_states']={'OBSERVED':'At least one admitted annotation in this channel','NO_ADMITTED_ANNOTATION_UNKNOWN':'No admitted annotation; not a tested negative','NOT_RUN':'No new scan performed by this builder','UNBOUND':'Source binding holds retained in held_features','PARSE_FAILED':'Raises; never converted to zero','TESTED_NO_CALL':'Not supplied by this source; never inferred'}
    (output/'data.json').write_text(json.dumps(data,separators=(',',':')))
    embedded=json.dumps(data,separators=(',',':')).replace('<','\\u003c')
    (output/'index.html').write_text(Path(template).read_text().replace('__DATA__',embedded))
    (output/'SOURCE_MANIFEST.json').write_text(json.dumps(dict(resume_binding=resume_binding,source=data['source'],population=data['population'],counts=data['counts'],builder_sha256=sha(__file__),template_sha256=sha(template),data_sha256=sha(output/'data.json'),html_sha256=sha(output/'index.html')),indent=2))
    return data

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--database',required=True);p.add_argument('--reader',required=True);p.add_argument('--output',required=True);p.add_argument('--population',required=True);p.add_argument('--expected-census',required=True);p.add_argument('--template',default=str(Path(__file__).with_name('explorer_template.html')));p.add_argument('--pilot',action='store_true');a=p.parse_args()
    d=build(a.database,a.reader,a.output,a.template,a.pilot,a.population,a.expected_census);print(json.dumps(d['counts'],indent=2))
