"""Local derived view of existing owner evidence. No scans or database copies.

Requires tool_database_reader candidate dependency and explicitly hash-pinned
DKP/architecture reader files. Run using tools/build_enzyme_neighborhoods.py.
"""
from pathlib import Path
import argparse, collections, csv, hashlib, importlib.util, json, re, sys, time
from .tool_database_reader import inspect_tool_database
from .csv_safety import SafeDictWriter


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def identity(row):
    parts = [row.get(k) for k in ('strain', 'full_node', 'region', 'bgc_alias')]
    if not all(isinstance(x, str) and x.strip() and ' / ' not in x for x in parts):
        raise ValueError('FOUR_PART_IDENTITY_HOLD')
    value = ' / '.join(parts)
    if value != row.get('exact_identity'):
        raise ValueError('IDENTITY_CONFLICT_HOLD')
    return value


def pinned(entry):
    p = Path(entry['path']).resolve(strict=True)
    if sha(p) != entry['sha256']:
        raise ValueError('SOURCE_PIN_HOLD: ' + p.name)
    if any(Path(str(p) + s).exists() for s in ('-wal', '-shm', '-journal')):
        raise ValueError('LIVE_SOURCE_HOLD')
    return p


def reader(entry, name):
    p = pinned(entry)
    spec = importlib.util.spec_from_file_location(name, p)
    module = importlib.util.module_from_spec(spec)
    # Never write bytecode into evidence roots.
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def pages(fn):
    out, offset = [], 0
    while True:
        page = fn(offset)
        out.extend(page['rows'])
        nxt = page['next_offset']
        if nxt is None:
            if len(out) != page['total']:
                raise ValueError('PAGINATION_COUNT_HOLD')
            return out
        if nxt <= offset:
            raise ValueError('PAGINATION_PROGRESS_HOLD')
        offset = nxt


def gene_key(g):
    return (g.get('locus_tag'), g.get('start', g.get('cds_start')),
            g.get('end', g.get('cds_end')), g.get('strand'), g.get('protein_sha256'))


