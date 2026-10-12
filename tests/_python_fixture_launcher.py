"""Portable POSIX launchers for synthetic Python executables in tests only."""
from pathlib import Path
import shlex
import sys


def write_python_fixture(path, body, *, python=None, mode=0o755):
    """Pin the exact invocation, preserving argv[1:], environment and exit status.

    Keep the Python payload adjacent so shell launchers work after a CWD change.
    Payload argv[0]/__file__ identify that payload; selected callers do not use them.
    mode=None lets an existing caller retain its own chmod policy.
    """
    path = Path(path).absolute()
    payload = path.with_name(path.name + ".fixture.py")
    interpreter = sys.executable if python is None else python
    payload.write_text(body, encoding="utf-8")
    path.write_text("#!/bin/sh\nexec " + shlex.quote(str(interpreter)) + " "
                    + shlex.quote(str(payload)) + ' "$@"\n', encoding="utf-8")
    if mode is not None:
        path.chmod(mode)
    return path
