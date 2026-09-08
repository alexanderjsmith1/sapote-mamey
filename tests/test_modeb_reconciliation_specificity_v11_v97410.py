from __future__ import annotations

from types import SimpleNamespace

from mamey.authored_verify import verify_modeb_command
from mamey.cli import build_parser
from mamey.modeb_publication_gate import publication_quality_findings
from mamey.modeb_structure_gate import lint_card
from tests.test_modeb_publication_quality_v9_7_372 import _card


CODE = "SECTION_RECONCILIATION_V11_TEMPLATE_REUSE"


def _codes(card: str, *, enabled: bool = True) -> set[str]:
    return {finding["code"] for finding in publication_quality_findings(
        card, check_reconciliation_specificity_v11=enabled)}


def _distinct_matrix(card: str) -> str:
    alphabet = [
        "amber", "birch", "cedar", "dahlia", "elm", "fir", "ginger", "hazel",
        "iris", "juniper", "kelp", "lilac", "maple", "nutmeg", "olive", "pine",
        "quince", "rose", "sage", "thyme", "umber", "violet", "willow", "xenia",
        "yarrow", "zinnia", "acorn", "basil", "clover", "dogwood", "eucalyptus",
        "fennel", "gardenia", "heather", "indigo", "jasmine", "kumquat", "lavender",
        "magnolia", "nectarine", "orchid", "papaya", "quinoa", "rosemary", "saffron",
        "tulip", "verbena", "walnut",
    ]
    for section, token in enumerate(alphabet, 1):
        card = card.replace(
            f"| §{section} | SUBSTANTIVE | named source | RETAIN | reconciled |",
            f"| §{section} | SUBSTANTIVE | {token} assay receipt | RETAIN | {token} evidence retained after conflict review |",
        )
    return card


def test_v11_is_separate_opt_in_and_rejects_generic_48_row_matrix():
    assert CODE not in _codes(_card(), enabled=False)
    assert CODE in _codes(_card())


def test_section_number_suffixes_do_not_manufacture_specificity():
    card = _card()
    for section in range(1, 49):
        card = card.replace(
            f"| §{section} | SUBSTANTIVE | named source | RETAIN | reconciled |",
            f"| §{section} | SUBSTANTIVE | named source for section {section} | RETAIN | reconciled §{section} |",
        )
    assert CODE in _codes(card)


def test_floor_allows_seven_copied_pairs_but_rejects_eight():
    distinct = _distinct_matrix(_card())
    copied = "| §{section} | SUBSTANTIVE | shared assay receipt | RETAIN | shared evidence retained |"
    seven = distinct
    for section in range(1, 8):
        seven = seven.replace(
            next(line for line in seven.splitlines() if line.startswith(f"| §{section} |")),
            copied.format(section=section),
        )
    assert CODE not in _codes(seven)
    eight = seven.replace(
        next(line for line in seven.splitlines() if line.startswith("| §8 |")),
        copied.format(section=8),
    )
    assert CODE in _codes(eight)


def test_distinct_section_specific_pairs_pass():
    assert CODE not in _codes(_distinct_matrix(_card()))


def test_repeated_claim_safety_prose_outside_matrix_is_not_scored():
    card = _distinct_matrix(_card()) + ("\nCapacity is not production or activity.\n" * 20)
    assert CODE not in _codes(card)


def test_structure_gate_forwards_v11():
    codes = {row["code"] for row in lint_card(
        _card(), check_publication_quality=True,
        check_reconciliation_specificity_v11=True)}
    assert CODE in codes


def test_cli_exposes_separate_v11_switch():
    args = build_parser().parse_args([
        "verify-modeb", "candidate.md", "--reconciliation-specificity-v11"])
    assert args.reconciliation_specificity_v11 is True
    assert args.figure_spec_v10 is False


def test_v11_switch_requires_finished_profile(tmp_path, capsys):
    path = tmp_path / "draft.md"
    path.write_text(_card(), encoding="utf-8")
    args = SimpleNamespace(
        file=str(path), package=None, bgc=None, no_strict_depth=True,
        force=False, interp=False, interp_strict=False, summary_only=False,
        report_json=None, reconciliation_specificity_v11=True,
    )
    assert verify_modeb_command(args) == 1
    assert "RECONCILIATION_SPECIFICITY_V11_REQUIRES_FINISHED_PROFILE" in capsys.readouterr().out
