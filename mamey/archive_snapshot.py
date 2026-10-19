"""Explicit bounded, immutable in-memory archive transaction prototype.

No disk staging, discovery, network or scientific-data selection. Each ZIP reader
opens a fresh view of exactly the bytes whose digest is recorded. Capture is not
an atomic filesystem snapshot: require an independent expected SHA256 to admit a
particular source version under concurrent mutation. Strict completeness covers
GenBank members only; JSON/TXT scientific evidence remains best effort.
"""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import hashlib
import io
from pathlib import Path
import re
import stat
import struct
import zlib
import zipfile
import weakref


class ArchiveSnapshotRefused(ValueError):
    def __init__(self, code, receipt=None):
        super().__init__(code)
        self.receipt = receipt


@dataclass(frozen=True)
class ArchiveSnapshotPolicy:
    max_archive_bytes: int
    max_members: int
    max_total_uncompressed_bytes: int

    def validate(self):
        for value in (self.max_archive_bytes, self.max_members, self.max_total_uncompressed_bytes):
            if type(value) is not int or value <= 0:
                raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_BUDGET_INVALID")


def _verify_expansion(payload, archive, ceiling):
    """Validate actual stored/deflate streams with bounded output chunks.

    ZipExtFile intentionally stops at the declared file_size. A forged size/CRC
    of a valid prefix can hide trailing records, so strict completeness cannot
    rely on that stop alone. Other compression methods are explicitly held.
    """
    total = 0
    for info in archive.infolist():
        if info.flag_bits & 1:
            raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_ENCRYPTED_MEMBER_REFUSED")
        if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_COMPRESSION_UNSUPPORTED")
        # Let ZipFile validate member names, overlaps and local-header shape.
        with archive.open(info):
            pass
        offset = info.header_offset
        if offset < 0 or payload[offset:offset+4] != b"PK\x03\x04" or offset+30 > len(payload):
            raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_MEMBER_LAYOUT_INVALID")
        name_len, extra_len = struct.unpack_from("<HH", payload, offset+26)
        begin = offset+30+name_len+extra_len
        end = begin+info.compress_size
        if end > len(payload) or end < begin:
            raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_MEMBER_LAYOUT_INVALID")
        consumed = crc = 0
        decoder = zlib.decompressobj(-15) if info.compress_type == zipfile.ZIP_DEFLATED else None
        for position in range(begin, end, 64*1024):
            chunk_end = min(position+64*1024, end)
            chunk = payload[position:chunk_end]
            while chunk:
                allowance = min(64*1024, info.file_size-consumed+1, ceiling-total+1)
                block = decoder.decompress(chunk, allowance) if decoder else chunk
                consumed += len(block); total += len(block)
                if consumed > info.file_size or total > ceiling:
                    raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_EXPANSION_MISMATCH")
                crc = zlib.crc32(block, crc)
                if decoder:
                    if decoder.eof and (decoder.unused_data or chunk_end < end):
                        raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_COMPRESSED_TRAILING_DATA")
                    chunk = decoder.unconsumed_tail
                else:
                    chunk = b""
        if ((decoder and not decoder.eof) or consumed != info.file_size or crc != info.CRC):
            raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_EXPANSION_MISMATCH")
    return total


_CAPTURED_ARCHIVES = weakref.WeakSet()


@dataclass(frozen=True, eq=False)
class ArchiveSnapshot:
    _payload: bytes
    label: str
    input_sha256: str
    member_count: int
    declared_uncompressed_bytes: int
    verified_uncompressed_bytes: int | None = None
    capture_policy: ArchiveSnapshotPolicy | None = None
    expected_sha256: str | None = None

    def __post_init__(self):
        if (type(self._payload) is not bytes or not isinstance(self.label, str)
                or hashlib.sha256(self._payload).hexdigest() != self.input_sha256):
            raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_OBJECT_BINDING_INVALID")

    def __deepcopy__(self, memo):
        # The payload/policy are immutable; preserve capability identity.
        return self

    @classmethod
    def capture(cls, source, *, policy, expected_sha256=None):
        if not isinstance(policy, ArchiveSnapshotPolicy):
            raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_POLICY_REQUIRED")
        policy.validate()
        if expected_sha256 is not None and (not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)):
            raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_EXPECTED_HASH_INVALID")
        path = Path(source)
        if any(part.is_symlink() for part in (path, *path.parents)):
            raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_PATH_REFUSED")
        try:
            if not stat.S_ISREG(path.stat().st_mode) or path.stat().st_size > policy.max_archive_bytes:
                raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_INPUT_REFUSED")
            with path.open("rb") as stream:
                # Read cap+1, rather than trust pre-stat or source size stability.
                payload = stream.read(policy.max_archive_bytes + 1)
        except OSError as exc:
            raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_INPUT_UNREADABLE") from exc
        if len(payload) > policy.max_archive_bytes:
            raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_BYTE_BUDGET_EXCEEDED")
        digest = hashlib.sha256(payload).hexdigest()
        if expected_sha256 is not None and digest != expected_sha256:
            raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_HASH_MISMATCH")
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                infos = archive.infolist()
                total = sum(info.file_size for info in infos)
                if (len(infos) > policy.max_members or total > policy.max_total_uncompressed_bytes
                        or any(info.file_size < 0 for info in infos)):
                    raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_MEMBER_BUDGET_EXCEEDED")
                verified = _verify_expansion(payload, archive, policy.max_total_uncompressed_bytes)
        except (OSError, zipfile.BadZipFile, zlib.error) as exc:
            raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_ZIP_INVALID") from exc
        snapshot = cls(payload, path.name, digest, len(infos), total, verified, policy, expected_sha256)
        _CAPTURED_ARCHIVES.add(snapshot)
        return snapshot

    def __str__(self):
        return self.label


