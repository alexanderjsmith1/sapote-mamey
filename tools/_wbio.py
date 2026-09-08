"""Shared atomic workbook I/O for the secondary-sheet builders.

`wb.save(path)` over the input path corrupts the workbook into an unreadable BadZipFile if the process is
interrupted mid-write. atomic_save writes to a sibling .tmp and os.replace()s it into place — os.replace is
atomic on the same filesystem, so the original file is never left half-written. An optional .bak keeps the
prior version.
"""
import contextlib
import os
import shutil
import stat
import tempfile


class AtomicJsonWriteRefused(RuntimeError):
    """The destination contract failed before any staging file was created."""


class AtomicJsonDurabilityError(RuntimeError):
    """Publication completed, but the containing-directory fsync did not."""

    destination_published = True


def _temp_path(path):
    """Reserve a unique sibling temp path.

    A fixed ``path + '.tmp'`` lets concurrent writers truncate or remove each
    other's in-progress output.  ``mkstemp`` gives every transaction a private
    same-filesystem path while retaining the sibling-rename atomicity contract.
    """
    path = os.path.abspath(os.fspath(path))
    fd, tmp = tempfile.mkstemp(
        prefix=f".{os.path.basename(path)}.", suffix=".tmp", dir=os.path.dirname(path)
    )
    os.close(fd)
    return tmp


def _inherit_mode(path, tmp):
    """v9.7.243: os.replace() adopts the TEMP file's permissions, so rewriting a 0600 deliverable
    left it 0644 — a real widening in a bundle that ships a MERGED-PRIVATE tier. Carry the original
    mode onto the temp before the rename. No-op when the target does not exist yet."""
    try:
        if os.path.exists(path):
            os.chmod(tmp, os.stat(path).st_mode & 0o7777)
    except OSError:
        pass


def _discard(tmp):
    """Remove a temp on a failed write. atomic_open already did this; the other three leaked."""
    try:
        if os.path.exists(tmp):
            os.remove(tmp)
    except OSError:
        pass


def _commit(path, tmp):
    """Apply target permissions and atomically publish one completed temp."""
    try:
        _inherit_mode(path, tmp)
        os.replace(tmp, path)
    except BaseException:
        _discard(tmp)
        raise


def _backup(path):
    """Refresh ``path.bak`` atomically without exposing a partial backup."""
    backup = path + ".bak"
    tmp = _temp_path(backup)
    try:
        shutil.copy2(path, tmp)
        os.replace(tmp, backup)
    except BaseException:
        _discard(tmp)
        raise


def atomic_save(wb, path, keep_bak=False):
    path = os.fspath(path)
    tmp = _temp_path(path)
    try:
        wb.save(tmp)
    except BaseException:
        _discard(tmp)
        raise
    if keep_bak and os.path.exists(path):
        try:
            # v9.7.243: COPY, not replace. os.replace(path, path+".bak") removed the original first,
            # leaving a window in which `path` did not exist at all — the opposite of the invariant
            # this module exists to guarantee.
            _backup(path)
        except OSError as e:
            import warnings
            warnings.warn(f"atomic_save: could not create .bak for {path}: {e}")
    _commit(path, tmp)
    return path


def atomic_write_text(path, text, encoding="utf-8"):
    """Write text crash-safely: write to a sibling .tmp, then os.replace into place.

    os.replace is atomic on the same filesystem, so a killed process never leaves a
    half-written deliverable. Mirrors atomic_save for plain-text / markdown output.

    Uses default newline handling (newline=None) to match the plain open(path, "w")
    calls this replaced — identical bytes on POSIX, and the same os.linesep translation
    on Windows the originals would have done. CSV writers keep their own newline=""
    open() blocks (the csv module's documented requirement); this helper is text-only.
    """
    path = os.fspath(path)
    tmp = _temp_path(path)
    try:
        with open(tmp, "w", encoding=encoding) as f:
            f.write(text)
    except BaseException:
        _discard(tmp)
        raise
    _commit(path, tmp)
    return path


def atomic_dump_json(obj, path, indent=2):
    """json.dump crash-safely via a sibling .tmp + os.replace.

    NOTE the argument order: atomic_dump_json(obj, path) is OBJECT-FIRST, matching the
    stdlib json.dump(obj, fp) it wraps — whereas atomic_write_text(path, text) is PATH-FIRST.
    They differ on purpose (each mirrors its stdlib model); don't swap them.
    """
    import json
    path = os.fspath(path)
    tmp = _temp_path(path)
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=indent)
    except BaseException:
        _discard(tmp)   # a non-serializable object used to leave a stray .tmp on disk
        raise
    _commit(path, tmp)
    return path


