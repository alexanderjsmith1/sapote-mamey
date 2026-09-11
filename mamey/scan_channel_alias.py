"""scan_channel_alias.py — resolve v9.7.400 source_scans channel-alias stubs.

Four ``manifest.json:source_scans`` sub-objects were embedded as VERBATIM copies of standalone
files already shipped in the same package (measured byte-identical; together ~83-90% of
``source_scans`` — e.g. 18.8 MB of 20.9 MB on a 96-BGC strain):

    rggmci                == {sid}_4A_RGGMCI_full.json
    mibig_per_gene        == {sid}_3_mibig_per_gene.json
    antismash_structured  == {sid}_3_antismash_structured.json
    clusterblast_genes    == {sid}_4A2_ClusterBlast_gene_map.json

The writer now embeds a stub ``{"schema": "source_scan_channel_alias_v1", "alias_of": "<file>"}``
per channel; the standalone files remain the authoritative copies. These helpers serve BOTH
generations: a pre-.400 manifest (full objects embedded) passes through untouched; a stub is
materialized from its file. Fail-open — a missing, malformed, unreadable, or unsafe target
returns the stub itself, never a new exception and never out-of-package evidence. Claim-safety:
packaging mechanics only; no scientific content changes.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path, PurePosixPath
from urllib.parse import quote

__all__ = ["CHANNEL_ALIAS_SCHEMA", "is_channel_stub", "resolve_scan_channel", "resolve_scan_channels",
           "ScanChannelBindingError", "load_bound_scan_manifest"]

CHANNEL_ALIAS_SCHEMA = "source_scan_channel_alias_v1"


class ScanChannelBindingError(ValueError):
    """A source cannot safely support a content-bound observation."""


def is_channel_stub(value) -> bool:
    """True iff *value* is a channel-alias stub (small dict with alias_of, no payload)."""
    return (isinstance(value, dict) and bool(value.get("alias_of"))
            and len(value) <= 3 and "per_gene_best_hit" not in value
            and "ranked_pairs" not in value)


def _validated_alias_target(package_dir, name) -> Path:
    """Return a package-contained, symlink-free alias path or raise a typed refusal."""
    if not isinstance(name, str) or not name:
        raise ScanChannelBindingError('SCAN_ALIAS_INVALID: target must be a non-empty string')
    relative = PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
        raise ScanChannelBindingError('SCAN_ALIAS_UNSAFE: package-relative target required')
    try:
        root = Path(package_dir).resolve()
        target = root.joinpath(*relative.parts)
        current = root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise ScanChannelBindingError('SCAN_ALIAS_UNSAFE: symlinks are not binding sources')
        if not target.resolve().is_relative_to(root):
            raise ScanChannelBindingError('SCAN_ALIAS_UNSAFE: target escapes package')
    except ScanChannelBindingError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise ScanChannelBindingError('SCAN_ALIAS_UNSAFE: target cannot be resolved') from exc
    return target


def resolve_scan_channel(scans, key: str, package_dir):
    """Return ``scans[key]``, materializing a channel-alias stub from its standalone file."""
    value = (scans or {}).get(key)
    if not is_channel_stub(value):
        return value if value is not None else {}
    try:
        target = _validated_alias_target(package_dir, value["alias_of"])
        if target.is_file():
            with open(target, encoding="utf-8") as fh:
                payload = json.load(fh)
            return payload if isinstance(payload, dict) else value
    except (OSError, UnicodeError, json.JSONDecodeError, ScanChannelBindingError):
        return value
    return value


def resolve_scan_channels(manifest: dict, package_dir) -> dict:
    """Materialize every stubbed channel in ``manifest['source_scans']`` IN PLACE; returns manifest."""
    scans = (manifest or {}).get("source_scans")
    if isinstance(scans, dict):
        for key, value in list(scans.items()):
            if is_channel_stub(value):
                scans[key] = resolve_scan_channel(scans, key, package_dir)
    return manifest


def load_bound_scan_manifest(manifest_path):
    """Read payloads and hash the exact bytes parsed, with per-channel provenance.

    Unlike the compatibility resolvers above, this opt-in binding path refuses
    broken/unsafe aliases. It never converts an unresolved stub into evidence.
    Returns (materialized_manifest, channel_sources, manifest_sha256).
    """
    path = Path(manifest_path)
    root = path.parent.resolve()

    def read_object(source):
        if source.is_symlink() or not source.is_file():
            raise ScanChannelBindingError('SCAN_SOURCE_UNREADABLE: regular file required')
        try:
            raw = source.read_bytes()
            value = json.loads(raw)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ScanChannelBindingError('SCAN_SOURCE_UNREADABLE: ' + type(exc).__name__) from exc
        if not isinstance(value, dict):
            raise ScanChannelBindingError('SCAN_SOURCE_TYPE: object required')
        return value, hashlib.sha256(raw).hexdigest()

    manifest, manifest_sha = read_object(path)
    scans = manifest.get('source_scans')
    if scans is None:
        return manifest, {}, manifest_sha
    if not isinstance(scans, dict):
        raise ScanChannelBindingError('SCAN_SOURCE_TYPE: source_scans must be an object or null')
    sources = {}
    for key, value in list(scans.items()):
        if not isinstance(key, str):
            raise ScanChannelBindingError('SCAN_SOURCE_TYPE: channel key must be a string')
        source = {'locator': 'package://' + quote(path.name), 'sha256': manifest_sha,
                  'pointer': '/source_scans/' + quote(key, safe='')}
        if isinstance(value, dict) and ('alias_of' in value or value.get('schema') == CHANNEL_ALIAS_SCHEMA):
            name = value.get('alias_of')
            if (value.get('schema') != CHANNEL_ALIAS_SCHEMA or not isinstance(name, str) or not name
                    or set(value) - {'schema', 'alias_of'}):
                raise ScanChannelBindingError('SCAN_ALIAS_INVALID: schema and target required')
            relative = PurePosixPath(name)
            target = _validated_alias_target(root, name)
            payload, digest = read_object(target)
            if 'alias_of' in payload or payload.get('schema') == CHANNEL_ALIAS_SCHEMA:
                raise ScanChannelBindingError('SCAN_ALIAS_INVALID: recursive alias refused')
            scans[key] = payload
            source = {'locator': 'package://' + quote(relative.as_posix()),
                      'sha256': digest, 'pointer': ''}
        sources[key] = source
    return manifest, sources, manifest_sha
