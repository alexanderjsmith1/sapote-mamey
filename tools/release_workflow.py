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


INTEGRITY_FILES = ('TIER_MANIFEST.txt', 'SOURCE_CHECKSUMS_SHA256.txt')
GENERATED_FILES = ('pyproject.toml', 'BUILD_STAMP.txt', 'CHANGELOG.md', 'mamey/__init__.py',
                   'AGENTS.md', 'CLAUDE.md', 'README.md', 'MODULE_MANIFEST.txt',
                   'docs/BOOTSTRAP_FILE_AUDIT.md', 'docs/COMMAND_CATALOG.generated.md',
                   'docs/DELIVERABLE_MENU.md', 'docs/DELIVERABLE_MENU_v97146.md',
                   'docs/TOOLS_INVENTORY.generated.md', 'docs/BUNDLE_CAPABILITIES.md',
                   'docs/MAINTENANCE_INVENTORY.generated.json', 'docs/MAINTENANCE_INVENTORY.generated.md')


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


def plan(source: Path, version: str, date: str, letter: str, files: int) -> tuple[Stage, ...]:
    """Declare exact source mutations and retain separate source/artifact validation."""
    base = ('{PYTHON}', '{SOURCE}/tools/release_workflow.py', '_step', '--source', '{SOURCE}',
            '--out', '{OUT}', '--files-per-partition', str(files))
    def step(name, **kwargs):
        argv = (*base, '--step', name)
        return Stage(name, argv, retry_argv=(*argv, '--retry-reason', '{RETRY_REASON}'), **kwargs)
    def shell(name, phase, **kwargs):
        return Stage(name, ('/usr/bin/env', 'RELEASE_WORKFLOW_PHASE='+phase, 'RELEASE_DATE='+date,
            'CUT_TIERS=code', 'bash', '{SOURCE}/tools/release_cut.sh', version, '{SOURCE}', '{OUT}/packages', letter), **kwargs)
    return (
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


def run_partitions(source: Path, output: Path, files: int, *, baseline=False, reason=None):
    """Yield the measured result; resume requires the outer explicit disposition."""
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
    runner = partitions.PartitionRunner(source, output, sys.executable, files_per_partition=files, baseline=baseline)
    result = runner.run(resume=resume, retry=retry)
    yield Outcome(('RELEASE BASELINE: ' if baseline else 'RELEASE PARTITIONS: ') + result['status'])
    return result


def checked(command: list[str], source: Path):
    """Run a child within the outer watched stage; propagate its real exit status."""
    subprocess.run(command, cwd=source, check=True)


def verified_final(source: Path, output: Path, admission: Path):
    """Re-admit the actual environment and verify the final partition evidence."""
    return partitions.verified_counts(source, output/'final/partition.json',
        support.sha256_file(output/'final/partition.json'), python=sys.executable, admission_output=admission)


def run_import_stage(source: Path, output: Path):
    """Keep every controlled import attempt; a held roster cannot advance a cut."""
    attempt = output/uuid.uuid4().hex
    attempt.mkdir(parents=True)
    environment = workflow_environment(sys.executable,source)
    report = imports.run_import_smoke(source, attempt/'smoke', sys.executable, env=environment)
    receipt = attempt/'smoke/import-smoke.json'
    reference = {'path':receipt.relative_to(output).as_posix(),'sha256':support.sha256_file(receipt)}
    support.atomic_json(output/'current.json',{'schema':'sapote-mamey.workflow-import-stage.v1',
                                             'status':report['status'],'receipt':reference})
    contract.require(report['status']=='PASS', 'complete import roster is '+report['status']+'; inspect '+str(receipt))
    imports.verify_import_receipt(source,receipt,reference['sha256'],report['environment_identity_sha256'],env=environment)
    yield Outcome('CONTROLLED IMPORT STAGE: PASS — '+str(output/'current.json'))


def verify_current_imports(source: Path, output: Path, admission: Path, *, python: str | None = None):
    """Fresh environment admission precedes consumption of the exact active import record."""
    current = json.loads((output/'current.json').read_text())
    contract.require(current.get('schema')=='sapote-mamey.workflow-import-stage.v1' and current.get('status')=='PASS',
                     'current complete import stage is not PASS')
    receipt, _ = partitions.read_artifact(output,current.get('receipt'))
    selected_python = sys.executable if python is None else python
    consumer_env = workflow_environment(selected_python,source)
    environment = support.admit_environment(selected_python,output=admission,env=partitions.test_environment(source,consumer_env))
    contract.require(environment['status']=='READY','current import-consumer environment refused')
    summary = imports.verify_import_receipt(source,receipt,current['receipt']['sha256'],environment['identity_sha256'],env=consumer_env)
    support.atomic_json(admission/'import-verification.json',{'status':'VERIFIED_IMPORTS',
                       'receipt_sha256':current['receipt']['sha256'],'summary':summary})
    return summary


def artifact_stage(source: Path, output: Path, files: int, reason: str | None):
    """Verify and extract the exact built ZIP, then independently test its full roster."""
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
    checked([sys.executable, 'tools/check_release_manifest.py', '--root', '.', '--quiet'], extracted)
    checked([sys.executable, 'tools/verify_release_identity.py', '--strict-membership'], extracted)
    current = root/'imports/current.json'
    if not current.is_file() or json.loads(current.read_text()).get('status')!='PASS':
        yield from run_import_stage(extracted, root/'imports')
    import_summary = verify_current_imports(extracted,root/'imports',root/'import-admissions'/uuid.uuid4().hex)
    result = yield from run_partitions(extracted, root/'validation', files, reason=reason)
    record.update(status='EXTRACTED_SUITE_PASS', partition_receipt={
        'path':'validation/partition.json', 'sha256':support.sha256_file(root/'validation/partition.json')},
        summary=result['totals'], import_safety={'status':'PASS','summary':import_summary,
                                               'current_sha256':support.sha256_file(current)})
    support.atomic_json(receipt, record)


def execute_step(args):
    """Yield ordered status events while performing one declared stage."""
    source = args.source.resolve(); output = args.out.resolve(); name = args.step
    directory = output/name
    if name in {'imports-precheck','imports-final'}:
        yield from run_import_stage(source,directory)
        return
    if name in {'baseline', 'final'}:
        yield from run_partitions(source, directory, args.files_per_partition, baseline=name == 'baseline', reason=args.retry_reason)
        return
    if name == 'artifact':
        yield from artifact_stage(source, output, args.files_per_partition, args.retry_reason)
        return
    # A retried non-partition step keeps each admission/log under its own UUID.
    attempt = directory/uuid.uuid4().hex
    attempt.mkdir(parents=True)
    if name == 'convergence':
        receipt = output/'baseline/partition.json'
        checked([sys.executable, 'tools/gen_release_manifest.py', '--fixed-point', '--partition-baseline', str(receipt),
            '--partition-receipt-sha256', support.sha256_file(receipt), '--partition-admission', str(attempt/'admission')], source)
    elif name == 'manifest-check':
        receipt = output/'final/partition.json'
        checked([sys.executable, 'tools/gen_release_manifest.py', '--check', '--partition-receipt', str(receipt),
            '--partition-receipt-sha256', support.sha256_file(receipt), '--partition-admission', str(attempt/'admission')], source)
    elif name == 'prepackage':
        yield Outcome('gate: recheck partition evidence immediately before package construction')
        counts, _ = verified_final(source, output, attempt/'admission')
        import_summary = verify_current_imports(source,output/'imports-final',attempt/'import-admission')
        support.atomic_json(attempt/'verified.json', {'status':'VERIFIED', 'main_passed':counts['passed'],
            'skipped_including_collection':counts['skipped'],'import_safety':import_summary})
    else:
        raise support.ValidationRefused('unknown workflow step')



def workflow_environment(python: str, source: Path) -> dict[str, str]:
    """Normalize orchestration switches; the stage definition binds these choices."""
    env = dict(os.environ)
    for key in ('RELEASE_WORKFLOW_RESUME', 'RELEASE_WORKFLOW_RETRY', 'RELEASE_PYTEST_MODE',
                'RELEASE_DATE', 'RELEASE_PARTITION_FILES', 'CUT_TIERS', 'RELEASE_WORKFLOW_PHASE',
                'SHLVL', 'OLDPWD', '_'):
        env.pop(key, None)
    env['PWD'] = str(source.resolve(strict=True))
    interpreter_bin = str(support.resolve_interpreter(python).parent)
    env['PATH'] = os.pathsep.join([interpreter_bin, *[entry for entry in env.get('PATH','').split(os.pathsep)
                                                   if entry != interpreter_bin]])
    return env


def cut_context(version: str, date: str, letter: str, files: int) -> dict:
    """Keep release identity and unresolved adoption requirements in the root record."""
    return {'profile':'configured-full-suite-partitioned-cut', 'bundle_version':version,
        'date':date, 'letter':letter, 'files_per_partition':files,
        'build_stamp':date+'v'+version.replace('.', '')+letter, 'seal_status':'NOT_RUN',
        'linux_py312_ci':'NOT_RUN_LOCALLY', 'import_safety':'REQUIRED_COMPLETE_SOURCE_AND_ARTIFACT'}


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
    step = subs.add_parser('_step')
    step.add_argument('--step', choices=['imports-precheck','baseline','convergence','imports-final',
                                       'final','manifest-check','prepackage','artifact'], required=True)
    step.add_argument('--retry-reason')
    for sub in (cut, step, verify):
        sub.add_argument('--source', type=Path, required=True); sub.add_argument('--out', type=Path, required=True)
        sub.add_argument('--files-per-partition', type=int, default=20)
    return parser.parse_args(argv)


def command_events(args):
    """Stream ordered command outcomes, including refusals after prior progress."""
    try:
        if args.operation == '_step':
            yield from execute_step(args)
            return
        if args.operation == 'verify':
            record_path = args.out/'workflow.json'
            contract.require(support.sha256_file(record_path) == args.sha256, 'workflow root SHA-256 mismatch')
            recorded = json.loads(record_path.read_text())['context']
            context = cut_context(recorded['bundle_version'], recorded['date'], recorded['letter'], recorded['files_per_partition'])
            stages = plan(args.source.resolve(strict=True), recorded['bundle_version'], recorded['date'], recorded['letter'], recorded['files_per_partition'])
            workflow = Workflow(args.source, args.out, stages, args.python, env=workflow_environment(args.python, args.source), context=context)
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
        stages = plan(source, args.version, args.date, args.letter, args.files_per_partition)
        workflow = Workflow(source, args.out, stages, args.python, env=workflow_environment(args.python, source),
            context=cut_context(args.version, args.date, args.letter, args.files_per_partition))
        result = yield from workflow.iter_run(resume=args.resume, retry=retries(args.retry))
        yield Outcome('RELEASE WORKFLOW: '+result['status']+' — '+str(args.out/'workflow.json')
                      + '\nAll declared stages completed; owner adoption and portability remain held. No seal or push performed.')
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
