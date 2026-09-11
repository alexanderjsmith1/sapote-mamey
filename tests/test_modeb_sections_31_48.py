"""test_modeb_sections_31_48.py — behaviour tests for the §31–§48 contract extension (v9.7.364).

Requested by the Codex/Rootstock review of the v1 and v2 patches. The point of this file is that the
earlier tests only counted contract rows — they asserted the JSON had entries above 30 and that they
were labelled `optional`. That is not behaviour. It could not detect (and did not detect) the actual
defect in v1: both Markdown parsers were hard-capped at `1 <= num <= 30`, so a card with valid §31/§48
headings parsed to [] / {} and the sections were silently discarded while the row-counting tests
stayed green.

Every test below exercises the parser, the linter, or the predicates against real card text.
"""
from __future__ import annotations

import pytest

from mamey import modeb_structure_gate as g

CONTRACT = g.load_contract()
BY_NUM = {s["number"]: s["title"] for s in CONTRACT["sections"]}
BODY = "Measured content for this section, long enough to be a real body. " * 5


def _sec(num: int, title: str | None = None, body: str = BODY) -> str:
    return f"## §{num} {title if title is not None else BY_NUM[num]}\n\n{body}"


def _core() -> str:
    """A well-formed §1–§30 card."""
    return "\n\n".join(_sec(n) for n in range(1, 31))


def _codes(findings, *, section=None, code_contains=None, severity=None):
    out = findings
    if section is not None:
        out = [f for f in out if f.get("section") == section]
    if code_contains is not None:
        out = [f for f in out if code_contains in str(f.get("code", ""))]
    if severity is not None:
        out = [f for f in out if f.get("severity") == severity]
    return out


# --------------------------------------------------------------- contract shape

def test_contract_covers_exactly_1_to_48_and_extension_tiers_are_pinned():
    """Pins the FULL range and the tier of every extension row, so a partially-omitted
    extension cannot pass.

    v9.7.369 (announced change, full48 gate binding + W13 amendment; Cerulean + INDIGO2
    owner-ruled, the Developer or User green-lit 2026-08-17): seven extension sections flipped
    optional→conditional, bound to predicates the engine computes. §32–§34 bind to
    `has_measured_assembly_line` (W13: MEASURED architecture only — a bare PKS/NRPS
    class label never makes a section required), NOT `has_assembly_line`. The exact
    binding map is pinned here so a silent rebind fails this test."""
    nums = sorted(s["number"] for s in CONTRACT["sections"])
    assert nums == list(range(1, 49)), f"contract must cover §1–§48 exactly, got {nums[:5]}…{nums[-3:]}"
    ext = [s for s in CONTRACT["sections"] if s["number"] > 30]
    assert len(ext) == 18
    expected_conditional = {
        32: "has_measured_assembly_line",
        33: "has_measured_assembly_line",
        34: "has_measured_assembly_line",
        35: "multi_protocluster",
        36: "boundary_or_overmerge_flag",
        38: "has_resistance_signal",
        43: "has_4a_rows",
    }
    got_conditional = {s["number"]: s["condition_key"]
                       for s in ext if s["required"] == "conditional"}
    assert got_conditional == expected_conditional, (
        f"extension conditional bindings drifted: {got_conditional}")
    assert all(s["required"] == "optional"
               for s in ext if s["number"] not in expected_conditional)
    core = [s for s in CONTRACT["sections"] if s["number"] <= 30]
    assert {s["required"] for s in core} <= {"always", "conditional"}
    assert CONTRACT["schema_version"] == "modeb_corrective_full48_v1"


# --------------------------------------------------------------- 1–3 parser

def test_1_valid_section_31_title_is_detected():
    got = dict(g.extract_section_titles(_sec(31)))
    assert 31 in got and got[31] == BY_NUM[31]


def test_2_valid_section_48_title_is_detected():
    got = dict(g.extract_section_titles(_sec(48)))
    assert 48 in got and got[48] == BY_NUM[48]


def test_3_bodies_are_extracted_for_31_and_48():
    bodies = g.extract_section_bodies(_sec(31) + "\n\n" + _sec(48))
    assert bodies.get(31, "").strip(), "§31 body not extracted"
    assert bodies.get(48, "").strip(), "§48 body not extracted"


# --------------------------------------------------------------- 4–7 linter

def test_4_absent_optional_section_produces_no_missing_error():
    f = g.lint_card(_core())
    assert not _codes(f, code_contains="MISSING") or not [
        x for x in _codes(f, code_contains="MISSING") if (x.get("section") or 0) > 30]


def test_5_present_section_31_with_wrong_title_fails():
    f = g.lint_card(_core() + "\n\n" + _sec(31, "Completely Different Heading"))
    assert _codes(f, section=31, code_contains="TITLE", severity="ERROR")


@pytest.mark.parametrize("num,wrong", [
    (34, "Initiation release logic"),                                        # & stripped
    (36, "Boundary status overmerge locus splitting adjudication merged"),   # +, /, () stripped
    (38, "Co located resistance efflux"),                                    # hyphen + & stripped
    (48, "Cross cohort synthesis claim ceiling"),                            # hyphen + & stripped
])
def test_5b_punctuation_stripped_titles_do_not_pass(num, wrong):
    """the Developer or User selected punctuation-bearing titles deliberately. `_normalise()` strips all
    punctuation, which silently broadened the contract — these variants used to pass."""
    f = g.lint_card(_core() + "\n\n" + _sec(num, wrong))
    assert _codes(f, section=num, code_contains="TITLE", severity="ERROR"), (
        f"§{num} '{wrong}' must not satisfy '{BY_NUM[num]}'")


