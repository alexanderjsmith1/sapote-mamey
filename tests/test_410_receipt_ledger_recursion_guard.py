"""test_r7_recursion_guard.py — v9.7.410 R-7: the two JSON-load sites that lacked
the H17 RecursionError hardening applied elsewhere must fail closed, not crash.

A truncated/corrupt receipt or ledger whose partial write stopped mid `[[[[…` parses
to pathologically deep JSON. `json.loads` on it raises RecursionError — a RuntimeError
subclass, NOT a ValueError — so a handler that catches only json.JSONDecodeError /
ValueError lets it escape and crashes with a traceback instead of routing to the
function's own fail-closed path.

Two sites are pinned here:
  - mode_b_receipt._load_receipt (the `mamey ingest-receipts --receipt` ingestion path):
    fail-closed contract is to raise ValueError (which the CLI boundary catches), not
    to escape as a bare RecursionError.
  - blast_ledger._load: fail-closed contract is to return [] (empty ledger).

The pathological string is built directly (cheap, no recursion); parsing it is what is
under test. We keep the nesting depth well above the interpreter's recursion limit so
the parse genuinely triggers RecursionError on an unhardened build.
"""
import json

import pytest

from mamey import blast_ledger as bl
from mamey import mode_b_receipt as mr

# ~200k unmatched openers: a truncated `[[[[…` partial write. Building the string is
# plain string multiplication (no recursion); only json.loads recurses on it.
_PATHOLOGICAL_JSON = "[" * 200_000


def _write_pathological(path):
    path.write_text(_PATHOLOGICAL_JSON, encoding="utf-8")
    return path


def test_pathological_string_actually_defeats_the_json_parser():
    """Sanity gate: confirm the fixture really provokes RecursionError from json.loads,
    so a green result below means the guard caught it — not that the input was benign."""
    with pytest.raises(RecursionError):
        json.loads(_PATHOLOGICAL_JSON)


def test_load_receipt_fails_closed_on_deep_json(tmp_path):
    receipt = _write_pathological(tmp_path / "mode_b_receipt.json")
    # Fail-closed contract for a corrupt receipt is a ValueError the CLI boundary
    # catches — NOT an uncaught RecursionError traceback.
    with pytest.raises(ValueError):
        mr._load_receipt(receipt)


def test_blast_ledger_load_fails_closed_on_deep_json(tmp_path):
    ledger = _write_pathological(tmp_path / "blast_ledger.json")
    # Fail-closed contract for a corrupt ledger is an empty list, returned without
    # raising anything.
    assert bl._load(ledger) == []
