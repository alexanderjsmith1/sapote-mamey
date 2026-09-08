#!/usr/bin/env python3
"""Fail-closed, no-replace final archive transaction."""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import sys
import tempfile
import unicodedata
import zipfile
import zlib
from dataclasses import dataclass
from typing import Callable, Iterable


class ArchiveTransactionError(RuntimeError):
    def __init__(self, code: str, reason: str, *, committed: bool = False) -> None:
        self.code, self.reason, self.committed = code, reason, committed
        super().__init__(f"{code}: {reason}")


@dataclass(frozen=True)
class Member:
    name: str
    kind: str
    size: int
    sha256: str
    mode: int


@dataclass(frozen=True)
class StageRootBinding:
    supplied: Path
    resolved: Path
    device: int
    inode: int


@dataclass(frozen=True)
class ArchiveReceipt:
    status: str
    error_code: str | None
    reason_code: str | None
    final_name: str
    member_count: int
    archive_sha256: str | None
    archive_bytes: int | None
    cleanup_state: str

    def as_json(self) -> str:
        return json.dumps(self.__dict__, sort_keys=True, separators=(",", ":"))


_ZIP_EPOCH = (1980, 1, 2, 0, 0, 0)   # v9.7.409 (BC hostile audit H7): 1980-01-01 00:00 lands before 1980 in any western timezone once extracted, and Python's zipfile then refuses to re-archive the files (strict_timestamps); one day later is safe everywhere
_REGULAR_ATTR = (stat.S_IFREG | 0o644) << 16
_DIRECTORY_ATTR = ((stat.S_IFDIR | 0o755) << 16) | 0x10


def _fail(code: str, reason: str, *, committed: bool = False) -> None:
    raise ArchiveTransactionError(code, reason, committed=committed)


def _canonical_basename(value: str, *, allow_hidden: bool = False) -> str:
    if (not isinstance(value, str) or not value or value in {".", ".."} or
            any(token in value for token in ("/", "\\", "\x00", ":")) or
            os.path.basename(value) != value or value.startswith(" ") or
            (not allow_hidden and value.startswith("."))):
        _fail("ARCHTXN-ARG-001", "noncanonical_basename")
    return value


def _sha_path(path: Path) -> tuple[int, str]:
    digest, total = hashlib.sha256(), 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            total += len(block)
            digest.update(block)
    return total, digest.hexdigest()


def _stage_root_stat(path: Path) -> os.stat_result:
    try:
        state = path.lstat()
    except OSError:
        _fail("ARCHTXN-STAGE-001", "stage_root_unavailable")
    if stat.S_ISLNK(state.st_mode):
        _fail("ARCHTXN-STAGE-001", "stage_root_symlink")
    if not stat.S_ISDIR(state.st_mode):
        _fail("ARCHTXN-STAGE-001", "stage_root_not_directory")
    return state


def _bind_stage_root(stage_root: Path) -> StageRootBinding:
    supplied = Path(stage_root)
    supplied_state = _stage_root_stat(supplied)
    try:
        resolved = supplied.resolve(strict=True)
    except OSError:
        _fail("ARCHTXN-STAGE-001", "stage_root_unavailable")
    resolved_state = _stage_root_stat(resolved)
    identity = (supplied_state.st_dev, supplied_state.st_ino)
    if (resolved_state.st_dev, resolved_state.st_ino) != identity:
        _fail("ARCHTXN-STAGE-001", "stage_root_identity_ambiguous")
    return StageRootBinding(supplied, resolved, *identity)


def _assert_stage_root_identity(binding: StageRootBinding) -> None:
    supplied_state = _stage_root_stat(binding.supplied)
    resolved_state = _stage_root_stat(binding.resolved)
    expected = (binding.device, binding.inode)
    if ((supplied_state.st_dev, supplied_state.st_ino) != expected or
            (resolved_state.st_dev, resolved_state.st_ino) != expected):
        _fail("ARCHTXN-STAGE-006", "stage_root_identity_changed")


def _safe_name(name: str) -> str:
    if not name or name.startswith(("/", "\\")) or "\\" in name or "\x00" in name:
        _fail("ARCHTXN-PATH-003" if name.startswith(("/", "\\")) else "ARCHTXN-PATH-001", "unsafe_member_name")
    if len(name) > 1 and name[1] == ":":
        _fail("ARCHTXN-PATH-003", "drive_member_name")
    if any(part in {"", ".", ".."} for part in name.split("/")):
        _fail("ARCHTXN-PATH-005", "traversal_or_empty_member")
    if unicodedata.normalize("NFC", name) != name:
        _fail("ARCHTXN-ZIP-012", "noncanonical_unicode_member")
    return name


