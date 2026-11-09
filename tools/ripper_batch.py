"""One admitted roster, many record x bait native runs; each pair keeps its own lifecycle.

The batch never launches a process itself. For every roster pair it derives a
single-query roster and a per-pair lifecycle spec, then calls the existing
ripper_lifecycle.lifecycle() in a fresh per-pair run root. Preflight writes one
BATCH_REVIEW_REQUEST.json that binds every pair's own NATIVE_REVIEW_REQUEST.json by
SHA-256. One matching parent admission (ripper-native-batch-admission/1) then lets the
batch write a derived per-pair admission and resume each reviewed preflight. Every pair
keeps its own PREFLIGHT/TERMINAL and EXECUTION_* receipts and its own outcome state.
Raw discovery stays raw: no HMM annotation, coordinates or BGC membership are inferred.
"""
import hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path

BATCH_SPEC='ripper-lifecycle-batch-spec/1'
BATCH_ADMISSION='ripper-native-batch-admission/1'
PAIR_TERMINAL='ripper-batch-pair-terminal/1'
IDENTITY=('strain','full_contig','region','bgc_alias')
PAIR_ROLES=('genbank','query_fasta','queries')
SAFE_ID=r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}'
SPEC_KEYS=('mode','profile_id','source_revision','limits','executable_byte_budget','executable_hash_timeout_seconds','model_byte_budget','hash_timeout_seconds','bind_observed_runtime_closure')
APPROVED={'decision':'APPROVED_NATIVE_LOCAL_EXECUTION','local_use_decision':'REVIEWED_LOCAL_EXECUTION_ONLY_NO_DISTRIBUTION_CLEARANCE'}
PREFLIGHT_NAMES={'BATCH_PREFLIGHT.json','BATCH_TERMINAL.json','BATCH_REVIEW_REQUEST.json','inputs','pairs'}
SCOPE='Raw native discovery per admitted record x bait pair only; HMM annotation not run; candidate coordinates and BGC membership unverified; no product, structure or bioactivity claim; no retained row is not biological absence.'


def now():return datetime.now(timezone.utc).isoformat()


def file_sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda:handle.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def check_declared(spec,shared,files,pair_ids):
    """Every shared and per-pair file still has its declared digest; checked before any write or launch."""
    paths={}
    for item in shared or []:
        role,sep,path=item.partition('=')
        if not sep or not path or role in paths:raise ValueError('RUN_BINDING_EXPLICIT_FILE_ARGUMENT_INVALID')
        paths[role]=path
    if set(paths)!=set(spec['shared_files']):raise ValueError('RUN_BINDING_EXPLICIT_FILE_ROSTER_MISMATCH')
    for role,path in paths.items():
        if Path(path).is_symlink() or not Path(path).is_file() or file_sha(path)!=spec['shared_files'][role]:raise ValueError('RUN_BINDING_FILE_DIGEST_MISMATCH: '+role)
    for pair_id in pair_ids:
        for role,path in files[pair_id].items():
            if Path(path).is_symlink() or not Path(path).is_file() or file_sha(path)!=spec['pair_files'][pair_id][role]:raise ValueError('BATCH_PAIR_FILE_DIGEST_MISMATCH: '+pair_id+':'+role)


def write_new(path,data):
    with Path(path).open('x',encoding='utf8') as handle:json.dump(data,handle,sort_keys=True,indent=2);handle.write('\n')


