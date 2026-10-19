"""Bounded local lifecycle; reviewed opt-in native discovery or explicit tiny stubs.

Native RiPPER execution requires a concrete byte-bound parent review admission.
Polling limits are supervisory, not hard OS quotas or a network/filesystem sandbox.
"""
import csv,hashlib,io,json,math,os,signal,subprocess,time,sys
from datetime import datetime,timezone
from pathlib import Path

NATIVE_CONTRACT_VERSION='ripper-native-discovery/1'


def policy(spec):
    limits=spec.get('limits')
    if not isinstance(limits,dict):raise ValueError('RUNNER_LIMITS_REQUIRED')
    ceilings={'wall_seconds':3600,'rss_bytes':(2 if spec.get('mode')=='adapted_local05' else 1)*1024**3,'disk_bytes':256*1024**2,'poll_seconds':0.25}
    for key,ceiling in ceilings.items():
        v=limits.get(key)
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<v<=ceiling:
            raise ValueError('RUNNER_LIMIT_INVALID: '+key)
    if limits['poll_seconds']<0.01 or type(limits['rss_bytes']) is not int or type(limits['disk_bytes']) is not int:
        raise ValueError('RUNNER_LIMIT_INVALID')
    return limits


def disk_size(root):
    total=0
    for here,dirs,files in os.walk(root,followlinks=False):
        for name in dirs+files:
            p=Path(here)/name
            if p.is_symlink():raise ValueError('RUNNER_OUTPUT_SYMLINK_REFUSED')
        for name in files:total+=(Path(here)/name).stat().st_size
    return total


def write_new(path,data):
    with path.open('x',encoding='utf8') as handle:json.dump(data,handle,sort_keys=True,indent=2);handle.write('\n')


def write_terminal(path,result):
    """Serialize off-canonical; publish only after a complete successful close.

    Staging bytes are retained and never constitute a terminal. The exclusive
    canonical hard link is the final filesystem operation and commit marker.
    """
    staging=path.with_name(path.name+'.staging')
    result['terminal_publication']={'protocol':'EXCLUSIVE_CANONICAL_LINK_AFTER_SERIALIZATION',
        'canonical_name':path.name,'staging_names_are_not_completion':True}
    try:write_new(staging,result)
    except KeyboardInterrupt as exc:
        result['terminal_write_prior_reason']=result.get('reason')
        result['terminal_write_prior_error']=result.get('error')
        result.setdefault('primary_status',result.get('status'))
        result.setdefault('primary_reason',result.get('reason'))
        result.setdefault('primary_error',result.get('error'))
        result.update(status='INTERRUPTED',reason='KEYBOARD_INTERRUPT_DURING_TERMINAL_WRITE',
            terminal_write_error=str(exc),output_admission='NOT_ADMITTED')
        result.pop('retained_row_count',None)
        if 'raw_discovery' in result:
            result['raw_discovery'].update(candidate_count=None,admission='NOT_ADMITTED_BY_TERMINAL')
        if staging.exists() or staging.is_symlink():
            result['interrupted_terminal_write']=output_binding(staging,256*1024**2)
        else:result['interrupted_terminal_write']='NO_PARTIAL_FILE_CREATED'
        result['terminal_utc']=datetime.now(timezone.utc).isoformat()
        staging=path.with_name(path.name+'.recovery.staging')
        # Repeated interruption or any I/O failure leaves no canonical terminal.
        write_new(staging,result)
    # A writer/open/close/preservation failure above cannot expose success bytes
    # under the canonical name. Retain staging without cleanup after publication.
    os.link(staging,path,follow_symlinks=False)


