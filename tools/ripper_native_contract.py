"""Native discovery admission and exact argv; never launches a process itself."""
import hashlib,json,math,os,re,shutil,sqlite3
from pathlib import Path

CONTRACT='ripper-native-discovery/1'
DISPATCHER_SHA256='dc242b1fdc5f031cc6b82638ad034ac12ac7dd4dd026353d57be56276848089d'
TOOLS={'perl_runtime','makeblastdb','blastp','blastn','prodigal_short'}
REQUIRED=TOOLS|{'archived_base','source_patch','upstream_source','adaptation_receipt','source_closure','config','genbank','query_fasta','queries','runtime_receipt','prodigal_recipe','perl_dispatcher'}
MODULES={'Bio::SeqIO','Bio::SearchIO','Bio::Seq','Bio::SeqFeature::Generic','Bio::Species','DBI','DBD::SQLite','Digest::SHA','XML::Simple','LWP::Simple','JSON::PP'}
MODULE_ROLES={name:'perl_module_'+name.lower().replace('::','_') for name in MODULES}
REQUIRED |= set(MODULE_ROLES.values())
NUMERIC={'minPPlen':(20,120),'maxPPlen':(20,120),'flankLen':(1,50000),'maxDistFromTE':(0,100000),'fastaOutputLimit':(0,100),'prodigalScoreThresh':(-1000,1000),'sameStrandReward':(-100,100)}


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def configuration(api,path,inner,prodigal):
    text=api['load_bytes'](path).decode();values={}
    if not text.strip():raise ValueError('NATIVE_CONFIG_NONEMPTY_REQUIRED')
    allowed=set(NUMERIC)|{'prepeptab','prodigalshortbin','sqlite3fn','blastdbdir'}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):continue
        fields=line.split()
        if line[0].isspace() or len(fields)!=2 or fields[0] not in allowed or fields[0] in values:raise ValueError('NATIVE_CONFIG_ALLOWLIST_OR_TWO_FIELDS_REQUIRED')
        key,value=fields;values[key]=value
        if key in NUMERIC:
            if not re.fullmatch(r'-?(?:\d+(?:\.\d*)?|\.\d+)',value):raise ValueError('NATIVE_CONFIG_NUMBER_INVALID')
            number=float(value);low,high=NUMERIC[key]
            if not math.isfinite(number) or not low<=number<=high or (key not in {'prodigalScoreThresh','sameStrandReward'} and not number.is_integer()):raise ValueError('NATIVE_CONFIG_NUMBER_RANGE')
    if values.get('prodigalshortbin')!=prodigal:raise ValueError('NATIVE_CONFIG_EXACT_PRODIGAL_REQUIRED')
    for key,wanted in {'sqlite3fn':str(inner/'sqlite/ripper.sqlite3'),'blastdbdir':str(inner/'blastdb')}.items():
        if key in values and values[key]!=wanted:raise ValueError('NATIVE_CONFIG_OUTPUT_NAMESPACE_MISMATCH')
    table=values.get('prepeptab','ripper')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}',table):raise ValueError('NATIVE_CONFIG_TABLE_INVALID')
    if float(values.get('minPPlen',20))>float(values.get('maxPPlen',120)):raise ValueError('NATIVE_CONFIG_PEPTIDE_RANGE_INVALID')
    return dict(values=values,table=table,min_peptide_length=int(values.get('minPPlen',20)),max_peptide_length=int(values.get('maxPPlen',120)))