def roster_input(api,path,sources):
    """A ripper-queries/1 roster whose rows also name a unique pair_id."""
    data=api['json_input'](path,sources)
    if not isinstance(data,dict) or data.get('schema_version')!='ripper-queries/1':raise ValueError('BATCH_ROSTER_SCHEMA_INVALID')
    rows=data.get('queries')
    if not isinstance(rows,list) or not rows or len(rows)>1000:raise ValueError('BATCH_ROSTER_INVALID')
    pair_ids=set();contexts=set()
    for row in rows:
        if not isinstance(row,dict):raise ValueError('BATCH_ROSTER_ROW_INVALID')
        pair_id=row.get('pair_id');accession=row.get('enzyme_accession')
        if not isinstance(pair_id,str) or not re.fullmatch(SAFE_ID,pair_id) or pair_id in pair_ids:raise ValueError('BATCH_PAIR_ID_MISSING_OR_DUPLICATE')
        pair_ids.add(pair_id)
        if not api['nonempty'](accession) or not re.fullmatch(r'[A-Za-z0-9_.]+',accession):raise ValueError('QUERY_ACCESSION_MISSING_OR_DUPLICATE')
        if any(not api['nonempty'](row.get(k)) or ' / ' in row[k] for k in IDENTITY):raise ValueError('QUERY_FULL_LOCUS_IDENTITY_REQUIRED')
        context=(row['strain'],row['full_contig'],row['region'],accession)
        if context in contexts:raise ValueError('BATCH_DUPLICATE_RECORD_BAIT_PAIR')
        contexts.add(context)
    return rows


def pair_files(supplied):
    """--pair-file PAIR_ID:ROLE=PATH, ROLE in genbank/query_fasta."""
    found={}
    for item in supplied or []:
        head,sep,path=item.partition('=');pair_id,colon,role=head.rpartition(':')
        if not sep or not colon or not path or role not in ('genbank','query_fasta') or not re.fullmatch(SAFE_ID,pair_id) or role in found.get(pair_id,{}):
            raise ValueError('BATCH_PAIR_FILE_ARGUMENT_INVALID')
        found.setdefault(pair_id,{})[role]=path
    return found


def identity(row):return ' / '.join(row[k] for k in IDENTITY)


def load_batch(api,spec_path,roster_path,shared,paired,sources):
    spec=api['json_input'](spec_path,sources)
    if not isinstance(spec,dict) or spec.get('schema_version')!=BATCH_SPEC or spec.get('mode')!='adapted_local05':raise ValueError('BATCH_SPEC_INVALID')
    rows=roster_input(api,roster_path,sources)
    if spec.get('roster_sha256')!=sources[-1]['sha256']:raise ValueError('BATCH_ROSTER_DIGEST_MISMATCH')
    shared_decl=spec.get('shared_files');declared=spec.get('pair_files')
    if not isinstance(shared_decl,dict) or any(role in shared_decl for role in PAIR_ROLES):raise ValueError('BATCH_SHARED_FILE_ROSTER_INVALID')
    if not isinstance(declared,dict) or set(declared)!={r['pair_id'] for r in rows}:raise ValueError('BATCH_PAIR_FILE_ROSTER_MISMATCH')
    files=pair_files(paired)
    if set(files)!=set(declared):raise ValueError('BATCH_PAIR_FILE_ROSTER_MISMATCH')
    for pair_id,decl in declared.items():
        if not isinstance(decl,dict) or set(decl)!={'genbank','query_fasta'} or set(files[pair_id])!=set(decl):raise ValueError('BATCH_PAIR_FILE_ROSTER_MISMATCH')
    for item in shared or []:
        role=item.partition('=')[0]
        if role in PAIR_ROLES:raise ValueError('BATCH_PAIR_ROLE_SUPPLIED_AS_SHARED')
    check_declared(spec,shared,files,[r['pair_id'] for r in rows])
    return spec,rows,files


def derive_pair(spec,row,root,files):
    """Single-query roster and per-pair lifecycle spec; identity copied verbatim from the roster row."""
    pair_id=row['pair_id'];folder=root/'inputs'/pair_id
    queries={'schema_version':'ripper-queries/1','queries':[{k:row[k] for k in ('enzyme_accession',)+IDENTITY}]}
    query_bytes=(json.dumps(queries,indent=2,sort_keys=True)+'\n').encode()
    decl=dict(spec['shared_files'],genbank=spec['pair_files'][pair_id]['genbank'],query_fasta=spec['pair_files'][pair_id]['query_fasta'],queries=hashlib.sha256(query_bytes).hexdigest())
    pair_spec={'schema_version':'ripper-lifecycle-spec/1','files':decl,'batch_pair_id':pair_id}
    pair_spec.update({k:spec[k] for k in SPEC_KEYS if k in spec})
    spec_bytes=(json.dumps(pair_spec,indent=2,sort_keys=True)+'\n').encode()
    supplied=['genbank='+files[pair_id]['genbank'],'query_fasta='+files[pair_id]['query_fasta'],'queries='+str(folder/'queries.json')]
    return folder,query_bytes,spec_bytes,supplied


