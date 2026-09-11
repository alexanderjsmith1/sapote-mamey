"""Private local annotation view. No sequence search or scientific admission.

External, hash-pinned source readers remain semantic owners. Run with a config
whose inputs carry paths and SHA256. Output is a small JSON view, never SQLite.
"""
import argparse, collections, hashlib, importlib.util, json, re, sys, zlib, time
from pathlib import Path
sys.dont_write_bytecode = True
RULES = {
 'Glycosyltransferases': r'glycosyltransfer|glycosyl transfer|glycos_transf|glyco_transf',
 'Methyltransferases': r'methyltransfer|methyltransf|methylase',
 'Oxidoreductases': r'oxidoreduct|oxidored|dehydrogenase|reductase|oxygenase|cytochrome p450|\bp450\b',
 'Halogenases': r'halogenase|halogenat|chlorinase|brominase',
 'Acyltransferases': r'acyltransfer|acyl_transf',
 'Aminotransferases': r'aminotransfer|transaminase',
 'Sugar modification context': r'epimerase|dehydratase|glycosylphosphotransferase',
}
FIELDS = ('aSDomain','description','product','gene_ontologies')
CEILING = 'Broad annotation families only. Tailoring role, substrate, reaction, expression and bioactivity are not established. Empty results are not biological absence.'
def sha(p):
 with Path(p).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def write(path, data, root):
 path=Path(path);root=Path(root).resolve()
 if not path.resolve().is_relative_to(root): raise ValueError('OUTPUT_ROOT_DRIFT')
 if path.exists():
  if path.read_text()!=data:raise ValueError('ADDITIVE_OUTPUT_CONFLICT')
  return
 path.write_text(data)