def validate_captured(snapshot, *, policy, expected_sha256=None):
    """Admit an existing process-local capture under explicit policy, with no I/O.

    Current bytes must fit both the original capture and supplied admission
    policies. A new matching expected digest is an explicit caller assertion;
    a consumed digest is never inferred to be independently expected.
    """
    if not isinstance(snapshot, ArchiveSnapshot) or snapshot not in _CAPTURED_ARCHIVES:
        raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_NOT_CAPTURED_IN_PROCESS")
    if not isinstance(policy, ArchiveSnapshotPolicy):
        raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_POLICY_REQUIRED")
    policy.validate()
    original = snapshot.capture_policy
    if not isinstance(original, ArchiveSnapshotPolicy):
        raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_ORIGINAL_POLICY_UNAVAILABLE")
    original.validate()
    for admitted in (original, policy):
        if (len(snapshot._payload) > admitted.max_archive_bytes or snapshot.member_count > admitted.max_members
                or type(snapshot.verified_uncompressed_bytes) is not int
                or snapshot.verified_uncompressed_bytes != snapshot.declared_uncompressed_bytes
                or snapshot.verified_uncompressed_bytes > admitted.max_total_uncompressed_bytes):
            raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_POLICY_MISMATCH")
    expected = snapshot.expected_sha256 if expected_sha256 is None else expected_sha256
    if expected is not None:
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_EXPECTED_HASH_INVALID")
        if snapshot.input_sha256 != expected:
            raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_HASH_MISMATCH")
    return {"input_sha256": snapshot.input_sha256, "archive_bytes": len(snapshot._payload),
            "member_count": snapshot.member_count,
            "declared_uncompressed_bytes": snapshot.declared_uncompressed_bytes,
            "verified_uncompressed_bytes": snapshot.verified_uncompressed_bytes,
            "capture_policy": asdict(original), "admission_policy": asdict(policy),
            "expected_digest_bound": expected is not None,
            "original_version": "EXPECTED_DIGEST_MATCHED" if expected is not None else "ORIGINAL_VERSION_UNASSERTED",
            # Keep the earlier prototype's scope spelling as an explicit alias.
            "source_version_scope": "EXPECTED_DIGEST_MATCHED" if expected is not None else "CONSUMED_BYTES_ONLY",
            "capture_scope": "immutable consumed bytes; not atomic original-path capture",
            "resource_scope": "input/actual-expansion bounds; not a peak-heap or whole-parse CPU quota"}


@contextmanager
def captured_zip(snapshot, *, policy, expected_sha256=None):
    """Fresh same-capture ZIP reader; never accepts a locator or recaptures."""
    validate_captured(snapshot, policy=policy, expected_sha256=expected_sha256)
    with snapshot_zip(snapshot) as archive:
        yield archive


def archive_label_path(source):
    """Filename metadata only; never reopen a captured source through this label."""
    return Path(source.label) if isinstance(source, ArchiveSnapshot) else Path(source)


@contextmanager
def snapshot_zip(source):
    if isinstance(source, ArchiveSnapshot):
        validate_captured(source, policy=source.capture_policy)
        with io.BytesIO(source._payload) as stream:
            with zipfile.ZipFile(stream) as archive:
                yield archive
    else:
        with zipfile.ZipFile(source) as archive:
            yield archive


