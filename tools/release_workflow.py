#!/usr/bin/env python3
"""Run the optional partitioned cut through one resumable, source-bound stage record.

Internal steps use the same shell preflight, generated-surface, identity, strict
health and tier-builder functions as the default monolithic cut. Nothing seals,
places an owner release, tags, pushes or installs a runtime.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import uuid
import zipfile

from _console import emit
import _release_partition_runner as partitions
import _release_partitions as contract
import _release_validation as support
import _release_import_smoke as imports
from _release_workflow import Stage, Workflow
from release_validate import Outcome, retries


class RegistryRefused(support.ValidationRefused):
    """Typed, redacted high-level registry admission; never a disclosure decision."""
    def __init__(self, state, message):
        super().__init__(message)
        self.state = state
        self.code = 1 if state == 'FAIL' else 2


def registry_selection(source: Path, args) -> dict | None:
    """Bind only four explicit options; no inherited selection or local discovery."""
    values = {name: getattr(args, 'synthetic_' + name, None)
              for name in ('registry', 'registry_sha256', 'guard_sha256', 'allowlist_sha256')}
    if all(value is None for value in values.values()):
        return None
    if not all(values.values()):
        raise RegistryRefused('HOLD', 'registry admission HOLD: supply all four explicit synthetic registry/guard/list options')
    registry = Path(values['registry'])
    if not registry.is_absolute():
        raise RegistryRefused('HOLD', 'registry admission HOLD: the explicit metadata path must be absolute')
    for name in ('registry_sha256', 'guard_sha256', 'allowlist_sha256'):
        if re.fullmatch('[0-9a-fA-F]{64}', values[name]) is None:
            raise RegistryRefused('HOLD', 'registry admission HOLD: selected digests must be 64 hexadecimal characters')
    selected = {'registry_path': str(registry), **{name: values[name].lower()
                for name in ('registry_sha256', 'guard_sha256', 'allowlist_sha256')}}
    expected = {'guard_sha256': 'synthetic_id_registry_guard.py',
                'allowlist_sha256': 'test_synthetic_ids.txt', 'helper_sha256': 'verify_export_registry.py'}
    for field, filename in expected.items():
        path = source / 'tools' / filename
        if not path.is_file() or path.is_symlink():
            raise RegistryRefused('HOLD', 'registry admission HOLD: selected source helper/guard/list is unavailable; reconcile its owner first')
        digest = support.sha256_file(path)
        if field in selected and digest != selected[field]:
            raise RegistryRefused('HOLD', 'registry admission HOLD: selected source guard/list digest mismatch')
        selected[field] = digest
    return selected


def registry_options(selected: dict | None) -> tuple[str, ...]:
    """Forward the same declared source/metadata choices to every caller boundary."""
    if selected is None:
        return ()
    return tuple(value for flag, key in (
        ('--synthetic-registry', 'registry_path'),
        ('--synthetic-registry-sha256', 'registry_sha256'),
        ('--synthetic-guard-sha256', 'guard_sha256'),
        ('--synthetic-allowlist-sha256', 'allowlist_sha256')) for value in (flag, selected[key]))


def registry_context(selected: dict | None) -> dict:
    """Keep expected digests in the stage definition, without printing a locator."""
    if selected is None:
        return {'state': 'NOT_REQUESTED', 'diagnostic_status': 'NOT_RUN',
                'selected_hashes_verified': False, 'fixture_role_clearance': 'NOT_EVALUATED',
                'source_disclosure_clearance': 'NOT_EVALUATED'}
    return {name: value for name, value in selected.items() if name != 'registry_path'} | {
        'registry_locator_sha256': hashlib.sha256(selected['registry_path'].encode()).hexdigest(),
        'state': 'SELECTED', 'diagnostic_status': 'REQUESTED',
        'scope': 'explicit selected synthetic-list snapshot only',
        'fixture_role_clearance': 'HOLD', 'source_disclosure_clearance': 'HOLD'}


def registry_inputs(selected: dict | None) -> tuple[dict, ...]:
    """External metadata stays in place; generic workflow checks it before/after stages."""
    if selected is None:
        return ()
    return ({'path': selected['registry_path'], 'sha256': selected['registry_sha256']},)


def selected_interpreter(python: str) -> tuple[Path, dict]:
    """Match the exporter compatibility response without resolving a venv prefix."""
    try:
        locator = support.resolve_interpreter(python)
        probe = subprocess.run([str(locator), '-B', '-c',
            'import sys; supported = sys.version_info >= (3, 12); sys.stdout.write("SAPOTE_EXPORT_PYTHON_3_12_PLUS" if supported else ""); raise SystemExit(0 if supported else 2)'],
            capture_output=True, text=True, timeout=60)   # a cold interpreter start on a busy machine can exceed 5 s
        if probe.returncode != 0 or probe.stdout != 'SAPOTE_EXPORT_PYTHON_3_12_PLUS':
            raise ValueError('compatibility response refused')
    except (OSError, ValueError, subprocess.SubprocessError):
        raise RegistryRefused('HOLD', 'registry admission HOLD: select one installed compatible Python3.12+ executable') from None
    return locator, {'locator_sha256': hashlib.sha256(str(locator).encode()).hexdigest(),
                     'binary_sha256': support.sha256_file(locator),
                     'compatibility_response': 'SAPOTE_EXPORT_PYTHON_3_12_PLUS'}


def registry_preflight(source: Path, selected: dict | None, python: str) -> tuple[dict, int]:
    """Run only a selected diagnostic; absence grants no synthetic-role clearance."""
    if selected is None:
        return {'schema': 'sapote.high-level-registry-admission.v1',
                'state': 'NOT_REQUESTED', 'diagnostic_status': 'NOT_RUN',
                'selected': registry_context(None), 'selected_hashes_verified': False,
                'fixture_role_clearance': 'NOT_EVALUATED',
                'source_disclosure_clearance': 'NOT_EVALUATED'}, 0
    source = source.resolve(strict=True)
    for field, filename in (('helper_sha256', 'verify_export_registry.py'),
                            ('guard_sha256', 'synthetic_id_registry_guard.py'),
                            ('allowlist_sha256', 'test_synthetic_ids.txt')):
        path = source / 'tools' / filename
        if not path.is_file() or path.is_symlink() or support.sha256_file(path) != selected[field]:
            raise RegistryRefused('HOLD', 'registry admission HOLD: selected source/stage helper, guard or list changed')
    before = partitions.source_digest(source)
    locator, interpreter = selected_interpreter(python)
    environment = partitions.test_environment(source, workflow_environment(str(locator), source))
    command = [str(locator), '-B', str(source / 'tools/verify_export_registry.py'),
               '--root', str(source), '--registry', selected['registry_path'],
               '--registry-sha256', selected['registry_sha256'], '--guard-sha256', selected['guard_sha256'],
               '--allowlist-sha256', selected['allowlist_sha256']]
    try:
        process = subprocess.run(command, cwd=source, env=environment, capture_output=True,
                                 text=True, timeout=300)   # 30 s is too short on a machine busy with a cut; a refusal is still a refusal
        data = json.loads(process.stderr.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        raise RegistryRefused('HOLD', 'registry admission HOLD: selected owner invocation or redacted result contract refused') from None
    if not isinstance(data, dict):
        raise RegistryRefused('HOLD', 'registry admission HOLD: selected owner result contract refused')
    state = data.get('state')
    code = {'PASS_BOUND_SNAPSHOT': 0, 'FAIL': 1, 'HOLD': 2}.get(state)
    count = data.get('collision_count', 0)
    if (process.stdout or data.get('schema') != 'sapote.export-registry-preflight.v1'
            or code is None or process.returncode != code or type(count) is not int or count < 0
            or (state == 'PASS_BOUND_SNAPSHOT' and count)
            or (state in {'PASS_BOUND_SNAPSHOT', 'FAIL'} and any(data.get(key) != selected[key]
                for key in ('registry_sha256', 'guard_sha256', 'allowlist_sha256')))):
        raise RegistryRefused('HOLD', 'registry admission HOLD: selected owner result contract refused')
    if partitions.source_digest(source) != before:
        raise RegistryRefused('HOLD', 'registry admission HOLD: source/stage changed during admission')
    # Never echo child stderr, issues, registry paths or row identities. Expected
    # selections are marked verified only after a positive bounded owner result.
    record = {'schema': 'sapote.high-level-registry-admission.v1', 'state': state,
              'selected': registry_context(selected), 'selected_hashes_verified': state == 'PASS_BOUND_SNAPSHOT',
              'source_tree_sha256': before,
              'environment_sha256': hashlib.sha256(support.canonical_json(environment)).hexdigest(),
              'interpreter': interpreter, 'collision_count': count, 'fixture_role_clearance': 'HOLD', 'source_disclosure_clearance': 'HOLD'}
    return record, code


def require_registry_preflight(source, selected, python):
    record, code = registry_preflight(source, selected, python)
    if code:
        raise RegistryRefused(record['state'], 'registry admission ' + record['state'] + ': preserve selected bindings; resolve the guard finding without exemptions')
    return record


INTEGRITY_FILES = ('TIER_MANIFEST.txt', 'SOURCE_CHECKSUMS_SHA256.txt')
GENERATED_FILES = ('pyproject.toml', 'BUILD_STAMP.txt', 'CHANGELOG.md', 'mamey/__init__.py',
                   'AGENTS.md', 'CLAUDE.md', 'README.md', 'MODULE_MANIFEST.txt',
                   'docs/BOOTSTRAP_FILE_AUDIT.md', 'docs/COMMAND_CATALOG.generated.md',
                   'docs/DELIVERABLE_MENU.md', 'docs/DELIVERABLE_MENU_v97146.md',
                   'docs/TOOLS_INVENTORY.generated.md', 'docs/BUNDLE_CAPABILITIES.md',
                   'docs/MAINTENANCE_INVENTORY.generated.json', 'docs/MAINTENANCE_INVENTORY.generated.md',
                   'docs/FILE_ATLAS.csv', 'docs/FILE_ATLAS.md',
                   'docs/reference/01_Math_Reference_VolI.md',
                   'docs/reference/02_Math_Reference_VolII.md',
                   'docs/reference/03_Plumbing_Reference.md')


def preparation_outputs(source: Path) -> tuple[str, ...]:
    """Discover version-rule targets statically, without importing production code."""
    paths = set(GENERATED_FILES) | set(INTEGRITY_FILES)
    for name, variables in [('sync_version.py', {'RULES'}), ('sync_wiki_mirrors.py', {'MIRRORS'})]:
        path = source/'tools'/name
        if not path.is_file():
            raise support.ValidationRefused('preparation owner is missing: tools/' + name)
        tree = ast.parse(path.read_text())
        for node in tree.body:
            if not isinstance(node, ast.Assign) or not any(isinstance(target, ast.Name) and target.id in variables for target in node.targets):
                continue
            for value in ast.walk(node.value):
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    relative = Path(value.value)
                    if (not relative.is_absolute() and '..' not in relative.parts
                            and (source/relative).is_file()):
                        paths.add(relative.as_posix())
    bootstrap = source/'bootstrap_contract.yml'
    if bootstrap.is_file():
        paths.update(re.findall(r'(?m)^\s+target:\s*([\w./-]+)\s*$', bootstrap.read_text()))
    return tuple(sorted(paths))


def plan(source: Path, version: str, date: str, letter: str, files: int, registry: dict | None = None) -> tuple[Stage, ...]:
    """Declare exact source mutations and retain separate source/artifact validation."""
    base = ('{PYTHON}', '{SOURCE}/tools/release_workflow.py', '_step', '--source', '{SOURCE}',
            '--out', '{OUT}', '--python', '{PYTHON}', '--files-per-partition', str(files), *registry_options(registry))
    def step(name, **kwargs):
        argv = (*base, '--step', name)
        return Stage(name, argv, retry_argv=(*argv, '--retry-reason', '{RETRY_REASON}'), **kwargs)
    def shell(name, phase, **kwargs):
        return Stage(name, ('/usr/bin/env', 'RELEASE_WORKFLOW_PHASE='+phase, 'RELEASE_DATE='+date,
            'CUT_TIERS=code', 'bash', '{SOURCE}/tools/release_cut.sh', version, '{SOURCE}', '{OUT}/packages', letter, *registry_options(registry)), **kwargs)
    return (
        Stage('registry-preflight', ('{PYTHON}', '{SOURCE}/tools/release_workflow.py', '_registry',
              '--source', '{SOURCE}', '--python', '{PYTHON}', *registry_options(registry))),
        shell('prepare', 'prepare', source_changes=preparation_outputs(source)),
        shell('integrity-baseline', 'integrity', source_changes=INTEGRITY_FILES),
        step('imports-precheck', output_trees=('imports-precheck',)),
        step('baseline', output_trees=('baseline',)),
        step('convergence', source_changes=('RELEASE_MANIFEST.md',), output_trees=('convergence',)),
        shell('integrity-final', 'integrity', source_changes=INTEGRITY_FILES),
        step('imports-final', output_trees=('imports-final',)),
        step('final', output_trees=('final',)),
        step('manifest-check', output_trees=('manifest-check',)),
        shell('post-gates', 'post-gates'),
        step('prepackage', output_trees=('prepackage',)),
        shell('package', 'package', output_trees=('packages',)),
        step('artifact', output_trees=('artifact',)),
    )


def run_partitions(source: Path, output: Path, files: int, *, baseline=False, reason=None, python: str | None = None):
    """Yield the measured result; resume requires the outer explicit disposition."""
    selected_python = sys.executable if python is None else python
    resume = output.exists()
    retry = {}
    if resume:
        contract.require(bool(reason and reason.strip()), 'occupied partition output requires explicit retry disposition')
        receipt = output/'partition.json'
        contract.require(receipt.is_file(), 'partition initialization is incomplete; preserve it and rebuild a fresh workflow')
        record = json.loads(receipt.read_text())
        collection = record.get('collection', {})
        if collection.get('status') not in {'PASS', 'PENDING'}:
            retry['collection'] = reason
        expected = 'MEASURED' if baseline else 'PASS'
        for entry in record.get('partitions', []):
            if entry.get('status') not in {expected, 'PENDING'}:
                retry[entry['plan']['id']] = reason
    runner = partitions.PartitionRunner(source, output, selected_python, files_per_partition=files, baseline=baseline)
    result = runner.run(resume=resume, retry=retry)
    yield Outcome(('RELEASE BASELINE: ' if baseline else 'RELEASE PARTITIONS: ') + result['status'])
    return result


def checked(command: list[str], source: Path):
    """Run a child within the outer watched stage; propagate its real exit status."""
    subprocess.run(command, cwd=source, check=True)


def verified_final(source: Path, output: Path, admission: Path, *, python: str | None = None):
    """Re-admit the actual environment and verify the final partition evidence."""
    selected_python = sys.executable if python is None else python
    return partitions.verified_counts(source, output/'final/partition.json',
        support.sha256_file(output/'final/partition.json'), python=selected_python, admission_output=admission)


def run_import_stage(source: Path, output: Path, *, python: str | None = None):
    """Keep every controlled import attempt; a held roster cannot advance a cut."""
    selected_python = sys.executable if python is None else python
    attempt = output/uuid.uuid4().hex
    attempt.mkdir(parents=True)
    environment = workflow_environment(selected_python,source)
    report = imports.run_import_smoke(source, attempt/'smoke', selected_python, env=environment)
    receipt = attempt/'smoke/import-smoke.json'
    reference = {'path':receipt.relative_to(output).as_posix(),'sha256':support.sha256_file(receipt)}
    support.atomic_json(output/'current.json',{'schema':'sapote-mamey.workflow-import-stage.v1',
                                             'status':report['status'],'receipt':reference})
    contract.require(report['status'] in imports.IMPORT_READY_STATES, 'complete import roster is '+report['status']+'; inspect '+str(receipt))
    imports.verify_import_receipt(source,receipt,reference['sha256'],report['environment_identity_sha256'],env=environment)
    yield Outcome('CONTROLLED IMPORT STAGE: '+report['status']+' — '+str(output/'current.json'))


def verify_current_imports(source: Path, output: Path, admission: Path, *, python: str | None = None):
    """Fresh environment admission precedes consumption of the exact active import record."""
    current = json.loads((output/'current.json').read_text())
    contract.require(current.get('schema')=='sapote-mamey.workflow-import-stage.v1' and current.get('status') in imports.IMPORT_READY_STATES,
                     'current complete import stage is not PASS')
    receipt, _ = partitions.read_artifact(output,current.get('receipt'))
    selected_python = sys.executable if python is None else python
    consumer_env = workflow_environment(selected_python,source)
    environment = support.admit_environment(selected_python,output=admission,env=partitions.test_environment(source,consumer_env))
    contract.require(environment['status']=='READY','current import-consumer environment refused')
    summary = imports.verify_import_receipt(source,receipt,current['receipt']['sha256'],environment['identity_sha256'],env=consumer_env)
    contract.require(summary['status']==current['status'],'current import status differs from verified receipt')
    support.atomic_json(admission/'import-verification.json',{'status':'VERIFIED_IMPORTS',
                       'receipt_sha256':current['receipt']['sha256'],'summary':summary})
    return summary


def artifact_stage(source: Path, output: Path, files: int, reason: str | None, registry: dict | None = None, *, python: str | None = None):
    """Verify and extract the exact built ZIP, then independently test its full roster."""
    selected_python = sys.executable if python is None else python
    root = output/'artifact'; receipt = root/'artifact.json'; extracted = root/'source'
    archives = list((output/'packages/code').glob('*.zip'))
    contract.require(len(archives) == 1, 'CODE artifact is missing or ambiguous')
    archive = archives[0]
    if not root.exists():
        root.mkdir()
        with zipfile.ZipFile(archive) as zipped:
            entries = zipped.infolist(); names = [entry.filename for entry in entries]
            contract.require(names and len(names) == len(set(names)), 'artifact has empty or duplicate members')
            required_space = sum(entry.file_size for entry in entries)
            contract.require(shutil.disk_usage(output).free >= support.DEFAULT_MIN_DISK + required_space,
                             'insufficient disk for isolated artifact validation')
            for entry in entries:
                relative = Path(entry.filename)
                mode = entry.external_attr >> 16
                contract.require('\\' not in entry.filename and not relative.is_absolute() and '..' not in relative.parts
                    and not stat.S_ISLNK(mode) and (entry.is_dir() or stat.S_IFMT(mode) in {0, stat.S_IFREG}),
                    'artifact contains unsafe or nonregular members')
            contract.require(zipped.testzip() is None, 'artifact CRC failure')
            # This is the required isolated extracted-artifact check, not an owner release.
            support.atomic_json(root/'materialization.json', {'reason':'Independent extracted-artifact validation',
                'archive_sha256':support.sha256_file(archive), 'uncompressed_bytes':required_space,
                'estimated_size_before_extraction':required_space, 'member_count':len(entries)})
            extracted.mkdir()
            for entry in entries:
                target = extracted/entry.filename
                if entry.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zipped.open(entry) as incoming, target.open('xb') as outgoing:
                        shutil.copyfileobj(incoming, outgoing)
                    target.chmod((entry.external_attr >> 16) & 0o777 or 0o644)
        support.atomic_json(receipt, {'schema':'sapote-mamey.extracted-artifact.v1', 'status':'EXTRACTED',
            'archive_sha256':support.sha256_file(archive), 'extracted_source_sha256':partitions.source_digest(extracted)})
    contract.require(receipt.is_file(), 'partial extraction retained; rebuild a fresh workflow')
    record = json.loads(receipt.read_text())
    contract.require(record['archive_sha256'] == support.sha256_file(archive)
        and record['extracted_source_sha256'] == partitions.source_digest(extracted), 'extracted artifact drift')
    require_registry_preflight(extracted, registry, selected_python)
    checked([selected_python, 'tools/check_release_manifest.py', '--root', '.', '--quiet'], extracted)
    checked([selected_python, 'tools/verify_release_identity.py', '--strict-membership'], extracted)
    current = root/'imports/current.json'
    if not current.is_file() or json.loads(current.read_text()).get('status') not in imports.IMPORT_READY_STATES:
        yield from run_import_stage(extracted, root/'imports', python=selected_python)
    import_summary = verify_current_imports(extracted,root/'imports',root/'import-admissions'/uuid.uuid4().hex, python=selected_python)
    result = yield from run_partitions(extracted, root/'validation', files, reason=reason, python=selected_python)
    record.update(status='EXTRACTED_SUITE_PASS', partition_receipt={
        'path':'validation/partition.json', 'sha256':support.sha256_file(root/'validation/partition.json')},
        summary=result['totals'], import_safety={'status':import_summary['status'],'summary':import_summary,
                                               'current_sha256':support.sha256_file(current)})
    support.atomic_json(receipt, record)


def execute_step(args):
    """Yield ordered status events while performing one declared stage."""
    source = args.source.resolve(); output = args.out.resolve(); name = args.step
    directory = output/name
    if name in {'imports-precheck','imports-final'}:
        yield from run_import_stage(source,directory, python=args.python)
        return
    if name in {'baseline', 'final'}:
        yield from run_partitions(source, directory, args.files_per_partition, baseline=name == 'baseline', reason=args.retry_reason, python=args.python)
        return
    if name == 'artifact':
        yield from artifact_stage(source, output, args.files_per_partition, args.retry_reason, registry_selection(source, args), python=args.python)
        return
    # A retried non-partition step keeps each admission/log under its own UUID.
    attempt = directory/uuid.uuid4().hex
    attempt.mkdir(parents=True)
    if name == 'convergence':
        receipt = output/'baseline/partition.json'
        checked([args.python, 'tools/gen_release_manifest.py', '--python', args.python, '--fixed-point', '--partition-baseline', str(receipt),
            '--partition-receipt-sha256', support.sha256_file(receipt), '--partition-admission', str(attempt/'admission')], source)
    elif name == 'manifest-check':
        receipt = output/'final/partition.json'
        checked([args.python, 'tools/gen_release_manifest.py', '--python', args.python, '--check', '--partition-receipt', str(receipt),
            '--partition-receipt-sha256', support.sha256_file(receipt), '--partition-admission', str(attempt/'admission')], source)
    elif name == 'prepackage':
        yield Outcome('gate: recheck partition evidence immediately before package construction')
        counts, _ = verified_final(source, output, attempt/'admission', python=args.python)
        import_summary = verify_current_imports(source,output/'imports-final',attempt/'import-admission', python=args.python)
        support.atomic_json(attempt/'verified.json', {'status':'VERIFIED', 'main_passed':counts['passed'],
            'skipped_including_collection':counts['skipped'],'import_safety':import_summary})
    else:
        raise support.ValidationRefused('unknown workflow step')



def workflow_environment(python: str, source: Path) -> dict[str, str]:
    """Normalize orchestration switches; the stage definition binds these choices."""
    env = dict(os.environ)
    contract.require(not env.get("PYTEST_ADDOPTS"),
                     "PYTEST_ADDOPTS overrides the release test profile; unset it and retry before source preparation.")
    for key in ('RELEASE_WORKFLOW_RESUME', 'RELEASE_WORKFLOW_RETRY', 'RELEASE_PYTEST_MODE',
                'RELEASE_DATE', 'RELEASE_PARTITION_FILES', 'CUT_TIERS', 'RELEASE_WORKFLOW_PHASE',
                'SHLVL', 'OLDPWD', '_'):
        env.pop(key, None)
    env['PWD'] = str(source.resolve(strict=True))
    selected_python = support.resolve_interpreter(python)
    env['PYTHON'] = str(selected_python)
    interpreter_bin = str(selected_python.parent)
    env['PATH'] = os.pathsep.join([interpreter_bin, *[entry for entry in env.get('PATH','').split(os.pathsep)
                                                   if entry != interpreter_bin]])
    return env


def cut_context(version: str, date: str, letter: str, files: int, registry: dict | None = None) -> dict:
    """Keep release identity and unresolved adoption requirements in the root record."""
    return {'profile':'configured-full-suite-partitioned-cut', 'bundle_version':version,
        'date':date, 'letter':letter, 'files_per_partition':files,
        'build_stamp':date+'v'+version.replace('.', '')+letter, 'seal_status':'NOT_RUN',
        'linux_py312_ci':'NOT_RUN_LOCALLY', 'import_safety':'REQUIRED_COMPLETE_SOURCE_AND_ARTIFACT',
        'registry_selection':registry_context(registry)}


def parse_args(argv=None):
    """Parse the optional cut entry point or a declared internal stage."""
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='operation', required=True)
    cut = subs.add_parser('cut')
    cut.add_argument('--version', required=True); cut.add_argument('--date', required=True)
    cut.add_argument('--letter', default='a'); cut.add_argument('--python', default=sys.executable)
    cut.add_argument('--resume', action='store_true'); cut.add_argument('--retry', action='append', default=[])
    cut.add_argument('--seal-target', type=Path, help='Optional occupancy check only; this command never seals')
    verify = subs.add_parser('verify', help='Verify a bound completed workflow without rerunning stages')
    verify.add_argument('--sha256', required=True)
    verify.add_argument('--admission', required=True, type=Path)
    verify.add_argument('--python', default=sys.executable)
    registry = subs.add_parser('_registry', help='Explicit redacted registry admission only; no source mutation')
    registry.add_argument('--source', type=Path, required=True)
    registry.add_argument('--python', default=sys.executable)
    step = subs.add_parser('_step')
    step.add_argument('--step', choices=['imports-precheck','baseline','convergence','imports-final',
                                       'final','manifest-check','prepackage','artifact'], required=True)
    step.add_argument('--retry-reason')
    step.add_argument('--python', default=sys.executable)
    for sub in (cut, step, verify):
        sub.add_argument('--source', type=Path, required=True); sub.add_argument('--out', type=Path, required=True)
        sub.add_argument('--files-per-partition', type=int, default=20)
    for sub in (cut, step, verify, registry):
        sub.add_argument('--synthetic-registry', type=Path, help='Optional diagnostic: select this external TSV and all three digest options; never discovered. Omit all four for NOT_REQUESTED/NOT_RUN')
        sub.add_argument('--synthetic-registry-sha256')
        sub.add_argument('--synthetic-guard-sha256')
        sub.add_argument('--synthetic-allowlist-sha256')
    return parser.parse_args(argv)


def command_events(args):
    """Stream ordered command outcomes, including refusals after prior progress."""
    try:
        if args.operation == '_registry':
            source = args.source.resolve(strict=True)
            record, code = registry_preflight(source, registry_selection(source, args), args.python)
            yield Outcome(json.dumps(record, sort_keys=True), code, stderr=True)
            return
        if args.operation == '_step':
            yield from execute_step(args)
            return
        if args.operation == 'verify':
            record_path = args.out/'workflow.json'
            contract.require(support.sha256_file(record_path) == args.sha256, 'workflow root SHA-256 mismatch')
            root_record = json.loads(record_path.read_text())
            recorded = root_record.get('context') if isinstance(root_record, dict) else None
            if not isinstance(recorded, dict):
                raise RegistryRefused('HOLD', 'registry admission HOLD: workflow selection missing or legacy record is unbound')
            selected = registry_selection(args.source.resolve(strict=True), args)
            if recorded.get('registry_selection') != registry_context(selected):
                raise RegistryRefused('HOLD', 'registry admission HOLD: workflow selection differs or legacy record is unbound')
            require_registry_preflight(args.source.resolve(strict=True), selected, args.python)
            require_registry_preflight(args.out.resolve()/'artifact/source', selected, args.python)
            context = cut_context(recorded['bundle_version'], recorded['date'], recorded['letter'], recorded['files_per_partition'], selected)
            stages = plan(args.source.resolve(strict=True), recorded['bundle_version'], recorded['date'], recorded['letter'], recorded['files_per_partition'], selected)
            workflow = Workflow(args.source, args.out, stages, args.python, env=workflow_environment(args.python, args.source), context=context, inputs=registry_inputs(selected))
            checked_record = workflow.verify(args.sha256, args.admission)
            verify_current_imports(args.source.resolve(),args.out/'imports-final',args.admission/'source-imports', python=args.python)
            verify_current_imports(args.out.resolve()/'artifact/source',args.out/'artifact/imports',args.admission/'artifact-imports', python=args.python)
            yield Outcome('RELEASE WORKFLOW: '+checked_record['status']+'; complete imports verified; owner and portability holds remain')
            return
        contract.require(re.fullmatch(r'\d+\.\d+\.\d+[a-z]?', args.version) is not None
                         and re.fullmatch(r'\d{8}', args.date) is not None and re.fullmatch('[a-z]', args.letter) is not None,
                         'invalid release identity arguments')
        contract.require(args.files_per_partition > 0, 'partition size must be positive')
        contract.require(os.environ.get('CUT_TIERS', 'code') == 'code', 'resumable workflow currently validates CODE only')
        contract.require(args.seal_target is None or not (args.seal_target.exists() or args.seal_target.is_symlink()),
                         'seal target is occupied; no overwrite is allowed')
        source = args.source.resolve(strict=True)
        selected = registry_selection(source, args)
        require_registry_preflight(source, selected, args.python)
        stages = plan(source, args.version, args.date, args.letter, args.files_per_partition, selected)
        workflow = Workflow(source, args.out, stages, args.python, env=workflow_environment(args.python, source),
            context=cut_context(args.version, args.date, args.letter, args.files_per_partition, selected),
            inputs=registry_inputs(selected))
        result = yield from workflow.iter_run(resume=args.resume, retry=retries(args.retry))
        yield Outcome('RELEASE WORKFLOW: '+result['status']+' — '+str(args.out/'workflow.json')
                      + '\nAll declared stages completed; owner adoption and portability remain held. No seal or push performed.')
    except RegistryRefused as exc:
        yield Outcome('RELEASE WORKFLOW: '+str(exc), exc.code, stderr=True)
    except (ValueError, OSError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        yield Outcome('RELEASE WORKFLOW: REFUSED: '+str(exc), 2, stderr=True)


def main(argv=None):
    """Deliver each event immediately and unfiltered on its declared stream."""
    code = 0
    for event in command_events(parse_args(argv)):
        if isinstance(event, str):
            event = Outcome(event)
        emit(event.text, file=sys.stderr if event.stderr else sys.stdout)
        code = event.code
    return code


if __name__ == '__main__':
    raise SystemExit(main())
