"""Locks the v9.7.180 evidence-channel wiring into the Mode B template emitter.

The BGC006/colibrimycin failure happened because §4 was authored from antiSMASH Pfam alone and
§8 stated a KCB anchor without gene coverage. The emitted template must now REQUIRE both the
kcb-frontpage corroboration tier (§8) and the blastp-online independent channel (§4), so the
failure is structurally prevented, not just discouraged. These tests fail if that wiring is
removed."""
from mamey.modeb_template_emitter import _section_body


def test_section8_requires_kcb_coverage_not_just_score():
    s8 = _section_body(8, {"kcb_top": "colibrimycin", "kcb_score": 3734, "gene_rows": []}, {})
    assert "COVERAGE" in s8
    assert "kcb-frontpage" in s8            # the tool that supplies the tier
    assert "COINCIDENTAL" in s8             # names the failure mode
    # v9.7.246: was "the BGC006/colibrimycin fix: score 3734". The lesson is portable; another
    # strain's BGC id and KCB score are not, and they were being emitted into every card.
    assert "colibrimycin-class fix" in s8   # the caught-in-the-wild case, without foreign specifics
    assert "BGC006" not in s8               # another strain's BGC id must not be templated in
    # NB: 3734 DOES appear here — it is this card's own kcb_score, passed in facts. A fact of the card
    # is not boilerplate. Only the hardcoded foreign id was the leak.


def test_section4_requires_blastp_online_channel():
    s4 = _section_body(4, {"bgc": "BGC006", "gene_rows": []}, {})
    assert "blastp-online" in s4
    assert "REQUIRED" in s4
    assert "CONFIRM / REFINE / OVERTURN" in s4  # the reconcile verdicts
    assert "never fabricate" in s4             # fail-closed honesty carried into authoring


def test_section4_names_the_bgc_in_the_command():
    # v9.7.371 (BLACK_CHERRY modeb_template_emitter_wrong_key_fix): the emitter's real facts key is
    # "bgc_id" (see _section_body's own `bgc = facts.get("bgc_id")`); the old "bgc" key here was
    # validating the bug — production facts never carried it, so cards said `--bgc BGC` literally.
    s4 = _section_body(4, {"bgc_id": "BGC023", "gene_rows": []}, {})
    assert "--bgc BGC023" in s4              # command is pre-filled with the actual BGC id


def test_section4_requires_hmm_adjudication_on_overturn():
    """The third channel: a BLASTp-vs-antiSMASH OVERTURN must route to the HMM domain tie-breaker.
    This completes the three-channel reconciliation (antiSMASH Pfam + BLASTp + HMM) as an enforced
    authoring step. (The ctg12_71 esterase adjudication is the caught case — it belongs to
    *Amycolatopsis* sp. NPDC004378 and must NOT appear in another strain's card; see
    tests/test_phantom_locus_v97246.py.)"""
    s4 = _section_body(4, {"bgc": "BGC006", "gene_rows": []}, {})
    assert "hmm-adjudicate" in s4
    assert "OVERTURN" in s4
    assert "SUPPORTS_BLASTP" in s4 and "SUPPORTS_ANTISMASH" in s4
    # the channel division of labour is stated so the author knows why both run
    assert "what the machine IS" in s4 and "whose machine" in s4
