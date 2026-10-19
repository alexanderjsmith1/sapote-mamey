"""Optional exact local file-role binding, not execution/model authentication."""
import re
TOOL_ROLES={'python_runtime','perl_runtime','makeblastdb','blastp','blastn','prodigal_short','hmmsearch'}
MODEL_ROLES={'pfam_model','ripp_model'} | {prefix+'_index_'+suffix for prefix in ('pfam','ripp') for suffix in ('h3f','h3i','h3m','h3p')}
REQUIRED={'upstream_source','config','genbank','query_fasta','pfam_model','ripp_model','completion_log','raw_output','queries','columns'}


def files(api, declarations, supplied, sources, model_byte_budget=None, hash_timeout_seconds=30, executable_byte_budget=None, executable_hash_timeout_seconds=30):
    if model_byte_budget is not None:
        # Validate budgets even when the supplied roster contains no model role.
        import math
        if type(model_byte_budget) is not int or not 0<model_byte_budget<=16*1024**3 or isinstance(hash_timeout_seconds,bool) or not isinstance(hash_timeout_seconds,(int,float)) or not math.isfinite(hash_timeout_seconds) or not 0<hash_timeout_seconds<=600:
            raise ValueError("MODEL_STREAM_BUDGET_INVALID")
    import math
    if executable_byte_budget is not None:
        if type(executable_byte_budget) is not int or not 0<executable_byte_budget<=512*1024**2 or isinstance(executable_hash_timeout_seconds,bool) or not isinstance(executable_hash_timeout_seconds,(int,float)) or not math.isfinite(executable_hash_timeout_seconds) or not 0<executable_hash_timeout_seconds<=300:raise ValueError('EXECUTABLE_STREAM_BUDGET_INVALID')
    elif executable_hash_timeout_seconds!=30:raise ValueError('EXECUTABLE_STREAM_EXPLICIT_BYTE_BUDGET_REQUIRED')
    if not isinstance(declarations,dict) or not declarations or len(declarations)>32:
        raise ValueError('RUN_BINDING_FILE_ROSTER_INVALID')
    paths={}
    for item in supplied or []:
        role,sep,path=item.partition('=')
        if not sep or not re.fullmatch(r'[a-z][a-z0-9_]*',role) or not path or role in paths:
            raise ValueError('RUN_BINDING_EXPLICIT_FILE_ARGUMENT_INVALID')
        paths[role]=path
    if set(paths)!=set(declarations):raise ValueError('RUN_BINDING_EXPLICIT_FILE_ROSTER_MISMATCH')
    bound={}
    for role,path in paths.items():
        expected=declarations[role]
        if not isinstance(expected,str) or not re.fullmatch(r'[0-9a-f]{64}',expected):raise ValueError('RUN_BINDING_DIGEST_INVALID')
        b=api['stream_binding'](path,model_byte_budget,hash_timeout_seconds) if model_byte_budget is not None and role in MODEL_ROLES else api['tool_binding'](path,executable_byte_budget,executable_hash_timeout_seconds) if role in TOOL_ROLES else api['binding'](path,api['load_bytes'](path))
        sources.append(b)
        if b['sha256']!=expected:raise ValueError('RUN_BINDING_FILE_DIGEST_MISMATCH: '+role)
        bound[role]=b
    return bound


