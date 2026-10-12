"""Bounded native working paths; no subprocess, science, installation or discovery.

A caller owns budgets/watchers and persistent receipts. Native paths are deliberately
ASCII shell-literal-safe because some tools reparse them internally despite argv lists.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile


class NativeWorkspaceRefused(RuntimeError):
    """The native workspace/file ownership contract was not admitted."""


def clean_path(value, *, exists=True, refusal=NativeWorkspaceRefused):
    path = Path(os.path.abspath(value))
    if '..' in Path(value).parts:
        raise refusal('parent traversal is not admitted')
    for part in [*reversed(path.parents), path]:
        if part.is_symlink():
            raise refusal('symlink/ancestor aliases are not admitted')
    if exists and not path.exists():
        raise refusal('required path is missing')
    return path


def shell_safe_path(value, *, refusal=NativeWorkspaceRefused):
    path = clean_path(value, refusal=refusal)
    if not re.fullmatch(r'[A-Za-z0-9_./-]+', str(path), flags=re.ASCII):
        raise refusal('native workspace/executable path is not shell-safe')
    return path


def digest(value, *, ceiling=None, refusal=NativeWorkspaceRefused):
    path = clean_path(value, refusal=refusal)
    if not stat.S_ISREG(path.stat().st_mode):
        raise refusal('expected a regular file')
    if ceiling is not None and (type(ceiling) is not int or ceiling < 0):
        raise refusal('finite nonnegative digest ceiling required')
    if ceiling is not None and path.stat().st_size > ceiling:
        raise refusal('native copy exceeds admitted byte ceiling')
    h = hashlib.sha256(); consumed = 0
    with path.open('rb') as stream:
        while True:
            allowance = 1024 * 1024 if ceiling is None else min(1024 * 1024, ceiling - consumed + 1)
            block = stream.read(allowance)
            if not block: break
            consumed += len(block)
            if ceiling is not None and consumed > ceiling:
                raise refusal('native digest grew beyond admitted byte ceiling')
            h.update(block)
    if path.stat().st_size != consumed:
        raise refusal('native consumed-byte/source size changed')
    return {'path': str(path), 'bytes': consumed, 'sha256': h.hexdigest()}


def bounded_copy(source, destination, ceiling, *, refusal=NativeWorkspaceRefused):
    if type(ceiling) is not int or ceiling < 0:
        raise refusal('finite nonnegative copy ceiling required')
    before = digest(source, ceiling=ceiling, refusal=refusal)
    if before['bytes'] > ceiling:
        raise refusal('native copy exceeds admitted byte ceiling')
    target = clean_path(destination, exists=False, refusal=refusal)
    h = hashlib.sha256(); consumed = 0
    with clean_path(source, refusal=refusal).open('rb') as inp, target.open('xb') as out:
        while True:
            block = inp.read(min(1024 * 1024, ceiling - consumed + 1))
            if not block: break
            consumed += len(block)
            if consumed > ceiling:
                raise refusal('native copy grew beyond admitted byte ceiling')
            h.update(block); out.write(block)
    copied = digest(target, ceiling=ceiling, refusal=refusal)
    if (digest(source, ceiling=ceiling, refusal=refusal) != before or consumed != before['bytes'] or
            h.hexdigest() != before['sha256'] or
            (copied['bytes'], copied['sha256']) != (consumed, h.hexdigest())):
        raise refusal('native consumed-byte/source copy binding changed')
    return {'source': before, 'copy': copied}


def work_root(explicit=None, *, refusal=NativeWorkspaceRefused):
    # Resolve only the documented default alias (/var -> /private/var on macOS).
    # Explicit caller symlinks retain the refusal semantics.
    selected = explicit if explicit is not None else Path(tempfile.gettempdir()).resolve(strict=True)
    root = shell_safe_path(selected, refusal=refusal)
    if not root.is_dir(): raise refusal('native work root must be an existing directory')
    return root


class OwnedWorkspace:
    """Owned fresh child only; coordinator may allocate, worker attach, coordinator clean.

    Identity binding protects routine replacement mistakes; this is not a hostile
    concurrent filesystem sandbox. Persistent diagnostics belong outside this directory.
    """
    def __init__(self, path, device, inode, *, refusal=NativeWorkspaceRefused):
        self.refusal = refusal
        self.path = shell_safe_path(path, refusal=refusal)
        self.device = device; self.inode = inode
        self.validate()

    @classmethod
    def create(cls, root, prefix='mamey-native-', *, refusal=NativeWorkspaceRefused):
        root = work_root(root, refusal=refusal)
        if not re.fullmatch(r'[A-Za-z0-9_-]+', prefix, flags=re.ASCII):
            raise refusal('native prefix must be a safe filename component')
        path = Path(tempfile.mkdtemp(prefix=prefix, dir=root))
        observed = path.stat()
        return cls(path, observed.st_dev, observed.st_ino, refusal=refusal)

    def validate(self):
        path = shell_safe_path(self.path, refusal=self.refusal)
        observed = path.lstat()
        if not path.is_dir() or (observed.st_dev, observed.st_ino) != (self.device, self.inode):
            raise self.refusal('owned native scratch identity changed')
        return path

    def descriptor(self):
        self.validate()
        return {'path': str(self.path), 'device': self.device, 'inode': self.inode}

    def cleanup(self):
        self.validate()
        shutil.rmtree(self.path)
        return 'OWNED_TEMP_REMOVED'
