"""test_sprint1_linters.py — claim-safety linter + locator reconciliation (v9.7.122).

Sprint-1 ideas from the ChatGPT patch chat, hardened and adopted as post-hoc validators:
  - claim_safety_linter: flags identity overclaims and unanchored KCB mentions, WITHOUT
    false-positives on claim-safe capacity language.
  - locator_reconciliation: flags card header fields that drift from the canonical triage
    row (the AS-900 stale-locator failure mode).
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "tools"))

from claim_safety_linter import lint_claim_safety  # noqa: E402
from locator_reconciliation import reconcile_card, extract_card_header_fields  # noqa: E402


# ── claim-safety linter ────────────────────────────────────────────────────────
def test_claim_safe_capacity_language_passes():
    safe = [
        "The cluster produces a polyketide backbone consistent with the class.",
        "Biosynthetic capacity consistent with a kirromycin-like compound.",
        "KCB anchor: kirromycin — similarity anchor, not a product identity.",
        "This BGC produces secondary metabolites of the lanthipeptide class.",
        "Capacity consistent with a macrolide-like product; KCB = similarity not identity.",
    ]
    for s in safe:
        assert lint_claim_safety(s) == [], f"false positive on claim-safe text: {s!r}"


def test_identity_overclaim_is_flagged():
    assert lint_claim_safety("This BGC produces kirromycin.")
    assert lint_claim_safety("The product is bottromycin.")


def test_kcb_without_ceiling_is_flagged():
    assert lint_claim_safety("KnownClusterBlast hit to planosporicin confirms the compound.")


def test_kcb_with_ceiling_passes():
    assert lint_claim_safety(
        "KCB hit: planosporicin-like similarity anchor (not a product identity)."
    ) == []


# ── locator reconciliation ─────────────────────────────────────────────────────
_CARD = """**BGC_ID:** BGC001
**Assembly_Locator:** NODE_10_length_199265 region001 (BGC001)
**Node_ID:** NODE_10_length_199265
**Products:** RiPP; azole-containing-RiPP
**Boundary:** Interior
"""

_GOOD_ROW = {
    "bgc_id": "BGC001",
    "user_label": "NODE_10_length_199265 region001 (BGC001)",
    "contig": "NODE_10_length_199265",
    "products": "RiPP; azole-containing-RiPP",
    "edge_status": "Interior",
}


def test_header_fields_parse_without_markdown_markers():
    fields = extract_card_header_fields(_CARD)
    assert fields["BGC_ID"] == "BGC001"
    assert fields["Node_ID"] == "NODE_10_length_199265"
    assert "*" not in fields["Products"]


def test_matching_card_and_triage_reconcile_clean():
    assert reconcile_card(_CARD, _GOOD_ROW) == []


def test_stale_node_is_flagged():
    bad = dict(_GOOD_ROW, contig="NODE_99_WRONG")
    errs = reconcile_card(_CARD, bad)
    assert len(errs) == 1
    assert errs[0]["field"] == "Node_ID"


def test_stale_products_is_flagged():
    bad = dict(_GOOD_ROW, products="saccharide")
    errs = reconcile_card(_CARD, bad)
    assert any(e["field"] == "Products" for e in errs)


def test_absent_on_both_sides_is_not_a_mismatch():
    card_no_boundary = "\n".join(
        ln for ln in _CARD.splitlines() if not ln.startswith("**Boundary")
    )
    row_no_boundary = {k: v for k, v in _GOOD_ROW.items() if k != "edge_status"}
    assert reconcile_card(card_no_boundary, row_no_boundary) == []


# ── v9.7.125: calibration-driven refinements ────────────────────────────────────
def test_class_name_after_identity_verb_is_not_overclaim():
    """v9.7.125: compound-class names after are/is are capacity language, not identity.
    Calibration found 'are angucycline' / 'are anthracycline' false-positived in v9.7.124."""
    assert lint_claim_safety("These products are angucycline-class metabolites.") == []
    assert lint_claim_safety("The cluster encodes an anthracycline-type scaffold.") == []
    assert lint_claim_safety("Products are macrolide-class.") == []


def test_specific_compound_after_identity_verb_still_flags():
    """The class exemption must NOT swallow real specific-compound overclaims."""
    assert lint_claim_safety("This BGC produces kirromycin.")
    assert lint_claim_safety("The cluster produces erythromycin as its output.")
    assert lint_claim_safety("The product is bottromycin.")


def test_kcb_in_machine_data_line_is_not_flagged():
    """v9.7.125: KCB-without-ceiling is scoped to prose; pipe-delimited / accession-bearing
    machine-data rows are skipped (these drove a 30.6% FP rate in v9.7.124)."""
    machine = "NRPS BGC0000609.3 | nocathiacin | knownclusterblast #1 BGC0000609.3"
    assert lint_claim_safety(machine) == []
    accession = "BGC0001027.5 | nocobactin NA | knownclusterblast top hit"
    assert lint_claim_safety(accession) == []


def test_kcb_in_prose_without_ceiling_still_flags():
    """KCB mentioned in authored prose without ceiling language must still flag."""
    assert lint_claim_safety("KCB analysis shows this is the nosiheptide cluster.")


# ── v9.7.125b: AS-901 dogfood regression (copula-in-prose false positives) ──────
# Batch 1 produced a 100% false-positive rate (63/63) because the bare copula "is/are X"
# read every descriptive predicate as a compound identity. These are verbatim from that corpus.
AS901_FALSE_POSITIVE_SENTENCES = [
    "This BGC is Edge-status and therefore truncated.",
    "No activity is assumed at the extract level.",
    "No activity is attributed to this locus without fractionation.",
    "These are routing priors, not bioactivity measurements.",
    "The core peptides are protease-resistant.",
    "The boundary is interior to the contig.",
    "The precursor is captured in the assembly.",
    "The annotation is complete for this region.",
    "The product class is unknown without isolation.",
    "The compound identity is unresolved.",
    "The pathway is inferred from domain content.",
    "The architecture is likely modular.",
    "A halogenase is present in the cluster.",
    "The signal is diagnostic of the class.",
]


def test_as103_copula_false_positives_all_clean():
    """No descriptive 'is/are <word>' predicate may flag as an identity overclaim."""
    for s in AS901_FALSE_POSITIVE_SENTENCES:
        assert lint_claim_safety(s) == [], f"AS-901 regression: false positive on {s!r}"


def test_production_verb_overclaims_still_caught():
    """Production verbs ('produces/synthesizes X') with a compound-shaped token still flag."""
    assert lint_claim_safety("This BGC produces kirromycin.")
    assert lint_claim_safety("The cluster synthesizes colibrimycin.")
    assert lint_claim_safety("The locus yields gobichelin.")


def test_copula_with_compound_set_flags_real_identity():
    """With the strain's compound set supplied, 'is <compound>' flags, 'is <descriptor>' does not."""
    cset = {"colibrimycin", "ikarugamycin", "gobichelin", "tambjamine"}
    assert lint_claim_safety("The product is colibrimycin.", compound_names=cset)
    assert lint_claim_safety("This BGC is Edge-status.", compound_names=cset) == []
    assert lint_claim_safety("The boundary is interior.", compound_names=cset) == []


