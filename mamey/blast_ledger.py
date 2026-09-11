#!/usr/bin/env python3
"""blast_ledger.py — durable, cross-run contact ledger + fair-use budget for the online BLASTp channels.

NCBI's BLAST URL-API and EMBL-EBI's Job Dispatcher rate-limit per user/IP over a rolling window (NCBI
warns that >100 searches/24 h may be throttled or blocked). The submit-gap in blastp_online/blastp_ebi
only spaces requests WITHIN one invocation; it cannot see what a previous `mamey` run already sent. A
user who launches several runs can therefore blow past the daily cap and get their IP blocked — the
exact failure mode observed. This module persists every online contact to a JSON ledger that survives
across invocations, so `budget_remaining()` / `refuse_if_exhausted()` reflect the true rolling total.

Location (first that resolves):
  1. $MAMEY_BLAST_LEDGER                          (explicit override)
  2. $XDG_CACHE_HOME/sapote-mamey/blast_ledger.json
  3. ~/.cache/sapote-mamey/blast_ledger.json      (default)

Stdlib only. Cross-process safe via an fcntl lock where available (POSIX); degrades to a best-effort
write elsewhere. Read-only/observational: it records that a request was SENT; it makes no science claim.

CLAIM-SAFETY: this only counts network contacts for fair-use budgeting. No biological or provenance
claim; judgment deferred.
"""
from __future__ import annotations

import contextlib
import json
import os
import time
from pathlib import Path

# conservative defaults; NCBI's stated soft limit is ~100 searches / 24 h.
DEFAULT_DAILY_CAP = int(os.environ.get("MAMEY_BLAST_DAILY_CAP", "100"))
_WINDOW_SECONDS = 24 * 3600


def ledger_path() -> Path:
    p = os.environ.get("MAMEY_BLAST_LEDGER")
    if p:
        return Path(p)
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return Path(base) / "sapote-mamey" / "blast_ledger.json"


def _active() -> bool:
    """The ledger is inert inside the test harness UNLESS a test explicitly points it at a scratch
    file via MAMEY_BLAST_LEDGER — so the fair-use budget is never gated by the developer's real BLAST
    history during pytest, while a test that wants to exercise the ledger opts in by setting the path."""
    if os.environ.get("MAMEY_BLAST_LEDGER"):
        return True
    return "PYTEST_CURRENT_TEST" not in os.environ


def _load(path: Path) -> list[dict]:
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except (OSError, UnicodeDecodeError, ValueError, RecursionError):
        # v9.7.410: a truncated/corrupt ledger with pathologically deep JSON (e.g. a
        # partial write stopped mid `[[[[…`) raises RecursionError — a RuntimeError
        # subclass, not a ValueError — which previously escaped this handler. OSError
        # and UnicodeDecodeError are named explicitly, not caught by inheritance.
        return []


def _prune(entries: list[dict], now: float) -> list[dict]:
    """Keep only entries within the rolling window (bounds file growth)."""
    cut = now - _WINDOW_SECONDS
    return [e for e in entries if isinstance(e, dict) and float(e.get("t", 0)) >= cut]


class _Lock:
    """Best-effort exclusive lock on a sidecar file; no-op if fcntl is unavailable."""
    def __init__(self, target: Path):
        self._lockfile = target.with_suffix(target.suffix + ".lock")
        self._fh = None

    def __enter__(self):
        try:
            import fcntl
            self._lockfile.parent.mkdir(parents=True, exist_ok=True)
            self._fh = open(self._lockfile, "w")
            fcntl.flock(self._fh, fcntl.LOCK_EX)
        except (ImportError, OSError):
            self._fh = None
        return self

    def __exit__(self, *exc):
        if self._fh is not None:
            with contextlib.suppress(ImportError, OSError):  # unlock best-effort
                import fcntl
                fcntl.flock(self._fh, fcntl.LOCK_UN)
            self._fh.close()


def record(service: str, n: int = 1, path: Path | None = None) -> None:
    """Append `n` contact events for `service` (e.g. 'ncbi', 'ebi'), timestamped now. Cross-run durable."""
    if path is None and not _active():
        return
    p = path or ledger_path()
    now = time.time()
    with _Lock(p):
        entries = _prune(_load(p), now)
        entries.extend({"t": now, "svc": str(service)} for _ in range(max(1, int(n))))
        # a ledger we cannot persist must not crash a run; budget just can't be enforced
        with contextlib.suppress(OSError):
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(p.suffix + ".tmp")
            tmp.write_text(json.dumps(entries), encoding="utf-8")
            os.replace(tmp, p)


def count_last(hours: float = 24.0, service: str | None = None, path: Path | None = None) -> int:
    """Number of recorded contacts in the trailing `hours` window, optionally filtered by service."""
    p = path or ledger_path()
    now = time.time()
    cut = now - hours * 3600
    return sum(1 for e in _load(p)
               if float(e.get("t", 0)) >= cut and (service is None or e.get("svc") == service))


def budget_remaining(service: str | None = None, daily_cap: int | None = None,
                     path: Path | None = None) -> int:
    """Requests still allowed in the current rolling 24 h window (never negative)."""
    cap = DEFAULT_DAILY_CAP if daily_cap is None else int(daily_cap)
    return max(0, cap - count_last(24.0, service=service, path=path))


class BlastBudgetExceeded(RuntimeError):
    pass


def refuse_if_exhausted(service: str, need: int = 1, daily_cap: int | None = None,
                        path: Path | None = None) -> None:
    """Raise BlastBudgetExceeded if fewer than `need` requests remain in the rolling 24 h window.

    Callers should invoke this BEFORE submitting, then `record()` after a successful submit. Set
    MAMEY_BLAST_DAILY_CAP to tune, or a very large value to effectively disable (not recommended)."""
    if path is None and not _active():
        return
    remaining = budget_remaining(service=service, daily_cap=daily_cap, path=path)
    if remaining < need:
        cap = DEFAULT_DAILY_CAP if daily_cap is None else int(daily_cap)
        raise BlastBudgetExceeded(
            f"online BLASTp fair-use budget for {service!r} exhausted: {count_last(24.0, service=service, path=path)}"
            f"/{cap} contacts used in the last 24 h, {remaining} remaining, {need} requested. "
            f"Wait for the window to roll, raise MAMEY_BLAST_DAILY_CAP if you are certain, or use the "
            f"offline ingest-blastp path. Ledger: {path or ledger_path()}.")
