"""Per-run source binding for explicitly migrated readers; no global open patching."""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import os
import io
import zipfile

_ACTIVE = ContextVar("mamey_captured_run", default=None)


def active():
    return _ACTIVE.get()


def lexical_locator(source):
    """Normalize spelling without consulting a mutable filesystem target."""
    return Path(os.path.abspath(os.path.normpath(os.fspath(source))))


def bound_source(source):
    frame = active()
    if frame is not None and isinstance(source, (str, Path)):
        if lexical_locator(source) in frame.source_aliases:
            return frame.session.snapshot
    return source


class _CapturedReader:
    """Adapt08public captured_zip lifetime to existing ZipFile reader callsites."""
    def __init__(self, snapshot, policy):
        from .archive_snapshot import captured_zip
        self._manager = captured_zip(snapshot, policy=policy)
        self._archive = self._manager.__enter__()

    def __getattr__(self, name):
        return getattr(self._archive, name)

    def __enter__(self):
        return self._archive

    def __exit__(self, *args):
        if self._manager is not None:
            manager, self._manager = self._manager, None
            return manager.__exit__(*args)

    def close(self):
        self.__exit__(None, None, None)


def source_zipfile(source, *args, **kwargs):
    """Read the bound input with08public API; other ZIP operations stay unchanged."""
    mode = args[0] if args else kwargs.get("mode", "r")
    selected = bound_source(source)
    from .archive_snapshot import ArchiveSnapshot
    if isinstance(selected, ArchiveSnapshot):
        if mode != "r":
            raise ValueError("CAPTURED_SOURCE_IS_READ_ONLY")
        frame = active()
        return _CapturedReader(selected, frame.session.policy if frame is not None else selected.capture_policy)
    return zipfile.ZipFile(selected, *args, **kwargs)


@contextmanager
def source_archive(source):
    with source_zipfile(source) as archive:
        yield archive


@contextmanager
def binding(frame):
    token = _ACTIVE.set(frame)
    try:
        yield frame
    finally:
        _ACTIVE.reset(token)


def public_value(value):
    frame = active()
    if frame is None:
        return value
    if isinstance(value, str):
        return frame.display(value)
    if isinstance(value, list):
        return [public_value(x) for x in value]
    if isinstance(value, dict):
        return {key: public_value(item) for key, item in value.items()}
    return value



def source_size(source):
    selected = bound_source(source)
    from .archive_snapshot import ArchiveSnapshot
    if isinstance(selected, ArchiveSnapshot):
        return len(selected._payload)
    return Path(selected).stat().st_size


def source_exists(source):
    selected = bound_source(source)
    from .archive_snapshot import ArchiveSnapshot
    return isinstance(selected, ArchiveSnapshot) or Path(selected).exists()



def captured_digest(source):
    selected = bound_source(source)
    from .archive_snapshot import ArchiveSnapshot
    return selected.input_sha256 if isinstance(selected, ArchiveSnapshot) else None
