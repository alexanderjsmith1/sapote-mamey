"""Runnable fixtures for the v9.7.412 card-surface checks (BLACK_CHERRY-412).

Committed at Codex's request (2026-09-07): a prose receipt is not a test. Each check has a
POSITIVE fixture (must fire) and the shared NEGATIVE fixture (must stay silent). The negative
fixture deliberately contains the token shapes most likely to cause a false positive.
"""
import pytest

from mamey.modeb_publication_gate import (
    _governed_term_findings,
    _section_disposition_uniform_findings,
    _table_separator_findings,
    _word_number_spacing_findings,
)

_DISPOSITION_MIXED = "".join(
    f"| {n} | {'SUBSTANTIVE' if n % 3 else 'REASONED_NOT_APPLICABLE'} | basis {n} | "
    f"NOT_APPLICABLE | scope {n} |\n"
    for n in range(1, 51))

CLEAN = (
    "# Mode B — AS-001 / NODE_1_length_1000_cov_10.5 / region001 / BGC001\n\n"
    "The engine 1.9.149 build 20260906v97411a produced 2 objects. The RG-GMCI census is bound.\n"
    "Protein ctg1_2 is 3743 aa. TIGR00001, PF00109, COG3321 and WP_123456 matched at 86.2% over\n"
    "3 HSPs; see PMC8851239 and doi 10.1002/cbic.201000214. SMCOG1022 and E0D202 are retained.\n"
    "Domains: PKS_KS1, PKS_AT2, PKS_KR3, ACP1, PKS_DH2, adh_short, RmlD_sub_bind.\n\n"
    "| Gene | NCBI nr top hit | nr identity |\n|---|---|---|\n"
    "| `ctg1_2` | WP_123456 · type I polyketide synthase | 86.2% |\n\n"
    "| Section | Disposition | Evidence basis | Historical | Scope |\n|---:|---|---|---|---|\n"
    + _DISPOSITION_MIXED)


def _codes(text):
    return sorted({f["code"] for check in (
        _word_number_spacing_findings, _governed_term_findings,
        _table_separator_findings, _section_disposition_uniform_findings)
        for f in check(text)})


# ── NEGATIVE: the fixture that keeps the checks honest ────────────────────────────────────
def test_clean_card_is_silent():
    """Identifiers, accessions, DOIs, domain names and a mixed table must not fire."""
    assert _codes(CLEAN) == []


@pytest.mark.parametrize("token", [
    "TIGR00001", "PF00109", "COG3321", "WP_123456", "PMC8851239", "SMCOG1022",
    "E0D202", "ctg1_2", "BGC001", "region001", "PKS_KS1", "NODE_1_length_1000_cov_10.5",
])
def test_legitimate_identifiers_do_not_fire_spacing(token):
    assert _word_number_spacing_findings(f"The roster records {token} as bound.\n") == []


# ── POSITIVE: one injected defect per class ───────────────────────────────────────────────
def test_glued_word_and_number_fires():
    assert _codes(CLEAN.replace("engine 1.9.149", "engine1.9.149")) == [
        "CARD_WORD_NUMBER_SPACING"]


def test_governed_term_transposition_fires():
    assert _codes(CLEAN.replace("RG-GMCI", "RG-GCMI")) == [
        "CARD_GOVERNED_TERM_MISSPELLED"]


def test_separator_cell_count_mismatch_fires():
    assert _codes(CLEAN.replace("|---|---|---|", "|---|---:|---:|---:|")) == [
        "CARD_TABLE_SEPARATOR_MISMATCH"]


def test_uniform_disposition_table_fires():
    uniform = "".join(
        f"| {n} | SUBSTANTIVE | same basis | NOT_APPLICABLE | same scope |\n"
        for n in range(1, 51))
    assert _codes(CLEAN.replace(_DISPOSITION_MIXED, uniform)) == [
        "SECTION_DISPOSITION_TABLE_UNIFORM"]


def test_uniform_check_tolerates_two_evidence_bases():
    """The real cards vary evidence basis at §48/§49 but are otherwise uniform.

    The condition is state + scope, deliberately NOT evidence basis: an earlier draft that also
    required a single basis did not fire on the real cards and would have reported a clean
    result over a rule that could not catch the defect it was written for.
    """
    rows = "".join(
        f"| {n} | SUBSTANTIVE | "
        f"{'literature receipt' if n in (48, 49) else 'packet receipt'} | NOT_APPLICABLE | "
        "same scope |\n" for n in range(1, 51))
    assert _codes(CLEAN.replace(_DISPOSITION_MIXED, rows)) == [
        "SECTION_DISPOSITION_TABLE_UNIFORM"]


def test_a_short_disposition_table_is_out_of_scope():
    """Fewer than 20 rows is not a §1–§50 contract table; stay silent."""
    rows = "".join(f"| {n} | SUBSTANTIVE | b | NOT_APPLICABLE | s |\n" for n in range(1, 6))
    assert _section_disposition_uniform_findings(CLEAN + rows) == []
