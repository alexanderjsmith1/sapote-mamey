#!/usr/bin/env python3
"""Optional, external CORASON plan/run/read. No work occurs at import time.

Original pinned source profile; outputs PRIVATE. Native runtime/resource admission
is distinct from synthetic protocol conformance. See docs/CORASON_WORKFLOW.md.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import os
import platform
from pathlib import Path, PurePosixPath
import re
import shutil
import shlex
import subprocess
import sys
import time
from types import SimpleNamespace
import uuid
from urllib.parse import urlparse
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.csv_safety import SafeDictWriter
from mamey.exact_identity import exact_locus_from_native_manifest_bgc
from mamey.postseal_output import package_binding, resolve_source_archive
from _release_validation import atomic_json, canonical_json, run_watched, sha256_file, utc_now

PROFILE = 'corason-original-aa70ddde-region-v1'
COMMIT = 'aa70dddebafb210445794fd24b1c6b2e4177c58c'
MAX_FILE = 32 * 1024 * 1024
MAX_STAGE = 256 * 1024 * 1024
MAX_LOCI = 120
MAX_NEIGHBORHOODS = 1000
THREAD_ENV_KEYS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                   'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'OMP_THREAD_LIMIT')
SHA = re.compile(r'[0-9a-f]{64}')
TOKEN = re.compile(r'[A-Za-z0-9][A-Za-z0-9_]{0,63}')
SAFE_SHELL_PATH = re.compile(r'/[A-Za-z0-9_./-]+')
DEFAULTS = {'e_value': '1E-15', 'bitscore': '0', 'cluster_radio': '10',
            'e_cluster': '1E-3', 'e_core': '1E-3', 'rescale': '85000'}
# Git blob IDs from primary pinned CORASON directory metadata, not local runtime.
PINNED_HELPERS = {'1_Context_text.pl': '39339925ae23ceed275466570e1167513357b8f1', '2.Batch_RetrieveFiles.pl': '95db10d1f2eb96fdcf4e828e22e8c4e1484ff28f', '2_OrthoGroups.pl': 'c1656986feca750281d93a28f495a3d632146d36', '3_Draw.pl': '537b2f3b75fff924da296457ee1de689b40b9db6', 'ChangeName.pl': 'd20b30161e9f97a85c7b3d7ce383e0ca23e7d4ca', 'Concatenador.pl': '6bde10c1dad8c446132119a6ef1193889440a8f3', 'CoreCluster.pl': '9500edb8b0822b0e0bec8c38c94b18e50ad5324a', 'EliminadorLineas.pl': '2f73eecf588c6676273b148091c1b6fb58a4bbdb', 'GbkCreator.pl': '413a1107b3e6ff5fbabc519848d794178e7d5388', 'ReadReaccion.pl': '9982cec07354e4e6815b51683462418b6468072f', 'ReadingInputs.pl': '84f01685c5b5dd2c49ff4df58a56eb561552faac', 'RenamePrincipalHits.pl': '753ed8a78d35762b265b6d044acc9c74ff4af192', 'Rename_Ids_Star_Tree.pl': 'e95dba50d4ac0f76875aa79dc9ab4825ec6fa009', 'SSHcorason.pl': '56acd83183f1dd159b8d02b715d7544297722bb8', 'SearchAminoacidsFromCore.pl': '9656d95dfb5232354657ec585da167d6335401b8', 'allvsall.pl': '264b739c0e20e3602b8a1c76ca03d3c6012047f5', 'changeNamesWC.pl': '86baf927abf5aa554f1ecfe85a0fa669983fe1ea', 'converter.pl': '09bc5437d0f7fd564b0de6b42300c78d5bf5e9aa', 'cor_formatdb.pl': 'c3f1bee116006071d7d5424557a76bf670891363', 'corason.pl': 'ba4ffbcebc8b8c5174cd3147dc54f6a61dfc93ef', 'gbkIndex.pl': '278aa63b3a582ae104fd57cc774fad9089985936', 'gbkToRast.pl': '1a4d6d035e3ff0b92d7d38a49e0448421f5bcc8f', 'gbk_ToRast2.pl': '47be4d056cf2138fc35be80973fc0b75db807024', 'gbk_to_fasta.pl': 'c18474ce372dbd155f5a93722fe437db90b8d953', 'header.pl': 'e3b549ecd55203f4df3497cd9ba913a37a80a186', 'header2.pl': '983f497e531bc8a98e711878b96799b910158175', 'multiAlign_gb.pl': '62a42e89b1d068516914653e918094dad25cc69d', 'readTree.pl': 'c8a9da8e4070a15c327bb9832f44a6adb614e81e'}


class AdapterError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__('CORASON_ERROR[' + code + ']')


def require(condition, code):
    if not condition:
        raise AdapterError(code)


def digest(value):
    require(isinstance(value, str) and SHA.fullmatch(value), 'DIGEST_INVALID')
    return value


def binding(path):
    p = Path(path).expanduser().resolve(strict=True)
    require(p.is_file(), 'REGULAR_FILE_REQUIRED')
    return {'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha256_file(p)}


def json_file(path):
    p = Path(path)
    require(p.is_file() and p.stat().st_size <= MAX_FILE, 'METADATA_LIMIT_OR_MISSING')
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AdapterError('METADATA_MALFORMED') from exc
    require(isinstance(data, dict), 'METADATA_OBJECT_REQUIRED')
    return data


def content_digest(value):
    return hashlib.sha256(canonical_json(value)).hexdigest()


def bound_file(record):
    require(isinstance(record, dict), 'BINDING_INVALID')
    actual = binding(record['path'])
    require(actual == record, 'BOUND_FILE_CHANGED')
    return actual


def contained(p, root):
    return p == root or root in p.parents


def regular_tree(root):
    p = Path(root).resolve(strict=True)
    require(p.is_dir(), 'DIRECTORY_REQUIRED')
    result = {}
    for f in sorted(p.rglob('*')):
        require(not f.is_symlink(), 'RESULT_SYMLINK')
        if f.is_file():
            result[f.relative_to(p).as_posix()] = binding(f)
    return result


def output_path(out, write_root, protected):
    root = Path(write_root).resolve(strict=True)
    require(root.is_dir(), 'WRITE_ROOT_REQUIRED')
    raw = Path(out).expanduser().absolute()
    p = raw.resolve()
    require(contained(p, root) and p != root and not os.path.lexists(raw), 'OUTPUT_OCCUPIED_OR_OUTSIDE_ROOT')
    for other in [Path(__file__).resolve().parents[1], *map(Path, protected)]:
        other = other.resolve()
        require(not contained(p, other) and not contained(other, p), 'OUTPUT_PROTECTED_ALIAS')
    return p


def fresh(out, write_root, protected):
    p = output_path(out, write_root, protected)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive directory reservation; a racing existing destination is not reused.
    try:
        p.mkdir()
    except FileExistsError as exc:
        raise AdapterError('OUTPUT_RESERVATION_LOST') from exc
    return p


def source_loci(intake_path):
    intake = json_file(intake_path)
    require(intake.get('schema') == 'corason.public-intake.v1', 'INTAKE_SCHEMA')
    records = intake.get('records')
    require(isinstance(records, list) and 0 < len(records) <= MAX_LOCI, 'INTAKE_COUNT')
    loci = []
    sources = []
    seen = set()
    for record in records:
        pkg = Path(record['package']).resolve(strict=True)
        manifest_path = pkg / 'manifest.json'
        require(binding(manifest_path)['sha256'] == digest(record['package_manifest_sha256']), 'PACKAGE_BINDING')
        manifest = json_file(manifest_path)
        archive, archive_binding = resolve_source_archive(pkg, record['source_zip'])
        require(archive_binding['sha256'] == digest(record['source_zip_sha256']), 'SOURCE_ARCHIVE_BINDING')
        require(archive.stat().st_size == record['source_bytes'], 'SOURCE_ARCHIVE_SIZE')
        public_binding = bound_file(record['public_receipt'])
        public = json_file(public_binding['path'])
        require(public.get('schema') == 'corason.public-source-review.v1' and
                public.get('state') == 'REVIEWED_PUBLIC_SOURCE_BINDING' and
                public.get('source_zip_sha256') == archive_binding['sha256'] and
                isinstance(public.get('accession_versions'), list) and public['accession_versions'] and
                isinstance(public.get('primary_sources'), list) and public['primary_sources'], 'PUBLIC_INPUT_UNVERIFIED')
        for source in public['primary_sources']:
            require(isinstance(source, dict) and str(source.get('url', '')).startswith('https://') and
                    source.get('accession_version') in public['accession_versions'], 'PUBLIC_PRIMARY_BINDING')
            digest(source.get('metadata_sha256'))
        require(manifest.get('input_zip_sha256') == archive_binding['sha256'] and
                isinstance(manifest.get('bgcs'), list), 'PACKAGE_SCHEMA')
        package = package_binding(pkg)
        validation_binding = bound_file(record['validation_receipt'])
        validation = json_file(validation_binding['path'])
        require(validation.get('schema') == 'corason.package-validation-review.v1' and
                validation.get('state') == 'VALIDATED' and validation.get('package_tree_sha256') == package['package_tree_sha256'] and
                validation.get('evidence_sha256') and validation.get('evidence_path'), 'PACKAGE_VALIDATION_UNBOUND')
        require(binding(validation['evidence_path'])['sha256'] == digest(validation['evidence_sha256']), 'PACKAGE_VALIDATION_EVIDENCE_CHANGED')
        sources.append({'package': package, 'archive': binding(archive), 'public_receipt': public_binding, 'validation_receipt': validation_binding,
                        'validation_evidence': binding(validation['evidence_path'])})
        for bgc in manifest['bgcs']:
            ident = exact_locus_from_native_manifest_bgc(manifest['strain_id'], bgc)
            require(ident.full_contig in public['accession_versions'], 'PUBLIC_CONTIG_UNVERIFIED')
            key = ident.exact_locus
            require(key not in seen, 'DUPLICATE_LOCUS')
            seen.add(key)
            member = bgc.get('source_gbk')
            rel = PurePosixPath(str(member))
            require(member and not rel.is_absolute() and '..' not in rel.parts and '\\' not in member, 'SOURCE_MEMBER_INVALID')
            require(type(bgc.get('start')) is int and type(bgc.get('end')) is int and
                    0 <= bgc['start'] < bgc['end'], 'LOCUS_COORDINATES')
            loci.append({'exact_locus': key, 'strain': ident.strain, 'full_contig': ident.full_contig,
                         'region': ident.region, 'bgc_alias': ident.bgc_alias,
                         'start': bgc['start'], 'end': bgc['end'], 'source_member': member,
                         'archive': binding(archive), 'manifest': binding(manifest_path)})
    require(len(loci) <= MAX_LOCI, 'LOCUS_LIMIT')
    return {'intake': binding(intake_path), 'sources': sources, 'loci': loci}


def observer_source():
    """Run-local witness, not an upstream patch; bytes are part of method identity.

    Capture actual native neighborhoods before ReadingInputs deletes them. Witness
    original helper/tool status, argv and artifacts, preserving stdout semantics.
    """
    return r'''import hashlib,json,os,pathlib,subprocess,sys,time,uuid
cfg=json.loads(pathlib.Path(os.environ['CORASON_OBSERVER_CONFIG']).read_text())
name=sys.argv.pop(1)
entry=cfg['entries'][name]
qa=pathlib.Path(cfg['qa']); qa.mkdir(exist_ok=True)
id=uuid.uuid4().hex
record={'name':name,'argv':sys.argv[1:],'started':time.time(),'status':'RUNNING'}
log=qa/('witness_'+id+'.json'); log.write_text(json.dumps(record))
def sha(raw): return hashlib.sha256(raw).hexdigest()
try:
 if name=='blastp' and '-num_threads' in sys.argv:
  ix=sys.argv.index('-num_threads')
  if ix+1>=len(sys.argv) or int(sys.argv[ix+1])>cfg['resources']['cpu_total']: raise ValueError('CPU budget exceeded')
 if name=='ReadingInputs.pl':
  root=pathlib.Path(sys.argv[1]).resolve()
  work=pathlib.Path(cfg['work']).resolve()
  if root!=work/'query.faa-output': raise ValueError('unexpected output root')
  rows={}; total=0
  for p in sorted(root.glob('*')):
   if p.suffix not in ('.input','.input2') and not p.name.endswith(('.BLAST','.BLAST.pre')): continue
   if p.is_symlink() or not p.is_file() or p.stat().st_size>33554432: raise ValueError('capture file refused')
   raw=p.read_bytes(); total+=len(raw)
   if total>67108864: raise ValueError('capture limit')
   # Private working directory contains admitted public inputs only. Preserve
   # exact prefilter evidence in owned qa; never read a research result folder.
   dst=qa/('prefilter_'+p.name)
   with dst.open('xb') as h: h.write(raw)
   rows[p.name]={'bytes':len(raw),'sha256':sha(raw),'capture':str(dst)}
  if (qa/'PREFILTER.json').exists(): raise ValueError('duplicate capture')
  (qa/'PREFILTER.json').write_text(json.dumps({'schema':'corason.prefilter.v1','files':rows,'root':str(root)}))
 p=subprocess.run([*entry,*sys.argv[1:]],check=False)
 record.update(status='TERMINAL',returncode=p.returncode,ended=time.time())
 log.write_text(json.dumps(record))
 sys.exit(p.returncode)
except BaseException as exc:
 if isinstance(exc,SystemExit): raise
 record.update(status='FAILED_OBSERVER',error=type(exc).__name__,ended=time.time())
 log.write_text(json.dumps(record)); raise
'''


def native_cpu_budget(declared):
    available = os.cpu_count()
    require(type(available) is int and available > 0 and declared <= available, 'HOST_CPU_BUDGET_HOLD')
    return available


def runtime(path):
    data = json_file(path)
    require(data.get('schema') == 'corason.runtime.v1' and data.get('profile') == PROFILE, 'RUNTIME_PROFILE')
    kind = data.get('kind')
    require(kind in ('NATIVE', 'SYNTHETIC_PROTOCOL_TEST'), 'RUNTIME_KIND')
    identity = data.get('identity')
    require(isinstance(identity, dict), 'RUNTIME_IDENTITY')
    review_binding = bound_file(data['review_receipt'])
    review = json_file(review_binding['path'])
    require(review.get('schema') == 'corason.runtime-review.v1' and
            review.get('intent') == kind and review.get('state') == 'REVIEWED' and
            review.get('identity_sha256') == content_digest(identity) and
            review.get('observer_sha256') == hashlib.sha256(observer_source().encode()).hexdigest(), 'RUNTIME_NOT_REVIEWED')
    require(identity.get('commit') == COMMIT and identity.get('prefilter_observer') == 'ReadingInputs-before-deletion-v1', 'RUNTIME_SOURCE_PROFILE')
    interpreter = bound_file(identity['interpreter'])
    python = bound_file(identity['observer_python'])
    require(SAFE_SHELL_PATH.fullmatch(interpreter['path']) and SAFE_SHELL_PATH.fullmatch(python['path']), 'NATIVE_SHELL_PATH_UNSAFE')
    helpers = identity.get('helpers')
    require(isinstance(helpers, dict) and {'corason.pl', 'gbkIndex.pl', 'ReadingInputs.pl'} <= helpers.keys(), 'RUNTIME_HELPERS')
    if kind == 'NATIVE':
        source_root_value = identity.get('source_root')
        require(isinstance(source_root_value, str) and bool(source_root_value), 'NATIVE_SOURCE_ROOT')
        try:
            source_root = Path(source_root_value).resolve(strict=True)
        except OSError as exc:
            raise AdapterError('NATIVE_SOURCE_ROOT') from exc
        require(source_root.is_dir(), 'NATIVE_SOURCE_ROOT')
        require(set(helpers) == set(PINNED_HELPERS), 'NATIVE_HELPER_CLOSURE')
    for name, row in helpers.items():
        require(Path(name).name == name and TOKEN.fullmatch(name.replace('.', '_')), 'HELPER_NAME')
        actual = bound_file(row)
        require(SAFE_SHELL_PATH.fullmatch(actual['path']), 'NATIVE_SHELL_PATH_UNSAFE')
        if kind == 'NATIVE':
            require(Path(actual['path']) == source_root/'CORASON'/name, 'ENTRY_SOURCE_ROOT_MISMATCH')
            raw = Path(actual['path']).read_bytes()
            git_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            require(git_blob == PINNED_HELPERS[name], 'NATIVE_SOURCE_NOT_PINNED')
    # The actual executed entry is the admitted helper, not an independent script.
    require(identity.get('entry') == helpers['corason.pl'], 'ENTRY_SOURCE_MISMATCH')
    tools = identity.get('tools')
    require(isinstance(tools, dict), 'TOOLS_PROFILE')
    for name, row in tools.items():
        require(TOKEN.fullmatch(name), 'TOOL_NAME')
        bound_file(row['file'])
        require(SAFE_SHELL_PATH.fullmatch(row['file']['path']), 'NATIVE_SHELL_PATH_UNSAFE')
        require(isinstance(row.get('probe'), list) and all(isinstance(x, str) for x in row['probe']), 'TOOL_PROBE')
    if kind == 'NATIVE':
        require({'blastp', 'makeblastdb', 'muscle', 'Gblocks', 'FastTree', 'nw_topology', 'nw_display', 'nw_labels'} <= tools.keys(), 'NATIVE_TOOL_CLOSURE')
        for tool in tools.values():
            require(isinstance(tool.get('reported_version'), str) and tool['reported_version'], 'TOOL_VERSION_HOLD')
            digest(tool.get('probe_stdout_sha256')); digest(tool.get('probe_stderr_sha256'))
        require(identity.get('architecture') == platform.machine() and identity.get('perl_modules_reviewed') is True and
                identity.get('transitive_io_reviewed') is True, 'NATIVE_ENVIRONMENT_HOLD')
    resources = identity.get('resources', {})
    require(resources.get('source_reviewed') is True and resources.get('parallel_runs') == 1 and
            type(resources.get('cpu_total')) is int and resources['cpu_total'] > 0 and
            resources.get('prefilter_stage_reviewed') is True, 'RESOURCE_PROFILE_HOLD')
    if kind == 'NATIVE':
        require(resources['cpu_total'] >= 12, 'PINNED_BLAST_CPU_BUDGET')
        native_cpu_budget(resources['cpu_total'])
        threads = resources.get('effective_tool_threads', {})
        jobs = resources.get('max_concurrent_children')
        require(isinstance(threads, dict) and set(threads) == set(tools) and
                all(type(v) is int and v > 0 for v in threads.values()) and
                threads.get('blastp', 0) >= 12 and type(jobs) is int and jobs > 0 and
                max(threads.values()) * jobs <= resources['cpu_total'], 'EFFECTIVE_CPU_BOUND_HOLD')
        bound_file(identity['environment_receipt'])
        digest(identity.get('entry_help_stdout_sha256'))
    require(identity.get('environment') and isinstance(identity['environment'], dict), 'ENVIRONMENT_PROFILE')
    # No environment injection replacing observer entries; admitted PATH is explicit.
    require(not any(k.startswith('CORASON_') for k in identity['environment']), 'ENVIRONMENT_RESERVED')
    require(all(identity['environment'].get(k) == '1' for k in THREAD_ENV_KEYS) and
            identity['environment'].get('PYTHONDONTWRITEBYTECODE') == '1', 'THREAD_ENVIRONMENT_HOLD')
    require(all(isinstance(k, str) and isinstance(v, str) for k, v in identity['environment'].items()) and
            identity['environment'].get('PATH'), 'ENVIRONMENT_VALUES')
    return {'manifest': binding(path), 'review_receipt': review_binding, 'kind': kind, 'identity': identity,
            'host_cpu_observation': os.cpu_count(), 'cpu_policy': 'NO_OVERSUBSCRIPTION_IN_NATIVE_PROFILE'}


def check_unchanged(plan):
    bound_file(plan['intake']['intake'])
    for source in plan['intake']['sources']:
        bound_file(source['archive']); bound_file(source['public_receipt']); bound_file(source['validation_receipt']); bound_file(source['validation_evidence'])
        require(package_binding(source['package']['package']) == source['package'], 'PACKAGE_CHANGED')
    require(runtime(plan['runtime']['manifest']['path']) == plan['runtime'], 'RUNTIME_CHANGED')
    bound_file(plan['selection'])
    require(source_loci(plan['intake']['intake']['path']) == plan['intake'], 'PLAN_INTAKE_DERIVATION')
    selection = json_file(plan['selection']['path'])
    index = {row['exact_locus']: row for row in plan['intake']['loci']}
    require(selection.get('schema') == 'corason.selection.v1' and selection.get('query') == plan['query'] and
            plan['selected_loci'] == [index[x] for x in selection.get('loci', [])], 'PLAN_SELECTION_DERIVATION')
    require(plan['resource_policy'] == {'rss_limit': 3800000000, 'min_disk': 2000000000, 'timeout': 1800,
        'serial_runs': 1, 'cpu_total': plan['runtime']['identity']['resources']['cpu_total']}, 'PLAN_RESOURCE_DERIVATION')


def plan_command(a):
    intake = source_loci(a.intake)
    rt = runtime(a.runtime_manifest)
    if rt['kind'] == 'NATIVE':
        for source in intake['sources']:
            public = json_file(source['public_receipt']['path'])
            validation = json_file(source['validation_receipt']['path'])
            require(public.get('scope') == 'PRIMARY_PUBLIC_SOURCE_BINDING' and validation.get('scope') == 'ACTUAL_PACKAGE_VALIDATION', 'SYNTHETIC_EVIDENCE_NOT_NATIVE_ADMISSION')
            for record in public['primary_sources']:
                host = urlparse(record['url']).hostname or ''
                require(host == 'www.ebi.ac.uk' or host == 'eutils.ncbi.nlm.nih.gov' or host.endswith('.ncbi.nlm.nih.gov'), 'PUBLIC_PRIMARY_HOST_UNVERIFIED')
    selection = json_file(a.selection)
    require(selection.get('schema') == 'corason.selection.v1', 'SELECTION_SCHEMA')
    selected = selection.get('loci')
    query = selection.get('query')
    require(isinstance(selected, list) and 0 < len(selected) <= MAX_LOCI and len(set(selected)) == len(selected), 'SELECTION_COUNT')
    index = {row['exact_locus']: row for row in intake['loci']}
    require(set(selected) <= index.keys(), 'SELECTION_FOREIGN_LOCUS')
    require(isinstance(query, dict) and query.get('exact_locus') in selected and
            isinstance(query.get('locus_tag'), str) and query['locus_tag'], 'QUERY_UNBOUND')
    digest(query.get('translation_sha256'))
    protected = [a.intake, a.selection, a.runtime_manifest]
    for source in intake['sources']:
        protected += [source['archive']['path'], source['package']['package'], source['public_receipt']['path'], source['validation_receipt']['path'], source['validation_evidence']['path']]
    protected += [x['path'] for x in rt['identity']['helpers'].values()]
    protected += [rt['review_receipt']['path'], rt['identity']['interpreter']['path'], rt['identity']['observer_python']['path']]
    protected += [x['file']['path'] for x in rt['identity']['tools'].values()]
    if rt['kind'] == 'NATIVE':
        protected += [rt['identity']['source_root'], rt['identity']['environment_receipt']['path']]
    protected += list(a.read_only_root)
    native_root = Path(a.native_work_root).resolve(strict=True)
    require(native_root.is_dir() and SAFE_SHELL_PATH.fullmatch(str(native_root)), 'NATIVE_WORK_ROOT_UNSAFE')
    for item in protected + [str(Path(__file__).resolve().parents[1])]:
        other = Path(item).resolve()
        require(not contained(native_root, other) and not contained(other, native_root), 'NATIVE_WORK_ROOT_ALIAS')
    out = fresh(a.out, a.write_root, protected + [native_root])
    planned = {'schema': 'corason.plan.v1', 'state': 'PLANNED_AWAITING_APPROVAL', 'created_utc': utc_now(),
               'release': 'PRIVATE', 'profile': PROFILE, 'intake': intake, 'runtime': rt,
               'selection': binding(a.selection), 'selected_loci': [index[x] for x in selected], 'query': query,
               'parameters': DEFAULTS, 'protected': list(map(str, protected)), 'native_work_root': str(native_root),
               'resource_policy': {'rss_limit': 3800000000, 'min_disk': 2000000000, 'timeout': 1800, 'serial_runs': 1,
                                   'cpu_total': rt['identity']['resources']['cpu_total']},
               'scope': 'SYNTHETIC_PROTOCOL_ONLY' if rt['kind'] != 'NATIVE' else 'LOCAL_PUBLIC_INPUT_CORASON_EVIDENCE',
               'holds': ['MODERN_FORMAT_AND_CONVERSION_CHECK_REQUIRED_AT_RUN'],
               'original_source_count': len(intake['sources']), 'original_locus_count': len(intake['loci'])}
    (out / 'PLAN.json').write_text(json.dumps(planned, indent=2) + '\n')
    (out / 'COMMAND.sh').write_text('# Not native runtime admission or authorization. Use explicit reviewed run --plan and fresh --out.\nexit 2\n')
    return planned


def text_file(path):
    p = Path(path)
    require(not p.is_symlink() and p.is_file() and p.stat().st_size <= MAX_FILE, 'OUTPUT_FILE_INVALID')
    return p.read_text(encoding='utf-8')


def fasta(path):
    records = {}
    name = None
    for line in text_file(path).splitlines():
        if line.startswith('>'):
            name = line[1:].strip()
            require(name and name not in records and not any(c.isspace() for c in name), 'FASTA_IDENTITY')
            records[name] = ''
        elif line.strip():
            require(name is not None, 'FASTA_SCHEMA')
            records[name] += line.strip()
    require(records and all(records.values()) and all(re.fullmatch(r'[A-Za-z*-]+', value) for value in records.values()), 'FASTA_EMPTY_OR_ALPHABET')
    return records


def translated_region(row, raw):
    # Exact positions and antiSMASH structured qualifiers require the rich parser.
    try:
        from Bio import SeqIO
    except ImportError as exc:
        raise RuntimeError('CORASON region validation requires optional Biopython; no simplified parser fallback is admitted') from exc
    records = list(SeqIO.parse(io.StringIO(raw.decode('utf-8')), 'genbank'))
    require(len(records) == 1, 'REGION_RECORD_COUNT')
    record = records[0]
    full = record.annotations.get('structured_comment', {}).get('antiSMASH-Data', {})
    from mamey.parsers import _record_contig_id
    require(_record_contig_id(record) == row['full_contig'], 'REGION_FULL_CONTIG')
    require(len(record) == row['end'] - row['start'], 'REGION_SPAN')
    require(str(full.get('Orig. start')) == str(row['start']) and str(full.get('Orig. end')) == str(row['end']), 'REGION_ORIGINAL_BOUNDS')
    regions = [f for f in record.features if f.type == 'region']
    require(len(regions) == 1 and regions[0].qualifiers.get('region_number') == [str(int(row['region'][6:]))] and
            int(regions[0].location.start) == 0 and int(regions[0].location.end) == len(record), 'REGION_DECLARATION')
    genes = []
    tags = set()
    for feature in record.features:
        if feature.type != 'CDS':
            continue
        values = feature.qualifiers.get('translation', [])
        tag = feature.qualifiers.get('locus_tag', [])
        require(len(values) == 1 and len(tag) == 1 and tag[0] and tag[0] not in tags, 'CDS_TRANSLATION_OR_TAG')
        tags.add(tag[0])
        parts = list(feature.location.parts)
        require(len(parts) == 1 and type(parts[0].start).__name__ == 'ExactPosition' and
                type(parts[0].end).__name__ == 'ExactPosition' and feature.location.strand in (-1, 1), 'CDS_LOCATION_UNSUPPORTED')
        start, end = int(feature.location.start), int(feature.location.end)
        require(0 <= start < end <= len(record), 'CDS_BOUNDS')
        translation = re.sub(r'\s+', '', values[0])
        require(re.fullmatch(r'[A-Z]+\*?', translation), 'CDS_TRANSLATION_UNSUPPORTED')
        require('*' not in translation[:-1], 'CDS_INTERNAL_STOP')
        converted = translation.rstrip('*')
        require(converted, 'CDS_EMPTY_TRANSLATION')
        genes.append({'ordinal': len(genes) + 1, 'locus_tag': tag[0], 'start': start, 'end': end,
                      'strand': feature.location.strand, 'source_translation_sha256': hashlib.sha256(translation.encode()).hexdigest(),
                      'translation_sha256': hashlib.sha256(converted.encode()).hexdigest(), 'translation': converted,
                      'transformation': 'REMOVE_ONE_TERMINAL_STOP' if translation.endswith('*') else 'UNCHANGED'})
    require(genes, 'CDS_EMPTY')
    return genes


def stage_inputs(plan, work):
    destination = work / 'CORASON_GENOMES'; destination.mkdir()
    rows = []; query = None; total = 0
    for i, row in enumerate(plan['selected_loci'], 1):
        token = f'L{i:06d}'
        with zipfile.ZipFile(row['archive']['path']) as archive:
            members = [x for x in archive.infolist() if x.filename == row['source_member']]
            require(len(members) == 1 and not members[0].is_dir() and members[0].file_size <= MAX_FILE and
                    (members[0].external_attr >> 16) & 0o170000 != 0o120000, 'ARCHIVE_MEMBER_INVALID')
            total += members[0].file_size
            require(total <= MAX_STAGE, 'STAGING_LIMIT')
            raw = archive.read(members[0])
        genes = translated_region(row, raw)
        staged = {**row, 'token': token, 'source_member_sha256': hashlib.sha256(raw).hexdigest(), 'genes': genes}
        rows.append(staged)
        (destination / (token + '.gbk')).write_bytes(raw)
        if row['exact_locus'] == plan['query']['exact_locus']:
            matches = [g for g in genes if g['locus_tag'] == plan['query']['locus_tag'] and
                       g['source_translation_sha256'] == plan['query']['translation_sha256']]
            require(len(matches) == 1, 'QUERY_TRANSLATION_MISMATCH')
            query = (token, matches[0])
    require(query is not None, 'QUERY_NOT_STAGED')
    (work / 'query.faa').write_text('>QUERY\n' + query[1]['translation'] + '\n')
    # Needed by synthetic fixtures; exact same source-derived metadata drives conversion checks.
    # Omit bases/proteins from persistent portable tables below; this private work stays owned.
    (work / 'STAGED_SOURCE.json').write_text(json.dumps(rows, indent=2) + '\n')
    return rows, query


def check_conversion(work, rows):
    mapping = list(csv.reader(io.StringIO(text_file(work / 'Corason_Rast.IDs')), delimiter='\t'))
    require(len(mapping) == len(rows) and all(len(x) == 3 for x in mapping), 'CONVERSION_MAP_SCHEMA')
    by_token = {x['token']: x for x in rows}; by_org = {}; gene_map = {}
    for org, native_id, filename in mapping:
        filename = filename.strip()
        require(re.fullmatch(r'[1-9][0-9]*', org) and native_id == '666666.' + org and
                filename.endswith('.gbk') and filename[:-4] in by_token and org not in by_org, 'CONVERSION_MAP_IDENTITY')
        row = by_token.pop(filename[:-4]); by_org[org] = row
        amino = fasta(work / 'GENOMES' / (org + '.faa'))
        native = list(csv.reader(io.StringIO(text_file(work / 'GENOMES' / (org + '.txt'))), delimiter='\t'))
        header = ['contig_id','feature_id','type','location','start','stop','strand','function','locus_tag','figfam','species','nucleotide_sequence','amino_acid','sequence_accession']
        require(native and native[0] == header and len(native) - 1 == len(row['genes']), 'CONVERSION_TABLE_SCHEMA')
        require(len(amino) == len(row['genes']), 'CONVERSION_GENE_COUNT')
        for fields, gene in zip(native[1:], row['genes']):
            fid = f'fig|666666.{org}.peg.{gene["ordinal"]}'
            require(len(fields) == 14 and fields[1] == fid and fields[13] == gene['locus_tag'] and
                    fields[0] == row['full_contig'], 'CONVERSION_GENE_IDENTITY')
            expected = (gene['start'] + 1, gene['end']) if gene['strand'] == 1 else (gene['end'], gene['start'] + 1)
            require((fields[4], fields[5], fields[6]) == (str(expected[0]), str(expected[1]), '+' if gene['strand'] == 1 else '-'), 'CONVERSION_GENE_COORDINATES')
            require(fields[12] == amino.get(fid) and hashlib.sha256(fields[12].encode()).hexdigest() == gene['translation_sha256'], 'CONVERSION_TRANSLATION_MISMATCH')
            gene_map[fid] = {'exact_locus': row['exact_locus'], 'org': org, 'token': row['token'],
                             **{k: v for k, v in gene.items() if k != 'translation'}}
        row['org'] = org
    require(not by_token and {p.name for p in (work/'GENOMES').iterdir()} ==
            {org+suffix for org in by_org for suffix in ('.faa','.txt')}, 'CONVERSION_MAP_INCOMPLETE')
    return by_org, gene_map


def prepare_runtime(rt, work, qa):
    helpers = work / 'CORASON'; helpers.mkdir()
    bins = work / 'bin'; bins.mkdir()
    identity = rt['identity']; entries = {}
    for name, row in identity['helpers'].items():
        if name in ('ReadingInputs.pl', '1_Context_text.pl'):
            entries[name] = [identity['interpreter']['path'], row['path']]
        else:
            (helpers / name).symlink_to(row['path'])
    for name, row in identity['tools'].items():
        entries[name] = [row['file']['path']]
    config = {'work': str(work), 'qa': str(qa), 'entries': entries, 'resources': identity['resources']}
    cfg = qa / 'OBSERVER_CONFIG.json'; cfg.write_text(json.dumps(config, indent=2) + '\n')
    payload = qa/'OBSERVER.py'; payload.write_text(observer_source())
    generated = {'OBSERVER_PAYLOAD': binding(payload)}
    for name in entries:
        p = (helpers if name.endswith('.pl') else bins) / name
        code = '#!/bin/sh\nexec ' + ' '.join(shlex.quote(x) for x in
            (identity['observer_python']['path'], str(payload), name)) + ' "$@"\n'
        p.write_text(code); p.chmod(0o755); generated[name] = binding(p)
    env = dict(identity['environment'])
    env.update(PATH=str(bins) + os.pathsep + env.get('PATH', ''), LC_ALL='C', LANG='C',
               CORASON_OBSERVER_CONFIG=str(cfg))
    return env, {'config': binding(cfg), 'generated': generated}


def direct_child(command, *, cwd, log, env, timeout=None, stderr=None):
    """Same-process-group child; only the outer worker owns resource monitoring."""
    started = utc_now(); clock = time.monotonic()
    code = None; stop = None
    with Path(log).open('xb') as out:
        if stderr is None:
            process = subprocess.Popen(command, cwd=cwd, env=env, stdout=out, stderr=subprocess.STDOUT)
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                stop = 'PROBE_TIME_LIMIT'; process.kill(); process.wait()
                # Abort the worker. The outer watcher cleans every observed owned
                # descendant, including grandchildren left by a timed-out probe.
        else:
            with Path(stderr).open('xb') as err:
                process = subprocess.Popen(command, cwd=cwd, env=env, stdout=out, stderr=err)
                try:
                    code = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    stop = 'PROBE_TIME_LIMIT'; process.kill(); process.wait()
    return {'argv': list(command), 'cwd': str(Path(cwd).resolve()), 'exit_code': code,
            'stop_reason': stop, 'cleanup_error': None, 'started_utc': started, 'completed_utc': utc_now(),
            'elapsed_seconds': time.monotonic()-clock, 'log': str(Path(log).resolve()),
            'log_sha256': sha256_file(log), 'monitor': 'OUTER_WORKER_PROCESS_TREE',
            **({'stderr': binding(stderr)} if stderr is not None else {})}


def probe_runtime(rt, work, qa, env):
    rows = []
    # Direct file-captured probes inherit the single outer worker session.
    probes = [('entry_help', [rt['identity']['interpreter']['path'], 'CORASON/corason.pl', '--help'])]
    probes += [(name, [row['file']['path'], *row['probe']]) for name, row in rt['identity']['tools'].items()]
    for name, argv in probes:
        stdout = qa / (name + '.stdout'); stderr = qa / (name + '.stderr')
        receipt = direct_child(argv, cwd=work, log=stdout, stderr=stderr, env=env, timeout=10)
        require(receipt.get('exit_code') == 0 and not receipt.get('stop_reason'), 'RUNTIME_PROBE_FAILED')
        require(stdout.stat().st_size + stderr.stat().st_size <= MAX_FILE, 'RUNTIME_PROBE_OUTPUT_LIMIT')
        out = stdout.read_bytes(); err = stderr.read_bytes()
        if name != 'entry_help' and rt['kind'] == 'NATIVE':
            tool = rt['identity']['tools'][name]
            require(hashlib.sha256(out).hexdigest() == tool['probe_stdout_sha256'] and
                    hashlib.sha256(err).hexdigest() == tool['probe_stderr_sha256'], 'TOOL_PROBE_PROFILE_MISMATCH')
        rows.append({'name': name, 'argv': argv, 'returncode': 0, 'child_receipt': receipt,
                     'stdout_sha256': hashlib.sha256(out).hexdigest(), 'stderr_sha256': hashlib.sha256(err).hexdigest()})
        if name == 'entry_help':
            help_text = (out + err).decode('utf-8', 'replace')
            require('queryfile' in help_text and 'special_org' in help_text and 'rast_ids' in help_text, 'ENTRY_HELP_INCOMPATIBLE')
            if rt['kind'] == 'NATIVE':
                require(hashlib.sha256(out).hexdigest() == rt['identity']['entry_help_stdout_sha256'], 'ENTRY_HELP_PROFILE_MISMATCH')
    (qa / 'PROBES.json').write_text(json.dumps(rows, indent=2) + '\n')
    return rows


def native_argv(rt, orgs, reference):
    argv = [rt['identity']['interpreter']['path'], 'CORASON/corason.pl', '--conda', '--rast_ids',
            'Corason_Rast.IDs', '--queryfile', 'query.faa', '--special_org', reference, '--list', ','.join(orgs)]
    for flag, value in DEFAULTS.items():
        argv += ['--' + flag, value]
    return argv


def witness_closure(qa, kind):
    witnesses = [json_file(p) for p in sorted(qa.glob('witness_*.json'))]
    require(witnesses and any(x['name'] == 'ReadingInputs.pl' for x in witnesses), 'PREFILTER_WITNESS_MISSING')
    require(all(x.get('status') == 'TERMINAL' and x.get('returncode') == 0 for x in witnesses), 'NATIVE_CHILD_FAILURE')
    if kind == 'NATIVE':
        require(any(x['name'] == '1_Context_text.pl' for x in witnesses) and
                any(x['name'] == 'blastp' for x in witnesses), 'NATIVE_SEARCH_WITNESS_MISSING')
    return witnesses


def captured_neighborhoods(qa, orgs, gene_map):
    capture = json_file(qa / 'PREFILTER.json')
    require(capture.get('schema') == 'corason.prefilter.v1', 'PREFILTER_SCHEMA')
    files = capture.get('files', {})
    rows = {}; hit_orgs = set()
    for name, meta in files.items():
        path = Path(meta['capture']).resolve(strict=True)
        require(path.parent == qa.resolve() and not path.is_symlink() and
                binding(path)['sha256'] == meta['sha256'] and binding(path)['bytes'] == meta['bytes'], 'PREFILTER_BINDING')
        if not name.endswith('.input'):
            continue
        token = name[:-6]
        match = re.fullmatch(r'([1-9][0-9]*)_([1-9][0-9]*)', token)
        require(match and match[1] in orgs and token not in rows, 'NEIGHBORHOOD_IDENTITY')
        org, peg = match.groups(); fid = f'fig|666666.{org}.peg.{peg}'
        require(fid in gene_map and gene_map[fid]['org'] == org, 'NEIGHBORHOOD_ANCHOR')
        cells = list(csv.reader(io.StringIO(text_file(path)), delimiter='\t'))
        require(cells and all(len(x) == 9 for x in cells) and cells[0][6] == fid, 'NEIGHBORHOOD_SCHEMA')
        require(all(x[6] in gene_map and gene_map[x[6]]['org'] == org for x in cells), 'NEIGHBORHOOD_FOREIGN_GENE')
        pair = files.get(token + '.input2')
        require(pair, 'NEIGHBORHOOD_QUERY_ALIGNMENT_MISSING')
        amino = fasta(pair['capture'])
        require(len(amino) == 1 and set(amino) == {f'peg_{peg}_org{org}'}, 'NEIGHBORHOOD_QUERY_ALIGNMENT_SCHEMA')
        require(hashlib.sha256(next(iter(amino.values())).encode()).hexdigest() == gene_map[fid]['translation_sha256'], 'NEIGHBORHOOD_QUERY_TRANSLATION')
        rows[token] = {'neighborhood': token, 'org': org, 'peg': peg, 'anchor_fig_id': fid,
                       'token': orgs[org]['token'], 'exact_locus': orgs[org]['exact_locus'],
                       'input2_header': next(iter(amino)), 'context_gene_ids': [x[6] for x in cells]}
        hit_orgs.add(org)
    require(len(rows) <= MAX_NEIGHBORHOODS, 'NEIGHBORHOOD_LIMIT')
    # Affirmative tabular query search closes zero-hit input denominators. A file
    # absent from capture is unknown, not a negative search result.
    blast = [m for n, m in files.items() if n.endswith('.BLAST.pre')]
    require(len(blast) == 1, 'SEARCH_DENOMINATOR_EVIDENCE_MISSING')
    observed_hit_orgs = set()
    for line in text_file(blast[0]['capture']).splitlines():
        fields = line.split('\t')
        require(len(fields) == 12, 'SEARCH_DENOMINATOR_SCHEMA')
        match = re.fullmatch(r'(fig\|666666\.([1-9][0-9]*)\.peg\.[1-9][0-9]*)\|([1-9][0-9]*)', fields[1])
        require(match and match[1] in gene_map and match[2] == match[3] and gene_map[match[1]]['org'] == match[3], 'SEARCH_DENOMINATOR_IDENTITY')
        observed_hit_orgs.add(match[3])
    require(hit_orgs <= observed_hit_orgs, 'SEARCH_NEIGHBORHOOD_CONTRADICTION')
    return rows, observed_hit_orgs


def tree_leaves(path):
    from tree_sanity_check import parse
    try:
        leaves = [n.name for n in parse(str(path)).leaves()]
    except (ValueError, OSError) as exc:
        raise AdapterError('TREE_INVALID') from exc
    require(leaves and len(leaves) == len(set(leaves)), 'TREE_DUPLICATE_OR_EMPTY')
    return leaves


def verify_alignment(path, expected):
    rows = fasta(path)
    require(set(rows) == set(expected) and len({len(v) for v in rows.values()}) == 1, 'ALIGNMENT_IDENTITY_OR_WIDTH')
    return rows


def unique_partition_order(blocks, observed):
    """Verify native concatenation without assuming its readdir order is numeric.

    Preserve a unique observed partition order; ambiguous or expensive matching
    holds instead of inventing one. No alignment/sequence generation occurs.
    """
    require(blocks and len(blocks) <= 120 and set(next(iter(blocks.values()))) == set(observed), 'PARTITION_SCHEMA')
    solutions = []; steps = [0]
    def walk(left, offset, order):
        steps[0] += 1
        require(steps[0] <= 10000, 'PARTITION_MATCH_LIMIT')
        if len(solutions) > 1:
            return
        if not left:
            if all(offset == len(value) for value in observed.values()):
                solutions.append(order)
            return
        for key in left:
            block = blocks[key]
            size = len(next(iter(block.values())))
            if all(observed[tip][offset:offset+size] == value for tip, value in block.items()):
                walk([x for x in left if x != key], offset+size, order+[key])
    walk(list(blocks), 0, [])
    require(len(solutions) == 1, 'CONCATENATION_CONTENT_OR_ORDER_AMBIGUOUS')
    return solutions[0]


def readback(work, qa, orgs, gene_map, kind):
    witness_closure(qa, kind)
    pre, hits = captured_neighborhoods(qa, orgs, gene_map)
    root = work / 'query.faa-output'
    require(root.is_dir(), 'NATIVE_OUTPUT_MISSING')
    # Surviving native input files are the actual filter decision, checked against
    # preserved pre-filter snapshots. Every rejected neighborhood stays explicit.
    admitted = {p.stem for p in root.glob('*.input')}
    require(admitted <= pre.keys() and admitted, 'NATIVE_NEIGHBORHOODS_UNRESOLVED')
    require({p.stem for p in root.glob('*.input2')} == admitted, 'NATIVE_FILTER_INCONSISTENT')
    report = text_file(root / 'query.faa_Report')
    core_path = root / 'Core'
    core_rows = [line.split() for line in text_file(core_path).splitlines() if line.strip()]
    raw_core = []
    for line in core_rows:
        require(len(line) == len(admitted), 'CORE_DENOMINATOR')
        projected = []
        for cell in line:
            match = re.fullmatch(r'(fig\|666666\.([1-9][0-9]*)\.peg\.[1-9][0-9]*)\|([1-9][0-9]*_[1-9][0-9]*)', cell)
            require(match and match[1] in gene_map and match[3] in admitted and
                    pre[match[3]]['org'] == match[2] and match[1] in pre[match[3]]['context_gene_ids'], 'CORE_GENE_FOREIGN')
            projected.append(match[3])
        require(set(projected) == admitted and len(projected) == len(set(projected)), 'CORE_IDENTITY_CLOSURE')
        raw_core.append(line)
    require(len({tuple(x) for x in raw_core}) == len(raw_core), 'CORE_DUPLICATE')
    # Source's renamed tree labels contain safe locus name, anchor peg, and org.
    tips = {f'{pre[n]["token"]}_gbk_peg_{pre[n]["peg"]}_org_{pre[n]["org"]}': n for n in admitted}
    require(len(tips) == len(admitted), 'TIP_COLLISION')
    partition_order = []
    if len(core_rows) > 1:
        match = re.search(r'core composed by ([0-9]+) orhtolog', report)
        require(match and int(match[1]) == len(core_rows), 'REPORT_CORE_CONTRADICTION')
        route = 'MULTILOCUS_CORE'; goal = 'MET_STRUCTURAL_ONLY'
        alignment = root / 'RightNames.txt'; tree = root / 'query.faa_BGC.tre'; order = root / 'query.faa_BGC_TREE.order'
        lengths = []; blocks = {}
        # Existing native ChangeName/EliminadorLineas writes numeric per-core
        # FASTAs consumed by Concatenador. Exact selected files, not glob count.
        for i in range(1, len(core_rows) + 1):
            raw_inputs = fasta(root / 'CORASON' / 'FASTAINTER' / (str(i) + '.interFastatodos'))
            require(set(raw_inputs) == set(core_rows[i-1]), 'CORE_SOURCE_INPUT_IDENTITY')
            for raw_id, amino in raw_inputs.items():
                fid = raw_id.rsplit('|', 1)[0]
                require(hashlib.sha256(amino.encode()).hexdigest() == gene_map[fid]['translation_sha256'], 'CORE_SOURCE_TRANSLATION')
            rows = fasta(root / 'CORASON' / 'CONCATENADOS' / str(i))
            # Native input uses org<org>_<anchor-peg>; retain exact crosswalk.
            native_names = {f'org{pre[n]["org"]}_{pre[n]["peg"]}': n for n in admitted}
            require(set(rows) == set(native_names) and len({len(x) for x in rows.values()}) == 1, 'CORE_ALIGNMENT_CLOSURE')
            lengths.append(len(next(iter(rows.values()))))
            blocks[str(i)] = {tip: rows[f'org{pre[n]["org"]}_{pre[n]["peg"]}'] for tip, n in tips.items()}
        observed = verify_alignment(alignment, tips)
        partition_order = unique_partition_order(blocks, observed)
        lengths = [len(next(iter(blocks[key].values()))) for key in partition_order]
    elif (root / 'PrincipalHits.order').is_file() and (root / 'PrincipalHits.order').stat().st_size:
        require('single hits order' in report, 'REPORT_ROUTE_CONTRADICTION')
        route = 'QUERY_ONLY_SHAVED'; goal = 'NOT_MET'
        alignment = root / 'RightNamesPrincipalHits.txt'; tree = root / 'query.faa_PrincipalHits.tre'; order = root / 'PrincipalHits.order'
        lengths = [len(next(iter(verify_alignment(alignment, tips).values())))]
    elif (root / 'PrincipalHitsUnshaved.order').is_file() and (root / 'PrincipalHitsUnshaved.order').stat().st_size:
        require('single hits order' in report, 'REPORT_ROUTE_CONTRADICTION')
        route = 'QUERY_ONLY_UNSHAVED'; goal = 'NOT_MET'
        alignment = root / 'RightNamesPrincipalHits_Unshaved.txt'; tree = root / 'query.faa_Unshaved.tre'; order = root / 'PrincipalHitsUnshaved.order'
        lengths = [len(next(iter(verify_alignment(alignment, tips).values())))]
    else:
        require('single hits blast order' in report, 'ROUTE_UNRESOLVED')
        route = 'BLAST_ORDER'; goal = 'NOT_MET'; tree = None; alignment = None; order = None; lengths = []
    if tree:
        require(len(admitted) >= 2, 'COMPARATIVE_TREE_INSUFFICIENT_NEIGHBORHOODS')
        leaves = tree_leaves(tree)
        ordered = [x.strip() for x in text_file(order).splitlines() if x.strip()]
        require(set(leaves) == tips.keys() and set(ordered) == tips.keys() and len(ordered) == len(tips), 'TREE_ORDER_IDENTITY_CLOSURE')
    svg = text_file(root / 'query.faa.svg')
    require('<svg' in svg and '</svg>' in svg, 'SVG_INVALID')
    states = []
    for org, row in orgs.items():
        state = 'HAS_ADMITTED_NEIGHBORHOOD' if any(pre[n]['org'] == org for n in admitted) else (
            'NATIVE_FILTERED_ALL' if any(x['org'] == org for x in pre.values()) else (
                'HIT_WITHOUT_CAPTURED_NEIGHBORHOOD' if org in hits else 'NO_QUERY_HIT_IN_BOUND_SEARCH'))
        states.append({'exact_locus': row['exact_locus'], 'state': state})
    neighbors = [{**row, 'state': 'ADMITTED' if key in admitted else 'NATIVE_FILTERED'} for key, row in sorted(pre.items())]
    return {'route': route, 'multilocus_goal': goal, 'release': 'PRIVATE',
            'scope': 'SYNTHETIC_PROTOCOL_ONLY' if kind != 'NATIVE' else 'COMPUTATIONAL_LOCUS_COMPARISON_NOT_BIOLOGICAL_VALIDATION',
            'tree_status': 'STRUCTURE_CHECKED' if tree else 'NOT_ASSESSED', 'figure_status': 'RAW_NATIVE_SVG_NOT_VISUALLY_ADMITTED', 'core_genes': len(core_rows),
            'core_alignment_lengths': lengths, 'core_partition_order': partition_order, 'neighborhoods': neighbors, 'loci': states,
            'leaf_crosswalk': [{'raw_tip': tip, **pre[n]} for tip, n in sorted(tips.items())] if tree else [],
            'denominators': {'staged_loci': len(orgs), 'converted_genes': len(gene_map),
                'query_hit_loci': len(hits), 'prefilter_neighborhoods': len(pre), 'admitted_neighborhoods': len(admitted),
                'filtered_neighborhoods': len(pre) - len(admitted), 'tree_tips': len(tips) if tree else 0}}


def _run_worker(a):
    plan = json_file(a.plan)
    require(plan.get('schema') == 'corason.plan.v1' and plan.get('parameters') == DEFAULTS and
            plan.get('release') == 'PRIVATE', 'PLAN_CONTRACT')
    require(a.approved is True, 'APPROVAL_REQUIRED')
    check_unchanged(plan)
    protected = plan['protected'] + [a.plan, *a.read_only_root]
    out = Path(a.out).resolve(strict=True)
    state = {'schema': 'corason.attempt.v1', 'attempt_id': uuid.uuid4().hex, 'status': 'RUNNING',
             'plan': binding(a.plan), 'release': 'PRIVATE', 'created_utc': utc_now(), 'phases': []}
    atomic_json(out / 'RUN_STATE.json', state)
    (out / 'EVENTS.jsonl').write_text(json.dumps({'state': 'RUNNING', 'time': utc_now()}) + '\n')
    try:
        work = fresh(Path(plan['native_work_root']) / ('WORK_' + state['attempt_id']),
                     plan['native_work_root'], protected + [out])
        state['work_path'] = str(work)
        atomic_json(out / 'RUN_STATE.json', state)
        qa = out / 'qa'; qa.mkdir(); logs = out / 'logs'; logs.mkdir()
        require(SAFE_SHELL_PATH.fullmatch(str(work)), 'NATIVE_SHELL_PATH_UNSAFE')
        rows, query = stage_inputs(plan, work)
        env, generated = prepare_runtime(plan['runtime'], work, qa)
        (out / 'PRELAUNCH_MANIFEST.json').write_text(json.dumps({'schema': 'corason.prelaunch.v1',
            'plan': state['plan'], 'runtime': plan['runtime'], 'generated_observers': generated,
            'environment': env, 'work_path': str(work), 'resource_policy': plan['resource_policy'], 'release': 'PRIVATE'}, indent=2) + '\n')
        probes = probe_runtime(plan['runtime'], work, qa, env)
        converter = [plan['runtime']['identity']['interpreter']['path'], 'CORASON/gbkIndex.pl', 'CORASON_GENOMES', 'CORASON']
        commands = [converter]
        for phase in ('convert', 'analyse'):
            if phase == 'analyse':
                orgs, genes = check_conversion(work, rows)
                references = [org for org, row in orgs.items() if row['token'] == query[0]]
                require(len(references) == 1, 'REFERENCE_ORG_UNRESOLVED')
                commands.append(native_argv(plan['runtime'], sorted(orgs, key=int), references[0]))
            receipt = direct_child(commands[-1], cwd=work, log=logs / (phase + '.log'), env=env)
            state['phases'].append({'phase': phase, **receipt})
            atomic_json(out / 'RUN_STATE.json', state)
            require(receipt.get('exit_code') == 0 and not receipt.get('stop_reason') and not receipt.get('cleanup_error'), 'NATIVE_PHASE_FAILED')
        for row in generated['generated'].values():
            bound_file(row)
        bound_file(generated['config'])
        result = readback(work, qa, orgs, genes, plan['runtime']['kind'])
        result['denominators'].update(original_sources=plan['original_source_count'], original_loci=plan['original_locus_count'],
                                      selected_loci=len(plan['selected_loci']), unselected_loci=plan['original_locus_count']-len(plan['selected_loci']))
        check_unchanged(plan)
        # Method/helper bindings include generated observer and exact actual probes.
        manifest = {'schema': 'corason.run-manifest.v1', 'method': binding(__file__), 'plan': state['plan'], 'runtime': plan['runtime'],
                    'generated_observers': generated, 'probe_results': probes, 'commands': commands,
                    'environment': env, 'work_path': str(work), 'resource_policy': plan['resource_policy'], 'release': 'PRIVATE',
                    'source_rows': [{**row, 'genes': [{k: v for k, v in g.items() if k != 'translation'} for g in row['genes']]} for row in rows],
                    'gene_map': genes, 'orgs': {org: {k: v for k, v in row.items() if k != 'genes'} for org, row in orgs.items()}}
        (out / 'RUN_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
        result['producer'] = binding(out / 'RUN_MANIFEST.json')
        # Bind owned artifacts only; source/helper symlink view is separately bound.
        result['selected_artifacts'] = artifact_closure(work, qa)
        (out / 'SELECTED_RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
        state.update(status='COMPLETE_SCOPED_EVIDENCE', result=binding(out / 'SELECTED_RESULT.json'),
                     manifest=binding(out / 'RUN_MANIFEST.json'), route=result['route'], multilocus_goal=result['multilocus_goal'])
    except Exception as exc:
        state.update(status='FAILED', error=getattr(exc, 'code', type(exc).__name__))
        raise
    finally:
        try:
            check_unchanged(plan)
            state['input_runtime_immutable'] = True
        except Exception as changed:
            state['input_runtime_immutable'] = False
            state['status'] = 'FAILED'
            state['binding_error'] = getattr(changed, 'code', type(changed).__name__)
        state['ended_utc'] = utc_now()
        atomic_json(out / 'RUN_STATE.json', state)
        with (out / 'EVENTS.jsonl').open('a') as stream:
            stream.write(json.dumps({'state': state['status'], 'time': state['ended_utc']}) + '\n')
    require(state['status'] == 'COMPLETE_SCOPED_EVIDENCE', 'FINAL_BINDING_FAILED')
    return state


def artifact_closure(work, qa):
    return {'native': regular_tree(work / 'query.faa-output'), 'qa': regular_tree(qa),
            'converted': regular_tree(work / 'GENOMES'), 'staged_regions': regular_tree(work / 'CORASON_GENOMES'),
            'input_files': {name: binding(work / name) for name in ('query.faa', 'Corason_Rast.IDs', 'STAGED_SOURCE.json')}}


def _read_worker(a):
    state = json_file(a.run_receipt)
    require(state.get('schema') == 'corason.attempt.v1' and state.get('status') == 'COMPLETE_SCOPED_EVIDENCE', 'ATTEMPT_NOT_COMPLETE')
    admit_whole_worker(Path(a.run_receipt).resolve().parent, 'run', binding(a.run_receipt))
    bound_file(state['result']); bound_file(state['manifest']); bound_file(state['plan'])
    manifest = json_file(state['manifest']['path']); plan = json_file(state['plan']['path'])
    require(manifest.get('plan') == state['plan'], 'PRODUCER_PLAN_MISMATCH')
    check_unchanged(plan)
    selected = json_file(state['result']['path'])
    require(selected.get('producer') == state['manifest'], 'PRODUCER_RESULT_MISMATCH')
    out_root = Path(a.run_receipt).resolve().parent
    work = Path(state['work_path']).resolve(strict=True); qa = out_root / 'qa'
    require(work == Path(plan['native_work_root']).resolve() / ('WORK_' + state['attempt_id']) and
            manifest.get('work_path') == str(work), 'WORK_PRODUCER_MISMATCH')
    for row in manifest['generated_observers']['generated'].values():
        bound_file(row)
    bound_file(manifest['generated_observers']['config'])
    require(len(state.get('phases', [])) == 2, 'PHASE_DENOMINATOR')
    for phase, command in zip(state['phases'], manifest['commands']):
        argv = phase.get('argv', [])
        require(phase.get('exit_code') == 0 and not phase.get('stop_reason') and not phase.get('cleanup_error') and
                phase.get('cwd') == str(work) and (argv == command or
                    (argv and Path(argv[0]).name == 'nice' and argv[1:] == ['-n', '15', *command])), 'PHASE_PRODUCER_MISMATCH')
        require(binding(phase['log'])['sha256'] == phase['log_sha256'], 'PHASE_LOG_CHANGED')
    bound_file(manifest['method'])
    require(selected.get('selected_artifacts') == artifact_closure(work, qa), 'SELECTED_OUTPUT_CHANGED')
    observed_orgs, observed_genes = check_conversion(work, manifest['source_rows'])
    require(observed_genes == manifest['gene_map'] and
            {org: {k: v for k, v in row.items() if k != 'genes'} for org, row in observed_orgs.items()} == manifest['orgs'], 'READ_CONVERSION_CHANGED')
    actual = readback(work, qa, manifest['orgs'], manifest['gene_map'], plan['runtime']['kind'])
    for key in actual:
        if key == 'denominators':
            require(all(selected[key].get(k) == v for k, v in actual[key].items()), 'READBACK_CHANGED')
        else:
            require(selected.get(key) == actual[key], 'READBACK_CHANGED')
    out = Path(a.out).resolve(strict=True)
    export = {**selected, 'run_receipt': binding(a.run_receipt)}
    (out / 'EVIDENCE.json').write_text(json.dumps(export, indent=2) + '\n')
    for name, rows in [('loci', selected['loci']), ('neighborhoods', selected['neighborhoods']), ('leaf_crosswalk', selected['leaf_crosswalk'])]:
        fields = list(dict.fromkeys(k for row in rows for k in row))
        with (out / (name + '.tsv')).open('w', newline='') as stream:
            writer = SafeDictWriter(stream, fieldnames=fields or ['state'], delimiter='\t')
            writer.writeheader()
            for row in rows:
                writer.writerow({k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in row.items()})
    (out / 'HANDOFF.md').write_text('CORASON scoped evidence; release PRIVATE.\n\nRoute: ' + selected['route'] +
        '\nMultilocus goal: ' + selected['multilocus_goal'] + '\nScope: ' + selected['scope'] +
        '\nRead EVIDENCE.json and full-identity TSVs. Raw native SVG is not visually admitted.\nNo compound/activity/species/physical-adjacency conclusion.\n\n' +
        '\n'.join(row['exact_locus'] for row in selected['loci']) + '\n')
    (out / 'EXPORT_BINDINGS.json').write_text(json.dumps(regular_tree(out), indent=2) + '\n')
    return export


def controller(a, mode, plan):
    # The controller reads only bounded coordination metadata. All heavy intake,
    # conversion, probes, native children and independent readback run in one
    # fresh Python worker session owned by the existing process-tree watcher.
    require(runtime(plan['runtime']['manifest']['path']) == plan['runtime'], 'RUNTIME_CHANGED')
    require(plan['resource_policy'] == {'rss_limit': 3800000000, 'min_disk': 2000000000, 'timeout': 1800,
        'serial_runs': 1, 'cpu_total': plan['runtime']['identity']['resources']['cpu_total']}, 'PLAN_RESOURCE_DERIVATION')
    env = dict(plan['runtime']['identity']['environment'])
    require(all(env.get(k) == '1' for k in THREAD_ENV_KEYS) and env.get('PYTHONDONTWRITEBYTECODE') == '1', 'THREAD_ENVIRONMENT_HOLD')
    bound_file(plan['intake']['intake'])
    intake_metadata = json_file(plan['intake']['intake']['path'])
    protected = [*plan['protected'], *a.read_only_root, plan['intake']['intake']['path'], plan['selection']['path'],
                 plan['runtime']['manifest']['path'], plan['runtime']['review_receipt']['path']]
    for record in intake_metadata['records']:
        protected += [record['package'], record['source_zip'], record['public_receipt']['path'],
                      record['validation_receipt']['path']]
        validation = json_file(record['validation_receipt']['path'])
        protected.append(validation['evidence_path'])
    protected += [row['path'] for row in plan['runtime']['identity']['helpers'].values()]
    protected += [row['file']['path'] for row in plan['runtime']['identity']['tools'].values()]
    protected += [plan['runtime']['identity'][key]['path'] for key in ('interpreter','observer_python')]
    if plan['runtime']['kind'] == 'NATIVE':
        protected += [plan['runtime']['identity']['source_root'], plan['runtime']['identity']['environment_receipt']['path']]
    protected += [a.plan] if mode == 'run' else [Path(a.run_receipt).resolve().parent]
    out = fresh(a.out, a.write_root, protected + [plan['native_work_root']])
    args = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(a).items() if k != 'handler'}
    args['out'] = str(out)
    request = {'schema': 'corason.worker-request.v1', 'mode': mode, 'method': binding(__file__),
               'arguments': args, 'plan': binding(a.plan) if mode == 'run' else binding(json_file(a.run_receipt)['plan']['path'])}
    request_path = out / 'WORKER_REQUEST.json'; atomic_json(request_path, request)
    request_sha = sha256_file(request_path)
    env['CORASON_WORKER_REQUEST_SHA256'] = request_sha
    command = [plan['runtime']['identity']['observer_python']['path'], str(Path(__file__).resolve()),
               '--_worker', str(request_path), request_sha]
    atomic_json(out/'WORKER_STATE.json', {'status': 'RUNNING', 'release': 'PRIVATE', 'mode': mode})
    try:
        receipt = run_watched(command, cwd=out, log=out/'WHOLE_WORKER.log', env=env,
            rss_limit=plan['resource_policy']['rss_limit'], min_disk=plan['resource_policy']['min_disk'],
            timeout=plan['resource_policy']['timeout'],
            additional_disk_floors=((Path(plan['native_work_root']), plan['resource_policy']['min_disk']),))
        atomic_json(out/'WHOLE_WORKER_RECEIPT.json', receipt)
        if receipt['exit_code'] != 0 or receipt.get('stop_reason') or receipt.get('cleanup_error'):
            terminal_state = out/'RUN_STATE.json'
            error_file = terminal_state if terminal_state.exists() else out/'WORKER_ERROR.json'
            error = json_file(error_file).get('error', 'WHOLE_WORKER_FAILED') if error_file.exists() else 'WHOLE_WORKER_FAILED'
            raise AdapterError(error)
        terminal = out/('RUN_STATE.json' if mode == 'run' else 'EVIDENCE.json')
        terminal_binding = binding(terminal)
        bound_file(request['method']); bound_file(request['plan'])
        # Acyclic: terminal artifacts -> outer receipt -> independently admitted descriptor.
        descriptor = {'schema': 'corason.worker-admission.v1', 'status': 'ADMITTED', 'mode': mode,
            'request': binding(request_path), 'method': request['method'], 'worker': binding(out/'WHOLE_WORKER_RECEIPT.json'),
            'terminal': terminal_binding, 'command': command, 'environment': env, 'release': 'PRIVATE',
            'resource_policy': plan['resource_policy'], 'native_work_root': plan['native_work_root']}
        atomic_json(out/'WHOLE_WORKER_ADMISSION.json', descriptor)
        atomic_json(out/'WORKER_STATE.json', {'status': 'COMPLETE', 'mode': mode, 'release': 'PRIVATE'})
        if mode == 'read':
            # The log finished after the worker's initial export inventory.
            inventory = regular_tree(out); inventory.pop('EXPORT_BINDINGS.json', None)
            atomic_json(out/'EXPORT_BINDINGS.json', inventory)
        return json_file(terminal)
    except Exception as exc:
        atomic_json(out/'WORKER_STATE.json', {'status': 'FAILED', 'mode': mode, 'release': 'PRIVATE',
                                            'error': getattr(exc, 'code', type(exc).__name__)})
        if mode == 'run':
            terminal = out/'RUN_STATE.json'
            state = json_file(terminal) if terminal.exists() else {'schema': 'corason.attempt.v1', 'phases': [], 'release': 'PRIVATE'}
            state.setdefault('error', getattr(exc, 'code', type(exc).__name__))
            state.update(status='FAILED', outer_worker_error=getattr(exc, 'code', type(exc).__name__))
            atomic_json(terminal, state)
        raise


def admit_whole_worker(root, mode, terminal):
    descriptor = json_file(root/'WHOLE_WORKER_ADMISSION.json')
    require(descriptor.get('schema') == 'corason.worker-admission.v1' and descriptor.get('status') == 'ADMITTED' and
            descriptor.get('mode') == mode and descriptor.get('terminal') == terminal and descriptor.get('release') == 'PRIVATE', 'WHOLE_WORKER_NOT_ADMITTED')
    bound_file(descriptor['terminal']); bound_file(descriptor['worker']); bound_file(descriptor['request']); bound_file(descriptor['method'])
    request = json_file(descriptor['request']['path']); receipt = json_file(descriptor['worker']['path'])
    env = descriptor['environment']; policy = descriptor['resource_policy']
    require(request['method'] == descriptor['method'] == binding(__file__) and request['mode'] == mode and
            env.get('CORASON_WORKER_REQUEST_SHA256') == descriptor['request']['sha256'] and
            all(env.get(k) == '1' for k in THREAD_ENV_KEYS) and env.get('PYTHONDONTWRITEBYTECODE') == '1', 'WHOLE_WORKER_CONTEXT_CHANGED')
    argv = receipt.get('argv', [])
    command = descriptor['command']
    require((argv == command or (argv and Path(argv[0]).name == 'nice' and argv[1:] == ['-n','15',*command])) and
            receipt.get('cwd') == str(root) and receipt.get('exit_code') == 0 and not receipt.get('stop_reason') and
            not receipt.get('cleanup_error') and receipt.get('rss_stop_bytes') == policy['rss_limit'] and
            receipt.get('timeout_seconds') == policy['timeout'] and receipt.get('minimum_free_disk_bytes') == policy['min_disk'], 'WHOLE_WORKER_RECEIPT_CHANGED')
    require({(x['path'], x['min_free_bytes']) for x in receipt['disk_floors']} ==
            {(str(root), policy['min_disk']), (descriptor['native_work_root'], policy['min_disk'])}, 'WHOLE_WORKER_DISK_FLOORS')
    require(binding(receipt['log'])['sha256'] == receipt['log_sha256'], 'WHOLE_WORKER_LOG_CHANGED')
    return descriptor


def run_command(a):
    require(a.approved is True, 'APPROVAL_REQUIRED')
    plan = json_file(a.plan)
    require(plan.get('schema') == 'corason.plan.v1' and plan.get('parameters') == DEFAULTS and plan.get('release') == 'PRIVATE', 'PLAN_CONTRACT')
    return controller(a, 'run', plan)


def read_command(a):
    state = json_file(a.run_receipt)
    require(state.get('status') == 'COMPLETE_SCOPED_EVIDENCE', 'ATTEMPT_NOT_COMPLETE')
    admit_whole_worker(Path(a.run_receipt).resolve().parent, 'run', binding(a.run_receipt))
    return controller(a, 'read', json_file(state['plan']['path']))


def private_worker(path, expected):
    # argv supplies a string; the shared streaming hasher takes a pathlib.Path.
    path = Path(path)
    require(os.environ.get('CORASON_WORKER_REQUEST_SHA256') == expected and sha256_file(path) == digest(expected), 'WORKER_REQUEST_CHANNEL')
    request = json_file(path)
    require(request.get('schema') == 'corason.worker-request.v1' and request.get('method') == binding(__file__), 'WORKER_METHOD_CHANGED')
    bound_file(request['plan'])
    a = SimpleNamespace(**request['arguments'])
    out = Path(a.out).resolve(strict=True)
    require(out == Path.cwd().resolve() and Path(path).resolve() == out/'WORKER_REQUEST.json', 'WORKER_OUTPUT_CHANNEL')
    require(all(os.environ.get(k) == '1' for k in THREAD_ENV_KEYS) and os.environ.get('PYTHONDONTWRITEBYTECODE') == '1', 'THREAD_ENVIRONMENT_HOLD')
    try:
        if request['mode'] == 'run':
            _run_worker(a)
        elif request['mode'] == 'read':
            _read_worker(a)
        else:
            raise AdapterError('WORKER_MODE')
    except Exception as exc:
        atomic_json(out/'WORKER_ERROR.json', {'error': getattr(exc, 'code', type(exc).__name__)})
        raise
    return 0


def parser():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='mode', required=True)
    for mode in ('plan', 'run', 'read'):
        p = sub.add_parser(mode)
        p.add_argument('--out', required=True); p.add_argument('--write-root', required=True)
        p.add_argument('--read-only-root', action='append', default=[])
        p.set_defaults(handler={'plan': plan_command, 'run': run_command, 'read': read_command}[mode])
        if mode == 'plan':
            p.add_argument('--intake', required=True); p.add_argument('--selection', required=True); p.add_argument('--runtime-manifest', required=True)
            p.add_argument('--native-work-root', required=True)
        elif mode == 'run':
            p.add_argument('--plan', required=True); p.add_argument('--approved', action='store_true')
        else:
            p.add_argument('--run-receipt', required=True)
    return ap


def main(argv=None):
    try:
        args = sys.argv[1:] if argv is None else argv
        if args[:1] == ['--_worker']:
            require(len(args) == 3, 'WORKER_ARGUMENTS')
            return private_worker(args[1], args[2])
        a = parser().parse_args(args)
        a.handler(a)
        return 0
    except (AdapterError, ValueError, OSError, KeyError, TypeError) as exc:
        print('CORASON refused: ' + getattr(exc, 'code', type(exc).__name__), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
