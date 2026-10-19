"""Declared coordinate/sequence binding only; no upstream or BGC-membership proof."""
import hashlib
import io
import json
import re


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def subject_digest(source_sha, record_id, subject):
    fields=('subject_cds_id','source_id_qualifier','start_0based','end_exclusive','strand','translation_sha256')
    return digest(dict(source_genbank_sha256=source_sha,record_id=record_id,subject_cds={k:subject[k] for k in fields}))


def rich_coordinate_reader():
    """Require full GenBank features and explicit optional-dependency refusal."""
    try:
        from Bio import SeqIO
    except ImportError as exc:
        raise RuntimeError('Strict RiPPER coordinate validation requires optional Biopython') from exc
    return SeqIO


def bind_coordinates(api, evidence_path, plan_path, genbank_path, query_path, mapping_path, out):
    sources=[]
    evidence=api['json_input'](evidence_path,sources);evidence_sha=sources[-1]['sha256']
    plan=api['json_input'](plan_path,sources);plan_sha=sources[-1]['sha256']
    mapping=api['json_input'](mapping_path,sources)
    raw=api['load_bytes'](genbank_path);sources.append(api['binding'](genbank_path,raw));genbank_sha=sources[-1]['sha256'];gbk=raw.decode('utf-8')
    raw=api['load_bytes'](query_path);sources.append(api['binding'](query_path,raw));query_sha=sources[-1]['sha256'];fasta=raw.decode('utf-8')
    if not isinstance(evidence,dict) or evidence.get('schema_version')!='ripper-evidence/2' or evidence.get('declared_upstream_state')!='COMPLETE':
        raise ValueError('COORDINATE_COMPLETE_EVIDENCE_REQUIRED')
    allowed={'synthetic_fixture':'NOT_EXECUTED_SYNTHETIC','operator_supplied':'OPERATOR_DECLARED_UNATTESTED'}
    kind=evidence.get('evidence_kind')
    if not isinstance(kind,str) or kind not in allowed or evidence.get('upstream_execution')!=allowed[kind]:
        raise ValueError('COORDINATE_EVIDENCE_QUALIFICATION_PAIR_MISMATCH')
    if not isinstance(plan,dict) or plan.get('schema_version')!='ripper-local-plan/1' or plan.get('upstream_execution')!='NOT_EXECUTED' or not isinstance(plan.get('queries'),list) or len(plan['queries'])!=1 or not isinstance(plan['queries'][0],dict):
        raise ValueError('COORDINATE_SINGLE_LOCAL_PLAN_REQUIRED')
    if not isinstance(mapping,dict) or mapping.get('schema_version')!='ripper-coordinate-map/1' or mapping.get('mapping_origin') not in ('synthetic_fixture','operator_supplied'):
        raise ValueError('COORDINATE_MAP_SCHEMA_INVALID')
    expected=dict(evidence_sha256=evidence_sha,local_plan_sha256=plan_sha,source_genbank_sha256=genbank_sha,query_fasta_sha256=query_sha)
    if any(mapping.get(k)!=v for k,v in expected.items()):
        raise ValueError('COORDINATE_MAP_INPUT_HASH_MISMATCH')
    for b in (sources[-2],sources[-1]):
        if not any(isinstance(x,dict) and x.get('path')==b['path'] and x.get('sha256')==b['sha256'] and x.get('bytes')==b['bytes'] for x in plan.get('sources',[])):
            raise ValueError('COORDINATE_PLAN_SOURCE_BINDING_MISMATCH')
    query=plan['queries'][0]
    candidates=evidence.get('candidates')
    if type(evidence.get('query_count')) is not int or evidence['query_count']!=1:
        raise ValueError('COORDINATE_SINGLE_QUERY_EVIDENCE_REQUIRED')
    if not isinstance(candidates,list) or type(evidence.get('candidate_count')) is not int or evidence['candidate_count']!=len(candidates):
        raise ValueError('COORDINATE_CANDIDATE_DENOMINATOR_INVALID')
    keys={};raw_consistency={}
    for candidate in candidates:
        if not isinstance(candidate,dict) or candidate.get('enzyme_accession')!=query.get('enzyme_accession') or candidate.get('query_context')!={k:query.get(k) for k in api['IDENTITY']}:
            raise ValueError('COORDINATE_QUERY_CONTEXT_MISMATCH')
        present=[k in candidate for k in ('evidence_kind','upstream_execution')]
        if any(present):
            if not all(present):raise ValueError('COORDINATE_CANDIDATE_QUALIFICATION_INCOMPLETE')
            if candidate['evidence_kind']!=kind or candidate['upstream_execution']!=allowed[kind]:
                raise ValueError('COORDINATE_CANDIDATE_QUALIFICATION_PAIR_MISMATCH')
        if not isinstance(candidate.get('raw_fields'),dict):raise ValueError('COORDINATE_RAW_FIELDS_OBJECT_REQUIRED')
        serial=candidate['raw_fields'].get('PPSerial')
        key=(candidate['enzyme_accession'],candidate.get('peptide_id'),serial)
        if not isinstance(serial,str) or not re.fullmatch(r'[1-9][0-9]*',serial) or key[1]!=key[0]+'_'+serial or key in keys:
            raise ValueError('COORDINATE_SOURCE_SERIAL_ID_REQUIRED')
        sequence=candidate.get('sequence')
        if not isinstance(sequence,str) or not re.fullmatch(r'[ACDEFGHIKLMNPQRSTVWY]+',sequence):
            raise ValueError('COORDINATE_CANDIDATE_SEQUENCE_INVALID')
        mirrors={'Accession':candidate['enzyme_accession'],'FastaID':candidate['peptide_id'],'Sequence':sequence}
        present_raw=[name in candidate['raw_fields'] for name in mirrors]
        archived=isinstance(evidence.get('source_profile'),dict) and evidence['source_profile'].get('id')=='archived-e90b3e6-mergeRidePfam'
        if (archived or any(present_raw)) and not all(present_raw):raise ValueError('COORDINATE_RAW_IDENTITY_SEQUENCE_INCOMPLETE')
        if all(present_raw):
            for name,value in mirrors.items():
                if candidate['raw_fields'][name]!=value:raise ValueError('COORDINATE_RAW_IDENTITY_SEQUENCE_MISMATCH: '+name)
        keys[key]=candidate
        raw_consistency[key[1]]='MATCHED_DECLARED_RAW_IDENTITY_SEQUENCE' if all(present_raw) else 'NOT_DECLARED_LEGACY_MINIMAL_INPUT'
    rows=mapping.get('mappings')
    if not isinstance(rows,list) or len(rows)>10000:
        raise ValueError('COORDINATE_MAP_ROWS_INVALID')
    semantic=api['validate_local_semantics'](gbk,fasta,query)
    SeqIO=None
    if semantic['status']!='HOLD_DEPENDENCY_UNAVAILABLE':
        try:SeqIO=rich_coordinate_reader()
        except (RuntimeError,OSError) as exc:
            semantic=dict(status='HOLD_DEPENDENCY_UNAVAILABLE',dependency='Biopython',dependency_error=str(exc),upstream_execution='NOT_EXECUTED')
    assessments=[]
    if semantic['status']=='HOLD_DEPENDENCY_UNAVAILABLE':
        assessments=[dict(peptide_id=k[1],status='HOLD_DEPENDENCY_UNAVAILABLE',candidate_membership='UNVERIFIED') for k in keys]
        status='HOLD_DEPENDENCY_UNAVAILABLE'
    else:
        record=SeqIO.read(io.StringIO(gbk),'genbank')
        cds_sha=subject_digest(genbank_sha,record.id,semantic['selected_subject_cds'])
        if mapping.get('subject_cds_sha256')!=cds_sha:
            raise ValueError('COORDINATE_SUBJECT_CDS_HASH_MISMATCH')
        grouped={key:[] for key in keys};seen=set()
        for row in rows:
            if not isinstance(row,dict):raise ValueError('COORDINATE_MAP_ROW_INVALID')
            key=(row.get('enzyme_accession'),row.get('FastaID'),row.get('PPSerial'))
            if any(not isinstance(x,str) for x in key):raise ValueError('COORDINATE_MAP_IDENTIFIER_INVALID')
            if key not in keys:raise ValueError('COORDINATE_UNBOUND_CANDIDATE')
            candidate=keys[key]
            if row.get('sequence_sha256')!=hashlib.sha256(candidate['sequence'].encode()).hexdigest():
                raise ValueError('COORDINATE_CANDIDATE_SEQUENCE_HASH_MISMATCH')
            fields=('window_start_1based','window_end_inclusive','local_start_1based','local_end_inclusive','strand')
            if any(type(row.get(k)) is not int for k in fields):raise ValueError('COORDINATE_INTEGER_GEOMETRY_REQUIRED')
            ws,we,ls,le,strand=(row[k] for k in fields)
            if not 1<=ws<=we<=len(record) or not 1<=ls<=le<=we-ws+1 or strand not in (-1,1):
                raise ValueError('COORDINATE_GEOMETRY_OUT_OF_RANGE')
            window=str(record.seq[ws-1:we]).upper()
            if row.get('window_sequence_sha256')!=hashlib.sha256(window.encode('ascii')).hexdigest():
                raise ValueError('COORDINATE_WINDOW_SEQUENCE_HASH_MISMATCH')
            start,end=ws+ls-2,ws+le-1
            locator=(*key,start,end,strand)
            if locator in seen:raise ValueError('COORDINATE_DUPLICATE_MAPPING')
            seen.add(locator)
            dna=record.seq[start:end]
            if strand==-1:dna=dna.reverse_complement()
            transformations=[]
            if len(dna)%3 or not re.fullmatch(r'[ACGT]+',str(dna).upper()):
                matches=False;translated=None
            else:
                translated=str(dna.translate(table=1))
                if translated.endswith('*'):translated=translated[:-1];transformations.append('terminal_stop_removed')
                if translated.startswith(('V','L')):translated='M'+translated[1:];transformations.append('initial_V_or_L_to_M')
                matches=translated==candidate['sequence']
            grouped[key].append(dict(start_0based=start,end_exclusive=end,strand=strand,window_start_1based=ws,window_end_inclusive=we,
                window_sequence_sha256=row['window_sequence_sha256'],sequence_match=matches,source_translation_transformations=transformations))
        for key,locations in grouped.items():
            state='ABSENT_MAPPING' if not locations else ('AMBIGUOUS_DECLARED_MAPPINGS' if len(locations)>1 else ('DIRECT_SEQUENCE_MATCH_UNATTESTED' if locations[0]['sequence_match'] else 'SEQUENCE_MISMATCH'))
            assessments.append(dict(enzyme_accession=key[0],peptide_id=key[1],PPSerial=key[2],status=state,locations=locations,
                candidate_membership='UNVERIFIED',attribution_status='HOLD_BGC_MEMBERSHIP_NOT_ESTABLISHED'))
        status='COORDINATE_DECLARATIONS_EVALUATED'
    for assessment in assessments:
        assessment['evidence_kind']=kind
        assessment['upstream_execution']=allowed[kind]
        assessment['qualification_scope']='VALIDATED_PARENT_PAIR; candidate fields checked if present'
        assessment['raw_identity_consistency']=raw_consistency[assessment['peptide_id']]
    data=dict(schema_version='ripper-coordinate-binding/1',import_status=status,evidence_kind=evidence['evidence_kind'],upstream_execution=evidence['upstream_execution'],
        declared_upstream_state=evidence['declared_upstream_state'],query_count=1,candidate_count=len(candidates),sources=sources,
        input_bindings=expected,semantic_input_validation=semantic,mapping_origin=mapping['mapping_origin'],mapping_authentication='UNATTESTED_DECLARATIONS',
        assessments=assessments,candidate_membership='UNVERIFIED',holds=['HOLD_BGC_MEMBERSHIP_NOT_ESTABLISHED','HOLD_MAPPING_EXECUTION_PROVENANCE'],
        scope='bound local sequence/coordinate consistency only; not upstream execution, production, function or BGC attribution')
    api['publish'](out,{'RIPPER_COORDINATE_BINDING.json':data},sources)
    return data
