"""Index saved Mamey structured exports. No original antiSMASH parser or new scan."""
import argparse,collections,hashlib,json,re,sqlite3,zipfile,zlib,time,csv,io
from pathlib import Path
from .mode_b.gene_first_store_bridge import read_round_fasta
from .exact_identity import exact_locus_display
from . import tool_database_reader as owner
from .csv_safety import SafeDictWriter
TABLES=('modules','motifs','hmm','ripp_motifs','rrefinder')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def js(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def rawhash(x):return hashlib.sha256(js(x).encode()).hexdigest()
def ro(p):
 c=sqlite3.connect(Path(p).resolve().as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;return c

def load_export(p,expected):
 if Path(p).stat().st_size>67108864:raise ValueError('SOURCE_EXPORT_SIZE_LIMIT')
 if sha(p)!=expected:raise ValueError('EXPORT_HASH_DRIFT')
 x=json.loads(p.read_text())
 if x.get('schema_version')!='antismash_structured_tables_v2':raise ValueError('UNSUPPORTED_EXPORT_SCHEMA')
 if sum(x.get('counts',{}).get(t,0) for t in TABLES)>100000:raise ValueError('PACKAGE_ROW_LIMIT')
 for t in TABLES:
  if not isinstance(x.get(t),list) or len(x[t])!=x.get('counts',{}).get(t):raise ValueError('TABLE_COUNT_OR_TYPE_HOLD')
  ids=[r.get('row_id') for r in x[t]]
  if len(ids)!=len(set(ids)) or any(not i for i in ids):raise ValueError('DUPLICATE_OR_MISSING_ROW_ID')
 return x

def checksum_receipt(folder,paths):
 cf=folder/'checksums_sha256.txt';entries={};conflict=set()
 if cf.exists():
  for line in cf.read_text().splitlines():
   match=re.fullmatch(r'([0-9a-f]{64})\s+\*?(.+)',line)
   if match:
    h,n=match.groups()
    if n in entries and entries[n]!=h:conflict.add(n)
    entries[n]=h
 rows=[]
 for p in paths:
  exists=p.is_file();actual=sha(p) if exists else None;expected=entries.get(p.name);status='MISSING_INPUT' if not exists else 'CONSUMED_FILE_CHECKSUM_MATCH' if expected==actual and p.name not in conflict else 'CHECKSUM_CONFLICT' if expected else 'HASH_CAPTURED_NOT_LISTED_IN_PACKAGE_CHECKSUMS'
  rows.append({'path':str(p),'sha256':actual,'expected_sha256':expected,'state':status})
 return {'checksum_file_sha256':sha(cf) if cf.exists() else None,'files':rows,'scope':'Only consumed files checked; not whole package acceptance'}

def base_index(base):
 loci={};sources={r['strain']:dict(r) for r in base.execute('SELECT * FROM source')}
 for l in base.execute('SELECT * FROM locus'):
  a=json.loads(zlib.decompress(l['annotations_zlib']))['structured_comment']['antiSMASH-Data'];d=dict(l);d.pop('annotations_zlib');d['orig_start']=int(a['Orig. start']);d['orig_end']=int(a['Orig. end']);d['genes']=[dict(r) for r in base.execute('SELECT locus_tag,protein_sha256,cds_start,cds_end,strand,gene_order FROM gene WHERE locus_key=?',(l['locus_key'],))];d['features']=[]
  for f in base.execute('SELECT * FROM feature WHERE locus_key=?',(l['locus_key'],)):
   q=json.loads(zlib.decompress(f['source_qualifiers_zlib']));parts=json.loads(f['parts_json']);d['features'].append({'feature_order':f['feature_order'],'feature_type':f['feature_type'],'start':min(p['start'] for p in parts)+d['orig_start']+1,'end':max(p['end'] for p in parts)+d['orig_start'],'qualifier_hash':rawhash(q),'tags':json.loads(f['explicit_gene_tags_json']),'state':f['binding_state']})
  loci[l['exact_identity']]=d
 return loci,sources

def package_data(row,loci,sources,archive_cache):
 mp=Path(row['manifest']);folder=mp.parent
 if sha(mp)!=row['manifest_sha256']:raise ValueError('MANIFEST_DRIFT')
 m=json.loads(mp.read_text());sp=Path(row['structured_path']);x=load_export(sp,row['structured_sha256']);strain=m['strain_id'];prefix=sp.name.removesuffix('_3_antismash_structured.json');gp=folder/(prefix+'_gene_context.jsonl');fp=folder/(prefix+'_proteins.faa');ep=folder/(prefix+'_AntiSMASH_Evidence_Parse.json');checks=checksum_receipt(folder,[mp,sp,gp,fp,ep]);filebad=any(r['state'] in ['MISSING_INPUT','CHECKSUM_CONFLICT'] for r in checks['files'])
 contexts={}
 if gp.is_file():
  for line in gp.read_text().splitlines():
   r=json.loads(line)
   if 'bgc_id' in r:
    if r['bgc_id'] in contexts:raise ValueError('DUPLICATE_GENE_CONTEXT_LOCUS')
    contexts[r['bgc_id']]=r.get('cds',[])
 proteins={};duplicate_headers=False
 if fp.is_file():
  headers=[l[1:].strip() for l in fp.read_text().splitlines() if l.startswith('>')];duplicate_headers=len(headers)!=len(set(headers))
  for header,h in read_round_fasta(fp).items():
   match=re.fullmatch(r'(\S+) bgc=(\S+)',header)
   if match:proteins[(match[2],match[1])]=h
 source=sources.get(strain);archive={'state':'BASE_SOURCE_STRAIN_UNBOUND','json_members':[]};assembly_ok=False
 if source:
  path=Path(source['original_locator']);key=source['source_sha256']
  if key not in archive_cache:
   a={'path':str(path),'expected_sha256':key,'state':'SOURCE_ARCHIVE_UNAVAILABLE','json_members':[]}
   if path.is_file():
    actual=sha(path);a['actual_sha256']=actual;a['state']='ARCHIVE_HASH_VERIFIED' if actual==key else 'ARCHIVE_HASH_CONFLICT'
    if actual==key:
     with zipfile.ZipFile(path) as z:a['json_members']=[{'member':n.filename,'bytes':n.file_size,'crc32':n.CRC,'state':'MEMBER_PRESENT_NOT_PARSED_IN_THIS_LANE'} for n in z.infolist() if n.filename.lower().endswith('.json')]
   archive_cache[key]=a
  archive=archive_cache[key];assembly_ok=m.get('input_zip_sha256')==source['source_sha256'] and archive['state']=='ARCHIVE_HASH_VERIFIED'
 parse=json.loads(ep.read_text()) if ep.is_file() else {};boundloci={};locusrows=[]
 for b in m.get('bgcs',[]):
  alias=b.get('bgc_id');node=b.get('contig');region=b.get('antismash_region');identity=None
  try:identity=exact_locus_display(strain,node,region,alias)
  except (ValueError,TypeError):pass
  bl=loci.get(identity);holds=[];gs=contexts.get(alias,[]);package_genes=[]
  for g in gs:package_genes.append((g.get('locus_tag'),g.get('start'),g.get('end'),g.get('strand'),proteins.get((alias,g.get('locus_tag')))))
  if not identity:holds.append('COMPLETE_IDENTITY_UNAVAILABLE')
  if not bl:holds.append('LOCUS_NOT_IN_FROZEN_BASE')
  if not assembly_ok:holds.append('ASSEMBLY_SOURCE_HASH_UNBOUND_OR_CONFLICT')
  if filebad:holds.append('CONSUMED_INPUT_CHECKSUM_HOLD')
  if duplicate_headers:holds.append('FASTA_DUPLICATE_HEADER_HOLD')
  if bl:
   if b.get('start')!=bl['orig_start'] or b.get('end')!=bl['orig_end']:holds.append('REGION_GEOMETRY_CONFLICT')
   expected={(g['locus_tag'],g['cds_start'],g['cds_end'],g['strand'],g['protein_sha256']) for g in bl['genes']}
   if set(package_genes)!=expected or len(package_genes)!=len(expected):holds.append('EXACT_GENE_ROSTER_OR_PROTEIN_CONFLICT')
  lr={'package':row['package'],'strain':strain,'full_node':node,'region':region,'bgc_alias':alias,'exact_identity':identity,'base_locus_key':bl['locus_key'] if bl else None,'package_start':b.get('start'),'package_end':b.get('end'),'base_start':bl['orig_start'] if bl else None,'base_end':bl['orig_end'] if bl else None,'package_gene_count':len(package_genes),'base_gene_count':len(bl['genes']) if bl else None,'package_roster_sha256':rawhash(sorted(package_genes,key=str)),'holds':holds,'state':'FULL_SOURCE_LOCUS_ROSTER_PROTEIN_BOUND' if not holds else 'HELD_PACKAGE_LOCUS_PRESERVED'}
  locusrows.append(lr);boundloci[alias]=(lr,bl,gs)
 observations=[]
 for t in TABLES:
  for ordinal,r in enumerate(x[t]):
   pair=boundloci.get(r.get('bgc_id'));lr,bl,gs=pair if pair else (None,None,[]);holds=list(lr['holds']) if lr else ['UNMAPPED_PACKAGE_LOCUS'];tags=[]
   if r.get('locus_tag'):tags=[r['locus_tag']]
   q={}
   for key in ['detail_json','qualifiers_json']:
    if r.get(key):
     try:q=json.loads(r[key])
     except (ValueError,TypeError):holds.append('QUALIFIER_JSON_PARSE_HOLD')
   if r.get('feature_type')=='aSModule':tags=q.get('locus_tags',tags)
   if not tags:holds.append('EXPLICIT_GENE_LINK_MISSING')
   if r.get('mapping_status')!='MAPPED':holds.append('SOURCE_MAPPING_NOT_MAPPED')
   if lr and r.get('contig') and r['contig']!=lr['full_node']:holds.append('ROW_CONTIG_CONFLICT')
   genehashes=[]
   for tag in tags:
    found=[g for g in (bl['genes'] if bl else []) if g['locus_tag']==tag]
    h=proteins.get((r.get('bgc_id'),tag));genehashes.append({'gene':tag,'package_protein_sha256':h,'base_protein_sha256':found[0]['protein_sha256'] if len(found)==1 else None})
    if len(found)!=1 or not h or h!=found[0]['protein_sha256']:holds.append('GENE_PROTEIN_LINK_UNBOUND')
   matches=[]
   if bl and q and assembly_ok:
    matches=[f['feature_order'] for f in bl['features'] if f['feature_type']==r.get('feature_type') and f['start']==r.get('start') and f['end']==r.get('end') and f['qualifier_hash']==rawhash(q) and set(f['tags'])==set(tags)]
   if bl and any(f['feature_order'] in matches and f['state']!='SOURCE_SEQUENCE_AND_GEOMETRY_BOUND' for f in bl['features']):holds.append('BASE_FEATURE_BINDING_HELD')
   duplicate='EXACT_BASE_FEATURE_PROVENANCE_MATCH' if len(matches)==1 and not holds else 'CANDIDATE_BASE_FEATURE_MATCH_HELD' if matches else 'NO_EXACT_BASE_FEATURE_MATCH_NOT_NOVELTY'
   compatible=t in ['modules','hmm','rrefinder'] and (t!='modules' or r.get('feature_type') in ['aSDomain','aSModule'])
   channel='domain' if compatible else 'UNSUPPORTED_MOTIF_OR_PREDICTION_KIND'
   state='BOUND' if compatible and not holds else 'UNBOUND'
   if not compatible:holds.append('NO_COMPATIBLE_GENE_FIRST_CHANNEL')
   observations.append({'table':t,'ordinal':ordinal,'row_id':r['row_id'],'locus':lr,'tags':tags,'gene_hashes':genehashes,'holds':sorted(set(holds)),'state':state,'channel':channel,'duplicate_state':duplicate,'base_feature_orders':matches,'raw':r,'raw_sha256':rawhash(r)})
 meta={'package':row['package'],'strain':strain,'manifest_sha256':row['manifest_sha256'],'structured_sha256':row['structured_sha256'],'structured_locator':row['package']+'/package/'+sp.name,'schema':x['schema_version'],'version':x.get('antismash_version'),'bundle':m.get('bundle_version'),'engine':m.get('workflow_version'),'counts':x['counts'],'table_states':{t:'OBSERVED_ROWS' if x[t] else 'EXPORTED_EMPTY_NOT_BIOLOGICAL_ABSENCE' for t in TABLES},'source_schema_counts':dict(collections.Counter(r.get('source_schema','') for t in TABLES for r in x[t])),'parse_errors':x.get('parse_errors'),'json_mode':parse.get('json_mode'),'checksums':checks,'original_archive':archive,'input_zip_sha256_claim':m.get('input_zip_sha256'),'origin':'MAMEY_JSON_EXPORT_NOT_ORIGINAL_ANTISMASH_RESULTS_JSON'}
 return meta,locusrows,observations

NORMALIZED_SCHEMA = 'CREATE TABLE gene_hash_set(id INTEGER PRIMARY KEY,payload_json TEXT UNIQUE);\nCREATE TABLE hold_set(id INTEGER PRIMARY KEY,payload_json TEXT UNIQUE);\nCREATE TABLE observed_row(observation_id TEXT PRIMARY KEY,package_id TEXT REFERENCES package,source_table TEXT,row_id TEXT,binding_id TEXT REFERENCES locus_binding,channel TEXT,evidence_state TEXT,duplicate_state TEXT,base_feature_orders_json TEXT,gene_hash_set_id INTEGER REFERENCES gene_hash_set,hold_set_id INTEGER REFERENCES hold_set,raw_sha256 TEXT,UNIQUE(package_id,source_table,row_id));\nCREATE INDEX observed_binding ON observed_row(binding_id);\nCREATE INDEX observed_state ON observed_row(evidence_state);\nCREATE VIEW observation AS SELECT o.observation_id,o.package_id,o.source_table,o.row_id,o.binding_id,l.base_locus_key,l.exact_identity,o.channel,o.evidence_state,o.duplicate_state,o.base_feature_orders_json,g.payload_json AS gene_hashes_json,h.payload_json AS holds_json,o.raw_sha256,NULL AS raw_zlib FROM observed_row o LEFT JOIN locus_binding l USING(binding_id) JOIN gene_hash_set g ON g.id=o.gene_hash_set_id JOIN hold_set h ON h.id=o.hold_set_id;\n'

def build(inventory,base_path,out,base_sha,allowed_root,selection=None,resume=False,source_overrides=None):
 out=Path(out).resolve();allowed=Path(allowed_root).resolve()
 if not out.is_relative_to(allowed):raise ValueError('OUTPUT_ROOT_DRIFT')
 exists=out.exists()
 if exists and not resume:raise FileExistsError(out)
 if len(inventory)>128:raise ValueError('PACKAGE_COUNT_LIMIT')
 started=time.monotonic()
 if sha(base_path)!=base_sha:raise ValueError('BASE_HASH_DRIFT')
 base=ro(base_path);loci,sources=base_index(base)
 if source_overrides:
  for strain,path in source_overrides.items():
   if strain in sources:sources[strain]['original_locator']=str(path)
 c=sqlite3.connect(out);c.execute('PRAGMA foreign_keys=ON')
 if not exists:c.executescript("""CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);
CREATE TABLE package(package_id TEXT PRIMARY KEY,metadata_zlib BLOB);
CREATE TABLE locus_binding(binding_id TEXT PRIMARY KEY,package_id TEXT REFERENCES package,exact_identity TEXT,strain TEXT,full_node TEXT,region TEXT,bgc_alias TEXT,base_locus_key TEXT,state TEXT,detail_zlib BLOB);
CREATE TABLE section_profile(profile_sha256 TEXT,bundle_version TEXT,code_zip_sha256 TEXT,member TEXT,contract_text TEXT);
CREATE TABLE section_relevance(section_number INTEGER PRIMARY KEY,profile_sha256 TEXT,requirement TEXT,relation TEXT,limits TEXT);
""")
 if not exists:
  c.executescript(NORMALIZED_SCHEMA)
  c.executemany('INSERT INTO metadata VALUES(?,?)',[('resume_base_sha256',js(base_sha)),('resume_inventory_sha256',js(rawhash(inventory)))]);c.commit()
 else:
  recorded=dict(c.execute('SELECT key,value FROM metadata'))
  if recorded.get('resume_base_sha256')!=js(base_sha) or recorded.get('resume_inventory_sha256')!=js(rawhash(inventory)):raise ValueError('RESUME_DEPENDENCY_DRIFT')
 cache={};summary=[];gene_sets={v:k for k,v in c.execute('SELECT id,payload_json FROM gene_hash_set')};hold_sets={v:k for k,v in c.execute('SELECT id,payload_json FROM hold_set')};done={x[0] for x in c.execute('SELECT package_id FROM package')};new_partitions=0
 for row in inventory:
  if selection and row['package'] not in selection:continue
  if time.monotonic()-started>900:raise ValueError('RUNTIME_BUDGET_CHECKPOINT')
  if row['package'] in done:
   meta=json.loads(zlib.decompress(c.execute('SELECT metadata_zlib FROM package WHERE package_id=?',(row['package'],)).fetchone()[0]))
   for f in meta['checksums']['files']:
    if f['sha256'] and sha(f['path'])!=f['sha256']:raise ValueError('RESUME_SOURCE_DRIFT')
   ar=meta['original_archive']
   if ar.get('state')=='ARCHIVE_HASH_VERIFIED' and sha(ar['path'])!=ar['expected_sha256']:raise ValueError('RESUME_ARCHIVE_DRIFT')
   summary.append({'package':row['package'],'state':'RESUMED_EXISTING_VERIFIED_PARTITION'});continue
  meta,lrs,obs=package_data(row,loci,sources,cache);pid=row['package'];c.execute('INSERT INTO package VALUES(?,?)',(pid,zlib.compress(js(meta).encode(),9)));bid={}
  for l in lrs:
   key=pid+':'+l['bgc_alias'];bid[l['bgc_alias']]=key;c.execute('INSERT INTO locus_binding VALUES(?,?,?,?,?,?,?,?,?,?)',(key,pid,l['exact_identity'],l['strain'],l['full_node'],l['region'],l['bgc_alias'],l['base_locus_key'],l['state'],zlib.compress(js(l).encode(),9)))
  for x in obs:
   l=x['locus'];key=pid+':'+x['table']+':'+x['row_id'];g=js(x['gene_hashes']);h=js(x['holds'])
   for table,seen,v in [('gene_hash_set',gene_sets,g),('hold_set',hold_sets,h)]:
    if v not in seen:seen[v]=len(seen)+1;c.execute('INSERT INTO '+table+' VALUES(?,?)',(seen[v],v))
   c.execute('INSERT INTO observed_row VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(key,pid,x['table'],x['row_id'],bid[l['bgc_alias']] if l else None,x['channel'],x['state'],x['duplicate_state'],js(x['base_feature_orders']),gene_sets[g],hold_sets[h],x['raw_sha256']))
  if c.execute('PRAGMA page_count').fetchone()[0]*c.execute('PRAGMA page_size').fetchone()[0]>67108864:raise ValueError('SIDECAR_STORAGE_LIMIT')
  c.commit();new_partitions+=1;summary.append({'package':pid,'loci':len(lrs),'locus_states':dict(collections.Counter(x['state'] for x in lrs)),'observations':len(obs),'evidence_states':dict(collections.Counter(x['state'] for x in obs)),'duplicates':dict(collections.Counter(x['duplicate_state'] for x in obs))});print(json.dumps(summary[-1]),flush=True)
 if exists and new_partitions==0:
  c.close();base.close()
  if sha(base_path)!=base_sha:raise ValueError('BASE_POST_BUILD_DRIFT')
  return {'packages':summary,'database_sha256':sha(out),'bytes':out.stat().st_size,'state':'RESUME_COMPLETE_OUTPUT_UNCHANGED','archive_receipts':list(cache.values())}
 if not c.execute('SELECT count(*) FROM section_profile').fetchone()[0]:
  for r in base.execute('SELECT * FROM section_profile'):c.execute('INSERT INTO section_profile VALUES(?,?,?,?,?)',tuple(r))
 for r in base.execute('SELECT * FROM section_relevance ORDER BY section_number'):
  relation='NOT_DIRECTLY_ADDRESSED';limit='No interpretation or scientific admission.'
  if r['section_number'] in [4,8,48,50]:relation='STRUCTURED_ANNOTATION_CONTEXT_WITH_TYPED_BINDING';limit='Original annotations and source links; capacity only, not product, expression or activity. Unsupported motif kinds remain outside gene-first channel admission.'
  c.execute('INSERT OR REPLACE INTO section_relevance VALUES(?,?,?,?,?)',(r['section_number'],r['profile_sha256'],r['requirement'],relation,limit))
 for k,v in {'schema':'structured_domain_motif_extension/3','base_database_sha256':base_sha,'scope':'PILOT' if selection else 'ALL_SAVED_PACKAGES','inventory_sha256':rawhash(inventory),'no_original_json_extraction':True,'no_base_database_copy':True,'binding_policy':'Full source archive, exact locus, geometry, complete gene roster and protein hashes; fail closed','raw_encoding':'Raw source rows resolved from pinned package export by table/row_id; no raw export or base copy. Deduplicated gene-link and hold sets.'}.items():c.execute('INSERT OR REPLACE INTO metadata VALUES(?,?)',(k,js(v)))
 c.commit();assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not c.execute('PRAGMA foreign_key_check').fetchall();c.close();base.close()
 if sha(base_path)!=base_sha:raise ValueError('BASE_POST_BUILD_DRIFT')
 return {'packages':summary,'database_sha256':sha(out),'bytes':out.stat().st_size,'archive_receipts':list(cache.values())}

def inspect_verified_connections(d,b,m,*,channel='observations',identity=None,package=None,package_root=None,limit=100,offset=0):
 """Lane callback only. Parent reader owner must hold both pinned read transactions.

 No discovery, file opening for SQLite, schema registry, scientific admission, or
 CLI dispatch is introduced here. Original export resolution requires an explicit root.
 """
 if channel not in ['observations','held','duplicates','loci','genes','packages','sections','evidence-index']:owner._fail('UNKNOWN_CHANNEL')
 if type(limit) is not int or not 1<=limit<=500 or type(offset) is not int or offset<0:owner._fail('INVALID_PAGINATION')
 for connection,expected in [(d,m['database']['sha256']),(b,m['base_database_sha256'])]:
  if not connection.in_transaction or connection.execute('PRAGMA query_only').fetchone()[0]!=1:owner._fail('GUARDED_READ_TRANSACTION_REQUIRED')
  path=Path(connection.execute('PRAGMA database_list').fetchone()[2])
  if not path.is_file() or owner._digest(path)!=expected:owner._fail('CALLBACK_DATABASE_PIN_HOLD')
 owner._table(d,'observed_row',('observation_id','raw_sha256','evidence_state'));owner._table(b,'locus',owner.IDENTITY_COLUMNS)
 if [tuple(r) for r in d.execute('SELECT section_number,profile_sha256,requirement FROM section_relevance ORDER BY section_number')]!=[tuple(r) for r in b.execute('SELECT section_number,profile_sha256,requirement FROM section_relevance ORDER BY section_number')]:owner._fail('FULL50_EXACT_MAPPING_HOLD')
 if d.execute('SELECT count(*) FROM section_relevance').fetchone()[0]!=50:owner._fail('FULL50_REQUIRED')
 locus=None
 if identity is not None:
  if not isinstance(identity,(list,tuple)) or len(identity)!=4:owner._fail('COMPLETE_IDENTITY_REQUIRED')
  try:display=owner.exact_locus_display(*identity)
  except (owner.ExactLocusIdentityError,TypeError):owner._fail('COMPLETE_IDENTITY_REQUIRED')
  found=b.execute('SELECT * FROM locus WHERE exact_identity=?',(display,)).fetchall()
  if len(found)!=1:owner._fail('BASE_LOCUS_UNBOUND')
  locus=dict(found[0]);locus.pop('annotations_zlib',None)
 if channel=='evidence-index' and not locus:owner._fail('EXACT_LOCUS_REQUIRED_FOR_INDEX')
 params=[];where=[];db=d
 if channel=='genes':
  db=b;q='SELECT l.strain,l.full_node,l.region,l.bgc_alias,l.exact_identity,g.gene_order,g.locus_tag,g.protein_sha256,g.protein_length,g.cds_start,g.cds_end,g.strand,g.result_state FROM gene g JOIN locus l USING(locus_key)';order=' ORDER BY l.exact_identity,g.gene_order'
  if locus:where=['l.locus_key=?'];params=[locus['locus_key']]
  if package:owner._fail('PACKAGE_FILTER_NOT_APPLICABLE_TO_BASE_GENES')
 elif channel=='loci':
  q='SELECT binding_id,package_id,exact_identity,strain,full_node,region,bgc_alias,base_locus_key,state,detail_zlib FROM locus_binding';order=' ORDER BY package_id,exact_identity,binding_id'
 elif channel=='packages':q='SELECT * FROM package';order=' ORDER BY package_id'
 elif channel=='sections':q='SELECT * FROM section_relevance';order=' ORDER BY section_number'
 else:
  q='SELECT * FROM observation';order=' ORDER BY package_id,source_table,row_id'
  if channel=='held':where.append("evidence_state='UNBOUND'")
  if channel=='duplicates':where.append("duplicate_state='EXACT_BASE_FEATURE_PROVENANCE_MATCH'")
  if channel=='evidence-index':where.append("channel='domain'")
 if db==d:
  if locus and channel not in ['packages','sections']:where.append('base_locus_key=?');params.append(locus['locus_key'])
  if package and channel!='sections':where.append('package_id=?');params.append(package)
 if where:q+=' WHERE '+' AND '.join(where)
 total=db.execute('SELECT count(*) FROM ('+q+')',params).fetchone()[0];rows=[dict(r) for r in db.execute(q+order+' LIMIT ? OFFSET ?',params+[limit,offset])]
 source_cache={}
 for r in rows:
  if 'raw_zlib' in r and r['raw_zlib'] is None:
   if package_root is None:owner._fail('EXPLICIT_PACKAGE_SOURCE_ROOT_REQUIRED')
   pr=Path(package_root)
   if pr.is_symlink():owner._fail('SYMLINK_PACKAGE_ROOT_REFUSED')
   pr=pr.resolve(strict=True)
   if r['package_id'] not in source_cache:
    meta=json.loads(zlib.decompress(d.execute('SELECT metadata_zlib FROM package WHERE package_id=?',(r['package_id'],)).fetchone()[0]));sp=owner._relative_file(pr,pr,meta['structured_locator'])
    if sp.stat().st_size>67108864:owner._fail('SOURCE_EXPORT_SIZE_LIMIT')
    before=owner._stamp(sp);raw=sp.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=meta['structured_sha256'] or owner._stamp(sp)!=before:owner._fail('SOURCE_EXPORT_HASH_DRIFT')
    data=json.loads(raw,object_pairs_hook=owner._unique_object);source_cache[r['package_id']]={t:{x['row_id']:x for x in data[t]} for t in ['modules','motifs','hmm','ripp_motifs','rrefinder']}
   r.pop('raw_zlib');r['raw']=source_cache[r['package_id']][r['source_table']][r['row_id']]
  for key in ['raw_zlib','metadata_zlib','detail_zlib']:
   if key in r:r[key.removesuffix('_zlib')]=json.loads(zlib.decompress(r.pop(key)))
  if 'raw' in r and hashlib.sha256(json.dumps(r['raw'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()!=r['raw_sha256']:owner._fail('RAW_PAYLOAD_HASH_HOLD')
  if 'exact_identity' in r and all(k in r for k in ['strain','full_node','region','bgc_alias']) and r['exact_identity'] and r['exact_identity']!=owner.exact_locus_display(*(r[k] for k in ['strain','full_node','region','bgc_alias'])):owner._fail('IDENTITY_CONFLICT')
 out={'status':'READ_ONLY_CANDIDATE_INSPECTION','channel':channel,'total_source_rows':total,'offset':offset,'limit':limit,'returned_source_rows':len(rows),'next_offset':offset+len(rows) if offset+len(rows)<total else None,'rows':rows,'base_locus':locus,'scientific_admission':'NOT_PERFORMED','scope':'Mamey structured exports; original antiSMASH JSON not extracted; absent/held results are not biological absence.'}
 if channel=='evidence-index':
  fields=['channel','strain','full_node','region','bgc_alias','gene','evidence_state','source_locator','source_sha256','note','protein_sha256','observation_id','package_id'];index=[];known={r['locus_tag']:r['protein_sha256'] for r in b.execute('SELECT locus_tag,protein_sha256 FROM gene WHERE locus_key=?',(locus['locus_key'],))}
  for r in rows:
   for g in json.loads(r['gene_hashes_json']):
    if g['gene'] not in known:continue
    state=r['evidence_state']
    if state=='BOUND' and (not g['package_protein_sha256'] or known[g['gene']]!=g['package_protein_sha256'] or json.loads(r['holds_json'])):owner._fail('FALSE_BOUND_INDEX_REFUSED')
    index.append({'channel':'domain',**{k:locus[k] for k in ['strain','full_node','region','bgc_alias']},'gene':g['gene'],'evidence_state':state,'source_locator':'evidence://structured-domain-motif/'+r['observation_id'],'source_sha256':m['database']['sha256'],'note':'Pinned sidecar row; source export/hash and raw fields resolved through observation_id; capacity only. '+r['holds_json'],'protein_sha256':g['package_protein_sha256'],'observation_id':r['observation_id'],'package_id':r['package_id']})
  text=io.StringIO();w=SafeDictWriter(text,fieldnames=fields,delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(index);out['evidence_index_tsv']=text.getvalue();out['index_rows']=len(index);out['index_scope']='Compatible domain channel only. Unsupported motif/prediction rows remain sidecar-only; source-row pagination applies.'
 if len(json.dumps(out).encode())>4194304:owner._fail('RESULT_SIZE_LIMIT_EXCEEDED')
 return out

def resolve_inventory(source_root,rows):
 root=Path(source_root)
 if root.is_symlink():raise ValueError('SYMLINK_SOURCE_ROOT_REFUSED')
 root=root.resolve(strict=True);result=[]
 for row in rows:
  if not isinstance(row.get('package'),str) or not re.fullmatch(r'[A-Za-z0-9_.-]+',row['package']):raise ValueError('PACKAGE_LOCATOR_HOLD')
  r=dict(row)
  for key in ['manifest','structured_path']:r[key]=str(owner._relative_file(root,root,row[key]))
  result.append(r)
 return result

def main(argv=None):
 p=argparse.ArgumentParser(description='Index saved structured exports; no original antiSMASH extraction.')
 for arg in ['inventory','inventory-pin','source-root','base','base-pin','out','allowed-root','receipt']:p.add_argument('--'+arg,required=True)
 p.add_argument('--selection',nargs='*');p.add_argument('--resume',action='store_true');p.add_argument('--archive-root');p.add_argument('--archive-map');a=p.parse_args(argv)
 if sha(a.inventory)!=a.inventory_pin:raise ValueError('INVENTORY_PIN_HOLD')
 rows=resolve_inventory(a.source_root,json.loads(Path(a.inventory).read_text()));overrides=None
 if a.archive_map:
  if not a.archive_root:raise ValueError('ARCHIVE_ROOT_REQUIRED')
  ar=Path(a.archive_root).resolve(strict=True);overrides={k:str(owner._relative_file(ar,ar,v)) for k,v in json.loads(Path(a.archive_map).read_text()).items()}
 result=build(rows,a.base,a.out,a.base_pin,a.allowed_root,a.selection,resume=a.resume,source_overrides=overrides)
 rp=Path(a.receipt).resolve()
 if not rp.is_relative_to(Path(a.allowed_root).resolve()):raise ValueError('RECEIPT_ROOT_DRIFT')
 rp.write_text(json.dumps(result,indent=2)+'\n');return 0

if __name__=='__main__':
 try:raise SystemExit(main())
 except (ValueError,OSError,sqlite3.Error) as exc:print(json.dumps({'status':'REFUSED_OR_CHECKPOINT_REQUIRED','code':str(exc)}));raise SystemExit(2)
