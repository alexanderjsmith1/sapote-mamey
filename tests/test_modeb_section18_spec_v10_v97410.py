from __future__ import annotations

from mamey.cli import build_parser
from mamey.modeb_publication_gate import publication_quality_findings
from mamey.modeb_structure_gate import lint_card
from tests.test_modeb_publication_quality_v9_7_372 import _card


IDENTITY = "SYNTH-001 / NODE_7_length_12345_cov_20.500000 / region001 / BGC007"
MAP_SHA = "e" * 64
VISUAL_SHA = "f" * 64
HEADER = (
    "#### Figure specification\n"
    "| Figure state | Exact plotted identity | Plotted interval | Locus-map v8 receipt | Rendered formats | Evidence-state encoding | Uncertainty labels | Provenance footer | Lossless sidecar | Visual-review receipt | Visual-review state |\n"
    "|---|---|---|---|---|---|---|---|---|---|---|\n"
)
ROW = (
    f"| FIGURE_RENDERED_REVIEWED | {IDENTITY} | 100-400 bp | {MAP_SHA} | PNG+SVG+CSV | "
    "ENCODED_WITH_EXPLICIT_MISSING | boundary uncertainty and missing coverage labels remain visibly explicit | "
    f"PRESENT_PACKAGE_RELATIVE_SOURCES | VERIFIED_ALL_GENES | {VISUAL_SHA} | PASS_OWNER_REVIEWED |"
)


def _replace(card: str, body: str) -> str:
    marker = "## §18 Section 18\n"
    start = card.index(marker) + len(marker)
    end = card.index("## §19 Section 19\n", start)
    return card[:start] + body.strip() + "\n\n" + card[end:]


def _codes(card: str, enabled: bool = True) -> set[str]:
    return {row["code"] for row in publication_quality_findings(
        card, check_figure_spec_v10=enabled) if "_V10_" in row["code"]}


def test_complete_section18_spec_clears_v10():
    assert _codes(_replace(_card(), HEADER + ROW)) == set()


def test_v10_is_separate_opt_in_and_closes_section18_plan_prose():
    assert _codes(_card(), enabled=False) == set()
    assert "SECTION_18_V10_FIGURE_SPECIFICATION_MISSING" in _codes(_card())


def test_finished_profile_has_no_unrendered_self_asserted_terminal_state():
    card = _replace(_card(), HEADER + ROW.replace(
        "FIGURE_RENDERED_REVIEWED", "FIGURE_NOT_RENDERED_TYPED", 1))
    assert "SECTION_18_V10_FIGURE_STATE_INVALID" in _codes(card)


def test_identity_interval_and_hashes_are_exact():
    card = _replace(_card(), HEADER + ROW.replace(IDENTITY, "SYNTH-001 / BGC007", 1))
    assert "SECTION_18_V10_IDENTITY_INCOMPLETE" in _codes(card)
    card = _replace(_card(), HEADER + ROW.replace("100-400 bp", "400-100 bp", 1))
    assert "SECTION_18_V10_INTERVAL_INVALID" in _codes(card)
    card = _replace(_card(), HEADER + ROW.replace(MAP_SHA, "map", 1))
    assert "SECTION_18_V10_LOCUS_MAP_RECEIPT_INVALID" in _codes(card)
    card = _replace(_card(), HEADER + ROW.replace(VISUAL_SHA, "review", 1))
    assert "SECTION_18_V10_VISUAL_REVIEW_RECEIPT_INVALID" in _codes(card)


def test_format_evidence_provenance_and_sidecar_states_are_fixed():
    replacements = (
        ("PNG+SVG+CSV", "PNG", "SECTION_18_V10_FORMAT_SET_INCOMPLETE"),
        ("ENCODED_WITH_EXPLICIT_MISSING", "ENCODED", "SECTION_18_V10_EVIDENCE_ENCODING_INVALID"),
        ("PRESENT_PACKAGE_RELATIVE_SOURCES", "PRESENT", "SECTION_18_V10_PROVENANCE_FOOTER_INVALID"),
        ("VERIFIED_ALL_GENES", "PRESENT", "SECTION_18_V10_SIDECAR_UNVERIFIED"),
    )
    for old, new, code in replacements:
        assert code in _codes(_replace(_card(), HEADER + ROW.replace(old, new, 1)))


def test_uncertainty_labels_and_visual_state_are_substantive():
    card = _replace(_card(), HEADER + ROW.replace(
        "boundary uncertainty and missing coverage labels remain visibly explicit", "looks good", 1))
    assert "SECTION_18_V10_UNCERTAINTY_LABELS_MISSING" in _codes(card)
    card = _replace(_card(), HEADER + ROW.replace("PASS_OWNER_REVIEWED", "PASS", 1))
    assert "SECTION_18_V10_VISUAL_REVIEW_STATE_INVALID" in _codes(card)


def test_exactly_one_section18_row_is_required():
    card = _replace(_card(), HEADER + ROW + "\n" + ROW)
    assert "SECTION_18_V10_ROW_COUNT" in _codes(card)


def test_structure_gate_forwards_v10():
    codes = {row["code"] for row in lint_card(
        _card(), check_publication_quality=True, check_figure_spec_v10=True)}
    assert "SECTION_18_V10_FIGURE_SPECIFICATION_MISSING" in codes


def test_cli_exposes_separate_v10_switch():
    args = build_parser().parse_args(["verify-modeb", "candidate.md", "--figure-spec-v10"])
    assert args.figure_spec_v10 is True
    assert args.selection_process_v9 is False