def load_module(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def classify(q):
 text=' '.join(str(v) for k in FIELDS for v in (q.get(k,[]) if isinstance(q.get(k,[]),list) else [q[k]]))
 return [f for f,rule in RULES.items() if re.search(rule,text,re.I)]
def identity(row):
 parts=[row.get(k) for k in ('strain','full_node','region','bgc_alias')]
 if not all(isinstance(x,str) and x.strip()==x and x for x in parts):raise ValueError('COMPLETE_IDENTITY_REQUIRED')
 full=' / '.join(parts)
 if row.get('exact_identity')!=full:raise ValueError('IDENTITY_CONFLICT')
 return full
def clean(q):return {k:v for k,v in q.items() if k!='translation'}
def verify_inputs(cfg):
 for name,e in cfg['inputs'].items():
  p=Path(e['path'])
  if sha(p)!=e['sha256']:raise ValueError('INPUT_HASH_CHANGED:'+name)
 return cfg['inputs']
def verify_product(entry, manifest_path):
 m=json.loads(Path(manifest_path).read_text())
 matches=[f for f in m['files'] if Path(f['path']).name==Path(entry['path']).name]
 if len(matches)!=1 or matches[0]['sha256']!=entry['sha256']:raise ValueError('PRODUCT_MANIFEST_CONFLICT')
def binding_check(g, occurrence):
 if occurrence['protein_sha256']!=g['protein_sha256']:raise ValueError('REVIEWED_PROTEIN_CONFLICT')
def build(cfg, pilot=False):
 pins=verify_inputs(cfg);p=lambda name:Path(pins[name]['path'])
 sys.path.insert(0,str(p('domain_adapter').parent))
 adapter=load_module('atlas_domain_adapter',p('domain_adapter'))
 gly=load_module('atlas_gly_reader',p('gly_reader'))
 # Existing reader verifies source-model manifest, database and binding.
 glyrows={};off=0
 while True:
  page=gly.read(p('gly_db'),limit=500,offset=off)
  for r in page['rows']:glyrows[identity(r)]=r
  if page['next_offset'] is None:break
  off=page['next_offset']
 citations={};occ=collections.defaultdict(list)
 for name in ('dictionary_base','dictionary_overlay'):
  verify_product(pins[name],p(name+'_manifest'))
  d=json.loads(p(name).read_text())
  for entry in d['entries']:
   e=dict(entry);occurrences=e.pop('occurrences',[]);e['source_pin']=name
   citations[e['accession']]=e
   for o in occurrences:occ[(identity(o),o['gene_order'])].append((e['accession'],o))
 # Reuse existing frozen transaction and owner helpers for the domain store.
 mp=p('domain_manifest');m=json.loads(mp.read_text());entry={'path':m['database'],'sha256':m['database_sha256'],'bytes':m['bytes']}
 m={'database':entry,'files':[entry]}
 records=[];locus_views={};unbound=[];counts=collections.Counter()
 with adapter.frozen(mp.parent,mp,m,'database') as db:
  # Cohort projection budget, retaining a finite deadline and frozen transaction.
  deadline=time.monotonic()+120
  db.set_progress_handler(lambda:int(time.monotonic()>deadline),1000)
  metadata=dict(db.execute('select * from metadata'))
  profile=dict(db.execute('select * from section_profile').fetchone())
  contract=p('current50_contract').read_text()
  if profile['contract_text']!=contract or profile['profile_sha256']!=sha(p('current50_contract')):raise ValueError('CURRENT50_CONTRACT_CONFLICT')
  sections=[dict(row) for row in db.execute('select * from section_relevance order by section_number')]
  if [x['section_number'] for x in sections]!=list(range(1,51)):raise ValueError('CURRENT50_MAPPING_INCOMPLETE')
  mapping={'status':'CURRENT50_EXACT_CONTRACT_VERIFIED_NOT_SECTION_COMPLETENESS','profile_sha256':profile['profile_sha256'],'rows':sections,'atlas_application':'Section 6 annotation-family candidates and metabolic-context alternatives only; gene evidence can support review in section 50. No scientific section completion.'}
  gm=json.loads(p('gly_manifest').read_text())
  if metadata['census_sha256']!=gm['binding']['census_sha256']:raise ValueError('POPULATION_CONFLICT')
  loci=[dict(r) for r in db.execute('select locus_key,strain,full_node,region,bgc_alias,exact_identity,source_member,source_member_sha256 from locus order by exact_identity')]
  gene_rows=collections.defaultdict(list)
  for row in db.execute('select * from gene order by locus_key,gene_order'):
   g=dict(row);g['qualifiers']=clean(json.loads(zlib.decompress(g.pop('source_qualifiers_zlib'))));gene_rows[g['locus_key']].append(g)
  features=collections.defaultdict(list)
  for row in db.execute('select * from feature order by locus_key,feature_order'):
   f=dict(row);f['raw']=clean(json.loads(zlib.decompress(f.pop('source_qualifiers_zlib'))));features[f['locus_key']].append(f)
  for l in loci:
   ident=identity(l);key=l['locus_key'];genes=gene_rows[key];bytag={g['locus_tag']:g for g in genes};gf=collections.defaultdict(list)
   if len(bytag)!=len(genes):raise ValueError('DUPLICATE_GENE_TAG')
   for f in features[key]:
    tags=json.loads(f['explicit_gene_tags_json'])
    if len(tags)!=len(set(tags)):raise ValueError('DUPLICATE_FEATURE_GENE_LINK')
    for tag in tags:
     if tag in bytag:gf[tag].append(f)
    if classify(f['raw']) and (f['binding_state']!='SOURCE_SEQUENCE_AND_GEOMETRY_BOUND' or not json.loads(f['explicit_gene_tags_json'])):
     unbound.append({'exact_identity':ident,'feature_order':f['feature_order'],'binding_state':f['binding_state'],'holds':json.loads(f['holds_json']),'raw':f['raw']})
   roster=[];locus_records=[]
   for g in genes:
    fs=gf[g['locus_tag']];names=sorted(set(v for f in fs for v in f['raw'].get('aSDomain',[])))
    roster.append({'gene_order':g['gene_order'],'locus_tag':g['locus_tag'],'start':g['cds_start'],'end':g['cds_end'],'strand':g['strand'],'labels':names,'product':g['qualifiers'].get('product',[]),'state':g['result_state']})
    for accession,o in occ[(ident,g['gene_order'])]:binding_check(g,o)
    matched=[f for f in fs if classify(f['raw'])]
    families=sorted(set(fam for f in matched for fam in classify(f['raw'])))
    if not families:continue
    record={'exact_identity':ident,'locus_key':key,'gene_order':g['gene_order'],'locus_tag':g['locus_tag'],'protein_sha256':g['protein_sha256'],'families':families,'specificity':'UNKNOWN_NOT_ADMITTED','role':'TAILORING_OR_METABOLIC_CONTEXT_UNRESOLVED','reviewed_accessions':sorted(set(a for a,o in occ[(ident,g['gene_order'])])),'evidence':[{'feature_order':f['feature_order'],'binding_state':f['binding_state'],'holds':json.loads(f['holds_json']),'raw':f['raw'],'source_location':f['source_location'],'rules':{fam:RULES[fam] for fam in classify(f['raw'])}} for f in matched]}
    locus_records.append(record)
   if locus_records:
    model=glyrows.get(ident)
    if model is None:raise ValueError('GLYCOSYLATION_LOCUS_JOIN_MISSING')
    if model['source_member_sha256']!=l['source_member_sha256']:raise ValueError('LOCUS_SOURCE_CONFLICT')
    locus_views[key]={**l,'genes':roster,'glycosylation':model,'boundary_hold':'Source region roster only; +/-3 gene neighborhood is context, not a pathway boundary or coupling claim.'}
    records.extend(locus_records)
    counts.update(fam for r in locus_records for fam in r['families'])
  denominator={'population':'frozen45','strains':len({l['strain'] for l in loci}),'loci':len(loci),'gene_occurrences':sum(map(len,gene_rows.values())),'feature_records':sum(map(len,features.values())),'census_sha256':metadata['census_sha256']}
 # The atlas deliberately makes no exact50 mapping until current contract binding.
 if pilot:
  representatives=[]
  for family in RULES:
   row=next((r for r in records if family in r['families'] and r not in representatives),None)
   if row:representatives.append(row)
   if len(representatives)==5:break
  records=representatives;locus_views={r['locus_key']:locus_views[r['locus_key']] for r in records}
 verify_inputs(cfg)
 return {'schema':'tailoring_atlas/0.1','ceiling':CEILING,'denominator':denominator,'family_counts':dict(counts),'records':records,'loci':locus_views,'reviewed_dictionary':citations,'held_features':unbound,'inputs':pins,'rules':RULES,'modeb_mapping':mapping,'admitted_hits':'No new hit admission; source domain binding is not scientific function admission. No BLAST evidence used.','pilot':pilot}
def render(data, template):
 return template.replace('__ATLAS_DATA__',json.dumps(data,separators=(',',':')).replace('<','\\u003c'))
def main():
 a=argparse.ArgumentParser();a.add_argument('--config',required=True);a.add_argument('--output',required=True);a.add_argument('--pilot',action='store_true');a.add_argument('--offset',type=int,default=0);a.add_argument('--limit',type=int,default=20000);args=a.parse_args()
 cfg=json.loads(Path(args.config).read_text());root=Path(args.output).resolve()
 if args.offset<0 or not 1<=args.limit<=20000:raise ValueError('PARTITION_RANGE_HOLD')
 for entry in cfg['inputs'].values():
  entry['path']=str((Path(args.config).resolve().parent/entry['path']).resolve())
 if not root.is_relative_to(Path(cfg['permitted_output_root']).resolve()):raise ValueError('OUTPUT_ROOT_DRIFT')
 root.mkdir(parents=True,exist_ok=True);data=build(cfg,args.pilot)
 data['partition']={'offset':args.offset,'limit':args.limit,'total':len(data['records'])}
 data['records']=data['records'][args.offset:args.offset+args.limit]
 data['loci']={r['locus_key']:data['loci'][r['locus_key']] for r in data['records']}
 write(root/'ATLAS_DATA.json',json.dumps(data,separators=(',',':')),root)
 write(root/'START_HERE.html',render(data,Path(__file__).with_name('atlas_template.html').read_text()),root)
 print(json.dumps({'records':len(data['records']),'loci':len(data['loci']),'counts':data['family_counts'],'denominator':data['denominator']}))
if __name__=='__main__':main()
