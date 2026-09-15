"""Validate requested tree-series coverage and hash-bound reference rosters."""
import csv,hashlib,json
from pathlib import Path

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def validate(data,jobs,base):
 contract=data.get('series_requirements')
 if not isinstance(contract,dict):raise ValueError('TREE_SERIES_REQUIREMENTS_MISSING')
 scopes=contract.get('taxonomic_scopes',[]);panels=contract.get('reference_panels',[])
 ratios=contract.get('reference_ratios',[]);views=contract.get('views',[])
 axes=[scopes,panels,ratios,views]
 if any(not isinstance(a,list) or not a or len(set(a))!=len(a) for a in axes):raise ValueError('TREE_SERIES_REQUIREMENTS_AXES')
 if any(p not in {'type_only','type_plus_selected_non_type','type_plus_selected_additional'} for p in panels):raise ValueError('TREE_SERIES_PANEL_AXIS')
 if any(v not in {'publication','publication-detailed','publication-noloc','internal'} for v in views):raise ValueError('TREE_SERIES_VIEW_AXIS')
 if any(v!='all' and (type(v) is not int or v not in (1,2,3,4)) for v in ratios):raise ValueError('TREE_SERIES_RATIO_AXIS')
 expected={(g,p,r,v) for g in scopes for p in panels for r in ratios for v in views}
 observed=[(j['taxonomic_scope'],j['reference_panel'],j['reference_ratio'],j['view']) for j in jobs]
 if len(observed)!=len(set(observed)):raise ValueError('TREE_SERIES_DUPLICATE_VARIANT')
 if set(observed)!=expected:raise ValueError('TREE_SERIES_MATRIX_MISMATCH: missing or unrequested variants')
 receipts=[]
 for tree in data['trees']:
  binding=tree.get('reference_manifest')
  if not isinstance(binding,dict) or not binding.get('sha256'):raise ValueError('TREE_REFERENCE_MANIFEST_REQUIRED')
  path=(Path(base)/binding['path']).resolve()
  if digest(path)!=binding['sha256']:raise ValueError('TREE_REFERENCE_MANIFEST_HASH')
  with path.open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
  required={'tip','role','type_status','accession','sequence_sha256','evidence','admission'}
  if not rows or any(not required<=set(x) for x in rows):raise ValueError('TREE_REFERENCE_MANIFEST_SCHEMA')
  if len({x['tip'] for x in rows})!=len(rows) or any(not x['tip'] for x in rows):raise ValueError('TREE_REFERENCE_IDENTITY')
  if any(x['role'] not in {'query','reference','outgroup'} for x in rows):raise ValueError('TREE_REFERENCE_ROLE')
  refs=[x for x in rows if x['role']=='reference']
  if not refs:raise ValueError('TREE_REFERENCE_EMPTY')
  for x in rows:
   if len(x['sequence_sha256'])!=64 or any(c not in '0123456789abcdef' for c in x['sequence_sha256']):raise ValueError('TREE_REFERENCE_SEQUENCE_HASH')
   if not x['accession'] or not x['evidence'] or x['admission']!='admitted':raise ValueError('TREE_REFERENCE_NOT_ADMITTED')
   if x['type_status'] not in {'type','non_type','unverified','not_applicable'}:raise ValueError('TREE_REFERENCE_TYPE_STATUS')
  if tree['reference_panel']=='type_only' and any(x['type_status']!='type' for x in refs):raise ValueError('TREE_TYPE_ONLY_CONTRADICTION')
  if tree['reference_panel']=='type_plus_selected_non_type':
   if not any(x['type_status']=='type' for x in refs) or not any(x['type_status']=='non_type' for x in refs):raise ValueError('TREE_MIXED_PANEL_NOT_ESTABLISHED')
  if tree['reference_panel']=='type_plus_selected_additional':
   if not any(x['type_status']=='type' for x in refs) or not any(x['type_status'] in {'non_type','unverified'} for x in refs):raise ValueError('TREE_ADDITIONAL_PANEL_EMPTY')
  if tree['reference_panel']!='type_plus_selected_additional' and any(x['type_status']=='unverified' for x in refs):raise ValueError('TREE_REFERENCE_TYPE_UNVERIFIED: use an explicitly provisional additional-reference workflow')
  from Bio import Phylo,SeqIO
  files={}
  for key in ['tree','sequences']:
   b=binding.get(key,{})
   if not b.get('path') or not b.get('sha256'):raise ValueError('TREE_REFERENCE_INPUT_BINDING')
   fp=(Path(base)/b['path']).resolve()
   if digest(fp)!=b['sha256']:raise ValueError('TREE_REFERENCE_INPUT_HASH')
   files[key]=fp
  tips=[x.name for x in Phylo.read(files['tree'],'newick').get_terminals()]
  seqs=list(SeqIO.parse(files['sequences'],'fasta'))
  if len(tips)!=len(set(tips)) or set(tips)!={x['tip'] for x in rows} or len(seqs)!=len(rows) or {x.id for x in seqs}!=set(tips):raise ValueError('TREE_REFERENCE_ROSTER_MISMATCH')
  index={x.id:hashlib.sha256(str(x.seq).upper().replace('-','').encode()).hexdigest() for x in seqs}
  if any(index[x['tip']]!=x['sequence_sha256'] for x in rows):raise ValueError('TREE_REFERENCE_SEQUENCE_MISMATCH')
  from gate_stem_aware import gate
  outgroups=[x['tip'] for x in rows if x['role']=='outgroup']
  if not outgroups:raise ValueError('TREE_SERIES_OUTGROUP_REQUIRED')
  ok,message=gate(files['tree'],outgroup=outgroups)
  if not ok:raise ValueError('TREE_SERIES_BRANCH_GATE: '+message)
  receipts.append({'tree_id':tree['id'],'reference_manifest_sha256':binding['sha256'],'references':len(refs),'branch_gate_report':message})
 return {'status':'DECLARED_SERIES_AND_REFERENCE_ROSTERS_VALIDATED','expected_variants':len(expected),'references':receipts,'ceiling':'Checks declared evidence bindings; does not certify scientific source correctness or infer trees.'}