def stop_group(child,observations=None):
    errors=[];observations={} if observations is None else observations
    # These observations concern this group/leader at the check, not detached descendants.
    observations['process_group']=child.pid
    try:os.killpg(child.pid,signal.SIGKILL)
    except ProcessLookupError:
        observations['group_signal']='GROUP_ABSENT_AT_SIGNAL_CHECK'
    except OSError as exc:
        observations['group_signal']='SIGNAL_UNAVAILABLE';errors.append(str(exc))
    else:observations['group_signal']='SIGKILL_REQUEST_SENT'
    if child.poll() is None:
        observations['leader_kill']='REQUESTED'
        try:child.kill()
        except OSError as exc:
            observations['leader_kill']='UNAVAILABLE';errors.append(str(exc))
    else:observations['leader_kill']='NOT_REQUIRED_EXIT_OBSERVED'
    observations['leader_reap']='REQUESTED'
    try:child.wait(timeout=2)
    except subprocess.TimeoutExpired:
        observations['leader_reap']='TIMED_OUT';errors.append('CHILD_REAP_TIMEOUT')
    else:observations['leader_reap']='RETURNED'
    return errors


def output_binding(path,cap):
    if path.is_symlink() or not path.is_file():raise ValueError('RUNNER_OUTPUT_NOT_REGULAR')
    digest=hashlib.sha256();size=0
    with path.open('rb') as handle:
        while True:
            chunk=handle.read(1024*1024)
            if not chunk:break
            size+=len(chunk)
            if size>cap:raise ValueError('RUNNER_RECEIPT_HASH_CAP_EXCEEDED')
            digest.update(chunk)
    return dict(path=str(path.resolve()),bytes=size,sha256=digest.hexdigest())