def fresh_root(run_root):
    root=Path(run_root)
    if not root.is_absolute() or root.is_symlink():raise ValueError('BATCH_FRESH_ABSOLUTE_ROOT_REQUIRED')
    for part in root.parents:
        if part.is_symlink():raise ValueError('BATCH_ROOT_SYMLINK_PARENT_REFUSED')
    source_tree=Path(__file__).resolve().parents[1];resolved=root.resolve()
    if source_tree==resolved or source_tree in resolved.parents:raise ValueError('BATCH_ROOT_MUST_BE_EXTERNAL')
    return root,resolved


def pair_refusal(root,row,phase,exc):
    pair_root=root/'pairs'/row['pair_id'];pair_root.mkdir(exist_ok=True)
    data={'schema_version':PAIR_TERMINAL,'phase':phase,'status':'REFUSED_INPUT' if phase=='preflight' else 'REFUSED_EXECUTION','reason':str(exc),
          'pair_id':row['pair_id'],'query_identity':identity(row),'enzyme_accession':row['enzyme_accession'],'upstream_execution':'NOT_EXECUTED',
          'candidate_bgc_membership':'UNVERIFIED','biological_absence_inferred':False,'terminal_utc':now()}
    name='PAIR_REFUSED.json' if phase=='preflight' else 'PAIR_EXECUTION_REFUSED.json'
    write_new(pair_root/name,data);return data,pair_root/name


