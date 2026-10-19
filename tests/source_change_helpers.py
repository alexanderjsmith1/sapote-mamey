"""Generic file-replacement controls for synthetic byte-binding regression tests."""
import builtins
import importlib.util
import io
from pathlib import Path


def load_tool(relative_path, module_name):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(module_name, root / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replace_after_first_binary_read(monkeypatch, path, replacement, *, binary_only=True):
    """Mutate a toy source after a consumed binary handle closes, before a later read.

    Cover builtins.open and pathlib's io.open boundary. Preserve the real returned
    bytes; do not patch the candidate's digest/record result or prevent a new
    implementation from reading a single buffer. The premise must be asserted.
    """
    path = Path(path)
    native_builtin = builtins.open
    native_io = io.open
    changed = []

    class ReadHandle:
        def __init__(self, handle):
            self.handle = handle

        def __getattr__(self, name):
            return getattr(self.handle, name)

        def __iter__(self):
            return iter(self.handle)

        def __enter__(self):
            self.handle.__enter__()
            return self

        def __exit__(self, kind, value, traceback):
            result = self.handle.__exit__(kind, value, traceback)
            if kind is None and not changed:
                with native_builtin(path, "wb") as stream:
                    stream.write(replacement)
                changed.append(True)
            return result

    def wrap(native):
        def opening(file, mode="r", *args, **kwargs):
            handle = native(file, mode, *args, **kwargs)
            if isinstance(file, (str, Path)) and Path(file) == path and "r" in mode and (not binary_only or "b" in mode) and not changed:
                return ReadHandle(handle)
            return handle
        return opening

    monkeypatch.setattr(builtins, "open", wrap(native_builtin))
    monkeypatch.setattr(io, "open", wrap(native_io))
    return changed
