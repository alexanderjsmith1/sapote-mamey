#!/usr/bin/env python3
"""Experimental audit-side controlled invocation; not integrated into the bundle."""
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

from gate_snapshot_contract import compare

GATE_SHA256 = '6f9e63af2e96ddfad31aba78136b22b3d8263de0c7b5df6900f7c6097cd52e1c'
WRAPPER_SHA256 = 'ed02dc55052579f3ab62f778694f2f321037a05e26b0cd49eb9e4b789cd064c5'
WRAPPER = Path(__file__).resolve().parent / 'gate_structured_snapshot.py'


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def invoke(tree, gate, audited_tree_sha256, outgroups, timeout=30):
    """Invoke the fixed candidate with tree-only gate arguments; never approve."""
    try:
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('timeout must be finite and positive')
        tree, gate = Path(tree).resolve(strict=True), Path(gate).resolve(strict=True)
        if _sha(tree) != audited_tree_sha256:
            raise ValueError('tree does not match audited hash before invocation')
        if _sha(gate) != GATE_SHA256 or _sha(WRAPPER) != WRAPPER_SHA256:
            raise ValueError('unsupported gate or wrapper bytes')
        cmd = [sys.executable, str(WRAPPER), '--tree', str(tree), '--gate', str(gate)]
        result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if _sha(tree) != audited_tree_sha256 or _sha(gate) != GATE_SHA256 or _sha(WRAPPER) != WRAPPER_SHA256:
            raise ValueError('tree, gate or wrapper changed during invocation')
        check = compare(result.stdout, tree_sha256=audited_tree_sha256, gate_sha256=GATE_SHA256,
                        declared_outgroups=outgroups, expected_arguments=[])
        if check['status'] == 'ERROR':
            raise ValueError('structured result refused: ' + check['reason'])
        # Exit 0 means observed native pass; exit 2 may mean native fail or
        # wrapper error. Require the stdout contract to disambiguate those.
        record = json.loads(result.stdout)
        expected_exit = 0 if record.get('status') == 'OBSERVED' and record.get('gate_pass') is True else 2
        if result.returncode != expected_exit or result.returncode not in (0, 2):
            raise ValueError('process exit and result disagree')
        return {'status': check['status'], 'comparison': check,
                'tree_sha256': audited_tree_sha256, 'gate_sha256': GATE_SHA256,
                'wrapper_sha256': WRAPPER_SHA256, 'stdout_sha256': hashlib.sha256(result.stdout).hexdigest(),
                'exit_code': result.returncode, 'stderr': result.stderr.decode('utf-8', errors='replace'),
                'scope': 'Experimental controlled child process; HOLD is not scientific acceptance. The interpreter and imported dependencies are trusted and unpinned. Before/after path hashes do not prevent ABA or in-read races.'}
    except (OSError, ValueError, TypeError, UnicodeError, subprocess.TimeoutExpired) as exc:
        return {'status': 'ERROR', 'reason': str(exc)}