def lifecycle(api,spec_path,supplied,run_root,adapted_profile_path=None,execute_stub=False,cancel_path=None,execute_native=False,native_admission_path=None,resume_preflight=False):
    sources=[];spec=api['json_input'](spec_path,sources)
    if not isinstance(spec,dict) or spec.get('schema_version')!='ripper-lifecycle-spec/1':raise ValueError('RUNNER_SPEC_INVALID')
    limits=policy(spec);mode=spec.get('mode')
    if mode not in ('synthetic_stub','adapted_local05'):raise ValueError('RUNNER_MODE_INVALID')
    if execute_stub and mode!='synthetic_stub':raise ValueError('RUNNER_STUB_EXECUTION_MODE_REQUIRED')
    if execute_native and mode!='adapted_local05':raise ValueError('RUNNER_NATIVE_EXECUTION_MODE_REQUIRED')
    if execute_stub and execute_native:raise ValueError('RUNNER_EXECUTION_MODES_EXCLUSIVE')
    if native_admission_path and mode!='adapted_local05':raise ValueError('RUNNER_NATIVE_ADMISSION_MODE_REQUIRED')
    module=api['owned_module']('ripper_run_binding')
    bound=module.files(api,spec.get('files'),supplied,sources,spec.get('model_byte_budget'),spec.get('hash_timeout_seconds',30),spec.get('executable_byte_budget'),spec.get('executable_hash_timeout_seconds',30))
    profile=api['source_contract'](spec.get('profile_id'),sources)
    if spec.get('source_revision')!=profile['revision']:raise ValueError('RUNNER_SOURCE_REVISION_MISMATCH')
    adaptation=None
    if mode=='adapted_local05':
        if not adapted_profile_path:raise ValueError('RUNNER_EXPLICIT_ADAPTED_PROFILE_REQUIRED')
        adaptation=api['owned_module']('ripper_source_admission').verify_adapted(api,adapted_profile_path,bound,sources)
    elif adapted_profile_path:raise ValueError('RUNNER_STUB_CANNOT_CLAIM_ADAPTED_SOURCE')
    root=Path(run_root)
    if resume_preflight and (not execute_native or not root.is_dir()):raise ValueError('RUNNER_REVIEWED_PREFLIGHT_RESUME_REQUIRED')
    if not root.is_absolute() or root.is_symlink() or (root.exists() and not resume_preflight):raise ValueError('RUNNER_FRESH_ABSOLUTE_ROOT_REQUIRED')
    candidate=Path(__file__).resolve().parents[1]
    resolved=root.resolve()
    if candidate==resolved or candidate in resolved.parents:raise ValueError('RUNNER_ROOT_MUST_BE_EXTERNAL')
    for part in root.parents:
        if part.is_symlink():raise ValueError('RUNNER_ROOT_SYMLINK_PARENT_REFUSED')
    for b in sources:
        p=Path(b['path'])
        if resolved==p or resolved in p.parents:raise ValueError('RUNNER_ROOT_OVERLAPS_INPUT')
    cancel=Path(cancel_path) if cancel_path else None
    if cancel and (not cancel.is_absolute() or cancel.is_symlink() or cancel.resolve()==resolved or resolved in cancel.resolve().parents):
        raise ValueError('RUNNER_CANCEL_PATH_INVALID')
    native_module=api['owned_module']('ripper_native_contract') if mode=='adapted_local05' else None
    required={'python_runtime','stub_script','config'} if mode=='synthetic_stub' else native_module.REQUIRED
    missing=sorted(required-set(bound))
    native=native_module.prepare(api,spec,sources[0]['sha256'],bound,sources,adaptation,resolved/'upstream_run',native_admission_path) if native_module else None
    holds=native['holds'] if native else []
    if native:missing=sorted((required|set(native.get('additional_required_roles',[])))-set(bound))
    for role in required & set(bound):
        if role in {'python_runtime','perl_runtime','makeblastdb','blastp','blastn','prodigal_short','hmmsearch'} and not os.access(bound[role]['path'],os.X_OK):missing.append('executable:'+role)
    psutil=None
    execution_selected=execute_stub or execute_native
    if execution_selected and not missing and not holds:
        try:import psutil
        except ImportError:missing.append('optional_psutil')
    result=dict(schema_version='ripper-lifecycle/1',status=('HOLD' if mode=='adapted_local05' else 'UNAVAILABLE') if missing else 'HOLD' if holds else 'READY_NATIVE_REVIEWED_NOT_EXECUTED' if native else 'NOT_EXECUTED',mode=mode,
        upstream_execution='NOT_EXECUTED',stub_execution='NOT_EXECUTED',candidate_bgc_membership='UNVERIFIED',biological_absence_inferred=False,
        native_contract=native,created_utc=datetime.now(timezone.utc).isoformat(),adapter_python_version=sys.version,tool_versions='NATIVE_VERSIONS_FROM_BOUND_UNATTESTED_RUNTIME_RECEIPT' if native else 'NOT_PROBED; exact explicit bytes bound',sources=sources,files=bound,adaptation=adaptation,limits=limits,missing=missing,holds=holds,run_root=str(resolved),
        enforcement='sampled process-tree RSS/wall/disk; limits can overshoot between samples; not OS quotas or a security sandbox',
        interruption_limit='SIGKILL/machine loss may leave STARTED without TERMINAL; missing terminal is never completion')
    if native and native.get('argv'):
        result['prepared_argv']=native['argv']
        result['prepared_argv_status']='REVIEWED_READY' if not holds and not missing else 'HELD_PENDING_EXACT_NATIVE_ADMISSION'
    # Rehash all explicit inputs immediately before making any run artifacts.
    for b in sources:
        fresh=api['tool_binding'](b['path'],b['byte_budget'],b['hash_timeout_seconds']) if b.get('hash_mode')=='streamed_executable' else api['stream_binding'](b['path'],b['byte_budget'],b['hash_timeout_seconds']) if b.get('hash_mode')=='streamed_model' else api['tool_binding'](b['path']) if b.get('hash_mode')=='bounded_tool_16MiB' else api['binding'](b['path'],api['load_bytes'](b['path']))
        if fresh!=b:raise ValueError('RUNNER_INPUT_CHANGED_BEFORE_START')
    if resume_preflight:
        allowed={'PREFLIGHT.json','TERMINAL.json','NATIVE_REVIEW_REQUEST.json'}
        names={p.name for p in root.iterdir()}
        staging=root/'TERMINAL.json.staging'
        if names not in (allowed,allowed|{staging.name}) or any(p.is_symlink() or not p.is_file() for p in root.iterdir()):raise ValueError('RUNNER_PREFLIGHT_ROOT_NOT_PRISTINE')
        if staging.name in names and not os.path.samefile(staging,root/'TERMINAL.json'):raise ValueError('RUNNER_PREFLIGHT_PUBLICATION_PAIR_MISMATCH')
        old=api['json_input'](root/'PREFLIGHT.json',sources);terminal=api['json_input'](root/'TERMINAL.json',sources);request=api['json_input'](root/'NATIVE_REVIEW_REQUEST.json',sources)
        if not isinstance(old,dict) or not isinstance(old.get('sources'),list) or not old['sources'] or not isinstance(old['sources'][0],dict) or not isinstance(terminal,dict) or old.get('schema_version')!='ripper-lifecycle/1' or old.get('mode')!='adapted_local05' or old.get('files')!=bound or old.get('adaptation')!=adaptation or old.get('run_root')!=str(resolved) or old.get('sources',[{}])[0].get('sha256')!=sources[0]['sha256'] or terminal.get('upstream_execution')!='NOT_EXECUTED' or terminal.get('status') not in {'HOLD','READY_NATIVE_REVIEWED_NOT_EXECUTED'} or request!=native.get('review_request'):
            raise ValueError('RUNNER_PREFLIGHT_BOUNDARY_CHANGED')
        preflight_name='EXECUTION_PREFLIGHT.json';terminal_name='EXECUTION_TERMINAL.json'
    else:
        root.parent.mkdir(parents=True,exist_ok=True);root.mkdir()
        preflight_name='PREFLIGHT.json';terminal_name='TERMINAL.json'
    write_new(root/preflight_name,result)
    if native and native.get('review_request') and not resume_preflight:write_new(root/'NATIVE_REVIEW_REQUEST.json',native['review_request'])
    if not execution_selected or missing or holds:
        result['terminal_utc']=datetime.now(timezone.utc).isoformat()
        write_terminal(root/terminal_name,result);return result
    child=None;started=time.monotonic();reason=None;peak_rss=peak_disk=0
    argv=native['argv'] if execute_native else [bound['python_runtime']['path'],'-I','-S','-B',bound['stub_script']['path'],str(root/'result.tsv')]
    environment=native['environment'] if execute_native else {'PATH':'','LC_ALL':'C','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}
    result.update(status='STARTED',stub_execution='NOT_EXECUTED' if execute_native else 'STARTED_SYNTHETIC_ONLY',argv=argv,psutil_version=psutil.__version__)
    result['rss_sampling_observations']={'vanished_member_samples':0,'zombie_member_samples':0,'absent_tree_samples':0,'zombie_tree_samples':0,'zero_contribution_scope':'Only processes observed vanished/zombie during sampling; inspection denial remains supervision unavailable'}
    write_new(root/'STARTED.json',result)
    try:
        if cancel and cancel.exists():reason='CANCEL_REQUESTED_BEFORE_LAUNCH'
        else:
            if execute_native:(resolved/'runtime_tmp').mkdir(mode=0o700)
            with (root/'stdout.log').open('xb') as stdout,(root/'stderr.log').open('xb') as stderr:
                child=subprocess.Popen(argv,cwd=root,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True,
                    env=environment)
                result['pid']=child.pid
                if execute_native:result['upstream_execution']='EXECUTED_NATIVE_LOCAL_ADAPTER_OBSERVED'
                write_new(root/'LAUNCHED.json',dict(pid=child.pid,argv=argv,created_utc=datetime.now(timezone.utc).isoformat(),process_group=child.pid,stub_execution='NOT_EXECUTED' if execute_native else 'STARTED_SYNTHETIC_ONLY',upstream_execution=result['upstream_execution']))
                while True:
                    elapsed=time.monotonic()-started
                    if cancel and cancel.exists():reason='CANCEL_REQUESTED';break
                    if elapsed>limits['wall_seconds']:reason='WALL_LIMIT';break
                    disk=disk_size(root);peak_disk=max(peak_disk,disk)
                    if disk>limits['disk_bytes']:reason='DISK_LIMIT';break
                    try:
                        proc=psutil.Process(child.pid);tree=[proc]+proc.children(recursive=True);rss=0
                        for member in tree:
                            try:member_rss=member.memory_info().rss
                            except (psutil.NoSuchProcess,psutil.ZombieProcess) as exc:
                                member_rss=0
                                kind='zombie_member_samples' if isinstance(exc,psutil.ZombieProcess) else 'vanished_member_samples'
                                result['rss_sampling_observations'][kind]+=1
                            rss+=member_rss
                    except (psutil.NoSuchProcess,psutil.ZombieProcess) as exc:
                        rss=0
                        kind='zombie_tree_samples' if isinstance(exc,psutil.ZombieProcess) else 'absent_tree_samples'
                        result['rss_sampling_observations'][kind]+=1
                    peak_rss=max(peak_rss,rss)
                    if rss>limits['rss_bytes']:reason='RSS_LIMIT';break
                    if child.poll() is not None:break
                    time.sleep(limits['poll_seconds'])
            if child.poll() is not None and child.returncode!=0 and not reason:reason='EXIT_NONZERO'
    except KeyboardInterrupt:reason='KEYBOARD_INTERRUPT'
    except (PermissionError,psutil.AccessDenied) as exc:reason='SUPERVISION_UNAVAILABLE';result['error']=str(exc)
    except (OSError,ValueError,psutil.Error) as exc:reason='SUPERVISOR_ERROR';result['error']=str(exc)
    finally:
        if child is not None:
            result['cleanup_observations']={}
            try:cleanup_errors=stop_group(child,result['cleanup_observations'])
            except KeyboardInterrupt as exc:
                cleanup_errors=['CLEANUP_INTERRUPTED_NOT_CERTIFIED'];result['cleanup_interrupt']=str(exc)
                result['primary_reason']=reason;reason='KEYBOARD_INTERRUPT_DURING_CLEANUP'
                try:child.kill();child.wait(timeout=2)
                except (OSError,subprocess.TimeoutExpired,KeyboardInterrupt) as second:cleanup_errors.append(str(second))
            result['returncode']=child.returncode
            if cleanup_errors:
                result['cleanup_errors']=cleanup_errors;result.setdefault('primary_reason',reason);result.setdefault('primary_error',result.get('error'));result['cleanup_reason']='SUPERVISION_UNAVAILABLE';reason='SUPERVISION_UNAVAILABLE'
    result.update(elapsed_seconds=time.monotonic()-started,peak_sampled_rss_bytes=peak_rss,peak_sampled_disk_bytes=peak_disk,
        reason=reason,stub_execution='EXECUTED_SYNTHETIC_ONLY' if child and not execute_native else 'NOT_EXECUTED',status=('HOLD' if execute_native else 'UNAVAILABLE') if reason=='SUPERVISION_UNAVAILABLE' else 'INTERRUPTED' if reason in {'CANCEL_REQUESTED_BEFORE_LAUNCH','CANCEL_REQUESTED','KEYBOARD_INTERRUPT','WALL_LIMIT','DISK_LIMIT','RSS_LIMIT'} else 'FAILED' if reason else 'SUCCESS_UNBOUND')
    result['retained_outputs']={}
    try:
        # Complete inventory is limited to this fresh root; no external discovery.
        result['retained_disk_bytes']=disk_size(root)
        if result['retained_disk_bytes']>limits['disk_bytes'] and not reason:result.update(status='INTERRUPTED',reason='DISK_LIMIT_FINAL')
        for here,dirs,names in os.walk(root,followlinks=False):
            for name in sorted(names):
                p=Path(here)/name;relative=str(p.relative_to(root))
                if relative not in {'TERMINAL.json.staging','TERMINAL.json.recovery.staging','EXECUTION_TERMINAL.json.staging','EXECUTION_TERMINAL.json.recovery.staging','PREFLIGHT.json','STARTED.json','LAUNCHED.json','TERMINAL.json','EXECUTION_PREFLIGHT.json','EXECUTION_TERMINAL.json','NATIVE_REVIEW_REQUEST.json'}:
                    result['retained_outputs'][relative]=output_binding(p,256*1024**2)
        if result['status']=='SUCCESS_UNBOUND' and execute_native:
            discovery=api['owned_module']('ripper_raw_discovery').parse_discovery(api,resolved/'upstream_run',bound,native)
            discovery['upstream_execution']=result['upstream_execution']
            discovery['evidence_kind']='local_adapter_observed_native'
            write_new(root/'RAW_DISCOVERY.json',discovery)
            result['raw_discovery']=dict(status=discovery['status'],candidate_count=discovery['candidate_count'],retained_raw_candidate_count=discovery['retained_raw_candidate_count'],sha256=output_binding(root/'RAW_DISCOVERY.json',5*1024**2)['sha256'])
            result['retained_outputs']['RAW_DISCOVERY.json']=output_binding(root/'RAW_DISCOVERY.json',5*1024**2)
            result['status']=discovery['status'];result['outcome_scope']='RAW_NATIVE_DISCOVERY_ONLY_HMM_ANNOTATION_NOT_RUN'
        elif result['status']=='SUCCESS_UNBOUND':
            raw=api['load_bytes'](root/'result.tsv')
            if api['binding'](root/'result.tsv',raw)!=result['retained_outputs'].get('result.tsv'):raise ValueError('RUNNER_CONSUMED_OUTPUT_BINDING_MISMATCH')
            result['consumed_result_sha256']=hashlib.sha256(raw).hexdigest()
            rows=list(csv.reader(io.StringIO(raw.decode()),delimiter='\t'))
            if not rows or rows[0]!=profile['headers'] or any(len(row)!=len(rows[0]) for row in rows[1:]):raise ValueError('RUNNER_STUB_OUTPUT_SHAPE_INVALID')
            result['status']='NO_HIT' if len(rows)==1 else 'SUCCESS_UNBOUND'
            result['retained_row_count']=len(rows)-1;result['outcome_scope']='SELF_AUTHORED_STUB_ROWS_ONLY_NOT_RIPPER_OR_BIOLOGICAL_ABSENCE'
        for b in sources:
            fresh=api['tool_binding'](b['path'],b['byte_budget'],b['hash_timeout_seconds']) if b.get('hash_mode')=='streamed_executable' else api['stream_binding'](b['path'],b['byte_budget'],b['hash_timeout_seconds']) if b.get('hash_mode')=='streamed_model' else api['tool_binding'](b['path']) if b.get('hash_mode')=='bounded_tool_16MiB' else api['binding'](b['path'],api['load_bytes'](b['path']))
            if fresh!=b:raise ValueError('RUNNER_INPUT_CHANGED_DURING_NATIVE' if execute_native else 'RUNNER_INPUT_CHANGED_DURING_STUB')
        for name,b in result['retained_outputs'].items():
            if output_binding(root/name,256*1024**2)!=b:raise ValueError('RUNNER_OUTPUT_CHANGED_BEFORE_TERMINAL: '+name)
    except KeyboardInterrupt as exc:
        result.setdefault('primary_reason',result.get('reason'));result.setdefault('primary_error',result.get('error'))
        result.update(status='INTERRUPTED',reason='KEYBOARD_INTERRUPT_DURING_FINALIZATION',error=str(exc))
    except (OSError,ValueError,UnicodeError,csv.Error) as exc:
        result.setdefault('primary_reason',result.get('reason'));result.setdefault('primary_error',result.get('error'))
        if result.get('reason')=='SUPERVISION_UNAVAILABLE' or result.get('cleanup_errors'):
            result.update(status='HOLD' if execute_native else 'UNAVAILABLE',reason='SUPERVISION_UNAVAILABLE',finalization_error=str(exc))
        else:result.update(status='FAILED',reason='RECEIPT_OR_OUTPUT_VALIDATION_FAILED',error=str(exc))
    result['supervision_cleanup_uncertain']=bool(result.get('cleanup_errors'))
    result['output_admission']='SCOPED_BOUND_BYTES_ONLY' if result['status'] in {'NO_HIT','SUCCESS_UNBOUND','NO_RETAINED_CANDIDATES'} else 'NOT_ADMITTED'
    if result['output_admission']=='NOT_ADMITTED':
        result.pop('retained_row_count',None)
        if 'raw_discovery' in result:
            result['raw_discovery'].update(candidate_count=None,admission='NOT_ADMITTED_BY_TERMINAL')
    result['terminal_utc']=datetime.now(timezone.utc).isoformat()
    write_terminal(root/terminal_name,result);return result