def _inventory_bound_stage(binding: StageRootBinding) -> list[Member]:
    _assert_stage_root_identity(binding)
    root = binding.resolved
    rows: list[Member] = []
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        for entry in list(dirs):
            candidate, mode = current_path / entry, (current_path / entry).lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                _fail("ARCHTXN-STAGE-001", "stage_non_directory_or_symlink")
            rows.append(Member(_safe_name(candidate.relative_to(root).as_posix()) + "/", "DIRECTORY_NO_CONTENT", 0, "", stat.S_IMODE(mode)))
        for entry in files:
            candidate, mode = current_path / entry, (current_path / entry).lstat().st_mode
            if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
                _fail("ARCHTXN-STAGE-001", "stage_nonregular_member")
            size, digest = _sha_path(candidate)
            rows.append(Member(_safe_name(candidate.relative_to(root).as_posix()), "REGULAR_FILE", size, digest, stat.S_IMODE(mode)))
    if len({row.name for row in rows}) != len(rows):
        _fail("ARCHTXN-STAGE-006", "duplicate_stage_member")
    _assert_stage_root_identity(binding)
    return sorted(rows, key=lambda row: row.name.encode("utf-8"))


def inventory_stage(stage_root: Path) -> list[Member]:
    return _inventory_bound_stage(_bind_stage_root(stage_root))


def _assert_stage_unchanged(binding: StageRootBinding, prior: list[Member]) -> None:
    if _inventory_bound_stage(binding) != prior:
        _fail("ARCHTXN-STAGE-006", "stage_changed_after_audit")


def _write_archive(binding: StageRootBinding, destination: Path, rows: list[Member]) -> None:
    _assert_stage_root_identity(binding)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, strict_timestamps=True) as archive:
        archive.comment = b""
        for row in rows:
            info = zipfile.ZipInfo(row.name, date_time=_ZIP_EPOCH)
            info.create_system = 3
            info.flag_bits = 0x800 if any(ord(char) > 127 for char in row.name) else 0
            if row.kind == "DIRECTORY_NO_CONTENT":
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = _DIRECTORY_ATTR
                archive.writestr(info, b"")
            else:
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = _REGULAR_ATTR
                archive.writestr(info, (binding.resolved / row.name).read_bytes())
    _assert_stage_root_identity(binding)


def _classify_zip_member(info: zipfile.ZipInfo) -> tuple[str, int]:
    """Return the exact admitted member kind/mode or fail closed.

    Revision 11 admits six and only six tuples: ASCII/UTF-8 regular files
    using STORED or DEFLATED, and ASCII/UTF-8 directories using STORED.
    """
    name = info.filename
    if getattr(info, "orig_filename", name) != name:
        _fail("ARCHTXN-ZIP-012", "member_name_metadata_mismatch")
    directory = name.endswith("/")
    non_ascii = any(ord(char) > 127 for char in name)
    expected_flags = 0x0800 if non_ascii else 0x0000

    if info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
        _fail("ARCHTXN-ZIP-006", "unsupported_compression")
    if info.flag_bits & 0x0001:
        _fail("ARCHTXN-ZIP-005", "encrypted_member")

    unix_mode = (info.external_attr >> 16) & 0xFFFF
    file_type = stat.S_IFMT(unix_mode)
    if file_type not in {stat.S_IFREG, stat.S_IFDIR}:
        _fail("ARCHTXN-ZIP-004", "stored_nonregular_member")

    expected_attr = _DIRECTORY_ATTR if directory else _REGULAR_ATTR
    exact_common = (
        info.create_system == 3 and
        info.create_version == 20 and
        info.extract_version == 20 and
        info.reserved == 0 and
        info.flag_bits == expected_flags and
        info.volume == 0 and
        info.internal_attr == 0 and
        info.external_attr == expected_attr and
        info.extra == b"" and
        info.comment == b"" and
        info.date_time == _ZIP_EPOCH
    )
    exact_shape = (
        info.compress_type == zipfile.ZIP_STORED
        if directory else
        info.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
    )
    if not exact_common or not exact_shape:
        _fail("ARCHTXN-ZIP-012", "noncanonical_member_metadata")
    if directory:
        if info.file_size != 0 or info.compress_size != 0 or info.CRC != 0:
            _fail("ARCHTXN-ZIP-012", "noncanonical_directory_sizes")
        return "DIRECTORY_NO_CONTENT", 0o755
    return "REGULAR_FILE", 0o644


