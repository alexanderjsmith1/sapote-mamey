"""Bounded projection over pinned existing owner databases; never runs searches."""
import argparse, collections, hashlib, importlib.util, json, sqlite3, sys, time
from pathlib import Path

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def module(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def readonly(pin):
 p=Path(pin['database']);m=Path(pin['manifest'])
 if sha(m)!=pin['manifest_sha256'] or sha(p)!=pin['sha256']:raise ValueError('SOURCE_HASH_HOLD')
 manifest=json.loads(m.read_text())
 if manifest['database_sha256']!=pin['sha256'] or p.stat().st_size!=pin['bytes']:raise ValueError('SOURCE_MANIFEST_HOLD')
 if any(Path(str(p)+s).exists() for s in ('-wal','-journal')):raise ValueError('LIVE_DATABASE_HOLD')
 c=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;c.execute('pragma query_only=on');return c

def build(config,permitted_root,pilot=False,expected_config_sha256=None):
 if expected_config_sha256 is None or sha(config)!=expected_config_sha256:raise ValueError('CONFIG_HASH_HOLD')
 started=time.monotonic();cfg=json.loads(Path(config).read_text());out=Path(cfg['output_root']).resolve();allowed=Path(permitted_root).resolve()
 if not out.is_relative_to(allowed) or not Path(config).resolve().is_relative_to(allowed):raise ValueError('OUTPUT_ROOT_HOLD')
 rules_path=out/'FAMILY_RULES.json'
 if sha(rules_path)!=cfg['rules_sha256']:raise ValueError('RULES_HASH_HOLD')
 for key in ('reference_reader','architecture_reader'):
  if sha(cfg[key])!=cfg[key+'_sha256']:raise ValueError('READER_DEPENDENCY_HASH_HOLD')
 if sha(Path(cfg['code_root'])/'mamey/class_architecture.py')!=cfg['projection_sha256']:raise ValueError('PROJECTION_HASH_HOLD')
 rules=json.loads(rules_path.read_text());sys.path.insert(0,cfg['code_root'])
 from mamey.class_architecture import siderophore_evidence_projection
 from mamey.tool_database_reader import inspect_tool_database
 for name,adapter in [('census','gene-census-v1'),('transport','keyword-gene-v1')]:
  p=cfg['sources'][name];inspect_tool_database(Path(p['manifest']).parent,'RELEASE_MANIFEST.json',adapter=adapter,expected_manifest_sha256=p['manifest_sha256'])
 arch=module(cfg['architecture_reader'],'arch_reader');arch.read(cfg['sources']['architecture']['database'],limit=1)
 ref_reader=module(cfg['reference_reader'],'reference_reader')
 connections={k:readonly(v) for k,v in cfg['sources'].items() if k!='reference'}
 rp=cfg['sources']['reference']
 with ref_reader.admit(Path(rp['database']),Path(rp['manifest']),expected_sha256=rp['sha256'],expected_bytes=rp['bytes'],expected_manifest_sha256=rp['manifest_sha256']) as ref:
  census=connections['census'];loci=[dict(x) for x in census.execute('select * from locus order by exact_identity')]
  registered_strains=[dict(x) for x in census.execute('select * from strain order by strain')]
  locus_strains={l['strain'] for l in loci}
  strains=[r for r in registered_strains if r['strain'] in locus_strains]
  if any(r['state']!='COMPLETE' or r['selection_state'] not in ('SELECTED','SELECTED_AVAILABLE_SUPPLEMENT') for r in strains):raise ValueError('COHORT_SELECTION_HOLD')
  if len(strains)!=len(locus_strains):raise ValueError('COHORT_REGISTRATION_HOLD')
  population_hash=hashlib.sha256(json.dumps(strains,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  genes=collections.defaultdict(list)
  for row in census.execute('select * from gene order by locus_key,gene_order'):genes[row['locus_key']].append(dict(row))
  transports={(r['locus_key'],r['gene_order']):dict(r) for r in connections['transport'].execute('select * from gene')}
  cassettes={(r['locus_key'],r['gene_order']):dict(r) for r in connections['cassette'].execute("select * from gene where membership='EXACT_REGION'")}
  # Binding failures stop the partition; no silent cross-assembly/protein join.
  for name,c in list(connections.items())[1:]+[('reference',ref)]:
   other={r['locus_key']:dict(r) for r in c.execute('select * from locus')}
   for l in loci:
    r=other.get(l['locus_key'])
    if not r or any(r[k]!=l[k] for k in ('exact_identity','source_member_sha256')):raise ValueError(name+':LOCUS_SOURCE_HOLD')
  rg={(r['locus_key'],r['gene_order']):dict(r) for r in ref.execute('select * from gene')}
  owners={r['locus_key']:json.loads(r['capacity_json']) for r in connections['architecture'].execute('select * from architecture')}
  references=collections.defaultdict(list)
  for row in ref.execute("select r.*,f.locus_key,f.channel,f.sha256 file_sha256 from reference r join source_file f on f.id=r.file_id where f.channel='knownclusterblast' order by f.locus_key,r.source_rank,r.id"):
   r=dict(row);name=json.loads(r['metadata_json']).get('Source','')
   if r['source_rank']<=3 or name in rules:
    references[r['locus_key']].append(dict(reference_row_id=r['id'],reference_accession=r['reference_raw'],family_name=name,source_rank=r['source_rank'],channel=r['channel'],file_sha256=r['file_sha256'],alignment_count=r['actual_alignment_rows'],metadata=json.loads(r['metadata_json'])))
  selected=[]
  for l in loci:
   k=l['locus_key'];products=json.loads(l['products_json']);iron=any('siderophore_metallophore' in json.loads(cassettes.get((k,g['gene_order']),{}).get('groups_json','[]')) for g in genes[k])
   if any(p.lower() in ('ni-siderophore','nrp-metallophore') for p in products) or iron:selected.append(l)
  selected_ids={x['locus_key'] for x in selected}
  negatives=[l for l in loci if l['locus_key'] not in selected_ids][:5]
  use=(selected[:5] if pilot else selected)+negatives
  records=[]
  for l in use:
   k=l['locus_key'];identity=l['exact_identity'];l.update(population=cfg['population'],population_sha256=population_hash,products=json.loads(l['products_json']),taxonomy_state='UNBOUND',taxonomy=None,owner_capacity=owners[k])
   gdetail=[]
   for g in genes[k]:
    key=(k,g['gene_order']);t=transports.get(key);ca=cassettes.get(key);r=rg.get(key)
    if not all((t,ca,r)) or any(x['protein_sha256']!=g['protein_sha256'] or x['locus_tag']!=g['locus_tag'] for x in (t,ca,r)):raise ValueError('GENE_PROTEIN_SOURCE_BINDING_HOLD')
    gdetail.append(dict(g,exact_identity=identity,source_member_sha256=l['source_member_sha256'],transport_groups=json.loads(t['groups_json']),transport_state=t['state'],cassette_groups=json.loads(ca['groups_json']),cassette_state=ca['state']))
   refs=[dict(r,exact_identity=identity) for r in references[k]]
   record=siderophore_evidence_projection(l,gdetail,refs,rules)
   record['channel_states']=[dict(x) for x in ref.execute('select channel,state,detail from channel_state where locus_key=?',(k,))]
   record['selection']='OWNER_SIGNAL' if k in selected_ids else 'NEGATIVE_CONTROL'
   record['source_locus_key']=k;records.append(record)
  hand=cfg['current_handback'];hp=Path(hand['path'])
  if sha(hp)!=hand['sha256']:raise ValueError('CURRENT_HANDBACK_CHANGED')
  current=json.loads(hp.read_text())
  run_ids=[r['strain_id'] for r in current['primary_deliverables']]
  base_ids=sorted(set(x.split('_',1)[0] for x in run_ids))
  eligible_base_ids=sorted(set(r['strain_id'].split('_',1)[0] for r in current['primary_deliverables'] if r['governance']=='IN_SCOPE'))
  populations={'frozen45':{'strains':len(strains),'registered_strain_rows':len(registered_strains),'nonselected_rows':len(registered_strains)-len(strains),'loci':len(loci),'sha256':population_hash,'source_database_sha256':cfg['sources']['census']['sha256'],'members':[{'strain':r['strain'],'source_sha256':r['source_sha256']} for r in strains]},'current_handback':{'sha256':hand['sha256'],'run_entries':len(current['primary_deliverables']),'base_identity_count':len(base_ids),'eligible_base_count':len(eligible_base_ids),'base_identities':base_ids,'eligible_base_identities':eligible_base_ids,'denominator_rule':'46 handback run entries; collapse explicit underscore run suffixes gives 44 base identities; exclude QC hold gives 43 eligible bases. This is handback accounting, not frozen45 reclassification.','entries':current['primary_deliverables'],'scope_note':current['scope_note'],'binding_state':'SEPARATE_PACKAGE_POPULATION_NOT_JOINED_TO_FROZEN45','taxonomy_state':'UNBOUND_FOR_ATLAS'}}
  receipt={'schema':'siderophore_atlas/1','pilot':pilot,'selected_owner_loci':len(selected),'exported_records':len(records),'negative_controls':len(negatives),'population':populations,'sources':cfg['sources'],'rules_sha256':sha(rules_path),'code_sha256':sha(Path(cfg['code_root'])/'mamey/class_architecture.py'),'builder_sha256':sha(__file__),'elapsed_seconds':round(time.monotonic()-started,3),'claim_ceiling':'No locus chemistry admitted; source product route hypotheses and reference chemistry are independent','taxonomy_hold':'No taxonomy authority bound; no taxonomic aggregation permitted'}
  name='PILOT_ATLAS.json' if pilot else 'ATLAS.json';dest=out/name
  if not dest.resolve().is_relative_to(allowed):raise ValueError('OUTPUT_ROOT_HOLD')
  if dest.exists():raise ValueError('ADDITIVE_OUTPUT_EXISTS_HOLD')
  dest.write_text(json.dumps({'receipt':receipt,'records':records},separators=(',',':'))+'\n')
  (out/('PILOT_RECEIPT.json' if pilot else 'BUILD_RECEIPT.json')).write_text(json.dumps(receipt,indent=2)+'\n')
 for c in connections.values():c.close()
 return receipt
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('config');p.add_argument('--permitted-root',required=True);p.add_argument('--pilot',action='store_true');p.add_argument('--config-sha256',required=True);a=p.parse_args();print(json.dumps(build(a.config,a.permitted_root,a.pilot,a.config_sha256),indent=2))
