"""Regression cases for table lint; no scientific acceptance is implied."""
import pytest

from mamey.modeb_publication_gate import _table_separator_findings


@pytest.mark.parametrize("fence", ["```", "~~~~"])
def test_fenced_examples_are_not_tables(fence):
    assert not _table_separator_findings(
        f"{fence}\n| A | B |\n|---|\n{fence}\n")


def test_escaped_pipe_is_content():
    assert not _table_separator_findings(
        "| A \\| label | B |\n|---|---|\n| x \\| y | z |\n")


@pytest.mark.parametrize("body", ["| x |", "| x | y | z |"])
def test_body_width_must_match_header(body):
    findings = _table_separator_findings("| A | B |\n|---|---|\n" + body)
    assert [f["code"] for f in findings] == ["CARD_TABLE_BODY_MISMATCH"]


def test_header_separator_mismatch_still_detected():
    assert _table_separator_findings(
        "| A | B |\n|---|---|---|\n")[0]["code"] == "CARD_TABLE_SEPARATOR_MISMATCH"


def test_optional_outer_pipes():
    assert not _table_separator_findings("A | B\n--- | ---\nx | y\n")


def test_body_without_outer_pipes_is_checked():
    assert _table_separator_findings(
        "A | B\n--- | ---\nx | y | z\n")[0]["code"] == "CARD_TABLE_BODY_MISMATCH"


def test_non_table_paragraph_ends_table():
    assert not _table_separator_findings(
        "| A | B |\n|---|---|\n| x | y |\nparagraph\n| unrelated |\n")
