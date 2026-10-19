"""Inspect explicit retained native receipts; no process, annotation or coordinate import."""
import math
import re

ADMITTED={'SUCCESS_UNBOUND','NO_HIT','NO_RETAINED_CANDIDATES'}
OTHER={'HOLD','UNAVAILABLE','FAILED','INTERRUPTED','AMBIGUOUS','NOT_EXECUTED','READY_NATIVE_REVIEWED_NOT_EXECUTED'}
EXECUTED='EXECUTED_NATIVE_LOCAL_ADAPTER_OBSERVED'


def native_result(api,terminal_path,raw_path,out,control_path=None):
    sources=[];terminal=api['json_input'](terminal_path,sources)
    if not isinstance(terminal,dict) or terminal.get('schema_version')!='ripper-lifecycle/1' or terminal.get('mode')!='adapted_local05' or not isinstance(terminal.get('status'),str) or terminal['status'] not in ADMITTED|OTHER:
        raise ValueError('NATIVE_RESULT_TERMINAL_SCHEMA_INVALID')
    status=terminal['status'];execution=terminal.get('upstream_execution')
    if not isinstance(execution,str) or execution not in {EXECUTED,'NOT_EXECUTED'} or terminal.get('biological_absence_inferred') is not False or terminal.get('candidate_bgc_membership')!='UNVERIFIED':
        raise ValueError('NATIVE_RESULT_TERMINAL_QUALIFICATION_INVALID')
    count=None;channels={};raw_state='NOT_ADMITTED_BY_TERMINAL';declaration=None
    if status in ADMITTED:
        if execution!=EXECUTED or type(terminal.get('returncode')) is not int or terminal['returncode']!=0 or terminal.get('reason') is not None or terminal.get('supervision_cleanup_uncertain') is not False or terminal.get('cleanup_errors') or terminal.get('output_admission')!='SCOPED_BOUND_BYTES_ONLY' or terminal.get('outcome_scope')!='RAW_NATIVE_DISCOVERY_ONLY_HMM_ANNOTATION_NOT_RUN':
            raise ValueError('NATIVE_RESULT_TERMINAL_NOT_ADMITTED')
        contract=terminal.get('native_contract')
        if not isinstance(contract,dict) or contract.get('source_interface')!='n3' or contract.get('requires_discovery_declaration') is not True or contract.get('hmm_annotation')!='NOT_RUN_SEPARATE_STAGE':raise ValueError('NATIVE_RESULT_N3_RAW_CONTRACT_REQUIRED')
        publication=terminal.get('terminal_publication')
        if publication is not None:
            from pathlib import Path
            if not isinstance(publication,dict) or publication.get('protocol')!='EXCLUSIVE_CANONICAL_LINK_AFTER_SERIALIZATION' or publication.get('canonical_name')!=Path(terminal_path).name or publication.get('staging_names_are_not_completion') is not True:
                raise ValueError('NATIVE_RESULT_UNCOMMITTED_TERMINAL_FILE')
        elif not control_path:raise ValueError('NATIVE_RESULT_LEGACY_PUBLICATION_CONTROL_REQUIRED')
        if control_path:
            control=api['json_input'](control_path,sources)
            if not isinstance(control,dict) or control.get('status')!=status or control.get('upstream_execution')!=EXECUTED or type(control.get('returncode')) is not int or control['returncode']!=0 or control.get('reason') is not None or control.get('error') is not None or control.get('cleanup_errors') or control.get('supervision_cleanup_uncertain') is not False or control.get('terminal')!=sources[0]:raise ValueError('NATIVE_RESULT_CONTROL_NOT_ADMITTED')
        summary=terminal.get('raw_discovery')
        if not isinstance(summary,dict) or summary.get('status')!=status or not isinstance(summary.get('sha256'),str) or not re.fullmatch(r'[0-9a-f]{64}',summary['sha256']):raise ValueError('NATIVE_RESULT_RAW_SUMMARY_INVALID')
        if not raw_path:raise ValueError('NATIVE_RESULT_EXPLICIT_RAW_REQUIRED')
        if control_path and control.get('raw_discovery')!=summary:raise ValueError('NATIVE_RESULT_CONTROL_RAW_MISMATCH')
        raw=api['json_input'](raw_path,sources)
        if sources[-1]['sha256']!=summary['sha256']:raise ValueError('NATIVE_RESULT_RAW_DIGEST_MISMATCH')
        if not isinstance(raw,dict) or raw.get('schema_version')!='ripper-raw-discovery/1' or raw.get('status')!=status or raw.get('upstream_execution')!=EXECUTED or raw.get('evidence_kind')!='local_adapter_observed_native':raise ValueError('NATIVE_RESULT_RAW_STATE_MISMATCH')
        if raw.get('hmm_annotation')!='NOT_RUN_SEPARATE_STAGE' or raw.get('candidate_membership')!='UNVERIFIED' or raw.get('coordinate_provenance')!='ABSENT_PRODUCER_MAPPING' or raw.get('biological_absence_inferred') is not False or raw.get('subject_context_mismatch') is not False or raw.get('incomplete')!=[]:
            raise ValueError('NATIVE_RESULT_RAW_QUALIFICATION_INVALID')
        candidates=raw.get('candidates');count=raw.get('candidate_count')
        if not isinstance(candidates,list) or type(count) is not int or not 0<=count<=10000 or count!=len(candidates) or any(type(x.get('candidate_count')) is not int or x['candidate_count']!=count or type(x.get('retained_raw_candidate_count')) is not int or x['retained_raw_candidate_count']!=count for x in (summary,raw)):
            raise ValueError('NATIVE_RESULT_CANDIDATE_DENOMINATOR_INVALID')
        if (status=='SUCCESS_UNBOUND')!=(count>0):raise ValueError('NATIVE_RESULT_STATE_COUNT_CONTRADICTION')
        seen=set()
        for candidate in candidates:
            if not isinstance(candidate,dict) or candidate.get('candidate_membership')!='UNVERIFIED' or candidate.get('coordinate_status')!='ABSENT_PRODUCER_MAPPING' or candidate.get('hmm_annotation')!='NOT_RUN':raise ValueError('NATIVE_RESULT_CANDIDATE_QUALIFICATION_INVALID')
            accession=candidate.get('enzyme_accession');identifier=candidate.get('peptide_id');sequence=candidate.get('sequence');fields=candidate.get('source_fields')
            if not isinstance(fields,dict) or not isinstance(accession,str) or not re.fullmatch(r'[A-Za-z0-9_.]+',accession) or not isinstance(identifier,str) or not isinstance(sequence,str) or not re.fullmatch(r'[ACDEFGHIKLMNPQRSTVWY]+',sequence) or type(fields.get('ppser')) is not int or fields['ppser']<1 or fields.get('acc')!=accession or fields.get('fastaid')!=identifier or fields.get('aaseq')!=sequence or identifier!=accession+'_'+str(fields['ppser']) or identifier in seen:
                raise ValueError('NATIVE_RESULT_CANDIDATE_IDENTITY_INVALID')
            raw_columns={'acc','species','ppser','fastaid','aaseq','ppstrand','testrand','pptedist','score'}
            if set(fields)!=raw_columns or not isinstance(fields['species'],str) or any(type(fields[k]) is not int or fields[k] not in (-1,1) for k in ('ppstrand','testrand')) or type(fields['pptedist']) is not int or fields['pptedist']<0 or type(fields['score']) not in (int,float) or not math.isfinite(fields['score']):
                raise ValueError('NATIVE_RESULT_RAW_FIELDS_INVALID')
            seen.add(identifier);channel='distant' if re.fullmatch(r'9[0-9]{3,}',str(fields['ppser'])) else 'main'
            if candidate.get('channel')!=channel:raise ValueError('NATIVE_RESULT_LEXICAL_CHANNEL_MISMATCH')
            channels[channel]=channels.get(channel,0)+1
        declaration=raw.get('source_declaration')
        if not isinstance(declaration,dict) or declaration.get('status')!='MATCHED_UNATTESTED_SOURCE_DECLARATION' or type(declaration.get('candidate_rows_declared')) is not int or declaration['candidate_rows_declared']!=count or declaration.get('state')!=('NO_TE_HITS_DECLARED_UNATTESTED' if status=='NO_HIT' else 'TE_MATCH_WITH_ROWS_UNATTESTED' if count else 'TE_MATCH_NO_CANDIDATE_ROWS_UNATTESTED'):
            raise ValueError('NATIVE_RESULT_SOURCE_DECLARATION_CONTRADICTION')
        raw_state='EXPLICIT_HASH_BOUND_RAW_SCOPE_ONLY'
    elif raw_path:
        raise ValueError('NATIVE_RESULT_NONADMITTED_RAW_REFUSED')
    elif terminal.get('output_admission')=='SCOPED_BOUND_BYTES_ONLY':
        raise ValueError('NATIVE_RESULT_NONADMITTED_STATUS_CONTRADICTION')
    data=dict(schema_version='ripper-native-result/1',terminal_status=status,recorded_upstream_execution=execution,
        raw_result_status=status if status in ADMITTED else 'NOT_ADMITTED',raw_candidate_count=count,lexical_channel_counts=channels,
        raw_admission=raw_state,hmm_annotation='NOT_RUN_SEPARATE_STAGE' if status in ADMITTED else 'NOT_ESTABLISHED',
        coordinate_status='ABSENT_PRODUCER_MAPPING',candidate_membership='UNVERIFIED',biological_absence_inferred=False,
        canonical_import='NOT_ADMITTED',sources=sources,source_declaration=declaration,
        validation_scope='explicit terminal/raw content consistency only; original inputs, native stages and process identity are not independently revalidated',
        receipt_authentication='CONTENT_BOUND_NOT_IDENTITY_AUTHENTICATED',
        holds=['HOLD_HMM_ANNOTATION_NOT_RUN','HOLD_COORDINATE_PRODUCER','HOLD_BGC_MEMBERSHIP','HOLD_CANONICAL_IMPORT'],
        scope='retained native raw-result inspection only; no process launch, normalization into merged annotations, coordinate conversion or biological absence claim')
    if out is not None:api['publish'](out,{'NATIVE_RESULT.json':data},sources)
    return data