def audit_archive(archive_path: Path, expected: list[Member]) -> tuple[int, str]:
    size, digest = _sha_path(archive_path)
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            if archive.comment:
                _fail("ARCHTXN-ZIP-012", "archive_comment_present")
            infos, seen = archive.infolist(), set()
            # Name cardinality and grammar are checked before metadata/content
            # so a duplicate cannot be hidden by a malformed first entry.
            for info in infos:
                if info.filename in seen:
                    _fail("ARCHTXN-ZIP-003", "duplicate_member")
                seen.add(info.filename)
                _safe_name(info.filename[:-1] if info.is_dir() else info.filename)
            actual = []
            for info in infos:
                kind, mode = _classify_zip_member(info)
                if kind == "DIRECTORY_NO_CONTENT":
                    actual.append(Member(info.filename, "DIRECTORY_NO_CONTENT", 0, "", 0o755))
                else:
                    payload = archive.read(info)
                    if len(payload) != info.file_size or (zlib.crc32(payload) & 0xFFFFFFFF) != info.CRC:
                        _fail("ARCHTXN-ZIP-012", "member_size_or_crc_mismatch")
                    actual.append(Member(info.filename, kind, len(payload), hashlib.sha256(payload).hexdigest(), mode))
    except ArchiveTransactionError:
        raise
    except (OSError, zipfile.BadZipFile) as exc:
        _fail("ARCHTXN-ZIP-012", f"archive_unreadable_{type(exc).__name__}")
    expected_rows = [(m.name, m.kind, m.size, m.sha256) for m in expected]
    actual_rows = [(m.name, m.kind, m.size, m.sha256) for m in actual]
    if actual_rows != expected_rows:
        _fail("ARCHTXN-ZIP-009", "archive_member_parity_mismatch")
    return size, digest


def _libc() -> ctypes.CDLL:
    return ctypes.CDLL(None, use_errno=True)


def _commit_darwin(source_dirfd: int, source_name: str, destination_dirfd: int, destination_name: str) -> None:
    func = getattr(_libc(), "renameatx_np", None)
    if func is None:
        _fail("ARCHTXN-TXN-004", "darwin_adapter_unavailable")
    func.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    func.restype = ctypes.c_int
    if func(source_dirfd, source_name.encode(), destination_dirfd, destination_name.encode(), 0x00000004) == 0:
        return
    err = ctypes.get_errno()
    if err == errno.EEXIST:
        raise FileExistsError(err, "destination_exists")
    _fail("ARCHTXN-TXN-004", "darwin_noreplace_unsupported_or_crossdevice" if err in {errno.EXDEV, errno.ENOSYS, errno.ENOTSUP, errno.EOPNOTSUPP, errno.EINVAL} else f"darwin_native_errno_{err}")


def _commit_linux(source_dirfd: int, source_name: str, destination_dirfd: int, destination_name: str) -> None:
    number = {"x86_64": 316, "amd64": 316, "aarch64": 276, "arm64": 276}.get(platform.machine().lower())
    if number is None:
        _fail("ARCHTXN-TXN-004", "linux_syscall_number_unavailable")
    if _libc().syscall(number, source_dirfd, source_name.encode(), destination_dirfd, destination_name.encode(), 1) == 0:
        return
    err = ctypes.get_errno()
    if err == errno.EEXIST:
        raise FileExistsError(err, "destination_exists")
    _fail("ARCHTXN-TXN-004", "linux_noreplace_unsupported_or_crossdevice" if err in {errno.EXDEV, errno.ENOSYS, errno.EOPNOTSUPP, errno.EINVAL} else f"linux_native_errno_{err}")


