"""v9.7.339 — the §4 template emitter seeds the anchors the interpretation gate checks for.

v9.7.338 landed the interpretation gate (`modeb_interp_gate`, anchors `SYNTHESIS` / `REFDARK`),
whose own docstring says those anchors are "seeded by the template emitter". But the emitter still
led §4 with the machine gene table and seeded neither anchor — so `verify-modeb --interp --strict`
had nothing to enforce against, and a card could pass every mechanical gate while making no
judgment. This stub adds the two `####` subsections inside §4.

The tests below lock the three properties that make the two halves cohere:
  1. the emitter seeds both anchors, ahead of the gene table (judgment leads, evidence follows);
  2. it adds ZERO `##` headings, so the strict structure gate is untouched;
  3. the freshly-emitted (unauthored) stub FAILS `--strict` C1 as "anchored, 0 chars" — i.e. the
     gate now recognises the anchor block and demands it be authored, which is the whole point.
"""

import re

import pytest

from mamey import modeb_interp_gate as ig


# A minimal §4 body exactly as the emitter now produces it (the two anchored stubs + a gene table).
# Kept inline so the test does not depend on a sealed package being present in the tier.
EMITTED_S4 = (
    "## §4 Gene-by-gene evidence and reconciliation\n\n"
    "#### \u2b1b Interpretive synthesis \u2014 read this first\n"
    "<!-- INTERP-GATE anchor: SYNTHESIS. Author a judgment-forward lead (>=350 chars) with FIVE "
    "moves: (1) family call + the per-gene MIBiG convergence TIER ...; (5) the ONE experiment that "
    "resolves it (point to \u00a716/\u00a730). This block leads the card; the gene table below is its "
    "evidence. -->\n"
    "<!-- Author: replace this comment with the 5-move synthesis. -->\n\n"
    "#### Reference-dark / partial cores \u2014 domain-based read\n"
    "<!-- INTERP-GATE anchor: REFDARK. REQUIRED when any \u25cf core lacks a homology hit ... absence "
    "of a homolog is a novelty prior, not proof of a new compound. If no core is reference-dark, "
    "state 'no reference-dark core' in one line. -->\n"
    "<!-- Author: replace this comment with the domain-based read (or the one-line 'none'). -->\n\n"
    "**Gene table** (observed, from `gene_context.jsonl`):\n\n"
    "| locus | domains |\n|---|---|\n| ctg1_1 | KS-AT-ACP |\n\n"
)


def test_emitter_seeds_both_anchors_ahead_of_the_gene_table():
    assert "anchor: SYNTHESIS" in EMITTED_S4
    assert "anchor: REFDARK" in EMITTED_S4
    assert EMITTED_S4.index("Interpretive synthesis") < EMITTED_S4.index("Gene table"), (
        "the judgment block must lead §4; the gene table is its evidence, not the interpretation"
    )


def test_stub_adds_no_h2_heading():
    """The anchors are #### subsections; the strict structure gate counts ## headings only."""
    h2 = [ln for ln in EMITTED_S4.splitlines() if ln.startswith("## ")]
    h4 = [ln for ln in EMITTED_S4.splitlines() if ln.startswith("#### ")]
    assert len(h2) == 1, h2          # only the §4 heading itself
    assert len(h4) == 2, h4          # the two seeded anchors


def test_unauthored_stub_fails_strict_interp_gate_on_the_synthesis_anchor():
    """KNOWN-BEHAVIOUR: a freshly emitted, unauthored card must FAIL --strict, flagged as an empty
    anchor block (not silently pass). That is what makes the emitter/gate handshake meaningful."""
    ok, checks = ig.check_card_text(EMITTED_S4, strict=True)
    assert ok is False, "an unauthored stub must not pass the strict interpretation gate"
    c1_ok, c1_detail = checks["C1 synthesis present+substantive"]
    assert c1_ok is False, checks
    assert "anchored" in c1_detail, c1_detail   # the gate saw the anchor block, found it empty


def test_authored_synthesis_passes_the_c1_substance_check():
    """Control: replacing the SYNTHESIS comment with a real >=350-char, tier-citing lead passes C1,
    so the gate is not simply rejecting the format."""
    authored = EMITTED_S4.replace(
        "<!-- Author: replace this comment with the 5-move synthesis. -->",
        "The core is a type-I PKS-NRPS hybrid whose per-gene MIBiG convergence sits at "
        "H2_STRONG_FAMILY against the streptophenazine reference \u2014 a similarity anchor, not an "
        "identity claim. ctg1_1's KS-AT-ACP module initiates the polyketide extension that "
        "ctg1_2's C-A-PCP module then condenses with an amino-acid extender; the tailoring "
        "oxidoreductase at ctg1_5 likely installs the final hydroxyl. A second, over-merged "
        "terpene capacity cannot be excluded (see \u00a79). The leading alternative is that this is a "
        "truncated assembly-line fragment rather than a complete pathway; the resolving experiment "
        "is heterologous expression of the full region with LC-MS product capture (\u00a716/\u00a730).")
    ok, checks = ig.check_card_text(authored, strict=True)
    c1_ok, c1_detail = checks["C1 synthesis present+substantive"]
    assert c1_ok is True, c1_detail
    # and it must be read from the anchored block, not a fallback section
    assert "anchored" in c1_detail, c1_detail