def prepare(api,spec,spec_sha,bound,sources,adaptation,inner,review_path=None):
    """Only a matching, explicit parent review can close execution holds.

    Review/runtime declarations are byte-bound content, not authenticated identities.
    The parent must review the concrete request before supplying approval.
    """
    result={'contract':CONTRACT,'holds':[],'review_content_authentication':'UNATTESTED_EXPLICIT_PARENT_REVIEW_CONTENT','hmm_annotation':'NOT_RUN_SEPARATE_STAGE','scientific_holds':['HOLD_COORDINATE_PRODUCER','HOLD_BGC_MEMBERSHIP','HOLD_HMM_ANNOTATION_NOT_RUN','HOLD_DISTRIBUTION_RIGHTS_UNVERIFIED']}
    if not hasattr(sqlite3.Connection,'deserialize'):result['holds'].append('HOLD_SQLITE_SNAPSHOT_DEPENDENCY')
    interface=api['owned_module']('ripper_source_admission').NATIVE_INTERFACES.get(bound.get('upstream_source',{}).get('sha256'))
    result.update(source_interface=interface or 'UNREVIEWED',requires_discovery_declaration=interface=='n3',additional_required_roles=['source_discovery_contract'] if interface=='n3' else [])
    if 'upstream_source' in bound and not interface:result['holds'].append('HOLD_NATIVE_SOURCE_INTERFACE_UNREVIEWED')
    if (REQUIRED|set(result['additional_required_roles']))-set(bound):
        result['holds']+=['HOLD_MISSING_NATIVE_ROLES','HOLD_LOCAL_SOURCE_EXECUTION_ADMISSION'];return result
    if bound['perl_dispatcher']['sha256']!=DISPATCHER_SHA256:result['holds'].append('HOLD_NATIVE_DISPATCHER_INTERFACE_UNREVIEWED')
    closure=api['json_input'](bound['source_closure']['path'],sources)
    if interface=='n3':
        if not isinstance(closure,dict) or closure.get('schema')!='lane05-n3-proposed-source-handoff-v1' or closure.get('native_execution')!='NOT_EXECUTED':raise ValueError('NATIVE_N3_SOURCE_CLOSURE_INVALID')
        try:
            wanted={'archived_base':closure['original_base']['sha256'],'upstream_source':closure['proposed_source']['sha256'],'source_patch':closure['patches']['cumulative.patch']['sha256'],'adaptation_receipt':closure['owner_receipt']['sha256']}
        except (KeyError,TypeError) as exc:raise ValueError('NATIVE_N3_SOURCE_CLOSURE_INVALID') from exc
        if any(bound[k]['sha256']!=v for k,v in wanted.items()):raise ValueError('NATIVE_SOURCE_CLOSURE_BYTE_MISMATCH')
        definition=api['json_input'](bound['source_discovery_contract']['path'],sources)
        if not isinstance(definition,dict) or definition.get('schema')!='lane05-tiny-native-discovery-proposed-n3-contract-v1' or not isinstance(definition.get('selected_source'),dict) or definition['selected_source'].get('sha256')!=bound['upstream_source']['sha256'] or not isinstance(definition.get('raw_output_schema'),dict) or definition['raw_output_schema'].get('sqlite_columns')!=['acc','species','ppser','fastaid','aaseq','ppstrand','testrand','pptedist','score']:
            raise ValueError('NATIVE_N3_DISCOVERY_CONTRACT_MISMATCH')
        result['source_discovery_contract_sha256']=sources[-1]['sha256']
    else:
        if not isinstance(closure,dict) or closure.get('schema')!='lane05-ripper-adapted-source-profile-v1' or closure.get('source_revision')!=spec.get('source_revision') or not isinstance(closure.get('files'),list):raise ValueError('NATIVE_SOURCE_CLOSURE_INVALID')
        if not 1<=len(closure['files'])<=32 or any(not isinstance(x,dict) or not isinstance(x.get('role'),str) or not isinstance(x.get('sha256'),str) for x in closure['files']):raise ValueError('NATIVE_SOURCE_CLOSURE_ROSTER_INVALID')
        listed={x['role']:x['sha256'] for x in closure['files']}
        if len(listed)!=len(closure['files']):raise ValueError('NATIVE_SOURCE_CLOSURE_DUPLICATE_ROLE')
        for role,key in {'archived_base':'archived_base','adapted_source':'upstream_source','cumulative_patch':'source_patch'}.items():
            if listed.get(role)!=bound[key]['sha256']:raise ValueError('NATIVE_SOURCE_CLOSURE_BYTE_MISMATCH')
    input_basename=Path(bound['genbank']['path']).name
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*\.[A-Za-z0-9]+',input_basename):raise ValueError('NATIVE_SAFE_INPUT_BASENAME_REQUIRED')
    conf=configuration(api,bound['config']['path'],inner,bound['prodigal_short']['path']);result['config']=conf
    query=api['queries_input'](bound['queries']['path'],sources)
    if len(query)!=1:raise ValueError('NATIVE_SINGLE_QUERY_CONTEXT_REQUIRED')
    semantic=api['validate_local_semantics'](api['load_bytes'](bound['genbank']['path']).decode(),api['load_bytes'](bound['query_fasta']['path']).decode(),query[0]);result['semantic_validation']=semantic
    if semantic.get('status')!='PASS_INPUT_BINDING_ONLY':result['holds'].append('HOLD_NATIVE_INPUT_SEMANTIC_DEPENDENCY')
    elif semantic.get('query_relation')!='EXACT_SEQUENCE_SELF_MATCH_ONLY':result['holds'].append('HOLD_NATIVE_EXACT_QUERY_SUBJECT_REQUIRED')
    runtime=api['json_input'](bound['runtime_receipt']['path'],sources)
    if not isinstance(runtime,dict) or runtime.get('schema_version')!='ripper-native-runtime/1' or runtime.get('state')!='PROBED_NATIVE_RUNTIME_CONTENT_UNATTESTED':
        result['holds'].append('HOLD_NATIVE_RUNTIME_RECEIPT')
    else:
        hashes=runtime.get('tool_sha256');versions=runtime.get('tool_versions');modules=runtime.get('module_versions')
        if not isinstance(hashes,dict) or any(hashes.get(k)!=bound[k]['sha256'] for k in TOOLS):result['holds'].append('HOLD_NATIVE_RUNTIME_TOOL_BYTES')
        if not isinstance(versions,dict) or any(not isinstance(versions.get(k),str) or not versions[k].strip() or versions[k].strip().upper() in {'MISSING','UNAVAILABLE','UNKNOWN','NOT_PROBED','UNVERIFIED'} for k in TOOLS):result['holds'].append('HOLD_NATIVE_TOOL_VERSIONS')
        if not isinstance(modules,dict) or any(not isinstance(modules.get(k),str) or not modules[k].strip() or modules[k].strip().upper() in {'MISSING','UNAVAILABLE','UNKNOWN','NOT_PROBED','UNVERIFIED'} for k in MODULES):result['holds'].append('HOLD_NATIVE_PERL_MODULES')
        tool_exits=runtime.get('tool_probe_exit_codes');module_exits=runtime.get('module_probe_exit_codes')
        if runtime.get('probed_interpreter_sha256')!=bound['perl_runtime']['sha256'] or not isinstance(tool_exits,dict) or any(type(tool_exits.get(k)) is not int or tool_exits[k]!=0 for k in TOOLS) or not isinstance(module_exits,dict) or any(type(module_exits.get(k)) is not int or module_exits[k]!=0 for k in MODULES):result['holds'].append('HOLD_NATIVE_PROBE_COMPLETION')
        module_hashes=runtime.get('module_sha256');module_paths=runtime.get('module_paths')
        if not isinstance(module_hashes,dict) or not isinstance(module_paths,dict) or any(module_hashes.get(k)!=bound[role]['sha256'] or module_paths.get(k)!=bound[role]['path'] for k,role in MODULE_ROLES.items()):result['holds'].append('HOLD_NATIVE_PERL_MODULE_BYTES')
        decisions={'prodigal_short_validation':'SHORT_ORF_BEHAVIOR_REVIEWED','blast_database_format_validation':'REVIEWED_FOR_SELECTED_SOURCE','blast_pairwise_parser_validation':'REVIEWED_FOR_SELECTED_BIOPERL'}
        if any(runtime.get(k)!=v for k,v in decisions.items()) or runtime.get('prodigal_recipe_sha256')!=bound['prodigal_recipe']['sha256']:result['holds'].append('HOLD_NATIVE_TOOL_BEHAVIOR_REVIEW')
    libraries=runtime.get('perl5lib',[]) if isinstance(runtime,dict) else []
    if not isinstance(libraries,list) or len(libraries)>16 or any(not isinstance(x,str) or not Path(x).is_absolute() or ':' in x or x=='/Network' or x.startswith('/Network/') or Path(x).is_symlink() or not Path(x).is_dir() for x in libraries):raise ValueError('NATIVE_PERL_LIBRARY_PATH_INVALID')
    for name,role in MODULE_ROLES.items():
        suffix=Path(*name.split('::')).with_suffix('.pm')
        if not any(Path(library)/suffix==Path(bound[role]['path']) for library in libraries):result['holds'].append('HOLD_NATIVE_MODULE_LIBRARY_BINDING')
    closure_selected=spec.get('bind_observed_runtime_closure',False)
    if type(closure_selected) is not bool:raise ValueError('NATIVE_RUNTIME_CLOSURE_SELECTION_INVALID')
    result['observed_runtime_closure']={'status':'NOT_SELECTED_NO_TRANSITIVE_CLOSURE_CLAIM'}
    if closure_selected:
        entries=runtime.get('transitive_loaded_bindings') if isinstance(runtime,dict) else None
        if not isinstance(entries,list) or not 1<=len(entries)<=512:raise ValueError('NATIVE_RUNTIME_CLOSURE_ROSTER_INVALID')
        seen=set();total=0
        for entry in entries:
            if not isinstance(entry,dict) or set(entry)!={'path','bytes','sha256'} or not isinstance(entry['path'],str) or type(entry['bytes']) is not int or not 0<=entry['bytes']<=5*1024**2 or not isinstance(entry['sha256'],str) or not re.fullmatch(r'[0-9a-f]{64}',entry['sha256']):raise ValueError('NATIVE_RUNTIME_CLOSURE_ENTRY_INVALID')
            p=Path(entry['path']);total+=entry['bytes']
            if not p.is_absolute() or '..' in p.parts or str(p)=='/Network' or str(p).startswith('/Network/') or not any(Path(lib) in p.parents for lib in libraries) or str(p) in seen or total>64*1024**2:raise ValueError('NATIVE_RUNTIME_CLOSURE_PATH_OR_BUDGET_INVALID')
            seen.add(str(p));fresh=api['binding'](p,api['load_bytes'](p));sources.append(fresh)
            if fresh!=entry:raise ValueError('NATIVE_RUNTIME_CLOSURE_BYTES_MISMATCH')
        result['observed_runtime_closure']={'status':'EXACT_OBSERVED_FILES_BOUND_NOT_EXHAUSTIVE_RUNTIME_PROOF','file_count':len(entries),'bytes':total,'roster_sha256':digest(entries),'scope':'Owner-observed transitive files only, not all possible late loads or whole-system closure'}
    directories=list(dict.fromkeys(str(Path(bound[k]['path']).parent) for k in ('makeblastdb','blastp','blastn')));path=os.pathsep.join(directories)
    for k in ('makeblastdb','blastp','blastn'):
        selected=shutil.which(k,path=path)
        if selected is None or str(Path(selected).resolve())!=bound[k]['path']:result['holds'].append('HOLD_NATIVE_CONTROLLED_PATH_'+k.upper())
    env={'PATH':path,'LC_ALL':'C','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','TMPDIR':str(inner.parent/'runtime_tmp')}
    prefix=[bound['perl_runtime']['path'],bound['perl_dispatcher']['path'],str(len(libraries)),*libraries,bound['upstream_source']['path']]
    argv=prefix+['--run-root',str(inner),'--temp-root',str(inner/'temp'),'--conffile',bound['config']['path'],'--outdir',str(inner/'output'),'--outfile','summary.tsv','--queryfn',bound['query_fasta']['path'],'--',bound['genbank']['path']]
    if interface=='n3':
        argv=prefix+['--run-root',str(inner),'--temp-root',str(inner/'temp'),'--conffile',bound['config']['path'],'--queryfn',bound['query_fasta']['path'],'--outdir',str(inner/'output'),'--',bound['genbank']['path']]
    runner_hashes={}
    for name in ('ripper_adapter.py','ripper_run_binding.py','ripper_source_admission.py','ripper_lifecycle.py','ripper_native_contract.py','ripper_raw_discovery.py'):
        p=Path(__file__).with_name(name);b=api['binding'](p,api['load_bytes'](p));sources.append(b);runner_hashes[name]=b['sha256']
    request={'source_interface':interface or 'UNREVIEWED','requires_discovery_declaration':interface=='n3','adapter_sqlite_version':sqlite3.sqlite_version,'runner_sha256':runner_hashes,'schema_version':'ripper-native-admission/1','decision':'PENDING_PARENT_REVIEW','reviewer':'parent','evidence_kind':'operator_supplied','contract':CONTRACT,'spec_sha256':spec_sha,'adapted_profile_sha256':adaptation['artifact_sha256'],'file_sha256':{k:v['sha256'] for k,v in bound.items()},'argv_sha256':digest(argv),'environment_sha256':digest(env),'semantic_sha256':digest(semantic),'local_use_decision':'PENDING_LOCAL_EXECUTION_REVIEW_NO_DISTRIBUTION_CLEARANCE'}
    result.update(argv=argv,environment=env,review_request=request,expected_subject=query[0]['enzyme_accession'],input_basename=input_basename,table=conf['table'])
    if review_path:
        review=api['json_input'](review_path,sources)
        expected=dict(request,decision='APPROVED_NATIVE_LOCAL_EXECUTION',local_use_decision='REVIEWED_LOCAL_EXECUTION_ONLY_NO_DISTRIBUTION_CLEARANCE')
        if not isinstance(review,dict) or any(review.get(k)!=v for k,v in expected.items()):raise ValueError('NATIVE_PARENT_REVIEW_BINDING_MISMATCH')
        result['parent_review_sha256']=sources[-1]['sha256']
    else:result['holds'].append('HOLD_LOCAL_SOURCE_EXECUTION_ADMISSION')
    result['holds']=sorted(set(result['holds']));return result