def _commit_windows(source_dirfd: int, source_name: str, destination_dirfd: int, destination_name: str) -> None:
    """Handle-bound Windows rename with ReplaceIfExists permanently false.

    The first descriptor is a source *file* descriptor on Windows; callers
    never pass a pathname to a replacement-capable helper.
    """
    if platform.system() != "Windows":
        _fail("ARCHTXN-TXN-004", "windows_handle_adapter_runtime_unverified")
    import ctypes.wintypes as wintypes
    import msvcrt

    class FileRenameInfoHead(ctypes.Structure):
        _fields_ = [
            ("ReplaceIfExists", wintypes.BOOL),
            ("RootDirectory", wintypes.HANDLE),
            ("FileNameLength", wintypes.DWORD),
            ("FileName", wintypes.WCHAR * 1),
        ]

    source_handle = wintypes.HANDLE(msvcrt.get_osfhandle(source_dirfd))
    destination_handle = wintypes.HANDLE(msvcrt.get_osfhandle(destination_dirfd))
    encoded = destination_name.encode("utf-16-le")
    size = ctypes.sizeof(FileRenameInfoHead) + max(0, len(encoded) - ctypes.sizeof(wintypes.WCHAR))
    buffer = ctypes.create_string_buffer(size)
    head = ctypes.cast(buffer, ctypes.POINTER(FileRenameInfoHead)).contents
    head.ReplaceIfExists = False
    head.RootDirectory = destination_handle
    head.FileNameLength = len(encoded)
    offset = FileRenameInfoHead.FileName.offset
    ctypes.memmove(ctypes.addressof(buffer) + offset, encoded, len(encoded))
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    # FileRenameInfo is the only accepted information class here.
    if kernel32.SetFileInformationByHandle(source_handle, 3, buffer, size):
        return
    error = ctypes.get_last_error()
    if error in {80, 183}:  # ERROR_FILE_EXISTS / ERROR_ALREADY_EXISTS
        raise FileExistsError(error, "destination_exists")
    if error in {17, 50, 120, 1, 87}:  # cross-volume or unavailable/ambiguous probe support
        _fail("ARCHTXN-TXN-004", "windows_noreplace_unsupported_or_crossvolume")
    _fail("ARCHTXN-TXN-004", f"windows_native_error_{error}")


def commit_noreplace(source_dirfd: int, source_name: str, destination_dirfd: int, destination_name: str) -> None:
    _canonical_basename(source_name, allow_hidden=True)
    _canonical_basename(destination_name)
    system = platform.system()
    if system == "Darwin":
        _commit_darwin(source_dirfd, source_name, destination_dirfd, destination_name)
    elif system == "Linux":
        _commit_linux(source_dirfd, source_name, destination_dirfd, destination_name)
    elif system == "Windows":
        _commit_windows(source_dirfd, source_name, destination_dirfd, destination_name)
    else:
        _fail("ARCHTXN-TXN-004", "platform_adapter_unavailable")


def capability_probe(destination_parent: Path) -> None:
    probe = Path(tempfile.mkdtemp(prefix=".archtxn-probe-", dir=destination_parent))
    source_fd = destination_fd = -1
    try:
        (probe / "source-negative").write_bytes(b"negative")
        (probe / "destination-negative").write_bytes(b"existing")
        (probe / "source-positive").write_bytes(b"positive")
        source_fd = os.open(probe / "source-negative" if platform.system() == "Windows" else probe, os.O_RDONLY)
        destination_fd = os.open(probe, os.O_RDONLY)
        try:
            commit_noreplace(source_fd, "source-negative", destination_fd, "destination-negative")
        except FileExistsError:
            if (probe / "source-negative").read_bytes() != b"negative" or (probe / "destination-negative").read_bytes() != b"existing":
                _fail("ARCHTXN-TXN-004", "probe_negative_identity_mismatch")
        else:
            _fail("ARCHTXN-TXN-004", "probe_negative_unexpected_success")
        if platform.system() == "Windows":
            os.close(source_fd)
            source_fd = os.open(probe / "source-positive", os.O_RDONLY)
        commit_noreplace(source_fd, "source-positive", destination_fd, "destination-positive")
        if (probe / "destination-positive").read_bytes() != b"positive" or (probe / "source-positive").exists():
            _fail("ARCHTXN-TXN-004", "probe_positive_identity_mismatch")
    except ArchiveTransactionError:
        raise
    except OSError as exc:
        _fail("ARCHTXN-TXN-004", f"probe_oserror_{exc.errno or 'unknown'}")
    finally:
        if source_fd >= 0:
            os.close(source_fd)
        if destination_fd >= 0:
            os.close(destination_fd)
        try:
            shutil.rmtree(probe)
        except OSError:
            raise ArchiveTransactionError("ARCHTXN-TXN-004", "probe_cleanup_unverified")


