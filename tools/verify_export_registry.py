"""Bind the explicit synthetic-list registry guard before public export staging.

A PASS_BOUND_SNAPSHOT result is not source disclosure or release clearance.
No registry is discovered, copied, or exempted from a later literal/role gate.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import logging
from pathlib import Path
import re
import stat
import sys


def _regular(path):
    path=Path(path).absolute()
    if '..' in path.parts:
        raise ValueError('noncanonical input')
    for component in [*reversed(path.parents),path]:
        mode=component.lstat().st_mode
        if stat.S_ISLNK(mode):raise ValueError('linked input')
    if not path.is_file() or path.stat().st_size>16*1024*1024:
        raise ValueError('input shape')
    return path


def audit_export(root,registry=None,registry_sha256=None,*,guard_sha256=None,allowlist_sha256=None):
    result={'schema':'sapote.export-registry-preflight.v1','state':'HOLD',
            'scope':'bound synthetic-list snapshot only; literal/reference/history gates remain required',
            'issues':[]}
    if registry is None or not registry_sha256:
        result['issues']=['EXPLICIT_REGISTRY_AND_SHA256_REQUIRED'];return result
    if re.fullmatch(r'[0-9a-fA-F]{64}',registry_sha256) is None:
        result['issues']=['REGISTRY_DIGEST_INVALID'];return result
    if not guard_sha256 or not allowlist_sha256:
        result['issues']=['EXPECTED_GUARD_AND_ALLOWLIST_SHA256_REQUIRED'];return result
    if any(re.fullmatch(r'[0-9a-fA-F]{64}',v) is None for v in (guard_sha256,allowlist_sha256)):
        result['issues']=['SOURCE_DIGEST_INVALID'];return result
    try:
        if not Path(registry).is_absolute():raise ValueError('registry must be absolute')
        root=Path(root).absolute()
        if root.is_symlink() or not root.is_dir():raise ValueError('source root')
        registry=_regular(registry)
        if registry.is_relative_to(root.resolve()):raise ValueError('registry inside source')
        listing=_regular(root/'tools/test_synthetic_ids.txt')
        guard=_regular(root/'tools/synthetic_id_registry_guard.py')
        guard_source=guard.read_bytes()
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (registry,listing)}
        before[guard]=hashlib.sha256(guard_source).hexdigest()
        if before[registry]!=registry_sha256.lower():
            result['issues']=['REGISTRY_DIGEST_MISMATCH'];return result
        if before[guard]!=guard_sha256.lower() or before[listing]!=allowlist_sha256.lower():
            result['issues']=['SELECTED_SOURCE_DIGEST_MISMATCH'];return result
        spec=importlib.util.spec_from_file_location('bound_export_registry_guard',guard)
        module=importlib.util.module_from_spec(spec);exec(compile(guard_source,str(guard),'exec'),module.__dict__)
        audited=module.redacted_result(module.audit(listing,registry))
        if any(hashlib.sha256(p.read_bytes()).hexdigest()!=digest for p,digest in before.items()):
            result['issues']=['REGISTRY_GUARD_INPUT_CHANGED'];return result
        known_issues={'ALLOWLIST_UNREADABLE_OR_INVALID','ALLOWLIST_EMPTY','ALLOWLIST_NONCANONICAL',
                      'ALLOWLIST_DUPLICATE','ALLOWLIST_NORMALIZED_ALIAS_DUPLICATE',
                      'PUBLIC_REFERENCE_IS_NOT_A_SYNTHETIC_STRAIN','REGISTRY_UNBOUND',
                      'REGISTRY_EMPTY_OR_NO_IDENTITIES','REGISTRY_UNREADABLE_OR_INVALID',
                      'DECLARED_SYNTHETIC_ID_OCCURS_IN_REGISTRY'}
        state=audited.get('state');issues=audited.get('issues');count=audited.get('collision_count')
        if (audited.get('schema')!='sapote.synthetic-registry-audit.v1' or
                state not in {'PASS_BOUND_SNAPSHOT','FAIL','HOLD'} or
                type(issues) is not list or any(type(v) is not str or v not in known_issues for v in issues) or
                type(count) is not int or count<0 or
                (state=='PASS_BOUND_SNAPSHOT' and (issues or count)) or
                (state=='PASS_BOUND_SNAPSHOT' and (audited.get('registry_bound') is not True or
                  audited.get('registry_sha256')!=before[registry])) or
                (state!='PASS_BOUND_SNAPSHOT' and not issues) or
                audited.get('allowlist_sha256')!=before[listing] or
                (audited.get('registry_sha256') is not None and audited['registry_sha256']!=before[registry])):
            result['issues']=['REGISTRY_GUARD_RESULT_CONTRACT_REFUSED'];return result
        result.update(state=audited['state'],registry_sha256=before[registry],
                      allowlist_sha256=before[listing],guard_sha256=before[guard],
                      collision_count=audited.get('collision_count',0),issues=audited.get('issues',[]))
    except Exception:
        result['issues']=['REGISTRY_GUARD_INPUT_OR_CONTRACT_REFUSED']
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--registry',type=Path)
    parser.add_argument('--registry-sha256')
    parser.add_argument('--guard-sha256')
    parser.add_argument('--allowlist-sha256')
    args=parser.parse_args(argv)
    result=audit_export(args.root,args.registry,args.registry_sha256,guard_sha256=args.guard_sha256,allowlist_sha256=args.allowlist_sha256)
    logger=logging.Logger('sapote.export_registry',level=logging.INFO)
    handler=logging.StreamHandler(sys.stderr);handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
    try:logger.info(json.dumps(result,sort_keys=True))
    finally:handler.close()
    return 0 if result['state']=='PASS_BOUND_SNAPSHOT' else 2 if result['state']=='HOLD' else 1


if __name__=='__main__':raise SystemExit(main())
