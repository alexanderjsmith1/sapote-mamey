"""Private, local next-evidence view. Existing registry reader owns SQLite access.
No scan, submission, experiment, database copy, or scientific admission API exists.
"""
import argparse, contextlib, hashlib, importlib.util, json, re, sqlite3, sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

POLICY = 'Routing policy only, not scientifically validated optimization: explicit core first, biosynthetic-additional next, routine genes last. Discriminating roles require a separately bound scientific rationale and are not inferred from keywords. Original channel rank breaks ties. Verified no-hit is not an automatic rerun.'
RULES = {
 'missing': ('Search', 'NO_VERIFIED_SEARCH', 'READY_FOR_REVIEW_NOT_SUBMISSION', 'Would a verified search in this exact channel change the named-match interpretation?', 'Resolve missing channel evidence before interpreting lack of similarity.', 'Exact query FASTA SHA-256 and length, database name/version/date, run and query binding receipt, retained hits or verified zero-hit outcome, and admission review.', 'Search execution unauthorized; absence of a verified search is not biological absence.'),
 'mixed': ('Review', 'VERIFIED_MIXED_OUTCOMES', 'RERUN_DECISION_HELD', 'Why does this exact protein have mixed saved outcomes in this channel?', 'Reconcile run/version/query provenance before deciding whether a channel-specific rerun is necessary.', 'Compare the saved run receipts, database releases, query hashes, parameters and retained/no-hit outcomes. Record an adjudication or an exact-channel rerun request with a justified trigger.', 'Mixed outcomes may reflect different runs; no contradiction or rerun necessity inferred.'),
 'denominator': ('Review', 'BLOCKED', 'PROVENANCE_HOLD', 'What binding would make this denominator reproducible?', 'Prevent incomparable population counts from supporting prevalence or cohort claims.', 'The source release condition shown in raw evidence, a declared population/profile/version and a reproducible defining query.', 'Source provenance and denominator remain unresolved.'),
 'comparability': ('Review', 'COMPARABILITY_NOT_ESTABLISHED_NOT_A_CONTRADICTION', 'COMPARABILITY_HOLD', 'Can these source assertions be compared on a common scope?', 'Avoid converting differences of population, taxonomy or source granularity into biological conflicts.', 'A common metadata profile, assertion as-of/version, source-field semantics and explicit owner adjudication.', 'Comparability is not established; this is not a confirmed contradiction.'),
 'wetlab': ('Experimental planning', 'METADATA_GAP', 'EXPERIMENT_DESIGN_HELD', 'Which missing assay records must be resolved before planning a confirmatory experiment?', 'Assay provenance, controls and attribution determine whether a follow-up can test the proposed claim.', 'Primary assay records, concentration, medium, inoculum, controls, processing denominator, biological/technical replicate identities, and an explicit experimental question. Locus claims additionally require direct locus-bound evidence.', 'Strain/fraction records do not establish gene or BGC activity. No experiment or expected outcome proposed.')
}

