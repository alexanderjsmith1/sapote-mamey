"""v9.7.246 — a fabricated observation shipped in 74 cards, and every guard passed it.

The §4 authoring template hardcoded a REAL per-gene BLASTp result belonging to *Amycolatopsis* sp.
NPDC004378 (`Wheelhouse/validations/BGC006_online_blastp.csv`):

    "per-gene BLASTp overturned two of ten on BGC006 (beta-lactamase->esterase, phenol-hydroxylase->ferritin)"
    "the offline, deterministic channel that settled BGC006 ctg12_71"

Templated, it was emitted verbatim into every card of every strain — asserting a specific BLASTp outcome
for strains on which no BLASTp had been run, and citing `ctg12_71`, a locus that exists on neither AS-421
(BGC006 is on NODE_1) nor AS-188 (NODE_16).

Two defects, two fixes:
  1. the template must not carry another organism's loci, scores, or BGC ids  (source)
  2. the gate must refuse a card citing a locus_tag absent from that strain's CDS table  (net)
"""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mamey.modeb_template_emitter import _section_body
from mamey.modeb_structure_gate import lint_card, readiness_state, _READINESS_BLOCKING

FOREIGN = re.compile(r"ctg\d+_\d+|two of ten|lactamase\u2192esterase|phenol-hydroxylase\u2192ferritin|score 3734")


def _phantom(findings):
    return [f for f in findings if f.get("code") == "PHANTOM_LOCUS"]


def test_no_emitted_section_carries_another_strains_specifics():
    for n in (1, 2, 3, 4, 5, 7, 8, 11, 14, 16, 21, 27):
        body = _section_body(n, {"bgc": "BGC001"}, {})
        assert not FOREIGN.search(body), f"§{n} still emits a foreign strain's specifics"


def test_section_4_keeps_the_methodology_and_cites_the_validation_set():
    body = _section_body(4, {"bgc": "BGC001", "gene_rows": []}, {})
    assert "hypothesis, not function" in body                       # the lesson survives
    assert "validations/BGC006_online_blastp.csv" in body           # the numbers live where they belong
    assert "do not cite its loci here" in body


def test_section_8_keeps_the_kcb_lesson_without_the_foreign_id_and_score():
    body = _section_body(8, {"bgc": "BGC001"}, {})
    assert "colibrimycin-class fix" in body and "BGC006" not in body and "3734" not in body


def test_phantom_locus_is_an_error_and_blocks_release():
    ctx = {"known_loci": {"ctg1_5", "ctg1_6"}}
    leaked = "## §4\nThe channel that settled BGC006 ctg12_71 (esterase, not beta-lactamase).\n"
    f = _phantom(lint_card(leaked, bgc_context=ctx))
    assert f and f[0]["severity"] == "ERROR"
    assert "ctg12_71" in f[0]["found"]
    assert "PHANTOM_LOCUS" in _READINESS_BLOCKING
    assert readiness_state(lint_card(leaked, bgc_context=ctx)) not in ("RELEASE_READY", "OWNER_REVIEW_CANDIDATE")  # v9.7.372: ladder renamed; a leak must never reach the mechanical ceiling


def test_real_loci_of_this_strain_pass_clean():
    ctx = {"known_loci": {"ctg10_10", "ctg10_11"}}
    card = "## §4\nctg10_10 and ctg10_11 carry the KS domain.\n"
    assert not _phantom(lint_card(card, bgc_context=ctx))


def test_silent_when_the_strains_loci_are_unknown():
    """Cannot judge what it cannot see. No CDS table -> no verdict, rather than a false accusation."""
    leaked = "## §4\nBGC006 ctg12_71 settled the call.\n"
    assert not _phantom(lint_card(leaked, bgc_context={}))
    assert not _phantom(lint_card(leaked, bgc_context={"known_loci": set()}))
