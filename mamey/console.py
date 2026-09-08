"""console.py — the single owner of direct terminal emission for the mamey package.

v9.7.407 ratchet paydown. Before this module, 700+ `print(` call sites were scattered across
`mamey/`, so there was no one place to change how the package talks to a terminal: no way to add a
`--quiet`, to route CLI chatter to a logger, or even to answer "what does this subcommand write to
stdout versus stderr" without grepping. `emit` is a deliberate pass-through — it takes exactly
print's signature and forwards every argument unchanged, so converting a call site is
byte-identical on both streams (same text, same separator, same terminator, same file). Nothing a
user sees changes; what changes is that the package now has one emission seam instead of hundreds.

Swapping in a logger, a quiet flag, or a capture buffer is now a change to `emit` alone. That
migration is deliberately NOT done here: it would alter what users see, which this paydown must
not do. See `mamey/logging_setup.py` for the structured-logging channel, which is a separate
concern — `emit` is terminal output that IS the deliverable (a receipt line, a typed refusal, a
CLI summary), not diagnostic logging.

Claim-safety: this module carries no scientific meaning. It moves bytes to a stream.
"""
from __future__ import annotations

import builtins
from typing import Any

__all__ = ["emit"]


def emit(*args: Any, **kwargs: Any) -> None:
    """Write to the terminal exactly as `print` would.

    Pass-through by contract: `sep`, `end`, `file` and `flush` all behave identically. Call sites
    converted from `print(...)` to `emit(...)` produce byte-identical output.
    """
    builtins.print(*args, **kwargs)
