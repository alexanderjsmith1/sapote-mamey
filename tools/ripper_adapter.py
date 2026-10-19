#!/usr/bin/env python3
"""Optional RiPPER planning/import, byte binding and reviewed native/stub lifecycle controls.

Core planning/import uses Python's standard library; optional semantic input
validation uses Biopython. Outputs are additive, external to the tool
source tree. Source bytes, completion declarations and declared query contexts
remain independently attributable; predictions are not compound identification.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import logging
import re
import os
import time
import math
from pathlib import Path

LOG = logging.getLogger('mamey.ripper_adapter')
PROJECT = 'https://github.com/streptomyces/ripper'
DOI = '10.1093/nar/gkz192'
MAX_BYTES = 5 * 1024 * 1024
LIMIT = 'putative precursor candidates only; no compound, production or bioactivity inference'
IDENTITY = ('strain', 'full_contig', 'region', 'bgc_alias')
STATES = {'COMPLETE', 'FAILED', 'UNAVAILABLE', 'NOT_RUN', 'MISSING', 'INTERRUPTED'}


def load_bytes(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('INPUT_NOT_REGULAR: ' + str(path))
    with path.open('rb') as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('INPUT_TOO_LARGE: ' + str(path))
    return raw


def binding(path, raw):
    return dict(path=str(Path(path).resolve()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def _stream_file(path, byte_budget, timeout_seconds, prefix, ceiling, timeout_ceiling, mode):
    if type(byte_budget) is not int or not 0<byte_budget<=ceiling or isinstance(timeout_seconds,bool) or not isinstance(timeout_seconds,(int,float)) or not math.isfinite(timeout_seconds) or not 0<timeout_seconds<=timeout_ceiling:
        raise ValueError(prefix+'_BUDGET_INVALID')
    p=Path(path)
    if p.is_symlink() or not p.is_file():raise ValueError('INPUT_NOT_REGULAR: '+str(p))
    deadline=time.monotonic()+timeout_seconds;count=0;hasher=hashlib.sha256()
    flags=os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)
    with os.fdopen(os.open(p,flags),'rb') as handle:
        before=os.fstat(handle.fileno())
        if before.st_size>byte_budget:raise ValueError(prefix+'_BYTE_BUDGET_EXCEEDED')
        while True:
            if time.monotonic()>deadline:raise ValueError(prefix+'_TIME_BUDGET_EXCEEDED')
            block=handle.read(min(1024*1024,byte_budget-count+1))
            if not block:break
            count+=len(block)
            if count>byte_budget:raise ValueError(prefix+'_BYTE_BUDGET_EXCEEDED')
            hasher.update(block)
        after=os.fstat(handle.fileno())
    if p.is_symlink():raise ValueError(prefix+'_FILE_CHANGED')
    try:current=p.stat()
    except OSError as exc:raise ValueError(prefix+'_FILE_CHANGED') from exc
    def identity(value):return (value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_ctime_ns,value.st_mode)
    if identity(before)!=identity(after) or identity(after)!=identity(current) or count!=after.st_size:
        raise ValueError(prefix+'_FILE_CHANGED')
    return dict(path=str(p.resolve()),bytes=count,sha256=hasher.hexdigest(),hash_mode=mode,byte_budget=byte_budget,hash_timeout_seconds=timeout_seconds)


def stream_binding(path, byte_budget, timeout_seconds=30):
    return _stream_file(path,byte_budget,timeout_seconds,'MODEL_STREAM',16*1024**3,600,'streamed_model')


def tool_binding(path, byte_budget=None, timeout_seconds=30):
    legacy=byte_budget is None
    if legacy and timeout_seconds!=30:raise ValueError('EXECUTABLE_STREAM_EXPLICIT_BYTE_BUDGET_REQUIRED')
    try:b=_stream_file(path,16*1024**2 if legacy else byte_budget,timeout_seconds,'EXECUTABLE_STREAM',512*1024**2,300,'streamed_executable')
    except ValueError as exc:
        if legacy and str(exc)=='EXECUTABLE_STREAM_BYTE_BUDGET_EXCEEDED':raise ValueError('EXPLICIT_TOOL_TOO_LARGE') from exc
        raise
    if legacy:return {k:b[k] for k in ('path','bytes','sha256')}|{'hash_mode':'bounded_tool_16MiB'}
    return b


def json_input(path, sources):
    raw = load_bytes(path)
    sources.append(binding(path, raw))
    return json.loads(raw.decode('utf-8'))


def nonempty(value):
    return isinstance(value, str) and bool(value.strip()) and value == value.strip() and not any(ord(c) < 32 for c in value)


def operator_actions(data):
    schema=data.get('schema_version')
    if schema=='ripper-native-coordinate-binding/1':
        return ['Retain evaluated native coordinate reconstruction and source row/window evidence. Instrumented producer origin, HMM annotation and BGC attribution remain separate; no native rerun or merged-evidence relabelling.']
    if schema=='ripper-native-result/1':
        return ['Retain the recorded raw scope and source evidence. HMM annotation and producer-backed coordinates require separate admission; no automatic native retry or canonical import.']
    if schema=='ripper-lifecycle/1' and data.get('mode')=='adapted_local05':
        return ['Retain exact native terminal/raw artifacts and cleanup status. Raw discovery does not establish HMM annotation, peptide coordinates or BGC membership; another native run requires separate admission.']
    if schema=='ripper-lifecycle/1':
        return ['Retain terminal status and exact artifacts; fix recorded missing prerequisites or limits before a separately selected fresh run. Stub outcomes never establish upstream execution or biological absence.']
    if schema=='ripper-adapted-source-profile/1':
        return ['Review the explicit base/patch/postimage and owner receipt; native execution, license and release admission remain held.']
    if schema=='ripper-local-plan/1':
        if data.get('semantic_validation',{}).get('status')=='HOLD_DEPENDENCY_UNAVAILABLE':
            return ['Use an already admitted Biopython runtime or retain text-only HOLD; missing validation is not a pass.']
        return ['Resolve source/runtime/model/license holds before any upstream run; input binding is not execution admission.']
    if schema=='ripper-coordinate-binding/1':
        statuses={x.get('status') for x in data.get('assessments',[]) if isinstance(x,dict)}
        if 'AMBIGUOUS_DECLARED_MAPPINGS' in statuses:
            return ['Resolve coordinate declarations against original source/window/stage evidence; do not choose by sequence alone.']
        if 'ABSENT_MAPPING' in statuses:
            return ['Obtain an explicit coordinate producer record; enzyme query context is not peptide location.']
        if 'SEQUENCE_MISMATCH' in statuses:
            return ['Check source/window/strand and retain the mismatch; do not reassign candidate identity.']
        return ['Retain source/region and producer-provenance holds; direct sequence consistency does not establish BGC membership.']
    if schema=='ripper-run-binding/1':
        if data.get('missing_roles'):
            return ['Provide explicitly admitted missing file roles: '+', '.join(data['missing_roles'])+'. No automatic discovery or installation.']
        return ['Review runtime/model/index/license/producer evidence; bound file bytes do not authorize execution.']
    if schema=='ripper-evidence/2':
        state=data.get('declared_upstream_state')
        if state!='COMPLETE':
            return ['Retain the declared '+str(state)+' state and logs; do not attach stale outputs or infer biological absence.']
        if data.get('candidate_count'):
            return ['Supply a bound coordinate declaration; do not attribute retained rows to the enzyme BGC.']
        return ['Inspect exact per-query completion and log coverage; no retained rows is scoped, not biological absence.']
    if schema=='ripper-source-profile/1':
        return ['Use matching archived source and exact output schema/channel; container equivalence and live compatibility remain unverified.']
    return ['Inspect recorded holds and exact inputs before selecting a separately admitted next stage.']


def refusal_action(code):
    actions={
        'INPUT_NOT_REGULAR':'Supply the exact admitted regular input file; missing evidence is not a negative.',
        'COMPLETE_QUERY_COVERAGE_REQUIRED':'Provide completion evidence for the exact query roster; do not infer unassessed queries.',
        'NONCOMPLETE_RESULTS_NOT_ADMITTED':'Keep failed/missing/interrupted status separate from stale raw rows.',
        'RUN_BINDING_FILE_DIGEST_MISMATCH':'Select matching historic inputs or create a newly bound run; retain prior artifacts.',
        'RUN_BINDING_ARCHIVED_SOURCE_PIN_MISMATCH':'Use the pinned original source or obtain separate adapted-profile admission with its owner.',
        'RUN_BINDING_RECEIPT_IDENTITY_MISMATCH':'Match declared run ID and binding artifact hash; do not relabel an old run.'}
    return actions.get(code,'Review the exact refusal and bound inputs; retain prior artifacts.')


def queries_input(path, sources):
    data = json_input(path, sources)
    if not isinstance(data, dict) or data.get('schema_version') != 'ripper-queries/1':
        raise ValueError('QUERY_SCHEMA_INVALID')
    queries = data.get('queries')
    if not isinstance(queries, list) or not queries or len(queries) > 1000:
        raise ValueError('QUERY_ROSTER_INVALID')
    seen = set()
    for query in queries:
        if not isinstance(query, dict):
            raise ValueError('QUERY_ROW_INVALID')
        accession = query.get('enzyme_accession')
        if not nonempty(accession) or not re.fullmatch(r'[A-Za-z0-9_.]+', accession) or accession in seen:
            raise ValueError('QUERY_ACCESSION_MISSING_OR_DUPLICATE')
        seen.add(accession)
        if any(not nonempty(query.get(k)) or ' / ' in query[k] for k in IDENTITY):
            raise ValueError('QUERY_FULL_LOCUS_IDENTITY_REQUIRED')
    return queries


def publish(out, payloads, sources):
    """Validate before writing; exclusively create the requested external directory."""
    if Path(out).is_symlink():
        raise ValueError('OUTPUT_SYMLINK_REFUSED')
    out = Path(out).resolve()
    root = Path(__file__).resolve().parents[1]
    if out == root or root in out.parents:
        raise ValueError('OUTPUT_MUST_BE_EXTERNAL_TO_SOURCE_TREE')
    for source in sources:
        p = Path(source['path'])
        if out == p or out in p.parents:
            raise ValueError('OUTPUT_OVERLAPS_INPUT')
        fresh=tool_binding(p,source['byte_budget'],source['hash_timeout_seconds']) if source.get('hash_mode')=='streamed_executable' else stream_binding(p,source['byte_budget'],source['hash_timeout_seconds']) if source.get('hash_mode')=='streamed_model' else tool_binding(p) if source.get('hash_mode')=='bounded_tool_16MiB' else binding(p,load_bytes(p))
        if fresh != source:
            raise ValueError('INPUT_CHANGED_DURING_IMPORT')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.mkdir()  # refuses occupied destinations, including simultaneous publishers
    for name, value in payloads.items():
        if isinstance(value,dict) and isinstance(value.get('schema_version'),str) and value['schema_version'].startswith('ripper-'):
            value.setdefault('operator_next_actions',operator_actions(value))
        with (out / name).open('x', encoding='utf-8') as handle:
            handle.write(value if isinstance(value, str) else json.dumps(value, indent=2, sort_keys=True) + '\n')
    return out


def plan(queries_path, out):
    sources = []
    queries = queries_input(queries_path, sources)
    data = dict(schema_version='ripper-plan/2', plan_status='PLANNED', upstream_execution='NOT_EXECUTED', upstream=PROJECT,
                method_doi=DOI, query_count=len(queries), queries=queries, sources=sources,
                adapter_mode='plan_only', network_required_for_documented_upstream=True,
                holds=['pinned upstream revision and license unverified',
                       'authentic TSV headers and per-query completion logs required',
                       'no verified offline arbitrary-GenBank input route'], claim_ceiling=LIMIT)
    publish(out, {'PLAN.json': data, 'enzyme_accessions.txt': ''.join(q['enzyme_accession']+'\n' for q in queries)}, sources)
    return data


def source_contract(profile_id, sources):
    profile = json_input(Path(__file__).with_name('ripper_source_profile.json'), sources)
    if profile_id != profile['id']:
        raise ValueError('UNKNOWN_ARCHIVED_SOURCE_PROFILE')
    return profile


def write_profile(profile_id, out):
    sources = []
    profile = source_contract(profile_id, sources)
    data = dict(profile, profile_status='SOURCE_DERIVED_NOT_EXECUTED', upstream_execution='NOT_EXECUTED', sources=sources)
    publish(out, {'RIPPER_SOURCE_PROFILE.json': data, 'columns.json': profile['columns']}, sources)
    return data


def rich_biopython_dependencies():
    """Require rich source features; never silently substitute a thin parser."""
    try:
        import Bio
        from Bio import SeqIO
        from Bio.SeqFeature import ExactPosition, SimpleLocation
        from Bio.Data.CodonTable import TranslationError
    except ImportError as exc:
        raise RuntimeError('Strict RiPPER input validation requires optional Biopython') from exc
    return Bio,SeqIO,ExactPosition,SimpleLocation,TranslationError


def validate_local_semantics(gbk, fasta, query):
    """Optional strict input binding, not a BLAST/TE/function/membership test."""
    try:
        Bio,SeqIO,ExactPosition,SimpleLocation,TranslationError=rich_biopython_dependencies()
    except (RuntimeError,OSError) as exc:
        return dict(status='HOLD_DEPENDENCY_UNAVAILABLE',dependency='Biopython',
                    dependency_error=str(exc),upstream_execution='NOT_EXECUTED')
    import warnings
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            records = list(SeqIO.parse(io.StringIO(gbk), 'genbank'))
            proteins = list(SeqIO.parse(io.StringIO(fasta), 'fasta'))
    except (ValueError, Warning) as exc:
        raise ValueError('LOCAL_SEMANTIC_PARSE_INVALID: '+str(exc)) from exc
    if len(records) != 1 or len(proteins) != 1:
        raise ValueError('LOCAL_SEMANTIC_SINGLE_RECORD_QUERY_REQUIRED')
    record, protein = records[0], proteins[0]
    if not nonempty(record.id) or record.id != query['full_contig']:
        raise ValueError('LOCAL_SEMANTIC_RECORD_QUERY_CONTEXT_MISMATCH')
    if not len(record) or record.annotations.get('molecule_type', '').upper() != 'DNA' or not re.fullmatch(r'[ACGTN]+', str(record.seq).upper()):
        raise ValueError('LOCAL_SEMANTIC_DNA_RECORD_INVALID')
    query_sequence = str(protein.seq)
    if not nonempty(protein.id) or not re.fullmatch(r'[ACDEFGHIKLMNPQRSTVWY]+', query_sequence):
        raise ValueError('LOCAL_SEMANTIC_PROTEIN_QUERY_INVALID')
    seen = set()
    cds_rows = []
    for feature in record.features:
        if feature.type != 'CDS':
            continue
        loc = feature.location
        if not isinstance(loc, SimpleLocation):
            raise ValueError('LOCAL_SEMANTIC_COMPOUND_OR_MISSING_CDS_LOCATION')
        if loc.ref or loc.ref_db:
            raise ValueError('LOCAL_SEMANTIC_REMOTE_CDS_LOCATION')
        if not isinstance(loc.start, ExactPosition) or not isinstance(loc.end, ExactPosition):
            raise ValueError('LOCAL_SEMANTIC_PARTIAL_CDS_LOCATION')
        if loc.strand not in (-1, 1) or not 0 <= int(loc.start) < int(loc.end) <= len(record):
            raise ValueError('LOCAL_SEMANTIC_CDS_COORDINATES_INVALID')
        if any(key in feature.qualifiers for key in ('pseudo', 'pseudogene', 'transl_except', 'exception', 'ribosomal_slippage')):
            raise ValueError('LOCAL_SEMANTIC_UNSUPPORTED_CDS_EXCEPTION')
        def qualifier(key, default=None):
            values = feature.qualifiers.get(key)
            if values is None:
                return default
            if not isinstance(values, list) or len(values) != 1 or not nonempty(values[0]):
                raise ValueError('LOCAL_SEMANTIC_AMBIGUOUS_OR_EMPTY_QUALIFIER: '+key)
            return values[0]
        subject = None
        id_key = None
        for key in ('locus_tag', 'old_locus_tag', 'protein_id', 'gene'):
            if key in feature.qualifiers:
                subject, id_key = qualifier(key), key
                break
        if subject is None or not re.fullmatch(r'[A-Za-z0-9_.]+', subject):
            raise ValueError('LOCAL_SEMANTIC_EXPLICIT_SAFE_CDS_ID_REQUIRED')
        if subject in seen:
            raise ValueError('LOCAL_SEMANTIC_DUPLICATE_CDS_ID')
        seen.add(subject)
        if qualifier('codon_start', '1') != '1':
            raise ValueError('LOCAL_SEMANTIC_UNSUPPORTED_CODON_START')
        table = qualifier('transl_table', '1')
        if table not in ('1', '11'):
            raise ValueError('LOCAL_SEMANTIC_UNSUPPORTED_TRANSLATION_TABLE')
        translation = qualifier('translation')
        if translation is None or not re.fullmatch(r'[ACDEFGHIKLMNPQRSTVWY]+', translation):
            raise ValueError('LOCAL_SEMANTIC_VALID_TRANSLATION_REQUIRED')
        dna = feature.extract(record.seq)
        if not re.fullmatch(r'[ACGT]+', str(dna).upper()) or not str(dna).upper().startswith('ATG'):
            raise ValueError('LOCAL_SEMANTIC_UNAMBIGUOUS_ATG_CDS_REQUIRED')
        try:
            computed = str(dna.translate(table=int(table), cds=True))
        except (ValueError, TranslationError) as exc:
            raise ValueError('LOCAL_SEMANTIC_CDS_TRANSLATION_INVALID: '+str(exc)) from exc
        if computed != translation:
            raise ValueError('LOCAL_SEMANTIC_CDS_TRANSLATION_MISMATCH')
        cds_rows.append(dict(subject_cds_id=subject, source_id_qualifier=id_key,
                             start_0based=int(loc.start), end_exclusive=int(loc.end), strand=loc.strand,
                             translation_table=int(table), aa_length=len(translation),
                             translation_sha256=hashlib.sha256(translation.encode()).hexdigest(),
                             query_exact_match=translation == query_sequence))
    if not cds_rows:
        raise ValueError('LOCAL_SEMANTIC_NONEMPTY_CDS_INVENTORY_REQUIRED')
    selected = [row for row in cds_rows if row['subject_cds_id'] == query['enzyme_accession']]
    if len(selected) != 1:
        raise ValueError('LOCAL_SEMANTIC_EXPECTED_SUBJECT_CDS_NOT_BOUND')
    exact = [row for row in cds_rows if row['query_exact_match']]
    if len(exact) > 1:
        raise ValueError('LOCAL_SEMANTIC_AMBIGUOUS_EXACT_QUERY_MATCH')
    if exact and exact[0]['subject_cds_id'] != query['enzyme_accession']:
        raise ValueError('LOCAL_SEMANTIC_DECLARED_SUBJECT_CONFLICTS_WITH_EXACT_QUERY')
    return dict(status='PASS_INPUT_BINDING_ONLY', validator='Biopython', version=Bio.__version__,
                record_id=record.id, record_length=len(record), cds_count=len(cds_rows), cds=cds_rows,
                selected_subject_cds=selected[0], query_fasta_id=protein.id,
                query_sequence_sha256=hashlib.sha256(query_sequence.encode()).hexdigest(),
                query_relation='EXACT_SEQUENCE_SELF_MATCH_ONLY' if exact else 'HOMOLOGY_UNASSESSED',
                blast_selection='UNASSESSED', gene_function='UNASSESSED', candidate_membership='UNVERIFIED',
                upstream_execution='NOT_EXECUTED',
                supported_scope='exact contiguous complete ATG CDS; codon_start1; tables1/11; explicit unique safe source-priority IDs')


def owned_module(name):
    import importlib.util
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_binding_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location('ripper_run_binding', Path(__file__).with_name('ripper_run_binding.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def binding_api():
    return dict(json_input=json_input,load_bytes=load_bytes,binding=binding,stream_binding=stream_binding,tool_binding=tool_binding,publish=publish,source_contract=source_contract,owned_module=owned_module,queries_input=queries_input,validate_local_semantics=validate_local_semantics)


def local_plan(queries_path, genbank_path, query_fasta_path, config_path, out, profile_id, semantic_validation=False, run_binding_path=None, bound_files=None, adapted_profile_path=None):
    if adapted_profile_path and not run_binding_path:raise ValueError('RUN_BINDING_EXPLICIT_ADAPTED_PROFILE_REQUIRED')
    sources = []
    queries = queries_input(queries_path, sources)
    profile = source_contract(profile_id, sources)
    if len(queries) != 1:
        raise ValueError('LOCAL_PLAN_REQUIRES_ONE_QUERY_CONTEXT')
    raw = load_bytes(genbank_path)
    sources.append(binding(genbank_path, raw))
    gbk = raw.decode('utf-8')
    if len(re.findall(r'^LOCUS\b', gbk, re.M)) != 1 or len(re.findall(r'^//\s*$', gbk, re.M)) != 1:
        raise ValueError('LOCAL_PLAN_REQUIRES_SINGLE_GENBANK_RECORD')
    if not gbk.startswith('LOCUS') or not re.search(r'^FEATURES\b', gbk, re.M) or not re.search(r'^ORIGIN\b', gbk, re.M) or not re.search(r'^\s+CDS\s', gbk, re.M):
        raise ValueError('LOCAL_PLAN_GENBANK_STRUCTURE_INVALID')
    raw = load_bytes(query_fasta_path)
    sources.append(binding(query_fasta_path, raw))
    fasta = raw.decode('utf-8')
    if not fasta.startswith('>') or len(re.findall(r'^>', fasta, re.M)) != 1:
        raise ValueError('LOCAL_PLAN_REQUIRES_SINGLE_FASTA_QUERY')
    sequence = ''.join(fasta.splitlines()[1:])
    if not re.fullmatch(r'[ACDEFGHIKLMNPQRSTVWY]+', sequence):
        raise ValueError('LOCAL_PLAN_QUERY_SEQUENCE_INVALID')
    raw = load_bytes(config_path)
    sources.append(binding(config_path, raw))
    config = {}
    for line in raw.decode('utf-8').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2 or parts[0] in config:
            raise ValueError('LOCAL_PLAN_CONFIG_INVALID')
        config[parts[0]] = parts[1]
    if not all(config.get(k) for k in ('sqlite3fn', 'prepeptab', 'blastdbdir')):
        raise ValueError('LOCAL_PLAN_CONFIG_REQUIRES_SQLITE_TABLE_BLASTDBDIR')
    run_binding = None
    if run_binding_path:
        required = {'genbank':sources[-3],'query_fasta':sources[-2],'config':sources[-1],'queries':sources[0]}
        run_binding = run_binding_module().verify_boundary(binding_api(),run_binding_path,bound_files,sources,required,adapted_profile_path=adapted_profile_path)
    elif bound_files:
        raise ValueError('RUN_BINDING_ARTIFACT_REQUIRED')
    semantic = validate_local_semantics(gbk, fasta, queries[0]) if semantic_validation else dict(status='NOT_REQUESTED_TEXT_ONLY')
    data = dict(schema_version='ripper-local-plan/1', plan_status='HOLD', upstream_execution='NOT_EXECUTED',
                source_profile=profile, queries=queries, query_count=1, sources=sources,
                admission_scope='optional strict semantic input binding; no live admission' if semantic_validation else 'text structure only, not full GenBank semantic validation',
                semantic_validation=semantic, run_binding=run_binding,
                expected_subject_cds_id=queries[0]['enzyme_accession'],
                subject_match_status='UNVERIFIED_REQUIRES_BLAST_RESULT_AND_ASSEMBLY_MAPPING',
                candidate_membership='UNVERIFIED',
                invocation_template=['perl', '<pinned_source>/ripper_local.pl', '-conffile', '<bound_config>',
                                     '-outdir', '<fresh_output>', '-queryfn', '<bound_single_query_fasta>', '--', '<bound_single_record_genbank>'],
                invocation_status='SOURCE_CONTRACT_TEMPLATE_ONLY_NOT_RUNNABLE_PLAN',
                holds=['upstream execution not implemented or authorized', 'license and runtime dependencies unverified',
                       'local script opens FTP at startup; offline adaptation not reviewed',
                       'temporary/database/output paths require isolated configuration review',
                       'first-hit TE selection and candidate assembly mapping unverified',
                       'batch wrapper deletes existing sqlite/network outputs; not admitted',
                       'archived source and Docker container equivalence unknown'])
    if semantic['status'] == 'HOLD_DEPENDENCY_UNAVAILABLE':
        data['holds'].append('optional Biopython semantic validation unavailable; input semantics unassessed')
    publish(out, {'LOCAL_PLAN.json': data}, sources)
    return data


def import_results(queries_path, receipt_path, out, raw_path=None, columns_path=None, config_path=None, completion_log_path=None, source_profile=None, channel=None, run_binding_path=None, bound_files=None, adapted_profile_path=None):
    if adapted_profile_path and not run_binding_path:raise ValueError('RUN_BINDING_EXPLICIT_ADAPTED_PROFILE_REQUIRED')
    sources = []
    queries = queries_input(queries_path, sources)
    receipt = json_input(receipt_path, sources)
    if not isinstance(receipt, dict) or receipt.get('schema_version') != 'ripper-run/1' or not isinstance(receipt.get('state'),str) or receipt['state'] not in STATES:
        raise ValueError('RUN_RECEIPT_SCHEMA_INVALID')
    if receipt.get('upstream') != PROJECT or not isinstance(receipt.get('evidence_kind'),str) or receipt['evidence_kind'] not in {'operator_supplied', 'synthetic_fixture'}:
        raise ValueError('RUN_PROVENANCE_INVALID')
    if not nonempty(receipt.get('reason')):
        raise ValueError('RUN_REASON_REQUIRED')
    profile = None
    if bool(source_profile) != bool(channel):
        raise ValueError('SOURCE_PROFILE_AND_CHANNEL_REQUIRED_TOGETHER')
    if source_profile:
        profile = source_contract(source_profile, sources)
        if channel not in profile['channels']:
            raise ValueError('SOURCE_PROFILE_CHANNEL_INVALID')
    state = receipt['state']
    evidence_kind = receipt['evidence_kind']
    synthetic = evidence_kind == 'synthetic_fixture'
    execution = 'NOT_EXECUTED_SYNTHETIC' if synthetic else 'OPERATOR_DECLARED_UNATTESTED'
    qualifier = 'SYNTHETIC' if synthetic else 'OPERATOR_DECLARED'
    run_binding = None
    candidates = []
    counts = {q['enzyme_accession']: 0 for q in queries}
    if state == 'COMPLETE':
        if profile and (receipt.get('output_profile') != profile['id'] or receipt.get('output_channel') != channel or receipt.get('source_profile_sha256') != sources[-1]['sha256']):
            raise ValueError('RUN_SOURCE_PROFILE_BINDING_MISMATCH')
        if profile and receipt['evidence_kind'] == 'operator_supplied' and receipt.get('upstream_revision') != profile['revision']:
            raise ValueError('ARCHIVED_PROFILE_REQUIRES_MATCHING_SOURCE_REVISION')
        if receipt.get('queries_sha256') != sources[0]['sha256']:
            raise ValueError('RUN_QUERIES_BINDING_MISMATCH')
        if not all((raw_path, columns_path, config_path, completion_log_path)):
            raise ValueError('COMPLETE_REQUIRES_RAW_COLUMNS_CONFIG_LOG')
        revision = receipt.get('upstream_revision', '')
        if not isinstance(revision, str) or not re.fullmatch(r'(?:[0-9a-f]{40}|sha256:[0-9a-f]{64})', revision):
            raise ValueError('UPSTREAM_COMMIT_OR_IMAGE_DIGEST_REQUIRED')
        if revision in {'0'*40, 'sha256:'+'0'*64} and receipt['evidence_kind'] != 'synthetic_fixture':
            raise ValueError('SYNTHETIC_REVISION_NOT_LIVE_PROVENANCE')
        if receipt.get('exit_code') != 0 or type(receipt.get('exit_code')) is not int:
            raise ValueError('COMPLETE_REQUIRES_ZERO_EXIT')
        versions = receipt.get('runtime_versions')
        if not isinstance(versions, dict) or not versions or any(not nonempty(k) or not nonempty(v) for k, v in versions.items()):
            raise ValueError('DECLARED_RUNTIME_VERSIONS_REQUIRED')
        assessed = receipt.get('completed_accessions')
        if not isinstance(assessed, list) or any(not isinstance(x, str) for x in assessed) or len(assessed) != len(set(assessed)) or set(assessed) != set(counts):
            raise ValueError('COMPLETE_QUERY_COVERAGE_REQUIRED')
        raw = load_bytes(raw_path)
        sources.append(binding(raw_path, raw))
        config = load_bytes(config_path)
        sources.append(binding(config_path, config))
        if not config.strip():
            raise ValueError('EMPTY_RUNTIME_CONFIG')
        if receipt.get('raw_sha256') != sources[-2]['sha256'] or receipt.get('config_sha256') != sources[-1]['sha256']:
            raise ValueError('RUN_RAW_OR_CONFIG_BINDING_MISMATCH')
        completion_log = load_bytes(completion_log_path)
        sources.append(binding(completion_log_path, completion_log))
        if not completion_log.strip() or receipt.get('completion_log_sha256') != sources[-1]['sha256']:
            raise ValueError('COMPLETION_LOG_BINDING_MISMATCH')
        columns = json_input(columns_path, sources)
        if receipt.get('columns_sha256') != sources[-1]['sha256']:
            raise ValueError('RUN_COLUMNS_BINDING_MISMATCH')
        if run_binding_path:
            wanted = {'raw_output':binding(raw_path,load_bytes(raw_path)), 'config':binding(config_path,load_bytes(config_path)),
                      'completion_log':binding(completion_log_path,load_bytes(completion_log_path)),
                      'queries':sources[0], 'columns':sources[-1]}
            run_binding = run_binding_module().verify_boundary(binding_api(),run_binding_path,bound_files,sources,wanted,True,receipt,adapted_profile_path)
        elif bound_files:
            raise ValueError('RUN_BINDING_ARTIFACT_REQUIRED')
        keys = {'enzyme_accession', 'peptide_id', 'sequence'}
        if not isinstance(columns, dict) or set(columns) != keys or any(not nonempty(v) for v in columns.values()) or len(set(columns.values())) != 3:
            raise ValueError('EXPLICIT_COLUMN_MAPPING_REQUIRED')
        if profile and columns != profile['columns']:
            raise ValueError('ARCHIVED_PROFILE_COLUMNS_MISMATCH')
        reader = csv.DictReader(io.StringIO(raw.decode('utf-8')), delimiter='\t')
        fields = reader.fieldnames
        if not fields or len(fields) != len(set(fields)) or not set(columns.values()) <= set(fields):
            raise ValueError('UPSTREAM_TSV_HEADER_MISMATCH')
        if profile and fields != profile['headers']:
            raise ValueError('ARCHIVED_PROFILE_EXACT_HEADER_REQUIRED')
        seen = set()
        by_accession = {q['enzyme_accession']: q for q in queries}
        for number, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise ValueError('UPSTREAM_TSV_ROW_INVALID')
            normalized = {k: row[v] for k, v in columns.items()}
            accession, peptide, sequence = (normalized[k] for k in ('enzyme_accession', 'peptide_id', 'sequence'))
            if accession not in by_accession:
                raise ValueError('UNBOUND_ENZYME_ACCESSION')
            if not nonempty(peptide) or not re.fullmatch(r'[ACDEFGHIKLMNPQRSTVWY]+', sequence):
                raise ValueError('PEPTIDE_ID_OR_SEQUENCE_INVALID')
            if profile:
                if not re.fullmatch(re.escape(accession)+r'_\d+', peptide):
                    raise ValueError('ARCHIVED_PROFILE_SUBJECT_PEPTIDE_ID_MISMATCH')
                serial = row['PPSerial']
                if not re.fullmatch(r'[1-9][0-9]*', serial):
                    raise ValueError('ARCHIVED_PROFILE_SERIAL_INVALID')
                if peptide != accession+'_'+serial:
                    raise ValueError('ARCHIVED_PROFILE_SERIAL_ID_MISMATCH')
                distant = bool(re.fullmatch(r'9[0-9]{3,}', serial))
                if distant != (channel == 'distant') or (distant and (not nonempty(row['hname']) or row['hname'] == 'none')):
                    raise ValueError('ARCHIVED_PROFILE_CHANNEL_ROW_MISMATCH')
            if (accession, peptide) in seen:
                raise ValueError('DUPLICATE_QUERY_PEPTIDE')
            seen.add((accession, peptide))
            query = by_accession[accession]
            candidates.append(dict(**normalized,
                                   query_context={k: query[k] for k in IDENTITY},
                                   query_identity=' / '.join(query[k] for k in IDENTITY),
                                   candidate_membership='UNVERIFIED',
                                   attribution_status='HOLD_COORDINATE_ASSEMBLY_MAPPING',
                                   evidence_kind=evidence_kind, upstream_execution=execution,
                                   candidate_status=qualifier+'_RETAINED_ROW',
                                   source_row=number, raw_fields=row))
            counts[accession] += 1
    elif any((raw_path, columns_path, config_path, completion_log_path,run_binding_path,bound_files)):
        raise ValueError('NONCOMPLETE_RESULTS_NOT_ADMITTED')
    assessments = []
    for query in queries:
        assessment_status = qualifier+'_DECLARED_'+state
        if state == 'COMPLETE':
            suffix = 'RETAINED_CANDIDATES' if counts[query['enzyme_accession']] else 'NO_RETAINED_CANDIDATES'
            assessment_status = qualifier+'_'+suffix
        assessments.append(dict(enzyme_accession=query['enzyme_accession'],
                                query_context={k: query[k] for k in IDENTITY},
                                query_identity=' / '.join(query[k] for k in IDENTITY),
                                assessment_status=assessment_status,
                                evidence_kind=evidence_kind, upstream_execution=execution,
                                declared_upstream_state=state,
                                retained_candidate_count=counts[query['enzyme_accession']] if state == 'COMPLETE' else None))
    data = dict(schema_version='ripper-evidence/2', upstream=PROJECT, method_doi=DOI,
                import_status='ADMITTED_SYNTHETIC' if synthetic else 'ADMITTED_OPERATOR_DECLARATION',
                declared_upstream_state=state, evidence_kind=evidence_kind,
                evidence_outcome=('RETAINED_CANDIDATES_UNBOUND' if candidates else 'NO_RETAINED_ROWS_DECLARED_SCOPE') if state == 'COMPLETE' else state,
                biological_absence_inferred=False,
                upstream_execution=execution, candidate_membership='UNVERIFIED',
                attribution_status='HOLD_COORDINATE_ASSEMBLY_MAPPING',
                provenance=receipt, provenance_verification='DECLARED_NOT_INDEPENDENTLY_ATTESTED',
                sources=sources, query_count=len(queries), candidate_count=len(candidates) if state == 'COMPLETE' else None,
                assessments=assessments, candidates=candidates, claim_ceiling=LIMIT,
                source_profile=profile, output_channel=channel, run_binding=run_binding,
                channel_validation=(dict(scope='canonical positive PPSerial/FastaID pair, lexical channel, nonblank/non-none hname; does not verify HMM collection',
                                         hmm_collection_identity='UNVERIFIED_NOT_PRESENT_IN_TSV',
                                         score_distance_validation='RAW_PRESERVED_NOT_SEMANTICALLY_VALIDATED',
                                         holds=['HOLD_HMM_COLLECTION_PROVENANCE'] if channel == 'distant' else []) if profile else None),
                scope='selected tailoring-enzyme queries and retained rows in one supplied TSV; no genome-wide absence inference')
    publish(out, {'RIPPER_EVIDENCE.json': data}, sources)
    return data


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('plan', help='write a plan and accession list; no execution')
    p.add_argument('--queries', required=True)
    p.add_argument('--out', required=True)
    p = sub.add_parser('source-profile', help='export verified archived output-column contract; no execution')
    p.add_argument('--profile', required=True)
    p.add_argument('--out', required=True)
    p = sub.add_parser('local-plan', help='hold-only local GenBank plan; no upstream execution')
    for arg in ('queries', 'genbank', 'query-fasta', 'config', 'profile', 'out'):
        p.add_argument('--'+arg, required=True)
    p.add_argument('--adapted-profile')
    p.add_argument('--run-bindings')
    p.add_argument('--bound-file', action='append')
    p.add_argument('--semantic-validation', action='store_true', help='opt in to strict Biopython input binding; still no execution')
    p = sub.add_parser('adapted-profile',help='bind explicit local05 base/patch/postimage; no upstream execution')
    for arg in ('owner-receipt','base-source','source-patch','adapted-source','out'):
        p.add_argument('--'+arg,required=True)
    p = sub.add_parser('bind-run', help='bind explicit file-role digests; no execution or readiness proof')
    p.add_argument('--adapted-profile')
    p.add_argument('--manifest',required=True)
    p.add_argument('--file',action='append',required=True)
    p.add_argument('--out',required=True)
    p = sub.add_parser('lifecycle',help='bounded preflight; explicit reviewed native or self-authored stub opt-in')
    for arg in ('spec','run-root'):
        p.add_argument('--'+arg,required=True)
    p.add_argument('--file',action='append',required=True)
    p.add_argument('--adapted-profile')
    p.add_argument('--execute-stub',action='store_true')
    p.add_argument('--execute-native',action='store_true')
    p.add_argument('--native-admission')
    p.add_argument('--resume-preflight',action='store_true')
    p.add_argument('--cancel-file')
    p = sub.add_parser('native-result',help='inspect explicit retained N3 native terminal/raw bytes; no execution or annotation')
    for arg in ('terminal','out'):p.add_argument('--'+arg,required=True)
    p.add_argument('--raw')
    p.add_argument('--control-result',help='explicit outer control receipt required for legacy terminal publication')
    p = sub.add_parser('native-coordinates',help='evaluate an explicit native reconstruction packet and file roster; no native execution')
    for arg in ('packet','out'):p.add_argument('--'+arg,required=True)
    p.add_argument('--file',action='append',required=True)
    p.add_argument('--control-result')
    p = sub.add_parser('bind-coordinates', help='evaluate bound coordinate declarations; no upstream or membership proof')
    for arg in ('evidence','local-plan','genbank','query-fasta','mapping','out'):
        p.add_argument('--'+arg, required=True)
    p = sub.add_parser('import', help='admit operator-supplied RiPPER rows or an unavailable/failed/not-run state')
    for arg in ('queries', 'receipt', 'out'):
        p.add_argument('--'+arg, required=True)
    for arg in ('raw', 'columns', 'config', 'completion-log', 'source-profile', 'channel'):
        p.add_argument('--'+arg)
    p.add_argument('--adapted-profile')
    p.add_argument('--run-bindings')
    p.add_argument('--bound-file',action='append')
    args = parser.parse_args(argv)
    try:
        if args.command == 'plan':
            data = plan(args.queries, args.out)
        elif args.command == 'source-profile':
            data = write_profile(args.profile, args.out)
        elif args.command == 'local-plan':
            data = local_plan(args.queries, args.genbank, args.query_fasta, args.config, args.out, args.profile, args.semantic_validation,args.run_bindings,args.bound_file,args.adapted_profile)
        elif args.command == 'adapted-profile':
            data=owned_module('ripper_source_admission').admit_adapted_profile(binding_api(),args.owner_receipt,args.base_source,args.source_patch,args.adapted_source,args.out)
        elif args.command == 'bind-run':
            data = run_binding_module().bind_run(binding_api(),args.manifest,args.file,args.out,args.adapted_profile)
        elif args.command == 'lifecycle':
            data=owned_module('ripper_lifecycle').lifecycle(binding_api(),args.spec,args.file,args.run_root,args.adapted_profile,args.execute_stub,args.cancel_file,args.execute_native,args.native_admission,args.resume_preflight)
            args.out=args.run_root
        elif args.command == 'native-result':
            data=owned_module('ripper_native_result').native_result(binding_api(),args.terminal,args.raw,args.out,args.control_result)
        elif args.command == 'native-coordinates':
            data=owned_module('ripper_native_coordinates').native_coordinates(binding_api(),args.packet,args.file,args.out,args.control_result)
        elif args.command == 'bind-coordinates':
            import importlib.util
            spec = importlib.util.spec_from_file_location('ripper_coordinate_binding', Path(__file__).with_name('ripper_coordinate_binding.py'))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            api = dict(json_input=json_input, load_bytes=load_bytes, binding=binding, publish=publish, IDENTITY=IDENTITY, validate_local_semantics=validate_local_semantics)
            data = module.bind_coordinates(api,args.evidence,args.local_plan,args.genbank,args.query_fasta,args.mapping,args.out)
        else:
            data = import_results(args.queries, args.receipt, args.out, args.raw, args.columns, args.config, args.completion_log, args.source_profile, args.channel,args.run_bindings,args.bound_file,args.adapted_profile)
        if args.command == 'adapted-profile':
            data.update(plan_status=data['profile_status'],query_count=0)
        if args.command == 'bind-run':
            data.update(plan_status=data['binding_status'],query_count=0)
        if args.command in ('plan', 'local-plan','bind-run','adapted-profile'):
            LOG.info('RiPPER plan %s; upstream_execution=%s; semantic_validation=%s; %s queries; output %s',
                     data['plan_status'], data['upstream_execution'],
                     data.get('semantic_validation', {}).get('status', 'NOT_APPLICABLE'), data['query_count'], Path(args.out).resolve())
        elif args.command == 'lifecycle':
            LOG.info('RiPPER lifecycle %s; mode=%s; upstream_execution=%s; raw_candidates=%s; output_admission=%s; BGC_membership=UNVERIFIED; output %s', data['status'],data.get('mode','UNDECLARED'),data['upstream_execution'],data.get('raw_discovery',{}).get('candidate_count') if data.get('output_admission')=='SCOPED_BOUND_BYTES_ONLY' else None,data.get('output_admission','NOT_ADMITTED'),Path(args.out).resolve())
        elif args.command == 'native-result':
            LOG.info('RiPPER native result %s; raw_candidates=%s; HMM=%s; coordinates=%s; BGC_membership=%s; canonical_import=%s; output %s',data['terminal_status'],data['raw_candidate_count'],data['hmm_annotation'],data['coordinate_status'],data['candidate_membership'],data['canonical_import'],Path(args.out).resolve())
        elif args.command == 'native-coordinates':
            LOG.info('RiPPER native coordinates %s; evaluated=%s; origin=%s; BGC_membership=UNVERIFIED; HMM=NOT_RUN_SEPARATE_STAGE; output %s',data['import_status'],data['evaluated_candidate_count'],data['coordinate_evidence_origin'],Path(args.out).resolve())
        elif args.command == 'source-profile':
            LOG.info('RiPPER source profile %s; upstream_execution=NOT_EXECUTED; output %s', data['id'], Path(args.out).resolve())
        else:
            LOG.info('RiPPER import %s; evidence_kind=%s; upstream_execution=%s; declared_upstream_state=%s; %s queries; output %s',
                     data['import_status'], data['evidence_kind'], data['upstream_execution'],
                     data['declared_upstream_state'], data['query_count'], Path(args.out).resolve())
        if args.command=='native-result' and data['raw_admission']!='EXPLICIT_HASH_BOUND_RAW_SCOPE_ONLY':return 2
        if args.command=='lifecycle':
            if data['status']=='INTERRUPTED':return 130
            if data['status'] in {'FAILED','AMBIGUOUS'} or ((args.execute_stub or args.execute_native) and data['status'] in {'UNAVAILABLE','HOLD'}):return 2
        return 0
    except (ValueError, OSError, UnicodeError, csv.Error, KeyboardInterrupt) as exc:
        LOG.error('RIPPER_ADAPTER_REFUSED: %s; next_action=%s', exc, refusal_action(str(exc).split(':',1)[0]))
        return 130 if isinstance(exc,KeyboardInterrupt) else 2


if __name__ == '__main__':
    raise SystemExit(main())
