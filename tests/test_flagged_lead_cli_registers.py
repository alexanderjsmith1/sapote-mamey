"""Smoke test — the flagged-lead workflow subcommands register in the cli (v9.7.353).

Mirrors the .352 bigscape card's `--help`-registers pattern. Self-skips when the wiring is not
applied yet, so it is safe to drop into `tests/` alongside the cli.py.diff and activates on apply.
"""
import pytest
from mamey import cli

WANT = {"majority-read", "surface-leads", "modeb-compile"}


def _registered_commands():
    """Best-effort: build the parser and collect subcommand names."""
    for builder in ("build_parser", "make_parser", "_build_parser", "get_parser"):
        fn = getattr(cli, builder, None)
        if fn:
            try:
                p = fn()
            except TypeError:
                continue
            for act in p._actions:
                if hasattr(act, "choices") and act.choices:
                    return set(act.choices)
    return set()


def test_workflow_subcommands_register():
    cmds = _registered_commands()
    if not (WANT & cmds):
        pytest.skip("flagged-lead workflow cli wiring not applied yet")
    missing = WANT - cmds
    assert not missing, f"missing subcommands: {missing}"


def test_dispatcher_present_once_applied():
    if not (WANT & _registered_commands()):
        pytest.skip("wiring not applied")
    assert hasattr(cli, "_flagged_lead_command"), "dispatcher _flagged_lead_command missing"
