"""degradation.py — v9.7.367 CANDIDATE (Indigo2 §1, the review lane-ruled 2026-08-15).

Process-local collector for silent-degradation breadcrumbs. When a defensive broad
except on the scoring surface fires, the handler records WHAT degraded here instead
of vanishing. cli drains the events into run_phase_receipts.jsonl (a MUTABLE_RECEIPT_NAMES
member, outside DETERMINISM_WHITELIST) at package-write time.

Contract: imports nothing from mamey (importable anywhere, no cycles); record() and
drain() never raise; no produced output value is ever touched by this module.
"""
from __future__ import annotations

import contextlib

_EVENTS: list[dict] = []


def record(site: str, exc, **ctx) -> None:
    """Append one breadcrumb. `site` = 'module.function.slot'; exc = exception or str."""
    # v9.7.370 swallow triage: the collector must never raise (module contract), and a
    # failure to record a breadcrumb cannot itself be recorded by the recorder — so the
    # suppression is DELIBERATE and now named, not an anonymous `except: pass`.
    with contextlib.suppress(Exception):
        _EVENTS.append({
            "site": str(site),
            "error": repr(exc) if isinstance(exc, BaseException) else str(exc),
            **{k: str(v) for k, v in ctx.items()},
        })


def drain() -> list[dict]:
    """Return and clear all recorded events (cli calls this once per package write)."""
    try:
        out = list(_EVENTS)
        _EVENTS.clear()
        return out
    except Exception:
        return []


def peek() -> list[dict]:
    """Non-destructive view (tests)."""
    return list(_EVENTS)