def project(locus, genes, context, domains, agenes, features, census):
    """Geometry/identity join only; never infer functional or orthologous links."""
    exact = identity(locus)
    by_census = {gene_key(g): g for g in census}
    by_arch = {gene_key(g): g for g in agenes if g['membership'] == 'EXACT_REGION'}
    if len(by_census) != len(census) or len({gene_key(g) for g in genes}) != len(genes):
        raise ValueError('DUPLICATE_GENE_HOLD')
    if set(by_census) != {gene_key(g) for g in genes} or set(by_arch) != set(by_census):
        raise ValueError('EXACT_ROSTER_CONFLICT_HOLD')
    if len(genes)+len(context)>2500 or len(features)>10000:raise ValueError('PARTITION_SIZE_HOLD')
    output = []
    for g in genes:
        g = dict(g, membership='EXACT_REGION')
        c, a = by_census[gene_key(g)], by_arch[gene_key(g)]
        g['census_raw'] = c
        g['architecture_raw'] = a
        g['annotation'] = a.get('product') or c.get('product') or g.get('product') or 'Unknown annotation'
        g['holds'] = [c['hold']] if c.get('hold') else []
        # Distinct parser projections are retained, never silently reconciled.
        g['annotation_projection_note'] = 'DKP product, census product and architecture text are separate raw projections.'
        g['domains'] = []
        output.append(g)
    known = {gene_key(g) for g in output}
    for g in context:
        if g['contig'] != locus['full_node']:
            raise ValueError('CONTEXT_CONTIG_CONFLICT_HOLD')
        if gene_key(g) not in known:
            if g['membership'] == 'EXACT_REGION':
                raise ValueError('EXACT_CONTEXT_ROSTER_HOLD')
            output.append(dict(g, annotation=g.get('product') or 'Owner-matched context; product unknown',
                               holds=['SPARSE_FLANK_CONTEXT_NOT_COMPLETE_GENE_CENSUS'], domains=[]))
            known.add(gene_key(g))
    unmatched = []
    for feature in features:
        f = dict(feature)
        for k in ('binding', 'classes', 'source_parts', 'source_feature_indices'):
            if k + '_json' in f:
                f[k] = json.loads(f.pop(k + '_json'))
        if f['contig'] != locus['full_node']:
            raise ValueError('DOMAIN_CONTIG_CONFLICT_HOLD')
        parents = f.get('binding', {}).get('parents', [])
        targets = [g for g in output if any(
            p.get('locus_tag') == g.get('locus_tag') and
            p.get('protein_sha256') and p.get('protein_sha256') == g.get('protein_sha256') and
            p.get('cds_start') == g['start'] and p.get('cds_end') == g['end'] and
            p.get('strand') == g.get('strand') for p in parents)]
        if len(targets) == 1 and not f.get('binding', {}).get('holds'):
            targets[0]['domains'].append(f)
        else:
            f['view_hold'] = 'DOMAIN_PARENT_UNBOUND_OR_AMBIGUOUS'
            unmatched.append(f)
    output.sort(key=lambda g: (g['start'], g['end'], g.get('locus_tag') or ''))
    for i, g in enumerate(output):
        if not isinstance(g['start'], int) or not isinstance(g['end'], int) or not 1 <= g['start'] <= g['end']:
            raise ValueError('COORDINATE_HOLD')
        g['display_order'] = i + 1
        g['exact_identity'] = exact
        # Signed gap to preceding displayed gene. Context gaps are explicitly sparse.
        g['gap_previous_bp'] = None if i == 0 else g['start'] - output[i-1]['end'] - 1
        g['gap_basis'] = 'PRECEDING_DISPLAYED_INTERVAL; NEGATIVE_MEANS_OVERLAP; FLANKS_SPARSE'
        g['distance_to_region_bp'] = (g['end']-locus['start'] if g['end'] < locus['start'] else
                                     g['start']-locus['end'] if g['start'] > locus['end'] else 0)
        if not g.get('strand') in (-1, 1):
            g['holds'].append('ORIENTATION_UNKNOWN')
    for g in output:
        g['domains'].sort(key=lambda f:(f['start'],f['end'],f['feature_order']))
        g['domain_state'] = 'OBSERVED_RECORDED' if g['domains'] else ('TESTED_NO_LINKED_FEATURE' if g['membership']=='EXACT_REGION' else 'NOT_AVAILABLE_IN_SPARSE_FLANK_VIEW')
    exact_genes = [g for g in output if g['membership'] == 'EXACT_REGION']
    signatures = []
    # Three consecutive exact-region genes around each source-owner CDS CDPS match.
    # These are coordinate-ordered annotation-group patterns, not orthology/synteny.
    for i, g in enumerate(exact_genes):
        if 'CDPS' in g.get('owner_term_groups', []) and 0 < i < len(exact_genes)-1:
            window = exact_genes[i-1:i+2]
            tokens = [','.join(sorted(x.get('owner_term_groups', []))) or 'UNCLASSIFIED' for x in window]
            orientations = [str(x.get('strand')) for x in window]
            signatures.append({'pattern': ' | '.join(t+' ['+s+']' for t,s in zip(tokens,orientations)),
                               'anchor':g.get('locus_tag'), 'genes':[x.get('locus_tag') for x in window],
                               'rule':'Three coordinate-ordered exact-region CDS; source owner term groups + raw strands; no reverse normalization or orthology inference.'})
    return {'locus':locus, 'exact_identity':exact, 'genes':output, 'unbound_features':unmatched,
            'dkp_domain_observations':domains, 'signatures':signatures,
            'denominators':{'exact_region_cds':len(genes), 'displayed_cds':len(output),
                            'sparse_flank_cds':len(output)-len(genes), 'architecture_features':len(features),
                            'linked_feature_observations':sum(len(g['domains']) for g in output),
                            'unbound_feature_observations':len(unmatched)},
            'holds':['OWNER_CANDIDATE_NOT_SCIENTIFIC_ACCEPTANCE', 'FLANK_CDS_AND_DOMAIN_COVERAGE_INCOMPLETE',
                     'ANNOTATION_RECURRENCE_NOT_ORTHOLOGY', 'MODEB_APPLICABILITY_ONLY_NOT_SECTION_COMPLETION']}


def write_json(path, value, root):
    path = Path(path)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('OUTPUT_ROOT_HOLD')
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')