def atomic_dump_json_owned(obj, path, *, owner_dir, indent=2, **json_kwargs):
    """Publish JSON through one explicitly owned destination directory.

    This JSON-only contract is intentionally narrower than the package-wide text
    writer family.  It refuses before staging unless ``path`` is a direct child
    of the caller-supplied ``owner_dir`` after both lexical normalization and
    symlink resolution.  The destination leaf must be absent or a regular file;
    symlinks and special files are refused.

    A unique private sibling is serialized, flushed, and file-fsynced before
    ``os.replace``.  The parent directory is fsynced after the rename.  Existing
    permissions are carried onto the stage; a newly created destination remains
    private (0600).  Failures before rename leave the destination unchanged or
    absent and remove the stage.  A parent-fsync failure after rename raises
    ``AtomicJsonDurabilityError`` because publication occurred but durable commit
    is uncertain.

    Atomic publication does not merge concurrent read-modify-write transactions.
    Callers that update the same logical JSON object must still be externally
    serialized; unique staging prevents temp collisions, not lost updates.
    """
    import json

    raw_path = os.path.abspath(os.fspath(path))
    raw_owner = os.path.abspath(os.fspath(owner_dir))
    if os.path.dirname(raw_path) != raw_owner:
        raise AtomicJsonWriteRefused(
            f"destination must be a direct child of owner_dir: {raw_path!r} not under {raw_owner!r}"
        )
    if not os.path.isdir(raw_owner):
        raise AtomicJsonWriteRefused(f"owner_dir is not an existing directory: {raw_owner!r}")

    resolved_owner = os.path.realpath(raw_owner)
    resolved_parent = os.path.realpath(os.path.dirname(raw_path))
    if resolved_parent != resolved_owner:
        raise AtomicJsonWriteRefused(
            f"resolved destination parent escapes owner_dir: {resolved_parent!r} != {resolved_owner!r}"
        )

    leaf = os.path.basename(raw_path)
    if leaf in ("", ".", ".."):
        raise AtomicJsonWriteRefused(f"invalid destination leaf: {leaf!r}")
    destination = os.path.join(resolved_parent, leaf)

    prior_mode = None
    if os.path.lexists(destination):
        prior = os.lstat(destination)
        if not stat.S_ISREG(prior.st_mode):
            raise AtomicJsonWriteRefused(
                f"destination must be absent or a regular file: {destination!r}"
            )
        prior_mode = stat.S_IMODE(prior.st_mode)

    dir_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        dir_fd = os.open(resolved_parent, dir_flags)
    except OSError as exc:
        raise AtomicJsonWriteRefused(
            f"cannot open destination directory for durability: {resolved_parent!r}"
        ) from exc

    tmp = None
    published = False
    try:
        try:
            os.fsync(dir_fd)
        except OSError as exc:
            raise AtomicJsonWriteRefused(
                f"destination directory does not support required fsync: {resolved_parent!r}"
            ) from exc

        fd, tmp = tempfile.mkstemp(prefix=f".{leaf}.", suffix=".tmp", dir=resolved_parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(obj, stream, indent=indent, **json_kwargs)
                stream.flush()
                if prior_mode is not None:
                    os.fchmod(stream.fileno(), prior_mode)
                os.fsync(stream.fileno())
        except BaseException:
            _discard(tmp)
            raise

        try:
            os.replace(tmp, destination)
            published = True
            tmp = None
        except BaseException:
            _discard(tmp)
            raise

        try:
            os.fsync(dir_fd)
        except OSError as exc:
            raise AtomicJsonDurabilityError(
                f"destination published but parent-directory fsync failed: {destination!r}"
            ) from exc
    finally:
        if not published and tmp is not None:
            _discard(tmp)
        os.close(dir_fd)

    return os.fspath(path)


@contextlib.contextmanager
def atomic_open(path, mode="w", encoding="utf-8", newline=None):
    """Context manager for crash-safe streamed writes: yields a file handle on a sibling .tmp,
    and os.replace()s it into place only on clean exit. If the block raises, the .tmp is removed
    and the original file is left untouched.

    Use for multi-write blocks (FASTA loops, line-by-line reports) where accumulating the whole
    payload in memory would be awkward — the loop body keeps its f.write() calls unchanged; only
    the `with open(path, "w")` becomes `with atomic_open(path)`.
    """
    path = os.fspath(path)
    tmp = _temp_path(path)
    f = None
    try:
        f = open(tmp, mode, encoding=encoding, newline=newline)
        yield f
        f.close()
        _commit(path, tmp)
    except BaseException:
        try:
            if f is not None:
                f.close()
        finally:
            _discard(tmp)
        raise