# ── v9.7.125b: runner-flagged defensive checks from the AS-901 confirming re-run ──
def test_production_regex_actually_matches():
    """Runner concern #2: a regex-escaping regression would make _PRODUCTION_RE match NOTHING,
    silently turning every overclaim into a 'clean' pass (a fake 0% FP win). Assert directly."""
    from claim_safety_linter import _PRODUCTION_RE, _COPULA_RE
    assert _PRODUCTION_RE.search("produces ikarugamycin")
    assert _PRODUCTION_RE.search("synthesizes tambjamine")
    assert _PRODUCTION_RE.search("yields gobichelin")
    assert _COPULA_RE.search("is colibrimycin")
    assert _COPULA_RE.search("are angucyclines")


def test_multiname_kcb_top_extracts_leading_token():
    """Runner concern #1: a multi-name KCB_top field 'gobichelin A/gobichelin B' must yield the
    bare leading token 'gobichelin', so 'is gobichelin' matches the compound set, not just
    'is gobichelin A'."""
    import tempfile, csv
    from pathlib import Path
    from mamey.judgment_store import _strain_compound_names
    d = Path(tempfile.mkdtemp())
    with open(d / "AS-900_4_triage_board.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["BGC_ID", "KCB_top", "KCB_clusterblast"])
        w.writerow(["BGC001", "BGC0001.1 | gobichelin A/gobichelin B | knownclusterblast #1", ""])
    names = _strain_compound_names(d)
    assert "gobichelin" in names           # bare leading token
    assert "gobichelin a" in names         # full phrase still present


def test_is_gobichelin_flags_with_extracted_set():
    """End-to-end: 'is gobichelin' is a real overclaim and must flag when gobichelin is the
    strain's KCB anchor (extracted from a multi-name KCB_top field)."""
    cset = {"gobichelin", "gobichelin a", "gobichelin b", "colibrimycin"}
    assert lint_claim_safety("This product is gobichelin.", compound_names=cset)
    assert lint_claim_safety("The boundary is interior.", compound_names=cset) == []
