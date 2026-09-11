"""verify-modeb must not certify §4 coverage it never actually checked.

Context — the recurring AS-846 BGC054 failure. The pure §4_BLASTP_COVERAGE gate scores a card-only
call against the card's OWN core rows (bgc_context=None -> denominator collapses to n_card_cores).
That card-only behaviour is intentional and locked by test_modeb_core_denominator_v9_7_323
(a 2-covered card returns clean with no context). The hole is one layer up: `verify-modeb` printed a
bare "OK" for a card run WITHOUT --package/--bgc, so a thin §4 that listed reconciled BLASTp verdicts
for the few rows it showed (BGC054 shipped 3 core rows) read as coverage-verified when it never was.

These assert the command-layer guard `_coverage_unverified_reason`:
  * fires when §4 asserts CONFIRM/REFINE/OVERTURN verdicts but no authoritative package core count
    reached the gate (card-only, or a --package/--bgc that yielded no count);
  * stays silent once a real package core count is available (item 5's coverage check then runs);
  * stays silent when §4 makes no reconciled BLASTp claim (nothing to certify).
"""
from mamey.authored_verify import _coverage_unverified_reason

# a §4 grid modelled on the real BGC054 card: reconciled per-gene BLASTp verdicts, 3 core rows.
CARD_S4_VERDICTS = (
    "## §4 — Evidence grid\n"
    "| Locus | BLASTp (nr) | %id | Recon |\n|---|---|---|---|\n"
    "| ctg8_205 ● | type I PKS [Amycolatopsis sp. lyj-112] | 93.5% | CONFIRM |\n"
    "| ctg8_216 ● | TOMM precursor [Amycolatopsis oliviviridis] | 98.3% | CONFIRM |\n"
    "| ctg8_183 ● | response regulator [Amycolatopsis coloradensis] | 98.0% | REFINE |\n"
    "## §5\n"
)
CARD_NO_VERDICT = "## §4\nNo per-gene BLASTp was run for this BGC; antiSMASH-Pfam labels only.\n## §5\n"


def test_card_only_run_flags_coverage_unverified():
    # no package context at all -> completeness was never checked against a real core count
    assert _coverage_unverified_reason(CARD_S4_VERDICTS, None)
    assert _coverage_unverified_reason(CARD_S4_VERDICTS, {})


def test_package_supplied_but_no_core_count_still_flags():
    # e.g. wrong --bgc or a package with no gene table: ctx exists but carries no core count
    assert _coverage_unverified_reason(CARD_S4_VERDICTS, {"bgc_id": "BGC054", "has_blastp_panel": True})


def test_authoritative_core_count_silences_it():
    # once the real rule-based core count reaches the gate, item 5's coverage check is the real one
    assert _coverage_unverified_reason(CARD_S4_VERDICTS, {"n_core_genes": 38}) is None
    assert _coverage_unverified_reason(CARD_S4_VERDICTS, {"core_gene_count": 10}) is None


def test_no_reconciled_verdict_no_warning():
    # §4 makes no CONFIRM/REFINE/OVERTURN claim -> there is nothing to certify
    assert _coverage_unverified_reason(CARD_NO_VERDICT, None) is None