def finalize_archive(stage_root: Path, output_dir: Path, archive_name: str, *, postcommit_fsync: Callable[[int], None] | None = None) -> ArchiveReceipt:
    final_name = _canonical_basename(archive_name)
    stage_binding = _bind_stage_root(stage_root)
    output_dir = output_dir.resolve(strict=True)
    if not output_dir.is_dir():
        _fail("ARCHTXN-ARG-001", "output_directory_not_directory")
    final_path = output_dir / final_name
    if final_path.exists() or final_path.is_symlink():
        _fail("ARCHTXN-TXN-001", "final_destination_exists")
    capability_probe(output_dir)
    members = _inventory_bound_stage(stage_binding)
    temporary = output_dir / f".{final_name}.archtxn.tmp"
    if temporary.exists():
        _fail("ARCHTXN-TXN-001", "owned_temporary_name_exists")
    srcfd = dstfd = -1
    try:
        _write_archive(stage_binding, temporary, members)
        size, digest = audit_archive(temporary, members)
        _assert_stage_unchanged(stage_binding, members)
        if _sha_path(temporary) != (size, digest):
            _fail("ARCHTXN-ZIP-011", "temporary_archive_changed_after_audit")
        srcfd = os.open(temporary if platform.system() == "Windows" else output_dir, os.O_RDONLY)
        dstfd = os.open(output_dir, os.O_RDONLY)
        try:
            commit_noreplace(srcfd, temporary.name, dstfd, final_name)
        except FileExistsError:
            # v9.7.405 (G1): the LOST-RACE path had no typed refusal. The early preflight above
            # only proves the destination was free when the transaction STARTED; a concurrent
            # writer can claim it during the write/audit/hash window, and no-replace is what
            # catches that — that is the entire reason commit_noreplace exists. Without this
            # handler the FileExistsError escaped `_main`'s `except ArchiveTransactionError`
            # and the tool exited with a traceback instead of its refusal receipt, so a caller
            # parsing error_code saw nothing and the builder could not tell "someone claimed the
            # name" apart from "the archive failed to build". The safety properties were already
            # correct — the claimant's bytes are untouched and the temporary is removed by the
            # `finally` below — but a release tool must SAY which refusal fired, not crash.
            # Same code as the preflight: both are "the final destination is taken".
            _fail("ARCHTXN-TXN-001", "final_destination_claimed_before_commit")
        final_size, final_digest = _sha_path(final_path)
        if (final_size, final_digest) != (size, digest):
            _fail("ARCHTXN-TXN-006", "postcommit_identity_unverified", committed=True)
        try:
            (postcommit_fsync or os.fsync)(dstfd)
        except OSError:
            _fail("ARCHTXN-TXN-006", "postcommit_directory_durability_hold", committed=True)
        return ArchiveReceipt("COMMITTED", None, None, final_name, len(members), digest, size, "TEMP_REMOVED_BY_COMMIT")
    finally:
        if srcfd >= 0:
            os.close(srcfd)
        if dstfd >= 0:
            os.close(dstfd)
        if temporary.exists():
            try:
                temporary.unlink()
            except OSError as cleanup_exc:
                # Best-effort cleanup inside `finally`: raising here would replace whatever real
                # error is already propagating. It must not be SILENT either — a temporary
                # archive left behind in the release output directory is operator-visible debris
                # that the next run's preflight will trip over, and the original code discarded
                # that fact with a bare `pass`. Warn and continue.
                sys.stderr.write(
                    f"WARN: temporary archive not removed: {temporary.name}: "
                    f"{type(cleanup_exc).__name__}\n")


def _main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit and no-clobber-publish a staged public-tier archive.")
    parser.add_argument("--stage-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--archive-name", required=True)
    args = parser.parse_args(argv)
    try:
        receipt = finalize_archive(Path(args.stage_root), Path(args.output_dir), args.archive_name)
    except ArchiveTransactionError as exc:
        # Typed refusal on stderr; stdout stays reserved for the committed-archive receipt so a
        # caller can parse one stream without the other. sys.stderr.write rather than
        # print(file=...) because the ratchet counts print( by AST and cannot see file=.
        sys.stderr.write(json.dumps(
            {"status": "REFUSED", "error_code": exc.code, "reason_code": exc.reason},
            sort_keys=True) + "\n")
        return 1
    sys.stdout.write(receipt.as_json() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