def validate_delivery(data,job,destination,base):
 """Do not equate a successful subprocess with a complete, identity-safe figure."""
 from Bio import Phylo
 destination=Path(destination);prefix=destination/job['job_id']
 required=[Path(str(prefix)+s) for s in ['_display.nwk','_display_meta.tsv','_rect02.pdf','_rect02.png']]
 if job.get('output_layout'):
  required=[destination/job['output_layout'][k] for k in ['tree','metadata','pdf','png']]
  if any(not p.resolve().is_relative_to(destination.resolve()) for p in required):raise ValueError('TREE_SERIES_OUTPUT_PATH_ESCAPE')
 if any(not p.is_file() or not p.stat().st_size for p in required):raise ValueError('TREE_SERIES_OUTPUT_MISSING')
 entry=next(x for x in data['trees'] if x['id']==job['tree_id'])
 with (Path(base)/entry['reference_manifest']['path']).open() as f:roster={x['tip']:x for x in csv.DictReader(f,delimiter='\t')}
 tips=[x.name for x in Phylo.read(required[0],'newick').get_terminals()]
 with required[1].open() as f:md=list(csv.DictReader(f,delimiter='\t'))
 if len(tips)!=len(set(tips)) or len(md)!=len(tips) or {x['tip'] for x in md}!=set(tips) or not set(tips)<=set(roster):raise ValueError('TREE_SERIES_OUTPUT_IDENTITY')
 mandatory={k for k,v in roster.items() if v['role'] in {'query','outgroup'}}
 if not mandatory<=set(tips):raise ValueError('TREE_SERIES_QUERY_OR_OUTGROUP_LOST')
 if job['reference_ratio']=='all' and set(tips)!=set(roster):raise ValueError('TREE_SERIES_FULL_CONTEXT_INCOMPLETE')
 import copy,math
 parent_binding=entry['reference_manifest']['tree']
 parent=Phylo.read(Path(base)/parent_binding['path'],'newick')
 for terminal in list(parent.get_terminals()):
  if terminal.name not in set(tips):parent.prune(terminal)
 def edges(tree):
  all_tips=frozenset(x.name for x in tree.get_terminals());out={}
  for clade in tree.find_clades():
   if clade is tree.root:continue
   part=frozenset(x.name for x in clade.get_terminals());other=all_tips-part
   if not part or not other:continue
   key=min(tuple(sorted(part)),tuple(sorted(other)),key=lambda x:(len(x),x))
   value=clade.branch_length or 0.0
   if not math.isfinite(value) or value<0:raise ValueError('TREE_SERIES_INVALID_BRANCH')
   out[key]=out.get(key,0.0)+value
  return out
 expected=edges(parent);actual=edges(Phylo.read(required[0],'newick'))
 # Zero-length resolutions carry no supported split. Bound decimal serialization error.
 if any(k not in actual and v>1e-4 for k,v in expected.items()) or any(k not in expected and v>1e-4 for k,v in actual.items()):raise ValueError('TREE_SERIES_TOPOLOGY_CHANGED')
 errors=[abs(expected.get(k,0)-actual.get(k,0)) for k in set(expected)|set(actual)]
 if any(e>1e-4 for e in errors):raise ValueError('TREE_SERIES_BRANCH_LENGTH_CHANGED')
 refs=[roster[t] for t in tips if roster[t]['role']=='reference']
 return {'status':'DELIVERED_IDENTITY_AND_DERIVATION_VALIDATED','max_branch_serialization_difference':max(errors,default=0),'branch_comparison_tolerance':1e-4,'type_references':sum(x['type_status']=='type' for x in refs),'non_type_references':sum(x['type_status']=='non_type' for x in refs),'unverified_type_references':sum(x['type_status']=='unverified' for x in refs),'outputs':{p.name:digest(p) for p in required},'note':'Panel designation describes the input backbone. Counts here describe the actual display subset.'}

def read_display_exclusions(path):
 """Read excluded identities only; retained representatives are not exclusions."""
 with Path(path).open() as f:
  reader=csv.DictReader(f,delimiter='\t')
  if not {'tip','accession'}<=set(reader.fieldnames or []):raise ValueError('TREE_EXCLUSIONS_SCHEMA')
  rows=list(reader)
 return {x[k] for x in rows for k in ['tip','accession'] if x.get(k)}
