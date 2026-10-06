#!/usr/bin/env python3
"""Deliver already-verified archive/sidecar bytes with exclusive, no-replace publication.

Flat-file publication cannot commit both names atomically. A sidecar collision after the
archive link is a COMMITTED_HOLD: the archive is retained and the conflicting file is
never removed. Source hashes must be captured before verification, then checked here.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import stat
import tempfile


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def publish_pair(archive, sidecar, outdir, expected_archive, expected_sidecar):
    sources = [Path(archive), Path(sidecar)]
    root = Path(outdir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    names = [p.name for p in sources]
    if len(set(names)) != 2 or names[1] != names[0] + '.sha256':
        raise ValueError('archive/sidecar names disagree')
    expected = [expected_archive, expected_sidecar]
    if any(p.is_symlink() or not p.is_file() or sha(p) != h for p,h in zip(sources, expected)):
        raise ValueError('verified input bytes changed')
    targets = [root / name for name in names]
    if any(p.exists() or p.is_symlink() for p in targets):
        raise FileExistsError('destination already exists')
    owned = Path(tempfile.mkdtemp(prefix='.verified-pair-', dir=root))
    owned_identity = owned.lstat()
    committed = []
    receipt = None
    try:
        for source, name, digest in zip(sources, names, expected):
            target = owned / name
            with source.open('rb') as src, target.open('xb') as dst:
                shutil.copyfileobj(src, dst)
                dst.flush()
                os.fsync(dst.fileno())
            if sha(target) != digest:
                raise ValueError('verified input bytes changed during staging')
        for name, target in zip(names, targets):
            # Hard-link creation fails atomically if a file or dangling symlink exists.
            os.link(owned / name, target)
            committed.append(str(target))
        if any(p.is_symlink() or sha(p) != h for p,h in zip(targets, expected)):
            raise ValueError('published bytes no longer match verified inputs')
        directory_fd = os.open(root, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        receipt = {'status': 'COMMITTED', 'committed': committed, 'sha256': expected}
        return receipt
    except Exception as exc:
        if committed:
            receipt = {'status': 'COMMITTED_HOLD', 'committed': committed,
                       'sha256': expected, 'reason': f'{type(exc).__name__}: {exc}'}
            return receipt
        raise
    finally:
        try:
            current = owned.lstat()
            if (not stat.S_ISDIR(current.st_mode) or
                    (current.st_dev, current.st_ino) != (owned_identity.st_dev, owned_identity.st_ino)):
                raise OSError('private staging directory ownership changed; replacement preserved')
            shutil.rmtree(owned)
        except OSError as cleanup_exc:
            if receipt is not None and committed:
                receipt['status'] = 'COMMITTED_HOLD'
                receipt['cleanup_hold'] = str(owned)
                receipt['cleanup_reason'] = f'{type(cleanup_exc).__name__}: {cleanup_exc}'
            else:
                sys.stderr.write(f"WARN: private staging cleanup failed: {owned}: {type(cleanup_exc).__name__}\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('archive', 'sidecar', 'outdir', 'expected_archive', 'expected_sidecar'):
        parser.add_argument(arg)
    args = parser.parse_args(argv)
    try:
        result = publish_pair(**vars(args))
    except Exception as exc:
        sys.stderr.write(json.dumps({'status': 'REFUSED', 'committed': [], 'reason': f'{type(exc).__name__}: {exc}'}) + '\n')
        return 2
    sys.stdout.write(json.dumps(result, sort_keys=True) + '\n')
    return 0 if result['status'] == 'COMMITTED' else 2

if __name__ == '__main__':
    raise SystemExit(main())
