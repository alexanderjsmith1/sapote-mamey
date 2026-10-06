"""Immutable reader-output routes and exact source-archive admission.

These helpers never amend package manifests, checksums or seals. They resolve
symlinks at admission; they do not claim containment against concurrent races.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def output_directory(package, command, explicit=None):
    """Return an external output path without creating it.

    Default: <package.parent>/post_seal/<command>. Explicit paths and existing
    symlinks must resolve outside the entire package. This applies even to
    fixtures/pre-seal reader inputs; run-time package assembly uses separate APIs.
    """
    pkg = Path(package).expanduser().resolve()
    if not pkg.is_dir():
        raise ValueError(f'POSTSEAL_PACKAGE_UNAVAILABLE: {pkg}')
    if not re.fullmatch(r'[a-z][a-z0-9_-]*', command):
        raise ValueError('POSTSEAL_COMMAND_INVALID')
    target = (Path(explicit).expanduser() if explicit is not None else
              pkg.parent / 'post_seal' / command).resolve()
    if target == pkg or pkg in target.parents:
        raise ValueError('POSTSEAL_OUTPUT_INSIDE_PACKAGE: choose an external sibling directory')
    if target.is_dir() and any(path.is_symlink() for path in target.rglob('*')):
        raise ValueError('POSTSEAL_OUTPUT_SYMLINK: choose a regular external output tree')
    return target


def output_file(package, command, filename, explicit=None):
    """Admit an external file, including its resolved existing symlink target."""
    if explicit is None:
        if Path(filename).name != filename or filename in ('', '.', '..'):
            raise ValueError('POSTSEAL_FILENAME_INVALID')
        target = output_directory(package, command) / filename
    else:
        target = Path(explicit).expanduser()
    output_directory(package, command, target)
    return target.resolve()


def package_binding(package):
    """Bind every original package file byte; symlinks are refused for snapshots."""
    pkg = Path(package).resolve()
    files = {}
    for path in sorted(pkg.rglob('*')):
        if path.is_symlink():
            raise ValueError('POSTSEAL_PACKAGE_SYMLINK: immutable reader snapshots require regular files')
        if path.is_file():
            files[path.relative_to(pkg).as_posix()] = sha256_file(path)
    digest = hashlib.sha256(''.join(f'{rel}\t{value}\n' for rel, value in files.items()).encode()).hexdigest()
    return {'package':str(pkg),'files_sha256':files,'package_tree_sha256':digest}


def resolve_source_archive(package, explicit=None):
    """Resolve one declared antiSMASH archive and require its package-bound SHA.

    No recursive workspace discovery or first-match fallback. A moved source can
    be supplied explicitly; it still must match input_zip_sha256 in manifest.
    """
    pkg = Path(package).resolve()
    manifest = pkg / 'manifest.json'
    payload = json.loads(manifest.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        raise ValueError('SOURCE_MANIFEST_NOT_OBJECT')
    expected = payload.get('input_zip_sha256')
    if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', expected):
        raise ValueError('SOURCE_ARCHIVE_DIGEST_UNBOUND: manifest input_zip_sha256 is required')
    if explicit is not None:
        candidates = [Path(explicit).expanduser().resolve()]
    else:
        locator = payload.get('input_zip')
        if not isinstance(locator, str) or not locator.strip():
            raise ValueError('SOURCE_ARCHIVE_LOCATOR_MISSING: pass --source-zip with the original antiSMASH ZIP')
        loc = Path(locator).expanduser()
        if loc.is_absolute():
            candidates = [loc.resolve()]
        else:
            candidates = [(base / loc).resolve() for base in (pkg, pkg.parent, pkg.parent.parent)]
    found = sorted({path for path in candidates if path.is_file()})
    if len(found) != 1:
        raise ValueError('SOURCE_ARCHIVE_AMBIGUOUS' if len(found) > 1 else
                         'SOURCE_ARCHIVE_UNAVAILABLE: pass --source-zip with the original antiSMASH ZIP')
    path = found[0]
    observed = sha256_file(path)
    if observed != expected.lower():
        raise ValueError('SOURCE_ARCHIVE_DIGEST_MISMATCH')
    return path, {'path':str(path),'sha256':observed,'manifest_sha256':sha256_file(manifest),
                  'state':'ARCHIVE_HASH_VERIFIED'}


def current_compiled_report(package):
    """Read the default external report only with a current byte-bound receipt.

    Return None when no external report exists. An unbound/stale report is a
    refusal, so a reader never silently falls back to an older in-package copy.
    """
    pkg = Path(package).resolve()
    payload = json.loads((pkg / 'manifest.json').read_text())
    strain = payload.get('strain_id')
    if not isinstance(strain, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', strain):
        raise ValueError('POSTSEAL_REPORT_STRAIN_INVALID')
    report = output_file(pkg, 'compile-report', f'{strain}_compiled_report.md')
    if not report.is_file():
        return None
    receipt_path = report.with_suffix('.source_receipt.json')
    if not receipt_path.is_file():
        raise ValueError('POSTSEAL_REPORT_RECEIPT_MISSING')
    receipt = json.loads(receipt_path.read_text())
    if (receipt.get('schema') != 'sapote.postseal-report.v1' or receipt.get('status') != 'WRITTEN' or
            receipt.get('source') != package_binding(pkg) or receipt.get('source_unchanged') is not True or
            receipt.get('report') != str(report) or receipt.get('report_sha256') != sha256_file(report)):
        raise ValueError('POSTSEAL_REPORT_BINDING_STALE_OR_INVALID')
    return report
