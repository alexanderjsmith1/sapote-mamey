"""v9.7.232: KCB-name-as-identity lint (catches the selvamicin failure) + §29 pad-lint exemption."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mamey.modeb_structure_gate import _kcb_identity_findings, _padding_findings

def _ki(fs): return [x for x in fs if (x.get("code") if isinstance(x, dict) else "") == "KCB_IDENTITY_RISK"]

def test_kcb_name_as_identity_flagged_unless_hedged():
    ctx = {"kcb_top": "BGC0000115.5 | selvamicin | knownclusterblast #1"}
    bad = "## §1 Identity\nThis BGC is selvamicin.\n\n## §8 Comparators\nIt is selvamicin, the antifungal.\n"
    hedged = "## §1 Identity\nBackbone similarity to selvamicin (KCB comparator, not identity).\n"
    assert _ki(_kcb_identity_findings(bad, ctx))
    assert not _ki(_kcb_identity_findings(hedged, ctx))
    assert not _ki(_kcb_identity_findings(bad, {}))          # needs kcb_top in context

def test_kcb_comparator_class_phrasing_is_flagged():
    """v9.7.233: '<comparator>-class' is the BGC046 failure the changelog cites — it MUST flag,
    not be exempted. Regression for the hedge-list hole where '-class' silently passed."""
    ctx = {"kcb_top": "BGC0000114.1 | selvamicin | knownclusterblast #1"}
    for sent in ("This is a selvamicin-class polyene.",
                 "The locus is a selvamicin-class antifungal cluster."):
        card = f"## §1 Identity\n{sent}\n"
        assert _ki(_kcb_identity_findings(card, ctx)), f"should flag: {sent!r}"

def test_generic_class_without_kcb_comparator_stays_clean():
    """The fix must not make the lint fire on generic capacity language. The trigger token is
    always the specific KCB comparator name; a generic class word with no matching comparator
    (or no kcb_top) must stay clean, preserving the general-linter's -class capacity exemption."""
    # kcb_top comparator is 'nystatin'; the card says 'macrolide-class' — different word, no match.
    ctx = {"kcb_top": "BGC0000115.5 | nystatin | knownclusterblast #1"}
    card = "## §1 Identity\nThese products are macrolide-class metabolites.\n"
    assert not _ki(_kcb_identity_findings(card, ctx))
    # and '-adjacent' remains a genuine hedge even on the comparator name itself
    hedged = "## §1 Identity\nA nystatin-adjacent scaffold, per KCB backbone similarity.\n"
    assert not _ki(_kcb_identity_findings(hedged, ctx))

def test_section_29_excluded_from_padding_scan():
    card = ("## §1 Identity\nBGC001.\n\n## §29 Cross-cluster interactions\n"
            "As with BGC012 and BGC034, precursors may be shared; read together with BGC099.\n")
    assert not _padding_findings(card)                        # §29 cross-refs are legitimate, not padding
