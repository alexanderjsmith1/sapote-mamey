"""Path 1 regression — enrichment section header format.

BUG FOUND (2026-06-24): compose_enrichment() generators produce *unnumbered* headers of the form
  "§ Rarest domains."
but mode_b_quality_gate._RE_ENRICHMENT_HEAD looks for *numbered* headers:
  §11, §12, ..., §20

This means _enrichment_chars() ALWAYS returns (0, 0) for cards built with compose_enrichment(),
so every such card fails the §11–§20 floor check even when enrichment content is fully present.

Fix required (in mamey/enrichment_sections.py or compose_enrichment()):
  Either number the headers at compose time:
    text = re.sub(r'^§ ', f'## §{section_num} ', block, count=1, flags=re.M)
    section_num += 1
  Or replace the leading "§ Name." with "## §NN Name." in each generator directly.

These tests will FAIL on the current tree. They pass when the fix is applied.
"""
import re
import pytest
from collections import Counter
from mamey.enrichment_sections import (
    Gene, compose_enrichment, genome_domain_frequency,
    emit_rarest_domains, emit_rarest_genes, emit_domain_inventory,
)
from mamey.mode_b_quality_gate import _RE_ENRICHMENT_HEAD, _enrichment_chars


def _g(locus, doms, aa=300):
    return Gene(locus, tuple(doms), aa)


_STANDARD_GENES = [
    _g("ctg1_10", ["AMP-binding", "Condensation", "PP-binding"], aa=1200),
    _g("ctg1_11", ["PKS_KS", "PKS_AT", "KR"], aa=1800),
    _g("ctg1_12", ["MerR_1"], aa=220),
    _g("ctg1_13", ["FMO-like", "Flavin_binding"], aa=560),
    _g("ctg1_14", ["Halogenase"], aa=480),
    _g("ctg1_15", ["NRPS-A_a3", "NRPS-A_a6"], aa=900),
]


@pytest.fixture
def standard_setup():
    genes = _STANDARD_GENES
    freq = genome_domain_frequency({"BGC_TEST": genes})
    text, used = compose_enrichment(genes, freq, "NRPS", floor=1000)
    return text, used


def test_compose_enrichment_produces_numbered_section_headers(standard_setup):
    """compose_enrichment() output must contain at least one §11–§20 header.

    CURRENTLY FAILS: generators produce '§ Rarest domains.' (unnumbered).
    Fix: number headers at compose time so _RE_ENRICHMENT_HEAD can detect them.
    """
    text, used = standard_setup
    matches = _RE_ENRICHMENT_HEAD.findall(text)
    assert matches, (
        f"compose_enrichment() output contains no §11–§20 headers.\n"
        f"Sections used: {used}\n"
        f"First 400 chars: {text[:400]!r}\n"
        "BUG: generators produce unnumbered '§ Name.' headers — "
        "_enrichment_chars() cannot detect them. Fix: number at compose time."
    )


def test_enrichment_chars_detects_compose_enrichment_output(standard_setup):
    """_enrichment_chars() must return n_headers >= 1 for compose_enrichment() output.

    CURRENTLY FAILS: same root cause — unnumbered headers not detected.
    """
    text, used = standard_setup
    n_heads, char_count = _enrichment_chars(text)
    assert n_heads >= 1, (
        f"_enrichment_chars() returned n_heads={n_heads} for compose_enrichment() output "
        f"({len(text)} chars, sections={used}). "
        "The quality gate will report enrichment=0 for this card."
    )
    assert char_count >= 1000, (
        f"_enrichment_chars() returned char_count={char_count} (< 1,000 floor). "
        f"n_heads={n_heads}. The card will be SHALLOW despite valid enrichment content."
    )


def test_section_numbers_are_sequential_11_to_20(standard_setup):
    """Numbered headers must be in the §11–§20 range and sequential.

    After fix: expects §11, §12, §13 ... in the order sections were emitted.
    """
    text, used = standard_setup
    nums = [int(m) for m in re.findall(r'§(1[1-9]|20)\b', text)]
    assert nums, "No numbered §11–§20 headers found — see above test for root cause."
    assert nums == sorted(nums), f"Section numbers are not sequential: {nums}"
    assert all(11 <= n <= 20 for n in nums), (
        f"Section numbers outside §11–§20 range: {nums}"
    )
    # Each section name in 'used' should have a corresponding numbered header
    assert len(nums) == len(used), (
        f"Mismatch: {len(used)} sections used but {len(nums)} numbered headers found. "
        f"Sections: {used}, headers: {nums}"
    )


def test_floor_1000_reached_when_headers_present():
    """Once headers are correctly numbered, a standard gene set reaches the 1000c floor."""
    genes = _STANDARD_GENES
    freq = genome_domain_frequency({"BGC_TEST": genes})
    text, used = compose_enrichment(genes, freq, "NRPS", floor=1000)
    # This assertion already passes (the content is long enough)
    assert len(text) >= 1000, (
        f"compose_enrichment() returned only {len(text)} chars — catch-alls failed."
    )
    # This is the gated assertion that requires the header fix:
    _, char_count = _enrichment_chars(text)
    assert char_count >= 1000, (
        f"Even with {len(text)} total chars, _enrichment_chars() measured only "
        f"{char_count}. Root cause: unnumbered headers. Apply the header-numbering fix."
    )


# ── v9.7.125 (audit item 4): end-to-end enrichment → quality-gate detection ──────
def test_compose_enrichment_output_detected_by_quality_gate():
    """The audit's end-to-end concern: compose_enrichment() output, embedded in a card,
    must be detected as §11–§20 enrichment by the live quality gate — not only counted by
    the helper. This closes the loop the AS-902 unnumbered-header bug exposed."""
    from mamey.enrichment_sections import Gene, compose_enrichment, genome_domain_frequency
    from mamey.mode_b_quality_gate import _enrichment_chars

    genes = [
        Gene("ctg1_1", ("KS", "AT", "KR"), 1500),
        Gene("ctg1_2", ("Condensation", "AMP-binding"), 1200),
        Gene("ctg1_3", ("Halogenase",), 500),
    ]
    freq = genome_domain_frequency({"BGC001": genes})
    enrich, used = compose_enrichment(genes, freq, "T1PKS")
    assert used, "compose_enrichment produced no sections"

    card = (
        "## BGC001 (NODE_1 · region001)\n"
        "§1 §2 §3 §4 §5 §6 §7 §8 §9 §10 core card body content.\n"
        + enrich
    )
    n_heads, chars = _enrichment_chars(card)
    assert n_heads >= 1, f"quality gate detected no §11–§20 headers in composed card: {enrich[:80]!r}"
    assert chars > 0
    # the numbered headers must be sequential from §11
    import re
    nums = [int(n) for n in re.findall(r"§(\d+)", enrich)]
    assert nums == list(range(11, 11 + len(nums))), f"non-sequential enrichment numbering: {nums}"