def digest(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load_module(path,name):
 sys.dont_write_bytecode=True
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

class View:
 def __init__(self,root,manifest,pin):
  self.root=Path(root).resolve(strict=True);mp=Path(manifest).resolve(strict=True)
  if digest(mp)!=pin:raise ValueError('MANIFEST_PIN_MISMATCH')
  self.m=json.loads(mp.read_text());self.paths={};self.stamps={}
  if self.m['schema']!='next_evidence_actions/1':raise ValueError('SCHEMA_HOLD')
  for key,e in self.m['sources'].items():
   p=(self.root/e['path']).resolve(strict=True)
   if not p.is_relative_to(self.root):raise ValueError('SOURCE_ROOT_DRIFT')
   if p.stat().st_size!=e['bytes'] or digest(p)!=e['sha256']:raise ValueError('SOURCE_HASH_MISMATCH:'+key)
   self.paths[key]=p;self.stamps[key]=self.stamp(p)
   if p.suffix=='.sqlite':self.no_sidecars(p)
  self.reader=load_module(self.paths['reader'],'next_actions_existing_reader')
  self.identity=load_module(self.paths['identity'],'next_actions_existing_identity')
  self.contract_hash=self.m['sources']['contract']['sha256']
  with self.db('registry') as c:
   profile=c.execute('SELECT profile_sha256,contract_text FROM profile').fetchall()
   if len(profile)!=1 or profile[0][0]!=self.contract_hash or hashlib.sha256(profile[0][1].encode()).hexdigest()!=self.contract_hash:raise ValueError('CONTRACT_PROFILE_HOLD')
   self.sections=[dict(r) for r in c.execute('SELECT * FROM section_relevance ORDER BY section')]
   if [r['section'] for r in self.sections]!=list(range(1,51)) or any(r['profile_sha256']!=self.contract_hash for r in self.sections):raise ValueError('EXACT50_HOLD')
  with self.db('census') as c:
   self.population_rows=[dict(r) for r in c.execute('SELECT selection_state,state,count(*) count FROM strain GROUP BY selection_state,state')]
   self.loci=c.execute('SELECT count(*) FROM locus').fetchone()[0]
   self.genes=c.execute('SELECT count(*) FROM gene').fetchone()[0]
   self.selection=dict(c.execute('SELECT * FROM metadata'))['selection_sha256']
  with self.db('priority') as c:
   source=json.loads(dict(c.execute('SELECT * FROM metadata'))['sources'])
   if source['antismash_gene_census__v0.1.1__2026-09-07']['sha256']!=self.m['sources']['census']['sha256']:raise ValueError('CENSUS_BINDING_HOLD')
   self.source_policy=dict(c.execute('SELECT * FROM metadata'))['method']
   self.channel_states=[dict(r) for r in c.execute('SELECT channel,state,count(*) count FROM channel_state GROUP BY channel,state ORDER BY channel,state')]
   self.channel_totals=dict(c.execute('SELECT channel,count(*) FROM channel_state GROUP BY channel'))
  self.validate_bindings()
  self.counts={k:self.query(k,count_only=True) for k in RULES}
 def validate_bindings(self):
  # Reuse source semantic keys, never alias-based joins or sequence-only locus transfer.
  with self.db('census') as c:
   if c.execute('PRAGMA foreign_key_check').fetchone():raise ValueError('CENSUS_FOREIGN_KEY_HOLD')
   census={}
   for r in c.execute('SELECT l.exact_identity,g.* FROM gene g JOIN locus l USING(locus_key)'):
    self.check_identity(r['exact_identity']);census[(r['locus_key'],r['gene_order'])]=(r['exact_identity'],r['locus_tag'],r['protein_sha256'],r['protein_length'])
  with self.db('priority') as c:
   seen=set();representatives=set()
   for r in c.execute('SELECT * FROM occurrence'):
    k=(r['locus_key'],r['gene_order']);value=(r['exact_identity'],r['locus_tag'],r['query_sha256'],r['protein_length'])
    if k in seen or census.get(k)!=value:raise ValueError('ASSEMBLY_ROSTER_OR_PROTEIN_BINDING_HOLD')
    self.check_identity(r['exact_identity']);seen.add(k);representatives.add((r['query_sha256'],r['exact_identity'],r['locus_tag']))
   for r in c.execute('SELECT q.*,s.state FROM queue q LEFT JOIN channel_state s USING(channel,query_sha256)'):
    if r['state']!='NO_VERIFIED_SEARCH' or (r['query_sha256'],r['representative_identity'],r['representative_gene']) not in representatives:raise ValueError('QUEUE_STATE_OR_IDENTITY_HOLD')
  with self.db('wetlab') as c:
   md=dict(c.execute('SELECT * FROM metadata'))
   if json.loads(md['census_sha256'])!=self.m['sources']['census']['sha256']:raise ValueError('WETLAB_CENSUS_HOLD')
   wp=c.execute('SELECT profile_sha256,contract_text FROM section_profile').fetchall()
   if len(wp)!=1 or wp[0][0]!=self.contract_hash or hashlib.sha256(wp[0][1].encode()).hexdigest()!=self.contract_hash:raise ValueError('WETLAB_PROFILE_HOLD')
   self.wet_sections=[dict(r) for r in c.execute('SELECT * FROM section_relevance ORDER BY section_number')]
   if [(r['section_number'],r['profile_sha256'],r['requirement']) for r in self.wet_sections]!=[(r['section'],r['profile_sha256'],r['requirement']) for r in self.sections]:raise ValueError('WETLAB_EXACT50_HOLD')
  self.section_routes={}
  for kind,indices in {'missing':[50],'mixed':[50,28],'denominator':[44,45],'comparability':[28,44,45],'wetlab':[14,17,23]}.items():
   self.section_routes[kind]=[dict(self.sections[i-1],routing_relation='REVIEW_QUESTION_RELEVANCE_NOT_SECTION_COMPLETION') for i in indices]

 @staticmethod
 def stamp(p):
  s=p.stat();return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
 @staticmethod
 def no_sidecars(p):
  if any(Path(str(p)+s).exists() for s in ('-wal','-shm','-journal')):raise ValueError('SQLITE_SIDECAR_HOLD')
 def unchanged(self):
  for k,p in self.paths.items():
   if self.stamp(p)!=self.stamps[k]:raise ValueError('SOURCE_CHANGED_RESTART_AND_REPIN_REQUIRED')
 @contextlib.contextmanager
 def db(self,key):
  self.unchanged();p=self.paths[key];self.no_sidecars(p)
  with contextlib.closing(self.reader.connect(p)) as c:
   c.execute('PRAGMA trusted_schema=OFF');c.execute('BEGIN')
   yield c
   self.no_sidecars(p);self.unchanged()
 def metadata(self):
  return {'counts':self.counts,'population':self.m['population'],'population_rows':self.population_rows,'selection_sha256':self.selection,'loci':self.loci,'gene_occurrences':self.genes,'channel_states':self.channel_states,'policy':POLICY,'source_policy':self.source_policy,'sources':self.m['sources'],'contract_sha256':self.contract_hash,'section_mapping':'Review relevance routes verified against pinned current50 contract, not section completion. Source evidence-index profile transitions are explicit in raw denominator rows.', 'section_routes':self.section_routes,'sections':self.sections,'limits':'Exact source-region genes only; no extra boundary context. All outcomes unknown until evidence resolves the question. Distinct populations must not be merged.'}
 def query(self,kind='missing',channel='nr',tier='all',search='',offset=0,limit=25,count_only=False):
  if kind not in RULES or channel not in ('nr','clustered_nr') or tier not in ('all','0','1','2'):raise ValueError('INVALID_FILTER')
  if type(offset)!=int or offset<0 or type(limit)!=int or not 1<=limit<=100 or len(search)>200:raise ValueError('INVALID_PAGINATION')
  params=[];where=[]
  if kind=='missing':
   key='priority';sql='SELECT * FROM queue';order='tier,rank';idfield='query_sha256'
   if not count_only:where=['channel=?'];params=[channel]
   if tier!='all':where.append('tier=?');params.append(int(tier))
   field='representative_identity || representative_gene || query_sha256'
  elif kind=='mixed':
   key='priority';sql="SELECT s.channel,s.query_sha256,s.state,min(o.tier) tier,min(o.exact_identity) representative_identity FROM channel_state s JOIN occurrence o USING(query_sha256) WHERE s.state='VERIFIED_MIXED_OUTCOMES'";order='tier,query_sha256';idfield='query_sha256';field='o.exact_identity || o.locus_tag || s.query_sha256'
   if not count_only:where=['s.channel=?'];params=[channel]
   if tier!='all':where.append('o.tier=?');params.append(int(tier))
  elif kind=='denominator':
   key='registry';sql="SELECT * FROM denominator_resolution WHERE state='BLOCKED'";order='assertion_id';idfield='assertion_id';field='population || coalesce(blocker,\'\') || source_id'
  elif kind=='comparability':
   key='registry';sql='SELECT * FROM comparison_group';order='group_id';idfield='group_id';field='entity || attribute || blockers_json'
  else:
   key='wetlab';sql="SELECT r.strain,count(DISTINCT r.record_id) record_count,count(*) observation_count,group_concat(DISTINCT o.missing_metadata_json) missing_metadata FROM source_record r JOIN observation o USING(record_id) WHERE r.strain IS NOT NULL AND o.missing_metadata_json!='[]'";order='strain';idfield='strain';field='r.strain'
  if search:where.append('instr(lower('+field+'),lower(?))>0');params.append(search)
  if where:sql+=(' AND ' if ' WHERE ' in sql else ' WHERE ')+' AND '.join(where)
  if kind=='mixed':sql+=' GROUP BY s.channel,s.query_sha256'
  if kind=='wetlab':sql+=' GROUP BY r.strain'
  with self.db(key) as c:
   total=c.execute('SELECT count(*) FROM ('+sql+')',params).fetchone()[0]
   if count_only:return total
   rows=[dict(r) for r in c.execute(sql+' ORDER BY '+order+' LIMIT ? OFFSET ?',params+[limit,offset])]
  for r in rows:
   r['id']=str(r[idfield]);r['kind']=kind
   if 'representative_identity' in r:self.check_identity(r['representative_identity'])
   r['question']=RULES[kind][3];r['readiness']=RULES[kind][2]
  return {'rows':rows,'total':total,'offset':offset,'limit':limit,'denominator_unit':'unique protein-channel requests' if kind in ('missing','mixed') else 'source assertions' if kind=='denominator' else 'comparison groups' if kind=='comparability' else 'strains with recorded metadata gaps','rule':RULES[kind]}
 def check_identity(self,s):
  parts=s.split(' / ')
  if len(parts)!=4 or self.identity.exact_locus_display(*parts)!=s:raise ValueError('EXACT_IDENTITY_HOLD')
 def evidence(self,kind,id,channel='nr'):
  if kind not in RULES or channel not in ('nr','clustered_nr'):raise ValueError('INVALID_FILTER')
  if kind in ('missing','mixed'):
   if not re.fullmatch('[a-f0-9]{64}',id):raise ValueError('PROTEIN_IDENTITY_HOLD')
   key='priority'
   with self.db(key) as c:
    state=c.execute('SELECT * FROM channel_state WHERE channel=? AND query_sha256=?',(channel,id)).fetchone()
    expected='NO_VERIFIED_SEARCH' if kind=='missing' else 'VERIFIED_MIXED_OUTCOMES'
    if not state or state['state']!=expected:raise ValueError('ACTION_STATE_MISMATCH')
    raw=[dict(r) for r in c.execute('SELECT * FROM occurrence WHERE query_sha256=? ORDER BY exact_identity,gene_order',(id,))]
    states=[dict(r) for r in c.execute('SELECT * FROM channel_state WHERE query_sha256=? ORDER BY channel',(id,))]
    q=[dict(r) for r in c.execute('SELECT * FROM queue WHERE channel=? AND query_sha256=?',(channel,id))]
   for r in raw:self.check_identity(r['exact_identity'])
   with self.db('census') as c:
    bound=[]
    for r in raw:
     g=c.execute('SELECT l.*,g.* FROM gene g JOIN locus l USING(locus_key) WHERE g.locus_key=? AND g.gene_order=?',(r['locus_key'],r['gene_order'])).fetchone()
     if g is None:raise ValueError('CENSUS_OCCURRENCE_HOLD')
     bound.append(dict(g))
   denominator={'unit':'unique exact protein hashes per channel','value':self.channel_totals[channel],'channel':channel,'selection_sha256':self.selection}
   raw={'occurrences':raw,'canonical_census_rows':bound,'census_source':self.m['sources']['census'],'coordinate_convention':'1-based inclusive absolute; source Orig. start zero-based offset','channel_states':states,'queue':q,'boundary':'Source-region membership only; adjacent genes not expanded','query_sha256':id}
  elif kind=='wetlab':
   key='wetlab'
   with self.db(key) as c:
    raw=[dict(r) for r in c.execute('SELECT r.*,o.*,s.path source_path,s.sha256 source_sha256 FROM source_record r JOIN observation o USING(record_id) JOIN source s USING(source_id) WHERE r.strain=? ORDER BY r.source_id,r.sheet,r.row_number,o.observation_id',(id,))]
   if not raw:raise ValueError('NOT_FOUND')
   denominator={'unit':'recorded observations for this strain; not biological replicates','value':len(raw),'attribution':'STRAIN_FRACTION_ONLY_NO_LOCUS_TRANSFER'}
  else:
   if not id.isdigit():raise ValueError('INVALID_ID')
   key='registry'
   with self.db(key) as c:
    if kind=='denominator':raw=[dict(r) for r in c.execute("SELECT * FROM denominator_resolution WHERE assertion_id=? AND state='BLOCKED'",(int(id),))]
    else:raw=[dict(r) for r in c.execute('SELECT * FROM comparison_member WHERE group_id=? ORDER BY assertion_id',(int(id),))]
   if not raw:raise ValueError('NOT_FOUND')
   denominator={'unit':'Source-specific; see raw population, unit and reported values. No merged denominator.','value':None}
  return {'kind':kind,'id':id,'channel':channel if key=='priority' else None,'rule':RULES[kind],'policy':POLICY,'source':self.m['sources'][key],'denominator':denominator,'raw':raw,'expected_outcome':'UNKNOWN_NOT_PREDICTED','section_mapping':self.section_routes[kind]}

def serve(view,html,port):
 class Handler(BaseHTTPRequestHandler):
  def do_GET(self):
   try:
    if self.headers.get('Host') not in ('127.0.0.1:'+str(port),'localhost:'+str(port)):raise ValueError('LOCAL_HOST_REQUIRED')
    u=urlparse(self.path);a={k:v[0] for k,v in parse_qs(u.query).items()}
    if u.path=='/':data=html.read_bytes();ctype='text/html; charset=utf-8'
    elif u.path=='/api/meta':data=json.dumps(view.metadata()).encode();ctype='application/json'
    elif u.path=='/api/queue':
     for k in ('offset','limit'):
      if k in a:a[k]=int(a[k])
     data=json.dumps(view.query(**a)).encode();ctype='application/json'
    elif u.path=='/api/evidence':data=json.dumps(view.evidence(**a)).encode();ctype='application/json'
    else:self.send_error(404);return
    self.send_response(200);self.send_header('Content-Type',ctype);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'");self.end_headers();self.wfile.write(data)
   except (ValueError,TypeError,sqlite3.Error) as e:
    self.send_response(400);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps({'status':'HELD','reason':str(e)}).encode())
  def log_message(self,*args):pass
 print('Local private widget: http://127.0.0.1:'+str(port),flush=True)
 HTTPServer(('127.0.0.1',port),Handler).serve_forever()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True,type=Path);p.add_argument('--manifest',required=True,type=Path);p.add_argument('--manifest-pin',required=True);p.add_argument('--port',type=int,default=8768);p.add_argument('--html',type=Path,default=Path(__file__).with_name('next_evidence_actions.html'));p.add_argument('--audit',action='store_true');a=p.parse_args()
 v=View(a.root,a.manifest,a.manifest_pin)
 if a.audit:print(json.dumps(v.metadata(),indent=2))
 else:serve(v,a.html,a.port)
if __name__=='__main__':main()
