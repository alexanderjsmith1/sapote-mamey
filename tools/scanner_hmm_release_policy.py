#!/usr/bin/env python3
"""Stage-only export policy for operator-provisioned scanner databases/indexes.

This exact-name policy does not classify arbitrary HMM content or external
runtime provisioning. It never opens model contents or follows directory links.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import os
from pathlib import PurePosixPath
import stat
import sys

SCANNER_HMM_BASENAMES = frozenset({"scanner_pfam.hmm", "scanner_pfam_150.hmm"})
HMMER_INDEX_SUFFIXES = (".h3f", ".h3i", ".h3m", ".h3p")
SCANNER_ASSET_BASENAMES = frozenset(
    name + suffix for name in SCANNER_HMM_BASENAMES
    for suffix in ("",) + HMMER_INDEX_SUFFIXES
)


class ScannerAssetPolicyError(ValueError):
    """The stage could not be completely checked or safely modified."""


def is_provisioned_scanner_asset(relative_path: str) -> bool:
    """Match only the ten reserved basenames, anywhere within a relative stage."""
    path = PurePosixPath(str(relative_path).replace(os.sep, "/"))
    return (not path.is_absolute() and ".." not in path.parts
            and path.name in SCANNER_ASSET_BASENAMES)


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns)


@contextmanager
def _directory(parent_fd, name):
    # No unsafe path fallback: the shell builder supports POSIX platforms.
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise ScannerAssetPolicyError("HMM_EXPORT_NO_SAFE_DIRECTORY_OPEN")
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
    try:
        yield fd
    finally:
        os.close(fd)


def _collect(directory_fd, prefix=()):
    matches = []
    for name in sorted(os.listdir(directory_fd)):
        info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        parts = prefix + (name,)
        reserved = is_provisioned_scanner_asset("/".join(parts))
        if stat.S_ISDIR(info.st_mode):
            if reserved:
                raise ScannerAssetPolicyError("HMM_EXPORT_ASSET_IS_DIRECTORY")
            with _directory(directory_fd, name) as child_fd:
                if _identity(os.fstat(child_fd)) != _identity(info):
                    raise ScannerAssetPolicyError("HMM_EXPORT_DIRECTORY_CHANGED")
                matches.extend(_collect(child_fd, parts))
        elif reserved:
            if not (stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)):
                raise ScannerAssetPolicyError("HMM_EXPORT_ASSET_KIND_UNSUPPORTED")
            matches.append((parts, _identity(info)))
        # Unrelated links are not followed; the archive finalizer still owns
        # whether such an object can be included in the final transaction.
    return matches


def _unlink(directory_fd, parts, expected):
    if len(parts) > 1:
        with _directory(directory_fd, parts[0]) as child_fd:
            _unlink(child_fd, parts[1:], expected)
        return
    info = os.stat(parts[0], dir_fd=directory_fd, follow_symlinks=False)
    if _identity(info) != expected:
        raise ScannerAssetPolicyError("HMM_EXPORT_ASSET_CHANGED")
    os.unlink(parts[0], dir_fd=directory_fd)


def _stage_operation(stage_root, *, remove):
    try:
        with _directory(None, os.fspath(stage_root)) as root_fd:
            # Complete classification before deleting anything: an unreadable
            # subtree or wrongly typed asset cannot become a partial clean pass.
            matches = _collect(root_fd)
            if not remove and matches:
                raise ScannerAssetPolicyError("HMM_EXPORT_RESERVED_ASSET_REMAINS")
            if remove:
                for parts, expected in matches:
                    _unlink(root_fd, parts, expected)
                if _collect(root_fd):
                    raise ScannerAssetPolicyError("HMM_EXPORT_ASSET_REINTRODUCED")
            return len(matches)
    except OSError as exc:
        raise ScannerAssetPolicyError("HMM_EXPORT_SCAN_OR_REMOVAL_FAILED") from exc


def strip_stage_assets(stage_root) -> int:
    """Remove reserved leaves from an explicitly disposable stage; return count."""
    return _stage_operation(stage_root, remove=True)


def check_stage_assets(stage_root) -> int:
    """Refuse any reserved asset or incomplete walk; never mutate the stage."""
    return _stage_operation(stage_root, remove=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-root", required=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        count = (check_stage_assets if args.check_only else strip_stage_assets)(args.stage_root)
    except ScannerAssetPolicyError as exc:
        # Stable reason codes only: no source paths or model data in receipts.
        sys.stderr.write(f"REFUSED: scanner export policy: {exc}\n")
        return 1
    sys.stdout.write(f"scanner export policy: {'checked' if args.check_only else 'removed'} {count} reserved assets\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
