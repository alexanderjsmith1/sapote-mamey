"""Byte-bound explicit local adaptation metadata; never imports/executes upstream."""
import hashlib,re
NATIVE_INTERFACES={
    "ddfe1a095647095755b80291732fea606a2bee5f5a216326614054316d74acb3":"q3",
    "f37e1341c1f4ba1118fea6d30622bcc65a67d8ec3e9f605ee73d701f3e387ec9":"n3",
    "0b92227d09bb033074ec70379ef27c4767e2ab30c7e478e76e71c3abc13be0f3":"n3",
}


def apply_patch_text(base,patch):
    lines=base.splitlines(keepends=True);diff=patch.splitlines(keepends=True);result=[];cursor=0;index=0;hunks=0;headers=0
    while index<len(diff):
        line=diff[index]
        if line.startswith('--- '):headers+=1
        match=re.match(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@',line)
        if not match:index+=1;continue
        if headers!=1:raise ValueError('ADAPTED_PROFILE_SINGLE_FILE_PATCH_REQUIRED')
        start=int(match.group(1))-1;old_count=int(match.group(2) or '1');new_count=int(match.group(4) or '1')
        if start<cursor or start>len(lines):raise ValueError('ADAPTED_PROFILE_PATCH_POSITION_INVALID')
        result.extend(lines[cursor:start]);cursor=start;used=created=0;index+=1
        while index<len(diff) and not diff[index].startswith(('@@ ','--- ')):
            part=diff[index];prefix=part[:1]
            if prefix in (' ','-'):
                if cursor>=len(lines) or lines[cursor]!=part[1:]:raise ValueError('ADAPTED_PROFILE_PATCH_PREIMAGE_MISMATCH')
                if prefix==' ':result.append(part[1:]);created+=1
                cursor+=1;used+=1
            elif prefix=='+':result.append(part[1:]);created+=1
            else:raise ValueError('ADAPTED_PROFILE_PATCH_FORMAT_UNSUPPORTED')
            index+=1
        if used!=old_count or created!=new_count:raise ValueError('ADAPTED_PROFILE_PATCH_COUNT_MISMATCH')
        hunks+=1
    if headers!=1 or not hunks:raise ValueError('ADAPTED_PROFILE_PATCH_REQUIRED')
    result.extend(lines[cursor:]);return ''.join(result)


def admit_adapted_profile(api,owner_path,base_path,patch_path,adapted_path,out):
    sources=[];owner=api['json_input'](owner_path,sources);owner_sha=sources[-1]['sha256'];profile=api['source_contract']('archived-e90b3e6-mergeRidePfam',sources)
    raw={}
    for role,path in (('base',base_path),('patch',patch_path),('adapted',adapted_path)):
        raw[role]=api['load_bytes'](path);sources.append(api['binding'](path,raw[role]))
    bound={role:hashlib.sha256(value).hexdigest() for role,value in raw.items()}
    expected=next(x['sha256'] for x in profile['reviewed_sources'] if x['file']=='ripper_local.pl')
    if bound['base']!=expected:raise ValueError('ADAPTED_PROFILE_ARCHIVED_BASE_MISMATCH')
    provenance=owner.get('provenance',{}) if isinstance(owner,dict) else {}
    if not isinstance(provenance,dict) or not isinstance(provenance.get('patches'),dict) or not isinstance(provenance['patches'].get('cumulative.patch'),dict):raise ValueError('ADAPTED_PROFILE_OWNER_RECEIPT_INVALID')
    if provenance.get('proposed_sha256')!=bound['adapted'] or provenance.get('patches',{}).get('cumulative.patch',{}).get('sha256')!=bound['patch']:
        raise ValueError('ADAPTED_PROFILE_OWNER_RECEIPT_MISMATCH')
    if apply_patch_text(raw['base'].decode(),raw['patch'].decode()).encode()!=raw['adapted']:
        raise ValueError('ADAPTED_PROFILE_PATCH_POSTIMAGE_MISMATCH')
    text=raw['adapted'].decode()
    if '"run-root=s"' not in text or '"temp-root=s"' not in text:raise ValueError('ADAPTED_PROFILE_EXPLICIT_ROOT_INTERFACE_REQUIRED')
    interface=NATIVE_INTERFACES.get(bound['adapted'])
    phases={'source_interface':interface or 'UNREVIEWED','raw_discovery':{'status':'STATIC_INTERFACE_REVIEW_ONLY_NOT_NATIVE_VALIDATED','hmm_models_required':False,'sqlite_column_count':9,'blastn_required':True},'hmm_annotation':{'status':'NOT_RUN_SEPARATE_ADMISSION','hmm_models_required':True,'merged_column_count':11}} if interface else {'source_interface':'UNREVIEWED','native_execution':'HOLD_INTERFACE_REVIEW'}
    data=dict(phase_contracts=phases,schema_version='ripper-adapted-source-profile/1',adapted_profile_id='local05-'+bound['patch'][:16],base_profile_id=profile['id'],base_revision=profile['revision'],
        archived_base_sha256=bound['base'],source_patch_sha256=bound['patch'],adapted_source_sha256=bound['adapted'],owner_receipt_sha256=owner_sha,
        profile_status='EXPLICIT_LOCAL_ADAPTATION_REVIEW_ONLY',owner_admission='OWNER_RECEIPT_CONTENT_BOUND_NOT_AUTHENTICATED',source_mode='adapted_local05',
        upstream_execution='NOT_EXECUTED',license_status='UNVERIFIED',sources=sources,
        invocation_flags=['--run-root','--temp-root','--conffile','--queryfn','--outdir'],
        holds=['HOLD_NATIVE_RUNTIME_AND_SHORT_PRODIGAL','HOLD_SEPARATE_ANNOTATION_MODEL_AND_INDEX_ADMISSION','HOLD_LOCAL_SOURCE_EXECUTION_ADMISSION','HOLD_COORDINATE_PRODUCER','HOLD_LICENSE'],
        scope='base+patch+postimage byte equality only; no native execution, release or distribution acceptance')
    api['publish'](out,{'ADAPTED_SOURCE_PROFILE.json':data},sources);return data


def verify_adapted(api,path,bound,sources):
    data=api['json_input'](path,sources);artifact_sha=sources[-1]['sha256']
    if not isinstance(data,dict) or data.get('schema_version')!='ripper-adapted-source-profile/1' or data.get('profile_status')!='EXPLICIT_LOCAL_ADAPTATION_REVIEW_ONLY':
        raise ValueError('ADAPTED_PROFILE_EXPLICIT_REVIEW_PROFILE_REQUIRED')
    wanted={'archived_base':data.get('archived_base_sha256'),'source_patch':data.get('source_patch_sha256'),'upstream_source':data.get('adapted_source_sha256'),'adaptation_receipt':data.get('owner_receipt_sha256')}
    if any(not isinstance(v,str) or not re.fullmatch(r'[0-9a-f]{64}',v) for v in wanted.values()) or data.get('adapted_profile_id')!='local05-'+str(data.get('source_patch_sha256'))[:16]:raise ValueError('ADAPTED_PROFILE_DIGEST_OR_ID_INVALID')
    if any(bound.get(k,{}).get('sha256')!=v for k,v in wanted.items()):raise ValueError('ADAPTED_PROFILE_EXPLICIT_FILE_BINDING_MISMATCH')
    # Recompute the actual patch relation, not just mutually consistent declarations.
    base=api['load_bytes'](bound['archived_base']['path']);patch=api['load_bytes'](bound['source_patch']['path']);adapted=api['load_bytes'](bound['upstream_source']['path'])
    if apply_patch_text(base.decode(),patch.decode()).encode()!=adapted:raise ValueError('ADAPTED_PROFILE_PATCH_POSTIMAGE_MISMATCH')
    owner=api['json_input'](bound['adaptation_receipt']['path'],sources)
    prov=owner.get('provenance') if isinstance(owner,dict) else None
    if not isinstance(prov,dict) or prov.get('proposed_sha256')!=data['adapted_source_sha256'] or not isinstance(prov.get('patches'),dict) or not isinstance(prov['patches'].get('cumulative.patch'),dict) or prov['patches']['cumulative.patch'].get('sha256')!=data['source_patch_sha256']:
        raise ValueError('ADAPTED_PROFILE_OWNER_RECEIPT_MISMATCH')
    if '"run-root=s"' not in adapted.decode() or '"temp-root=s"' not in adapted.decode():raise ValueError('ADAPTED_PROFILE_EXPLICIT_ROOT_INTERFACE_REQUIRED')
    original=api['source_contract'](data.get('base_profile_id'),sources)
    expected=next(x['sha256'] for x in original['reviewed_sources'] if x['file']=='ripper_local.pl')
    if data.get('archived_base_sha256')!=expected or data.get('base_revision')!=original['revision']:
        raise ValueError('ADAPTED_PROFILE_ARCHIVED_BASE_MISMATCH')
    return dict(artifact_sha256=artifact_sha,adapted_profile_id=data['adapted_profile_id'],archived_base_sha256=expected,source_patch_sha256=data['source_patch_sha256'],
        adapted_source_sha256=data['adapted_source_sha256'],owner_receipt_sha256=data['owner_receipt_sha256'],profile_status='EXPLICIT_LOCAL_ADAPTATION_REVIEW_ONLY',upstream_execution='NOT_EXECUTED')