def build(config, output, pilot=False):
    start = time.monotonic()
    cfg = json.loads(Path(config).read_text())
    allowed = Path(cfg['allowed_output_root']).resolve(strict=True)
    output = Path(output).resolve()
    if not output.is_relative_to(allowed):
        raise ValueError('ADDITIVE_OUTPUT_ROOT_HOLD')
    sources = cfg['sources']
    for entry in sources.values():
        entry['path'] = str((Path(config).resolve().parent / entry['path']).resolve())
    paths = {k:pinned(v) for k,v in sources.items()}
    dm = json.loads(paths['dkp_manifest'].read_text())
    am = json.loads(paths['architecture_manifest'].read_text())
    cm = json.loads(paths['census_manifest'].read_text())
    dom = json.loads(paths['domain_manifest'].read_text())
    contract = paths['current50_contract'].read_text()
    requirements = {int(n):text.strip() for n,text in re.findall(r'^\| (\d+) \| (.*?) \|$', contract, re.M)}
    if set(requirements) != set(range(1,51)):
        raise ValueError('CURRENT50_CONTRACT_SHAPE_HOLD')
    supplied = {1:'Exact identity, interval and protein roster; assembly binding retained in source manifests.',3:'Recorded boundary and explicit exact/sparse-context counts; no overmerge adjudication.',4:'Source annotation groups and gene overview only; no role adjudication.',18:'Displayed geometry, strands, domains and raw evidence; no named-match channels or V7 reconciliation.',25:'Annotation-pattern comparison only; no orthology or genomic conservation claim.',28:'File/hash/rule provenance only; no 14-stream or predecessor reconciliation.',31:'Exact CDS census and sparse owner-matched flank subset; incomplete boundary census held.',32:'Source feature observations and recorded parent links; no module programming inference.',44:'Candidate-locus annotation recurrence denominator only; not biological prevalence.',50:'Exact roster and geometry; sparse context and unsupported named-match channels held.'}
    mapping = [{'section':n,'requirement':requirements[n],'applicability':'PARTIAL_RECORDED_CONTEXT' if n in supplied else 'NOT_SUPPLIED','provided_and_limit':supplied.get(n,'No evidence supplied by this widget.'),'completion':'NOT_ASSESSED','contract_sha256':sources['current50_contract']['sha256']} for n in range(1,51)]
    if not (dm['binding']['census_database_sha256'] == am['binding']['census_sha256'] == cm['database_sha256']):
        raise ValueError('POPULATION_JOIN_HOLD')
    if am['storage_projection']['dependency_sha256'] != dom['database_sha256']:
        raise ValueError('DOMAIN_DEPENDENCY_HOLD')
    for label,m in [('dkp',dm),('architecture',am),('census',cm),('domain',dom)]:
        db = paths[label+'_database']
        if db.name != m['database'] or sha(db) != m['database_sha256'] or db.stat().st_size != m['bytes']:
            raise ValueError('DATABASE_MANIFEST_HOLD')
    dr = reader(sources['dkp_reader'], 'neighborhood_dkp_reader')
    ar = reader(sources['architecture_reader'], 'neighborhood_arch_reader')
    ddb, adb = paths['dkp_database'], paths['architecture_database']
    pin = sources['dkp_manifest']['sha256']
    loci = pages(lambda off:dr.read(ddb,pin,limit=500,offset=off))
    for l in loci:identity(l)
    if len({identity(l) for l in loci})!=len(loci):raise ValueError('DUPLICATE_LOCUS_HOLD')
    candidates = [l for l in loci if l['call_state'] == 'OWNER_DKP_CDPS_CANDIDATE']
    negative = [l for l in loci if l['call_state'] == 'TESTED_NO_OWNER_CALL'][:5]
    # Representative pilot selection by source state, boundary and size, without scans.
    chosen = []
    for pred in [lambda l:l['owner_call']['bgc_context']=='recovered_outside_antiSMASH_boundary',
                 lambda l:l['edge_status']=='Edge', lambda l:l['owner_call']['cdo_adjacent']=='yes',
                 lambda l:l['owner_call']['bgc_context']=='antiSMASH_region', lambda l:True]:
        for l in sorted(candidates,key=lambda l:-l['region_nt']):
            if l not in chosen and pred(l):chosen.append(l);break
    if len(chosen)!=5:raise ValueError('FIVE_RECORD_PILOT_HOLD')
    selected = chosen + negative[:1] if pilot else candidates + negative
    if len(selected)>int(cfg.get('max_loci',100)):raise ValueError('COHORT_SIZE_HOLD')
    if not pilot:
        if sha(cfg['pilot_receipt']) != cfg.get('pilot_receipt_sha256'):raise ValueError('PILOT_RECEIPT_PIN_HOLD')
        receipt = json.loads(Path(cfg['pilot_receipt']).read_text())
        if receipt['status'] != 'PASS' or receipt['sources'] != sources:
            raise ValueError('PILOT_BINDING_HOLD')
    binding={'population':cfg['population'],'sources':sources,'builder_sha256':sha(__file__),'template_sha256':sha(Path(__file__).with_name('enzyme_neighborhoods.html')),'pilot':pilot,'selected':[identity(l) for l in selected]}
    output.mkdir(parents=True,exist_ok=True)
    binding_path=output/'BUILD_BINDING.json'
    if binding_path.exists():
        if json.loads(binding_path.read_text()) != binding:raise ValueError('RESUME_BINDING_HOLD')
    else:
        if any(output.iterdir()):raise ValueError('UNBOUND_OUTPUT_DIRECTORY_HOLD')
        write_json(binding_path,binding,allowed)
    final_manifest=output/'SOURCE_MANIFEST.json'
    if final_manifest.exists():
        completed=json.loads(final_manifest.read_text())
        for relative,digest in completed['outputs'].items():
            target=(output/relative).resolve()
            if not target.is_relative_to(output) or sha(target)!=digest:raise ValueError('COMPLETED_OUTPUT_CONTENT_HOLD')
        return json.loads((output/'BUILD_AUDIT.json').read_text())
    partitions=output/'partitions'
    if not partitions.resolve().is_relative_to(allowed):raise ValueError('OUTPUT_ROOT_HOLD')
    partitions.mkdir(exist_ok=True)
    records=[]
    for l in selected:
        if time.monotonic()-start>int(cfg.get('max_runtime_seconds',1800)):raise ValueError('RUNTIME_BUDGET_HOLD_RESUME_PARTITIONS')
        eid=identity(l)
        token='__'.join(re.sub(r'[^A-Za-z0-9_.-]','_',v) for v in eid.split(' / '))
        part=partitions/(token+'.json')
        seal=partitions/(token+'.receipt.json')
        if part.exists():
            if not seal.exists() or json.loads(seal.read_text()) != {'sha256':sha(part),'exact_identity':eid,'binding_sha256':sha(binding_path)}:
                raise ValueError('PARTITION_CONTENT_HOLD')
            cached=json.loads(part.read_text())
            if cached['exact_identity']!=eid:raise ValueError('PARTITION_IDENTITY_HOLD')
            records.append(cached);print('resumed',len(records),'of',len(selected),flush=True);continue
        details={kind:pages(lambda off,k=kind:dr.read(ddb,pin,eid,k,100,off,include_raw=True))
                 for kind in ('genes','cds_context','domains')}
        arch={kind:pages(lambda off,k=kind:ar.read(adb,eid,k,100,off,include_qualifiers=False))
              for kind in ('genes','features')}
        census=[];offset=0
        while True:
            page=inspect_tool_database(paths['census_manifest'].parent,paths['census_manifest'].name,
                adapter='gene-census-v1',identity=eid.split(' / '),limit=500,offset=offset,
                expected_manifest_sha256=sources['census_manifest']['sha256'])['results']
            census.extend(page['records'])
            if page['next_offset'] is None:break
            offset=page['next_offset']
        result=project(l,details['genes'],details['cds_context'],details['domains'],arch['genes'],arch['features'],census)
        write_json(part,result,allowed)
        write_json(seal,{'sha256':sha(part),'exact_identity':eid,'binding_sha256':sha(binding_path)},allowed)
        records.append(result)
        print('projected',len(records),'of',len(selected),flush=True)
    for entry in sources.values():pinned(entry)
    recurrence=collections.defaultdict(set)
    for r in records:
        if r['locus']['call_state']=='OWNER_DKP_CDPS_CANDIDATE':
            for s in r['signatures']:recurrence[s['pattern']].add(r['exact_identity'])
    data={'schema':'enzyme_neighborhood_view/1','population':cfg['population'],
          'claim_ceiling':dm['binding']['claim_ceiling'], 'sources':sources,
          'rules':{'owner':'mamey.dkp_cdps.scan_dkp_cdps','terms':dm['binding']['terms'],
                   'owner_sha256':dm['binding']['owner_sha256'], 'flank_bp':dm['binding']['flank_bp'],
                   'coordinates':'1-based inclusive whole-record coordinates',
                   'domain_link':'Recorded source parent requires matching locus tag, protein hash, CDS start/end and strand; no name-only joining',
                   'recurrence':'Triplet of source owner term groups and strands around an exact-region CDS CDPS term match; one count per locus; no orthology claim',
                   'section_mapping':'Verified current50 requirement text; applicability only. Census .411 profile remains distinct from .412 current contract.'},
          'denominators':{'source_loci':len(loci),'source_candidate_loci':len(candidates),
                          'source_no_call_loci':len(loci)-len(candidates),'loaded_loci':len(records),
                          'recurrence_loci_with_eligible_triplet':sum(bool(r['signatures']) for r in records if r['locus']['call_state']=='OWNER_DKP_CDPS_CANDIDATE')},
          'section_mapping':mapping,'records':records,'recurrence':[{'pattern':k,'count_loci':len(v),'identities':sorted(v)}
                       for k,v in sorted(recurrence.items(),key=lambda kv:(-len(kv[1]),kv[0]))]}
    write_json(output/'view_data.json',data,allowed)
    template=Path(__file__).with_name('enzyme_neighborhoods.html').read_text()
    safe=json.dumps(data,ensure_ascii=False,allow_nan=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    if len(safe.encode())>32*1024*1024:raise ValueError('VIEW_SIZE_HOLD')
    target=output/'explorer.html'
    if not target.resolve().is_relative_to(allowed):raise ValueError('OUTPUT_ROOT_HOLD')
    target.write_text(template.replace('__VIEW_DATA__',safe))
    # Separate evidence-index sidecars use the existing gene-first seam. BOUND
    # means source-bound observation, never function or section acceptance.
    from .mode_b.gene_first_explore import load_evidence_index
    index_checks=[]
    for r in records:
        l=r['locus'];eid=r['exact_identity']
        token='__'.join(re.sub(r'[^A-Za-z0-9_.-]','_',v) for v in eid.split(' / '))
        ip=partitions/(token+'.evidence.tsv')
        if not ip.resolve().is_relative_to(allowed):raise ValueError('OUTPUT_ROOT_HOLD')
        fields=['channel','strain','full_node','region','bgc_alias','gene','evidence_state','source_locator','source_sha256','note','exact_identity']
        with ip.open('w',newline='') as f:
            w=SafeDictWriter(f,fieldnames=fields,delimiter='\t');w.writeheader()
            w.writerow(dict(channel='cohort',**{k:l[k] for k in ('strain','full_node','region','bgc_alias')},gene='',evidence_state='BOUND',source_locator='evidence://enzyme-neighborhoods/'+token+'.json',source_sha256=sha(partitions/(token+'.json')),note='Source-bound annotation context only; not orthology; raw candidate/no-call state in referenced partition; incomplete flank census.',exact_identity=eid))
        obs,_=load_evidence_index(ip,l,{g['locus_tag'] for g in r['genes'] if g.get('locus_tag')})
        if len(obs)!=1:raise ValueError('EVIDENCE_INDEX_COMPATIBILITY_HOLD')
        index_checks.append(eid)
    write_json(output/'CURRENT50_APPLICABILITY.json',mapping,allowed)
    audit={'status':'PASS','evidence_index_validated_loci':index_checks,'scope':'Five representative candidates and one real no-call' if pilot else 'Full candidate projection and five real no-call controls',
           'sources':sources,'checks':[{'exact_identity':r['exact_identity'],'counts':r['denominators'],
                       'status':'EXACT_CENSUS_ARCHITECTURE_ROSTER_PARITY_AND_PARENT_JOIN_PASS'} for r in records],
           'elapsed_seconds':time.monotonic()-start,'denominators':data['denominators']}
    write_json(output/'BUILD_AUDIT.json',audit,allowed)
    write_json(output/'SOURCE_MANIFEST.json',{'sources':sources,'rules':data['rules'],'population':cfg['population'],
                'outputs':{p.relative_to(output).as_posix():sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p.name!='SOURCE_MANIFEST.json'}},allowed)
    return audit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',required=True);p.add_argument('--out',required=True);p.add_argument('--pilot',action='store_true')
    a=p.parse_args()
    try:
        result=build(a.config,a.out,a.pilot)
        print(json.dumps({'status':'EXTRACTION_QC_PASS_CANDIDATE','denominators':result['denominators']}))
    except FileNotFoundError as e:
        p.exit(2,json.dumps({'status':'MISSING_SOURCE','detail':str(e)})+'\n')
    except json.JSONDecodeError as e:
        p.exit(2,json.dumps({'status':'PARSE_FAILED','detail':str(e)})+'\n')
    except (ValueError,OSError) as e:
        p.exit(2,json.dumps({'status':'HELD','detail':str(e)})+'\n')
