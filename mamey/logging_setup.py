"""mamey/logging_setup.py — one logging front door for the engine.

One logging front door for the engine. Design constraints, in order:
1. BYTE-IDENTICAL default output for converted modules: bare "%(message)s" format, single
   StreamHandler to STDOUT (not the logging default of stderr), default level INFO. A module
   whose `print(x)` becomes `log.info(x)` or `log.warning(x)` emits the same bytes to the same
   stream. (Stdout/stderr separation is a future opt-in via configure(), not a silent change.)
2. Env override without code: MAMEY_LOG=debug|info|warning|error (default info).
3. Idempotent: configure() replaces the mamey handler rather than stacking duplicates
   (pytest/module-reload safe).
Claim-safety: infrastructure only; no message content is created or altered here.
"""
from __future__ import annotations

import logging
import os
import sys

_ROOT_NAME = "mamey"
_DEFAULT_FMT = "%(message)s"
_LEVELS = {"debug": logging.DEBUG, "info": logging.INFO,
           "warning": logging.WARNING, "error": logging.ERROR}
_configured = False


class _LiveStdoutHandler(logging.StreamHandler):
    """Writes to whatever sys.stdout is at the moment of each record, like print does.

    A plain StreamHandler(sys.stdout) keeps the stream object it was built with. A test runner or a caller that swaps
    sys.stdout afterwards (pytest capture, contextlib.redirect_stdout) would then lose the line, or hit a closed stream,
    where the former print reached the new stdout. This handler reads sys.stdout per record, so a converted line goes
    exactly where the print went."""

    def __init__(self):
        logging.Handler.__init__(self)

    @property
    def stream(self):
        return sys.stdout

    @stream.setter
    def stream(self, value):   # StreamHandler.setStream assigns here; the live lookup always wins
        return


def configure(level: str | int | None = None, fmt: str = _DEFAULT_FMT,
              stream=None) -> logging.Logger:
    """(Re)configure the mamey root logger. Called lazily by get_logger; callable
    explicitly by the CLI to change level/format/stream."""
    global _configured
    root = logging.getLogger(_ROOT_NAME)
    if level is None:
        level = _LEVELS.get(os.environ.get("MAMEY_LOG", "info").lower(), logging.INFO)
    elif isinstance(level, str):
        level = _LEVELS.get(level.lower(), logging.INFO)
    handler = logging.StreamHandler(stream) if stream is not None else _LiveStdoutHandler()
    handler.setFormatter(logging.Formatter(fmt))
    handler.set_name("mamey-default")
    for h in list(root.handlers):
        if h.get_name() == "mamey-default":
            root.removeHandler(h)
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False  # never double-print through the stdlib root logger
    _configured = True
    return root


def get_logger(name: str) -> logging.Logger:
    """Factory: get_logger(__name__) -> child of the 'mamey' logger, configuring on first use."""
    if not _configured:
        configure()
    if name == _ROOT_NAME or name.startswith(_ROOT_NAME + "."):
        return logging.getLogger(name)
    return logging.getLogger(f"{_ROOT_NAME}.{name}")
