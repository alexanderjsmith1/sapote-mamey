"""The render-all-figures help must not claim the package is left unchanged."""
import argparse

from mamey.cli import build_parser


def _help(name):
    parser = build_parser()
    sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    return next(a.help for a in sub._choices_actions if a.dest == name)


def test_help_states_package_writes():
    text = _help("render-all-figures")
    assert "without changing the sealed package" not in text
    assert "inside the package" in text
    assert "post_seal_checksums.txt" in text
    assert "working copy" in text