def batch(api,spec_path,roster_path,shared,paired,run_root,adapted_profile_path,execute_native=False,admission_path=None,resume_preflight=False,cancel_path=None):
    lifecycle=api['owned_module']('ripper_lifecycle').lifecycle
    if execute_native!=resume_preflight or bool(admission_path)!=execute_native:raise ValueError('BATCH_EXECUTION_REQUIRES_RESUME_AND_ADMISSION')
    if not adapted_profile_path:raise ValueError('RUNNER_EXPLICIT_ADAPTED_PROFILE_REQUIRED')
    sources=[];spec,rows,files=load_batch(api,spec_path,roster_path,shared,paired,sources)
    spec_sha=sources[0]['sha256'];roster_sha=sources[1]['sha256']
    root,resolved=fresh_root(run_root)
    for b in list(sources):
        p=Path(b['path'])
        if resolved==p or resolved in p.parents:raise ValueError('BATCH_ROOT_OVERLAPS_INPUT')
    if not execute_native:
        if root.exists():raise ValueError('BATCH_FRESH_ABSOLUTE_ROOT_REQUIRED')
        root.parent.mkdir(parents=True,exist_ok=True);root.mkdir();(root/'inputs').mkdir();(root/'pairs').mkdir()
        outcomes=[];reviewable=[];refused=[]
        for row in rows:
            folder,query_bytes,spec_bytes,supplied=derive_pair(spec,row,root,files)
            folder.mkdir()
            with (folder/'queries.json').open('xb') as h:h.write(query_bytes)
            with (folder/'LIFECYCLE_SPEC.json').open('xb') as h:h.write(spec_bytes)
            try:
                result=lifecycle(api,str(folder/'LIFECYCLE_SPEC.json'),list(shared or [])+supplied,str(root/'pairs'/row['pair_id']),adapted_profile_path)
            except ValueError as exc:
                data,path=pair_refusal(root,row,'preflight',exc)
                refused.append({'pair_id':row['pair_id'],'query_identity':identity(row),'reason':data['reason'],'terminal_sha256':file_sha(path)})
                outcomes.append({'pair_id':row['pair_id'],'status':'REFUSED_INPUT','reason':data['reason']});continue
            semantic=(result.get('native_contract') or {}).get('semantic_validation') or {}
            outcome={'pair_id':row['pair_id'],'query_identity':identity(row),'status':result['status'],'holds':result['holds'],'missing':result['missing'],
                     'excluded_cds':[{k:x[k] for k in ('subject_cds_id','reason','start_codon')} for x in semantic.get('excluded_cds',[])],
                     'terminal_sha256':file_sha(root/'pairs'/row['pair_id']/'TERMINAL.json')}
            outcomes.append(outcome)
            if result['missing'] or result['holds']!=['HOLD_LOCAL_SOURCE_EXECUTION_ADMISSION']:continue
            request_path=root/'pairs'/row['pair_id']/'NATIVE_REVIEW_REQUEST.json'
            reviewable.append({'pair_id':row['pair_id'],'query_identity':identity(row),'review_request_sha256':file_sha(request_path),'excluded_cds_count':len(outcome['excluded_cds'])})
        request={'schema_version':BATCH_ADMISSION,'decision':'PENDING_PARENT_REVIEW','reviewer':'parent','evidence_kind':'operator_supplied',
                 'contract':'ripper-native-discovery/1','batch_spec_sha256':spec_sha,'roster_sha256':roster_sha,'run_root':str(resolved),
                 'pair_count':len(rows),'admissible_pair_count':len(reviewable),'pairs':reviewable,'refused_pairs':refused,
                 'local_use_decision':'PENDING_LOCAL_EXECUTION_REVIEW_NO_DISTRIBUTION_CLEARANCE','scope':SCOPE}
        write_new(root/'BATCH_REVIEW_REQUEST.json',request)
        counts={}
        for o in outcomes:counts[o['status']]=counts.get(o['status'],0)+1
        summary={'schema_version':'ripper-batch/1','phase':'preflight','status':'HOLD' if reviewable else 'NOT_ADMISSIBLE','upstream_execution':'NOT_EXECUTED',
                 'pair_count':len(rows),'status_counts':counts,'admissible_pair_count':len(reviewable),'refused_pair_count':len(refused),'pairs':outcomes,
                 'review_request_sha256':file_sha(root/'BATCH_REVIEW_REQUEST.json'),'batch_spec_sha256':spec_sha,'roster_sha256':roster_sha,
                 'candidate_bgc_membership':'UNVERIFIED','biological_absence_inferred':False,'sources':sources,'scope':SCOPE,'created_utc':now()}
        write_new(root/'BATCH_PREFLIGHT.json',summary)
        summary['terminal_utc']=now();write_new(root/'BATCH_TERMINAL.json',summary);return summary
    # Execution: one admission, consumed once, for the exact reviewed roster.
    if not root.is_dir() or {p.name for p in root.iterdir()}!=PREFLIGHT_NAMES:raise ValueError('BATCH_PREFLIGHT_ROOT_NOT_PRISTINE')
    terminal=json.loads((root/'BATCH_TERMINAL.json').read_text())
    request_bytes=(root/'BATCH_REVIEW_REQUEST.json').read_bytes()
    if terminal.get('review_request_sha256')!=hashlib.sha256(request_bytes).hexdigest() or terminal.get('batch_spec_sha256')!=spec_sha or terminal.get('roster_sha256')!=roster_sha:raise ValueError('BATCH_PREFLIGHT_BOUNDARY_CHANGED')
    request=json.loads(request_bytes)
    admission=api['json_input'](admission_path,sources);admission_sha=sources[-1]['sha256']
    expected=dict(request,**APPROVED)
    if not isinstance(admission,dict) or any(admission.get(k)!=v for k,v in expected.items()):raise ValueError('BATCH_PARENT_REVIEW_BINDING_MISMATCH')
    by_id={r['pair_id']:r for r in rows}
    for item in request['pairs']:
        if file_sha(root/'pairs'/item['pair_id']/'NATIVE_REVIEW_REQUEST.json')!=item['review_request_sha256']:raise ValueError('BATCH_PAIR_REVIEW_REQUEST_CHANGED: '+item['pair_id'])
        folder,query_bytes,spec_bytes,_=derive_pair(spec,by_id[item['pair_id']],root,files)
        if (folder/'queries.json').read_bytes()!=query_bytes or (folder/'LIFECYCLE_SPEC.json').read_bytes()!=spec_bytes:raise ValueError('BATCH_DERIVED_INPUT_CHANGED: '+item['pair_id'])
    (root/'admissions').mkdir()
    write_new(root/'BATCH_EXECUTION_STARTED.json',{'schema_version':'ripper-batch/1','phase':'execution','admission_sha256':admission_sha,'pair_count':len(request['pairs']),'created_utc':now()})
    outcomes=[];interrupted=False;cancel=Path(cancel_path) if cancel_path else None
    for item in request['pairs']:
        row=by_id[item['pair_id']];pair_root=root/'pairs'/row['pair_id']
        if interrupted or (cancel and cancel.exists()):
            outcomes.append({'pair_id':row['pair_id'],'query_identity':identity(row),'status':'NOT_RUN','reason':'BATCH_INTERRUPTED' if interrupted else 'CANCEL_REQUESTED_BEFORE_PAIR'});continue
        request_pair=json.loads((pair_root/'NATIVE_REVIEW_REQUEST.json').read_text())
        derived=dict(request_pair,**APPROVED,batch_admission_sha256=admission_sha,batch_pair_id=row['pair_id'])
        write_new(root/'admissions'/(row['pair_id']+'.json'),derived)
        folder,_,_,supplied=derive_pair(spec,row,root,files)
        try:
            result=lifecycle(api,str(folder/'LIFECYCLE_SPEC.json'),list(shared or [])+supplied,str(pair_root),adapted_profile_path,False,cancel_path,True,str(root/'admissions'/(row['pair_id']+'.json')),True)
        except ValueError as exc:
            data,path=pair_refusal(root,row,'execution',exc)
            outcomes.append({'pair_id':row['pair_id'],'query_identity':identity(row),'status':'REFUSED_EXECUTION','reason':data['reason'],'terminal_sha256':file_sha(path)});continue
        except KeyboardInterrupt:
            interrupted=True
            outcomes.append({'pair_id':row['pair_id'],'query_identity':identity(row),'status':'INTERRUPTED','reason':'KEYBOARD_INTERRUPT_OUTSIDE_LIFECYCLE'});continue
        if result['status']=='INTERRUPTED':interrupted=True
        raw=result.get('raw_discovery') or {}
        outcomes.append({'pair_id':row['pair_id'],'query_identity':identity(row),'status':result['status'],'reason':result.get('reason'),
                         'output_admission':result.get('output_admission'),'raw_candidate_count':raw.get('candidate_count') if result.get('output_admission')=='SCOPED_BOUND_BYTES_ONLY' else None,
                         'elapsed_seconds':result.get('elapsed_seconds'),'terminal_sha256':file_sha(pair_root/'EXECUTION_TERMINAL.json')})
    counts={}
    for o in outcomes:counts[o['status']]=counts.get(o['status'],0)+1
    summary={'schema_version':'ripper-batch/1','phase':'execution','status':'INTERRUPTED' if interrupted or any(o['status']=='NOT_RUN' for o in outcomes) else 'COMPLETE_PER_PAIR_TERMINALS',
             'admission_sha256':admission_sha,'review_request_sha256':terminal['review_request_sha256'],'pair_count':len(outcomes),'status_counts':counts,'pairs':outcomes,
             'refused_at_preflight':request['refused_pairs'],'candidate_bgc_membership':'UNVERIFIED','biological_absence_inferred':False,
             'outcome_scope':'RAW_NATIVE_DISCOVERY_ONLY_HMM_ANNOTATION_NOT_RUN','scope':SCOPE,'sources':sources,'terminal_utc':now()}
    write_new(root/'BATCH_EXECUTION_TERMINAL.json',summary);return summary
