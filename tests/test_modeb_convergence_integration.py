"""Test the per-gene MIBiG-convergence integration in Mode-B card authoring (v9.7.336 patch).

Drop into tests/. Asserts (1) a BGC with a convergence row emits the section with tier + verbatim
claim-safety, and (2) a reference-dark BGC (no row) emits the novelty-prior fallback. Reader-side only.
"""
import os
import csv
import tempfile
from mamey import modeb_cards


def _write_convergence(pkg, strain):
    """Minimal *_3_mibig_convergence.csv: one H2 concordant BGC, one absent (reference-dark)."""
    path = os.path.join(pkg, f"{strain}_3_mibig_convergence.csv")
    cols = ["bgc_id", "products", "boundary", "mibig_accession", "mibig_compound", "reference_type",
            "distinct_query_genes", "recognizable_gene_share", "median_pct_identity",
            "median_pct_coverage", "convergence_tier", "class_concordance", "convergence_rank",
            "dominance_status", "claim_safety"]
    rows = [dict(bgc_id="BGC001", products="phenazine", boundary="Interior",
                 mibig_accession="BGC0002010", mibig_compound="streptophenazine B",
                 reference_type="PKS", distinct_query_genes="25", recognizable_gene_share="0.625",
                 median_pct_identity="74.0", median_pct_coverage="99.0",
                 convergence_tier="H2_STRONG_FAMILY", class_concordance="CONCORDANT",
                 convergence_rank="1", dominance_status="CLEAR_DOMINANT",
                 claim_safety="Multi-gene convergence is direct sequence evidence for pathway-family "
                              "relatedness, not proof of exact product identity.")]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def test_convergence_loader_ranks_by_rank():
    with tempfile.TemporaryDirectory() as pkg:
        _write_convergence(pkg, "AS-TEST")
        conv = modeb_cards.load_convergence(pkg)
        assert "BGC001" in conv
        assert conv["BGC001"][0]["convergence_tier"] == "H2_STRONG_FAMILY"
        assert conv.get("BGC999") == [] or "BGC999" not in conv  # absent = reference-dark


def _render(conv_rows, conv_layer=True):
    """Render just enough of a card via card() with a stub rec/dd to reach the convergence block.

    v9.7.336: ``conv_layer`` says whether the package actually SHIPS
    ``*_3_mibig_convergence.csv``. It defaults to True here because these tests write one.
    """
    class _Rec:
        bgc = "BGC001"; cls = "phenazine"; contig = "NODE_1"; len_kb = 30.0
        is_edge = False; ab = 10; af = 20; novelty = 5; lead_tier = "Medium"; kcb_top = ""
    dd = {"BGC001": {"genes": {}, "domains": []}}
    ref = {}
    return modeb_cards.card("AS-TEST", _Rec(), dd, ref, [], {}, {}, {}, {}, {},
                            conv=conv_rows, conv_layer=conv_layer)


def test_card_emits_convergence_section_with_tier_and_claimsafety():
    with tempfile.TemporaryDirectory() as pkg:
        _write_convergence(pkg, "AS-TEST")
        rows = modeb_cards.load_convergence(pkg)["BGC001"]
    md = _render(rows)
    assert "## Per-gene MIBiG convergence — primary family evidence" in md
    assert "H2_STRONG_FAMILY" in md
    assert "lead-grade" in md
    assert "not proof of exact product identity" in md  # verbatim claim-safety reproduced


def test_reference_dark_bgc_emits_novelty_prior_fallback():
    """Layer PRESENT, no row for this BGC -> an evidence-backed reference-dark negative."""
    md = _render([], conv_layer=True)  # convergence table exists; this locus simply has no family
    assert "reference-dark" in md
    assert "novelty prior" in md
    assert "not** proof of a new compound" in md


def test_absent_convergence_layer_does_not_assert_reference_dark():
    """KNOWN-BAD (v9.7.336): the original patch printed the reference-dark novelty prior whenever
    ``conv`` was empty — including when the package carries no convergence table at all.

    Every package sealed before v9.7.332 lacks the layer, and the reporting-v2 gate deliberately
    treats those as LEGACY_NOT_APPLICABLE rather than invalid. So the first version of this
    integration would have printed a family-evidence conclusion, on EVERY BGC of every pre-.332
    package, derived from a file that was never written. Absence of a check is not a negative
    result — the same failure shape the whole v9.7.335 cut was about.

    NOTE for the cut chat: the incoming test asserted the novelty-prior text for the bare
    ``_render([])`` case, i.e. it codified this defect. That assertion is now scoped to
    ``conv_layer=True``. Bless the change consciously, as v9.7.335 did for test_blastp_online.
    """
    md = _render([], conv_layer=False)
    # Assert on the reference-dark branch's own distinctive sentence, not on the bare words: the
    # replacement text deliberately NAMES "reference-dark" and "novelty prior" in order to deny
    # them, and an unrelated priors caveat elsewhere in the card also contains "novelty prior".
    assert "Family evidence falls to" not in md, md[md.find("## Per-gene MIBiG"):][:400]
    assert "does not carry the per-gene MIBiG-convergence table" in md
    assert "not* a reference-dark finding" in md


def test_unknown_layer_presence_fails_safe():
    """conv_layer=None (presence never established) must use the conservative wording, not the prior."""
    md = _render([], conv_layer=None)
    assert "Family evidence falls to" not in md
    assert "no family-convergence statement can be made" in md


def test_layer_presence_probe_reads_the_real_directory():
    with tempfile.TemporaryDirectory() as pkg:
        assert modeb_cards.convergence_layer_present(pkg) is False
        _write_convergence(pkg, "AS-TEST")
        assert modeb_cards.convergence_layer_present(pkg) is True
