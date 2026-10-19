#!/usr/bin/env python3
"""Verify one completed release record before an explicitly authorized owner consumer.

The external consumer retains all existing sealing, adoption and placement gates.
This adapter verifies its inputs and records invocation; it never labels a return
code as a seal or publication. No consumer runs without --owner-authorized.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from types import SimpleNamespace


class OwnerConsumptionRefused(ValueError):
    """A missing authorization or invalid release binding blocks the consumer."""


def require(condition, message):
    if not condition:
        raise OwnerConsumptionRefused(message)


IMPORT_READY_STATES = frozenset({'PASS','READY_WITH_OPTIONAL_UNAVAILABLE'})


def owners():
    """Load existing release verifiers only after parsing and basic admission."""
    import release_workflow as workflow
    import _release_partition_runner as partitions
    import _release_validation as support
    return SimpleNamespace(workflow=workflow, partitions=partitions, support=support)


def file_pin(path: Path, expected_sha256=None):
    require(path.is_file() and not path.is_symlink(), 'required input is missing or nonregular: '+str(path))
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    measured = digest.hexdigest()
    require(expected_sha256 is None or measured == expected_sha256, 'input SHA-256 mismatch: '+str(path))
    info = path.stat()
    return {'path':str(path), 'sha256':measured, 'bytes':info.st_size,
            'mode':stat.S_IMODE(info.st_mode)}


def read_json(path: Path, expected_sha256):
    """Parse the exact admitted receipt bytes, with no second read for parsing."""
    require(path.is_file() and not path.is_symlink(), 'required receipt is missing or nonregular: '+str(path))
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected_sha256, 'receipt SHA-256 mismatch: '+str(path))
    value = json.loads(raw)
    require(isinstance(value, dict), 'receipt must be an object: '+str(path))
    return value


def member(root: Path, relative):
    require(isinstance(relative, str) and relative and not Path(relative).is_absolute()
            and '..' not in Path(relative).parts, 'receipt member path is unsafe')
    path = root/relative
    require(path.resolve().is_relative_to(root.resolve()), 'receipt member escapes its root')
    require(not any((root/Path(*Path(relative).parts[:index])).is_symlink()
                    for index in range(1,len(Path(relative).parts)+1)), 'receipt member uses a symlink')
    return path


def stage_outputs(output, root_record, name):
    """Follow root -> active attempt -> exact output inventory, without trusting counts."""
    entries = [row for row in root_record.get('stages', []) if row.get('name') == name]
    require(len(entries) == 1 and entries[0].get('status') == 'PASS', 'required stage is not uniquely PASS: '+name)
    reference = entries[0].get('active', {})
    attempt = read_json(member(output,reference.get('path')),reference.get('sha256'))
    rows = attempt.get('outputs')
    require(isinstance(rows, list) and all(isinstance(row,dict) for row in rows), 'stage output inventory is malformed')
    require(len({row.get('path') for row in rows}) == len(rows), 'stage output inventory has duplicate paths')
    return rows


def output_pin(output, rows, relative):
    selected = [row for row in rows if row.get('path') == relative]
    require(len(selected) == 1, 'required output is missing or ambiguous: '+relative)
    require(re.fullmatch('[0-9a-f]{64}',selected[0].get('sha256') or '') is not None,
            'required output lacks an explicit SHA-256: '+relative)
    pin = file_pin(member(output,relative),selected[0].get('sha256'))
    require(pin['bytes'] == selected[0].get('bytes'), 'stage output size differs: '+relative)
    return pin


def fresh_target(path):
    require(not (path.exists() or path.is_symlink()), 'seal target is occupied; preserve it: '+str(path))


def recheck(backend, pins, source, source_hash, extracted, extracted_hash, target=None):
    for pin in pins:
        require(file_pin(Path(pin['path'])) == pin, 'admitted input changed before or during owner consumption')
    require(backend.partitions.source_digest(source) == source_hash, 'source changed before or during owner consumption')
    require(backend.partitions.source_digest(extracted) == extracted_hash, 'extracted source changed before or during owner consumption')
    if target is not None:
        fresh_target(target)


def verify_partition(backend, source, pin, admission, python, *, workflow_env):
    # artifact_stage calls its partition runner inside the original workflow
    # child. Its inherited PWD remains the workflow source, even though pytest's
    # cwd is the extracted source. Reuse the independently admitted root env;
    # complete import verification has its own extracted-root normalization.
    environment = backend.support.admit_environment(python, output=admission,
        env=backend.partitions.test_environment(source,workflow_env))
    require(environment.get('status') == 'READY', 'current partition-consumer environment refused')
    totals = backend.partitions.verify_partition_receipt(Path(pin['path']),source,pin['sha256'],
                                                        environment['identity_sha256'])
    return {'receipt':pin,'verified_totals':totals,
            'environment':file_pin(admission/'environment.json'),
            'environment_identity_sha256':environment['identity_sha256']}


def consume(*, source: Path, workflow: Path, workflow_sha256: str, evidence: Path,
            target: Path, consumer: Path, consumer_sha256: str, owner_authorized=False,
            python=sys.executable, timeout=1800):
    """Invoke only after independent root, partition, import and archive admission.

    Authorization is an explicit operator attestation, not an inferred consequence
    of a green suite. External owner gates are neither implemented nor waived here.
    A failed or interrupted attempt is retained and never retried in place.
    """
    require(owner_authorized is True, 'explicit owner authorization is required')
    require(re.fullmatch('[0-9a-f]{64}',workflow_sha256 or '') is not None
            and re.fullmatch('[0-9a-f]{64}',consumer_sha256 or '') is not None, 'explicit SHA-256 bindings are required')
    require(timeout > 0, 'owner consumer timeout must be positive')
    source=source.resolve(strict=True);workflow=workflow.resolve(strict=True)
    output=workflow.parent;evidence=evidence.absolute();target=target.absolute()
    consumer=consumer.resolve(strict=True)
    require(workflow.name == 'workflow.json', 'expected authoritative workflow.json')
    for destination in (evidence,target):
        require(not any(destination.resolve().is_relative_to(root) or root.is_relative_to(destination.resolve())
                        for root in (source,output)), 'owner destinations must be separate from source and workflow')
    require(not (evidence.resolve().is_relative_to(target.resolve())
                 or target.resolve().is_relative_to(evidence.resolve())), 'evidence and seal target must be separate')
    fresh_target(target);fresh_target(evidence)
    root_pin=file_pin(workflow,workflow_sha256);root_record=read_json(workflow,workflow_sha256)
    context=root_record.get('context',{})
    require(isinstance(context,dict) and context.get('profile') == 'configured-full-suite-partitioned-cut'
            and all(key in context for key in ('bundle_version','date','letter','files_per_partition')),
            'root does not declare the owned release-cut profile')
    consumer_pin=file_pin(consumer,consumer_sha256)
    require(os.access(consumer,os.X_OK), 'external owner consumer must be executable')
    backend=owners()
    evidence.mkdir(parents=True,exist_ok=False)
    attempt={'schema':'sapote-mamey.owner-consumption-attempt.v1','status':'VERIFYING',
             'owner_authorization':'EXPLICIT_OPERATOR_ATTESTATION','root':root_pin,
             'consumer':consumer_pin,'seal_target':str(target),'started_utc':backend.support.utc_now(),
             'owner_invoked':False,'seal_status':'NOT_ESTABLISHED_BY_ADAPTER'}
    backend.support.atomic_json(evidence/'attempt.json',attempt)
    try:
        expected_context=backend.workflow.cut_context(context['bundle_version'],context['date'],
                                                      context['letter'],context['files_per_partition'])
        require(context == expected_context, 'release context differs from the owned profile')
        stages=backend.workflow.plan(source,context['bundle_version'],context['date'],context['letter'],
                                     context['files_per_partition'])
        engine=backend.workflow.Workflow(source,output,stages,python,
            env=backend.workflow.workflow_environment(python,source),context=expected_context)
        root_verification=engine.verify(workflow_sha256,evidence/'workflow-admission')
        require(root_verification.get('status') == 'VERIFIED_STAGES'
                and root_verification.get('root_sha256') == workflow_sha256, 'independent root verification is not bound')
        source_hash=backend.partitions.source_digest(source)
        require(source_hash == root_record.get('committed_source_sha256'), 'verified root source differs')
        final_rows=stage_outputs(output,root_record,'final')
        final_pin=output_pin(output,final_rows,'final/partition.json')
        final_proof=verify_partition(backend,source,final_pin,evidence/'source-partition',python,workflow_env=engine.env)
        source_imports=backend.workflow.verify_current_imports(source,output/'imports-final',evidence/'source-imports',python=python)
        require(source_imports.get('status') in IMPORT_READY_STATES, 'complete source import verification is not PASS')
        source_import_rows=stage_outputs(output,root_record,'imports-final')
        source_current_imports=output_pin(output,source_import_rows,'imports-final/current.json')
        package_rows=stage_outputs(output,root_record,'package')
        archives=[row for row in package_rows if isinstance(row.get('path'),str)
                  and row['path'].startswith('packages/code/') and row['path'].endswith('.zip')]
        require(len(archives) == 1, 'root package inventory has missing or ambiguous CODE ZIP')
        archive_pin=output_pin(output,package_rows,archives[0]['path'])
        artifact_rows=stage_outputs(output,root_record,'artifact')
        artifact_pin=output_pin(output,artifact_rows,'artifact/artifact.json')
        artifact=read_json(Path(artifact_pin['path']),artifact_pin['sha256'])
        extracted=member(output,'artifact/source').resolve(strict=True)
        extracted_hash=backend.partitions.source_digest(extracted)
        require(artifact.get('status') == 'EXTRACTED_SUITE_PASS'
                and artifact.get('archive_sha256') == archive_pin['sha256']
                and artifact.get('extracted_source_sha256') == extracted_hash,
                'extracted artifact does not bind the verified archive and source')
        reference=artifact.get('partition_receipt',{})
        artifact_partition=member(output/'artifact',reference.get('path'))
        artifact_partition_pin=output_pin(output,artifact_rows,artifact_partition.relative_to(output).as_posix())
        require(artifact_partition_pin['sha256'] == reference.get('sha256'), 'artifact partition reference differs')
        artifact_proof=verify_partition(backend,extracted,artifact_partition_pin,evidence/'artifact-partition',python,workflow_env=engine.env)
        require(artifact.get('summary') == artifact_proof['verified_totals'], 'artifact summary differs from independently verified outcomes')
        artifact_imports=backend.workflow.verify_current_imports(extracted,output/'artifact/imports',evidence/'artifact-imports',python=python)
        require(artifact_imports.get('status') in IMPORT_READY_STATES, 'complete artifact import verification is not PASS')
        current_imports=output_pin(output,artifact_rows,'artifact/imports/current.json')
        require(artifact.get('import_safety',{}).get('status') == artifact_imports['status']
                and artifact.get('import_safety',{}).get('current_sha256') == current_imports['sha256'],
                'artifact complete import record differs')
        pins=[root_pin,consumer_pin,final_pin,source_current_imports,archive_pin,artifact_pin,artifact_partition_pin,current_imports]
        engine.check_history()
        recheck(backend,pins,source,source_hash,extracted,extracted_hash,target)
        verified={'schema':'sapote-mamey.verified-owner-consumption.v1','status':'VERIFIED_FOR_OWNER_CONSUMER',
            'root':root_pin,'root_verification':root_verification,'context':expected_context,
            'source':{'path':str(source),'sha256':source_hash},'source_partition':final_proof,
            'source_complete_imports':source_imports,'source_import_current':source_current_imports,
            'archive':archive_pin,'artifact_receipt':artifact_pin,
            'extracted_source':{'path':str(extracted),'sha256':extracted_hash},
            'artifact_partition':artifact_proof,'artifact_complete_imports':artifact_imports,
            'artifact_import_current':current_imports,
            'consumer':consumer_pin,'seal_target':str(target),
            'owner_authorization':'EXPLICIT_OPERATOR_ATTESTATION',
            'limits':['External owner sealing and placement gates remain required.',
                      'Consumer exit zero does not establish a seal, publication or portability.']}
        receipt=evidence/'verified-owner-consumption.json'
        with receipt.open('x') as stream:
            json.dump(verified,stream,indent=2);stream.write('\n')
        receipt.chmod(0o444);receipt_pin=file_pin(receipt)
        command=[str(consumer),'--verified-release-record',str(receipt),
                 '--verified-release-record-sha256',receipt_pin['sha256'],'--seal-target',str(target)]
        engine.check_history()
        recheck(backend,[*pins,receipt_pin],source,source_hash,extracted,extracted_hash,target)
        # Before a returned watch, a preflight failure and an interrupted launch
        # are not distinguishable here. Retain uncertainty instead of claiming
        # that no owner work occurred or that automatic retry is safe.
        attempt.update(status='OWNER_CONSUMER_REQUESTED',owner_invoked=None,
                       verified_record=receipt_pin,command=command)
        backend.support.atomic_json(evidence/'attempt.json',attempt)
        watch=backend.support.run_watched(command,cwd=consumer.parent,log=evidence/'owner-consumer.log',
            env=backend.workflow.workflow_environment(python,source),timeout=timeout)
        attempt.update(watch=watch,owner_invoked=True)
        require(watch.get('exit_code') == 0 and watch.get('stop_reason') is None
                and watch.get('cleanup_error') is None, 'owner consumer failed, stopped or did not clean up')
        engine.check_history()
        recheck(backend,[*pins,receipt_pin],source,source_hash,extracted,extracted_hash)
        attempt['status']='OWNER_CONSUMER_COMPLETED'
        return attempt
    except BaseException as exc:
        attempt.update(status='OWNER_CONSUMPTION_INTERRUPTED' if isinstance(exc,KeyboardInterrupt)
                       else 'OWNER_CONSUMPTION_REFUSED',reason=str(exc))
        raise
    finally:
        attempt['completed_utc']=backend.support.utc_now()
        backend.support.atomic_json(evidence/'attempt.json',attempt)


def _report_cli(message, *, error=False):
    """Emit one CLI record to the existing stream without global logging changes."""
    import logging
    logger = logging.Logger(__name__, level=logging.INFO)
    logger.manager = logging.Manager(logger)
    handler = logging.StreamHandler(sys.stderr if error else sys.stdout)
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
    logger.log(logging.ERROR if error else logging.INFO, message)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','workflow','evidence','target','consumer'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--workflow-sha256',required=True)
    parser.add_argument('--consumer-sha256',required=True)
    parser.add_argument('--owner-authorized',action='store_true')
    parser.add_argument('--python',default=sys.executable)
    parser.add_argument('--timeout',type=float,default=1800)
    args=parser.parse_args(argv)
    try:
        result=consume(source=args.source,workflow=args.workflow,workflow_sha256=args.workflow_sha256,
            evidence=args.evidence,target=args.target,consumer=args.consumer,consumer_sha256=args.consumer_sha256,
            owner_authorized=args.owner_authorized,python=args.python,timeout=args.timeout)
    except (ValueError,OSError,KeyError,TypeError) as exc:
        _report_cli('OWNER CONSUMPTION: REFUSED: '+str(exc), error=True)
        return 2
    _report_cli('OWNER CONSUMPTION: '+result['status']+'; external seal and owner evidence remain separate')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