def parse_captured(snapshot, *, policy, json_mode="off", core_snapshot_out=None,
                   require_complete_genbank=True, parse_operation=None,
                   expected_sha256=None):
    """Parse one existing capture without reopening its label or recapturing.

    `parse_operation` is a trusted03-owned adapter with signature
    `(snapshot, *, json_mode, core_snapshot_out) -> bgcs`. It must validate its
    bound evidence/session, use this exact snapshot and preserve the supplied
    local core mapping. No arbitrary evidence dictionary is accepted here.
    None uses the ordinary parser over this capture and parses evidence there.
    GBK preflight does not run the JSON/TXT evidence extractor. Scientific
    channel completeness and whole-package publication remain caller policy.
    """
    from . import parsers
    if core_snapshot_out is not None and type(core_snapshot_out) is not dict:
        raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_OUTPUT_MUST_BE_PLAIN_DICT")
    if type(require_complete_genbank) is not bool:
        raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_COMPLETENESS_POLICY_INVALID")
    if parse_operation is not None and not callable(parse_operation):
        raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_PARSE_ADAPTER_REQUIRED")
    receipt = {"schema": "sapote.archive-intake-transaction.prototype.v2",
               **validate_captured(snapshot, policy=policy, expected_sha256=expected_sha256),
               "evidence_completeness": "BEST_EFFORT_JSON_TXT_NOT_CERTIFIED",
               "upstream_search_completion": "NOT_ESTABLISHED", "biological_absence": "NOT_ESTABLISHED",
               "state": "PENDING", "genbank": {}}
    operation = parsers.parse_bgcs_from_zip if parse_operation is None else parse_operation
    try:
        from .ziputil import duplicate_member_names, nonregular_file_names, is_macos_metadata_name
        with captured_zip(snapshot, policy=policy) as archive:
            duplicates = [name for name in duplicate_member_names(archive) if not is_macos_metadata_name(name)]
            special = [name for name in nonregular_file_names(archive) if not is_macos_metadata_name(name)]
        receipt["namespace"] = {"duplicate_count": len(duplicates), "nonregular_count": len(special)}
        parsers.read_genbank_records(snapshot, completeness_out=receipt["genbank"])
        if receipt["genbank"].get("input_sha256") != snapshot.input_sha256:
            receipt["state"] = "REFUSED"
            raise ArchiveSnapshotRefused("ARCHIVE_GENBANK_RECEIPT_SOURCE_MISMATCH", receipt)
        members = receipt["genbank"].get("members", [])
        complete = bool(members) and all(row["state"] == "COMPLETE" for row in members)
        receipt["genbank_completeness"] = "COMPLETE_GBK_MEMBERS" if complete else "INCOMPLETE_OR_ABSENT"
        if require_complete_genbank and not complete:
            receipt["state"] = "REFUSED"
            raise ArchiveSnapshotRefused("ARCHIVE_GENBANK_COMPLETENESS_REFUSED", receipt)
        if duplicates or special:
            receipt["state"] = "REFUSED"
            raise ArchiveSnapshotRefused("ARCHIVE_NAMESPACE_AMBIGUOUS_OR_SPECIAL", receipt)
        local = {}
        bgcs = operation(snapshot, json_mode=json_mode, core_snapshot_out=local)
        # The adapter must return a process-sealed core for these consumed bytes.
        parsers._open_region_core_snapshot(local, snapshot.input_sha256)
        receipt["core_records_sha256"] = local["records_sha256"]
        local["archive_intake_receipt"] = receipt
        if core_snapshot_out is not None:
            previous = core_snapshot_out.copy()
            receipt["state"] = "PUBLISHING"
            try:
                core_snapshot_out.clear()
                core_snapshot_out.update(local)
            except BaseException as primary:
                receipt["state"] = "PUBLICATION_FAILED"
                try:
                    core_snapshot_out.clear()
                    core_snapshot_out.update(previous)
                except BaseException as cleanup_error:
                    receipt["caller_mapping_restore"] = "FAILED"
                    primary.add_note("Caller mapping restoration failed: " + type(cleanup_error).__name__)
                else:
                    receipt["caller_mapping_restore"] = "RESTORED"
                raise
        receipt["state"] = "PARSED_SOURCE_BOUND" if complete else "PARSED_INCOMPLETE_EXPLICITLY_ADMITTED"
    except BaseException as primary:
        if receipt["state"] not in {"REFUSED", "PUBLICATION_FAILED"}:
            receipt["state"] = "FAILED"
        primary.archive_snapshot_receipt = receipt
        raise
    return bgcs, receipt


def parse_bgcs_transaction(source, *, policy, expected_sha256=None,
                           json_mode="off", core_snapshot_out=None,
                           require_complete_genbank=True):
    """Capture once then delegate; use parse_captured for an existing capability."""
    if core_snapshot_out is not None and type(core_snapshot_out) is not dict:
        raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_OUTPUT_MUST_BE_PLAIN_DICT")
    if type(require_complete_genbank) is not bool:
        raise ArchiveSnapshotRefused("ARCHIVE_SNAPSHOT_COMPLETENESS_POLICY_INVALID")
    snapshot = ArchiveSnapshot.capture(source, policy=policy, expected_sha256=expected_sha256)
    return parse_captured(snapshot, policy=policy, json_mode=json_mode,
                          core_snapshot_out=core_snapshot_out,
                          require_complete_genbank=require_complete_genbank)
