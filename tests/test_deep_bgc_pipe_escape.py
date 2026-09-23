"""Test that _cell() escapes pipe characters for Markdown table safety.

v9.7.438 patch: claude-alex-2026-40.
"""
import pytest


def test_cell_no_pipe():
    from mamey.deep_bgc_report import _cell
    assert _cell("simple text") == "simple text"


def test_cell_with_pipe():
    from mamey.deep_bgc_report import _cell
    assert _cell("type|I|PKS") == r"type\|I\|PKS"


def test_cell_integer():
    from mamey.deep_bgc_report import _cell
    assert _cell(42) == "42"


def test_cell_empty():
    from mamey.deep_bgc_report import _cell
    assert _cell("") == ""