def test_6_duplicate_extension_section_is_an_error():
    """Two blocks claiming one registered slot make body ownership ambiguous; only the first is
    parsed, so the second is silently dropped."""
    f = g.lint_card(_core() + "\n\n" + _sec(31) + "\n\n" + _sec(31))
    assert _codes(f, section=31, code_contains="DUPLICATE", severity="ERROR")


def test_7_section_48_before_31_fails_ordering():
    f = g.lint_card(_core() + "\n\n" + _sec(48) + "\n\n" + _sec(31))
    assert _codes(f, code_contains="ORDER"), "out-of-order extension sections must be flagged"


def test_8_unknown_section_49_is_surfaced_not_discarded():
    f = g.lint_card(_core() + "\n\n## §49 Something Unregistered\n\n" + BODY)
    assert _codes(f, code_contains="UNKNOWN_SECTION_NUMBER"), (
        "§49 must be SURFACED; silently dropping it is the defect this extension removed")


def test_9_legacy_1_to_30_card_gains_no_extension_errors():
    """The back-compat promise, restated for v9.7.369 (announced change): extending the
    numbering must not change legacy VERDICTS — a §1–§30 card linted without context
    gains no extension ERROR. It MAY gain WARN-level CONDITIONAL_SECTION_NOT_EVALUATED
    breadcrumbs for the seven now-conditional sections (that is the fold's point: the
    gate says out loud that it could not evaluate extension depth, instead of being
    structurally silent). WARNs do not fail a card."""
    f = g.lint_card(_core())
    ext = [x for x in f if (x.get("section") or 0) > 30]
    assert not [x for x in ext if x.get("severity") == "ERROR"], (
        f"legacy card must gain no extension ERRORs: {ext}")
    assert all(x.get("code") == "CONDITIONAL_SECTION_NOT_EVALUATED"
               for x in ext), f"unexpected extension findings: {ext}"


def test_present_but_empty_extension_section_is_an_error_without_check_depth():
    """Body/depth floors only run under check_depth=True, but several callers lint without it.
    An empty registered section asserts coverage it does not have."""
    f = g.lint_card(_core() + f"\n\n## §31 {BY_NUM[31]}\n\n")
    assert _codes(f, section=31, code_contains="EMPTY", severity="ERROR")


# --------------------------------------------------------------- 10–12 predicates

DEFICIT_STATES = ["0", "false", "NONE", "NOT_PRODUCED", "NOT_MEASURED", "UNBOUND",
                  "MEASURED_NONE_FOUND", "SOURCE_UNAVAILABLE",
                  "SOURCE_PRESENT_ROW_MISSING", "IDENTITY_OR_JOIN_HOLD", "NOT_APPLICABLE"]

PREDICATE_KEYS = ["has_gene_table", "has_assembly_line", "has_4d_rows", "has_4a_rows",
                  "has_resistance_signal", "has_wider_comparison_set",
                  "has_reference_genomes", "has_gcf_assignment", "has_cohort_context",
                  "has_composition_stats"]


@pytest.mark.parametrize("state", DEFICIT_STATES)
def test_10_deficit_states_do_not_fire_predicates(state):
    """An allowlist of positive states, not a blacklist of negatives: an UNRECOGNISED string must
    never assert that evidence exists."""
    ctx = {k: state for k in ("n_4d_rows", "n_4a_rows", "module_count", "resistance_tier",
                              "wider_comparison_set", "reference_genomes", "gcf_id",
                              "gene_table", "cross_strain_identity", "gc_content")}
    p = g._build_predicates(ctx)
    fired = [k for k in PREDICATE_KEYS if p.get(k)]
    assert not fired, f"deficit state {state!r} wrongly fired {fired}"


def test_11_bound_4d_record_fires_section_41_applicability():
    assert g._build_predicates({"n_4d_rows": 3})["has_4d_rows"] is True
    assert g._build_predicates({"has_4d_rows": "PRESENT"})["has_4d_rows"] is True


def test_12_bound_rggmci_record_fires_section_43_applicability():
    assert g._build_predicates({"n_4a_rows": 5})["has_4a_rows"] is True
    assert g._build_predicates({"has_4a_rows": "BOUND"})["has_4a_rows"] is True


def test_12b_section_43_title_preserves_candidate_only_framing():
    """§43 is adjudication evidence, never a merge or a nucleotide join."""
    title = BY_NUM[43]
    assert "RG-GMCI" in title
    assert not any(w in title.lower() for w in ("merge", "merged", "join", "joined", "rescued"))


def test_predicates_require_more_than_a_roster_fact():
    """Tightenings Codex asked for: §39 needs a bound comparison (not cohort size), §40 needs
    provenance (not a bare family id), §42 needs a declared baseline (GC alone is not HGT)."""
    assert g._build_predicates({"cohort_size": 2})["has_cohort_context"] is False
    assert g._build_predicates({"cross_strain_identity": "PRESENT"})["has_cohort_context"] is True

    assert g._build_predicates({"gcf_id": "fam555"})["has_gcf_assignment"] is False
    assert g._build_predicates(
        {"gcf_id": "fam555", "gcf_run": "32", "bigscape_cutoff": "0.3",
         "qualified_family_id": "bigscape-gcf:v1/run/32/cutoff/0.3/family/fam555"})["has_gcf_assignment"] is True

    assert g._build_predicates({"gc_content": 0.72})["has_composition_stats"] is False
    assert g._build_predicates(
        {"gc_content": 0.72, "composition_baseline": "PRESENT"})["has_composition_stats"] is True
