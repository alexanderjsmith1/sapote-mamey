#!/usr/bin/env python3
"""Run the canonical complete pytest profile and bind its receipt to candidate bytes.

Receipts protect against accidental stale approvals, not a hostile writer who can
replace this checker or forge a receipt. The package lookup policy is separate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SCHEMA = 'sapote.full-suite-receipt.v2'
# Keep aligned with release_cut.sh and verify_external_validation_receipt.py.
COMMAND_TAIL = ['-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--run-slow', '--run-network']
MARKER = '_CANDIDATE_NOTES/.fullsuite_green'
LOG = '_CANDIDATE_NOTES/.fullsuite.log'
IGNORE_DIRS = {'__pycache__', '.pytest_cache', '.git'}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tree_hash(root: Path) -> str:
    """Hash names, kinds and bytes; exclude only receipts and runtime metadata.

    In-tree symlinks bind their literal target and its separately inventoried
    contents. External/dangling links, directory symlinks, links to excluded
    content and special files refuse certification. File modes are also bound.
    """
    root = root.resolve(strict=True)
    entries = []
    def traversal_error(error):
        raise error
    for directory, names, files in os.walk(root, followlinks=False, onerror=traversal_error):
        names[:] = sorted(n for n in names if n not in IGNORE_DIRS)
        base = Path(directory)
        for name in sorted(names + files):
            path = base / name
            rel = path.relative_to(root).as_posix()
            if rel in {MARKER, LOG} or name == '.DS_Store' or name.endswith('.pyc'):
                continue
            if path.is_symlink():
                resolved = path.resolve(strict=True)
                if not resolved.is_relative_to(root):
                    raise ValueError('external symlink cannot be certified: ' + rel)
                target = resolved.relative_to(root)
                if (resolved.is_dir() or any(part in IGNORE_DIRS for part in target.parts) or
                        target.as_posix() in {MARKER, LOG} or target.name == '.DS_Store' or
                        target.suffix == '.pyc'):
                    raise ValueError('symlink target is excluded or a directory: ' + rel)
                kind, content = 'link', os.readlink(path).encode()
            elif path.is_file():
                kind, content = 'file', path.read_bytes()
            elif path.is_dir():
                # Directory names matter, including empty fixture directories.
                kind, content = 'directory', b''
            else:
                raise ValueError('special file cannot be certified: ' + rel)
            entries.append([rel, kind, path.lstat().st_mode & 0o777, sha(content)])
    return sha(json.dumps(sorted(entries), ensure_ascii=True,
                          separators=(',', ':')).encode())


def notes_path(root: Path, relative: str) -> Path:
    path = root / relative
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError('receipt paths must not be symlinks')
    if path.exists() and not path.is_file():
        raise ValueError('receipt destination is not a file')
    return path


def check(root: Path) -> dict:
    root = root.resolve(strict=True)
    marker = notes_path(root, MARKER)
    log = notes_path(root, LOG)
    receipt = json.loads(marker.read_text())
    if not isinstance(receipt, dict) or receipt.get('schema') != SCHEMA:
        raise ValueError('missing source-bound configured-suite receipt')
    command = receipt.get('command')
    if (not isinstance(command, list) or len(command) != len(COMMAND_TAIL) + 1 or
            not isinstance(command[0], str) or not command[0] or
            command[1:] != COMMAND_TAIL):
        raise ValueError('receipt is not for the exact canonical complete pytest profile')
    if receipt.get('cwd') != str(root):
        raise ValueError('receipt belongs to another candidate path')
    if receipt.get('exit_code') != 0 or type(receipt.get('exit_code')) is not int:
        raise ValueError('configured suite did not exit successfully')
    if receipt.get('pytest_addopts') != '' or receipt.get('pytest_plugins') != '':
        raise ValueError('receipt used external pytest command/plugin overrides')
    if (receipt.get('python_dont_write_bytecode') != '1' or
            receipt.get('pythonpath') != '.'):
        raise ValueError('receipt lacks canonical child environment binding')
    if receipt.get('log_sha256') != sha(log.read_bytes()):
        raise ValueError('configured-suite log changed')
    actual = tree_hash(root)
    if receipt.get('tree_before') != actual or receipt.get('tree_after') != actual:
        raise ValueError('candidate bytes changed or suite modified its inputs')
    return receipt


def atomic_json(path: Path, value: dict) -> None:
    # Temporary file lives outside the inventoried tree and is copied atomically
    # via a sibling temporary file only after the final hash has been measured.
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent,
                                     prefix='.receipt-', delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, indent=2)
        handle.write('\n')
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def run(root: Path) -> int:
    root = root.resolve(strict=True)
    marker, log = notes_path(root, MARKER), notes_path(root, LOG)
    # No previous success may survive a failed or interrupted rerun.
    marker.unlink(missing_ok=True)
    if os.environ.get('PYTEST_ADDOPTS') or os.environ.get('PYTEST_PLUGINS'):
        raise ValueError('unset PYTEST_ADDOPTS and PYTEST_PLUGINS before recording')
    marker.parent.mkdir(exist_ok=True)
    before = tree_hash(root)
    command = [sys.executable, *COMMAND_TAIL]
    child_env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': '.'}
    with log.open('wb') as output:
        result = subprocess.run(command, cwd=root, stdout=output,
                                stderr=subprocess.STDOUT, env=child_env)
    after = tree_hash(root)
    receipt = {'schema': SCHEMA, 'command': command, 'cwd': str(root),
               'exit_code': result.returncode, 'tree_before': before,
               'tree_after': after, 'log_sha256': sha(log.read_bytes()),
               'pytest_addopts': '', 'pytest_plugins': '',
               'python_dont_write_bytecode': '1', 'pythonpath': '.'}
    if result.returncode != 0:
        print('Suite failed; no green receipt written. Log: ' + str(log), file=sys.stderr)
        return result.returncode if result.returncode > 0 else 1
    if before != after:
        raise ValueError('suite changed inventoried candidate bytes; no green receipt written')
    atomic_json(marker, receipt)
    check(root)
    print('Configured suite receipt written: ' + str(marker))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['run', 'check'])
    parser.add_argument('--candidate', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == 'run':
            return run(args.candidate)
        check(args.candidate)
        print('Source-bound configured-suite receipt matches candidate.')
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print('Full-suite receipt refused: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
