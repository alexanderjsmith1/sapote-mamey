"""_console.py — the single owner of direct terminal emission for tools/ and deliverable_tools/.

v9.7.407 ratchet paydown, tools-side companion to `mamey/console.py`. Operator front doors are
standalone scripts whose stdout IS the deliverable (a receipt line, a census row, a typed refusal),
so this is deliberately NOT a logger: it is a pass-through that takes exactly print's signature and
forwards every argument unchanged. `sep`, `end`, `file` and `flush` all behave identically, so a
converted call site is byte-identical on stdout and stderr.

What it buys: one seam. Adding `--quiet`, a `--json` envelope, or an output capture to the operator
tool family is now a change to this function instead of an edit to every script. It is underscore-
prefixed so `tests/test_tool_front_doors.py` correctly treats it as a private helper rather than a
front door to run `--help` on.

It deliberately does NOT import from `mamey`: a standalone operator tool must keep working without
the package on sys.path, which is the whole point of the front-door guard.

Claim-safety: this module carries no scientific meaning. It moves bytes to a stream.
"""
from __future__ import annotations

import builtins
from typing import Any

__all__ = ["emit"]


def emit(*args: Any, **kwargs: Any) -> None:
    """Write to the terminal exactly as `print` would (pass-through by contract)."""
    builtins.print(*args, **kwargs)