def bind_run(api, manifest_path, supplied, out, adapted_profile_path=None):
    sources=[];manifest=api['json_input'](manifest_path,sources)
    if not isinstance(manifest,dict) or manifest.get('schema_version')!='ripper-run-binding-manifest/1' or manifest.get('evidence_kind') not in ('synthetic_fixture','operator_supplied'):
        raise ValueError('RUN_BINDING_MANIFEST_INVALID')
    run_id=manifest.get('run_id')
    if not isinstance(run_id,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',run_id):raise ValueError('RUN_BINDING_RUN_ID_REQUIRED')
    profile=api['source_contract'](manifest.get('profile_id'),sources);profile_sha=sources[-1]['sha256']
    if manifest.get('source_revision')!=profile['revision']:raise ValueError('RUN_BINDING_SOURCE_REVISION_MISMATCH')
    budget=manifest.get('model_byte_budget');timeout=manifest.get('hash_timeout_seconds',30)
    exe_budget=manifest.get('executable_byte_budget');exe_timeout=manifest.get('executable_hash_timeout_seconds',30)
    bound=files(api,manifest.get('files'),supplied,sources,budget,timeout,exe_budget,exe_timeout)
    adaptation=api['owned_module']('ripper_source_admission').verify_adapted(api,adapted_profile_path,bound,sources) if adapted_profile_path else None
    synthetic=manifest['evidence_kind']=='synthetic_fixture'
    expected=next(x['sha256'] for x in profile['reviewed_sources'] if x['file']=='ripper_local.pl')
    source_state='SYNTHETIC_SOURCE_NOT_UPSTREAM' if synthetic else 'ARCHIVED_SOURCE_BYTE_PIN_MATCH'
    if adaptation:source_state='EXPLICIT_LOCAL_ADAPTATION_REVIEW_ONLY'
    if not synthetic and not adaptation and bound.get('upstream_source',{}).get('sha256')!=expected:
        raise ValueError('RUN_BINDING_ARCHIVED_SOURCE_PIN_MISMATCH')
    missing=sorted(REQUIRED-set(bound))
    data=dict(schema_version='ripper-run-binding/1',binding_status='HOLD_REQUIRED_FILE_ROLES' if missing else 'BOUND_DECLARED_FILES_ONLY',
        run_id=run_id,evidence_kind=manifest['evidence_kind'],source_profile_id=profile['id'],source_profile_sha256=profile_sha,
        source_revision=profile['revision'],source_binding_status=source_state,adaptation=adaptation,model_byte_budget=budget,hash_timeout_seconds=timeout,executable_byte_budget=exe_budget,executable_hash_timeout_seconds=exe_timeout,files=bound,missing_roles=missing,sources=sources,
        upstream_execution='NOT_EXECUTED',model_validation='BYTE_DIGEST_ONLY_NOT_MODEL_READY',
        holds=['HOLD_RUNTIME_MODEL_AND_EXECUTION_VALIDATION','HOLD_LICENSE','HOLD_NO_GLOBAL_RUN_ID_OR_TIME_AUTHENTICATION'])
    api['publish'](out,{'RUN_BINDING.json':data},sources)
    return data


def verify_boundary(api,path,supplied,sources,required_inputs,complete=False,receipt=None,adapted_profile_path=None):
    data=api['json_input'](path,sources);artifact_sha=sources[-1]['sha256']
    if not isinstance(data,dict) or data.get('schema_version')!='ripper-run-binding/1' or not isinstance(data.get('files'),dict):
        raise ValueError('RUN_BINDING_ARTIFACT_INVALID')
    profile=api['source_contract'](data.get('source_profile_id'),sources)
    if data.get('source_profile_sha256')!=sources[-1]['sha256'] or data.get('source_revision')!=profile['revision']:
        raise ValueError('RUN_BINDING_PROFILE_CHANGED')
    if data.get('evidence_kind') not in ('synthetic_fixture','operator_supplied') or not isinstance(data.get('run_id'),str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',data['run_id']):
        raise ValueError('RUN_BINDING_ARTIFACT_IDENTITY_INVALID')
    declarations={k:v.get('sha256') for k,v in data['files'].items() if isinstance(v,dict)}
    if len(declarations)!=len(data['files']):raise ValueError('RUN_BINDING_ARTIFACT_FILES_INVALID')
    fresh=files(api,declarations,supplied,sources,data.get('model_byte_budget'),data.get('hash_timeout_seconds',30),data.get('executable_byte_budget'),data.get('executable_hash_timeout_seconds',30))
    if bool(data.get('adaptation'))!=bool(adapted_profile_path):raise ValueError('RUN_BINDING_EXPLICIT_ADAPTED_PROFILE_REQUIRED')
    adaptation=api['owned_module']('ripper_source_admission').verify_adapted(api,adapted_profile_path,fresh,sources) if adapted_profile_path else None
    if adaptation!=data.get('adaptation'):raise ValueError('RUN_BINDING_ADAPTED_PROFILE_CHANGED')
    for role,b in required_inputs.items():
        if fresh.get(role)!=b:raise ValueError('RUN_BINDING_BOUNDARY_INPUT_MISMATCH: '+role)
    for role,b in fresh.items():
        if b!=data['files'][role]:raise ValueError('RUN_BINDING_LOCATOR_CHANGED: '+role)
    if data['evidence_kind']=='operator_supplied' and not adaptation:
        expected=next(x['sha256'] for x in profile['reviewed_sources'] if x['file']=='ripper_local.pl')
        if fresh.get('upstream_source',{}).get('sha256')!=expected:
            raise ValueError('RUN_BINDING_ARCHIVED_SOURCE_PIN_MISMATCH')
    computed_status='HOLD_REQUIRED_FILE_ROLES' if REQUIRED-set(fresh) else 'BOUND_DECLARED_FILES_ONLY'
    if data.get('binding_status')!=computed_status:raise ValueError('RUN_BINDING_ARTIFACT_STATE_MISMATCH')
    if complete:
        if data.get('binding_status')!='BOUND_DECLARED_FILES_ONLY' or REQUIRED-set(fresh):raise ValueError('RUN_BINDING_COMPLETE_ROLES_REQUIRED')
        if receipt.get('run_id')!=data.get('run_id') or receipt.get('run_bindings_sha256')!=artifact_sha or receipt.get('evidence_kind')!=data.get('evidence_kind'):
            raise ValueError('RUN_BINDING_RECEIPT_IDENTITY_MISMATCH')
    return dict(artifact_sha256=artifact_sha,run_id=data.get('run_id'),binding_status=data.get('binding_status'),fresh_files=fresh,
        adaptation=adaptation,source_binding_status='EXPLICIT_LOCAL_ADAPTATION_REVIEW_ONLY' if adaptation else ('SYNTHETIC_SOURCE_NOT_UPSTREAM' if data['evidence_kind']=='synthetic_fixture' else 'ARCHIVED_SOURCE_BYTE_PIN_MATCH'),model_validation='BYTE_DIGEST_ONLY_NOT_MODEL_READY',
        upstream_execution='NOT_EXECUTED',holds=['HOLD_RUNTIME_MODEL_AND_EXECUTION_VALIDATION','HOLD_LICENSE','HOLD_NO_GLOBAL_RUN_ID_OR_TIME_AUTHENTICATION'])
