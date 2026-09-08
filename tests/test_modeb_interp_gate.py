"""FA4: tests for the Mode-B interpretation gate (mamey/modeb_interp_gate.py).

Adapted from July-27 `test_modeb_interp_gate.py` to the in-bundle module + the engine's
`extract_section_bodies` section view. Asserts the gate:
  (1) FAILs a slot-filled card with no synthesis anchor,
  (2) PASSes a judgment-forward card carrying both anchors + a reference-dark domain read,
  (3) FAILs a fresh card whose synthesis anchor is present but unauthored (stub only),
  (4) is COMPLEMENTARY to the structure gate: a card that PASSes verify-modeb's structure view can
      still FAIL interp, and interp_findings are advisory WARN-severity (never blocking).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mamey import modeb_interp_gate as gate  # noqa: E402

SLOT_FILLED = """## §4 Gene-by-gene interpretation
**Gene table**
| Core | Locus | aa |
| ● | ctg1_1 | 3116 |
This locus has a big PKS core. — DATA REQUEST (nr)
## §9 Alternative hypotheses
It could be a PKS.
## §19 Final Mode B judgement
A PKS locus.
"""

JUDGMENT_FORWARD = """## §4 Gene-by-gene interpretation
#### Interpretive synthesis
<!-- INTERP-GATE anchor: SYNTHESIS -->
Family call: capacity consistent with a streptophenazine-class system at convergence tier
H2_STRONG_FAMILY (a similarity anchor, not identity). The core genes ctg1_5-ctg1_10 cooperate as a
phenazine core; a second type-II PKS cassette is co-encoded (over-merge, four protoclusters). The
leading alternative is a two-molecule multi-core read. The resolving experiment is HMM module-grammar
adjudication plus dual LC-HRMS/MS (see §16/§30). BLASTp nr and MIBiG convergence and domain grammar
all inform this.
#### Reference-dark / partial cores — domain-based read
<!-- INTERP-GATE anchor: REFDARK -->
ctg1_18 (952 aa) shows KS + AT + ACP domain grammar with no complete module resolved and no Swiss-Prot
hit — read from domain architecture as partial side-chain machinery, a novelty prior not proof.
**Gene table**
| ● | ctg1_18 | 952 | KS AT ACP |
## §9 Alternative hypotheses
(1) one phenazine producer. (2) a multi-core cluster-of-clusters. (3) a mayamycin neighbourhood.
## §19 Final Mode B judgement
Streptophenazine-class capacity co-encoded with a second aromatic-PKS capacity.
"""

STUB_ONLY = """## §4 Gene-by-gene interpretation
#### Interpretive synthesis
<!-- INTERP-GATE anchor: SYNTHESIS -->
<!-- Author: replace this comment with the 5-move synthesis. -->
#### Reference-dark / partial cores — domain-based read
<!-- INTERP-GATE anchor: REFDARK -->
<!-- Author: replace this comment with the domain-based read (or the one-line 'none'). -->
**Gene table**
| ● | ctg1_1 | 3116 | KS AT | — DATA REQUEST (nr)
## §9 Alternative hypotheses
## §19 Final Mode B judgement
"""


def test_slot_filled_fails():
    passed, res = gate.check_card_text(SLOT_FILLED)
    assert not passed
    assert res["C1 synthesis present+substantive"][0] is False
    assert res["C6 reference-dark domain read"][0] is False  # DATA REQUEST but no REFDARK read


def test_judgment_forward_passes():
    passed, res = gate.check_card_text(JUDGMENT_FORWARD)
    assert passed, res
    assert res["C2 cites convergence tier"][0]
    assert res["C6 reference-dark domain read"][0]


def test_unauthored_stub_fails():
    passed, res = gate.check_card_text(STUB_ONLY)
    assert not passed
    assert res["C1 synthesis present+substantive"][0] is False  # stub comment only


def test_interp_findings_are_advisory_and_complementary():
    # The slot-filled card FAILs interp; findings are WARN-severity (never blocking) and carry
    # INTERP_* codes so they compose with modeb_structure_gate findings under `verify-modeb --interp`.
    findings = gate.interp_findings(SLOT_FILLED)
    assert findings, "expected advisory findings for a slot-filled card"
    assert all(f["severity"] == "WARN" for f in findings)
    assert all(f["code"].startswith("INTERP_") for f in findings)
    # A passing card yields no findings (nothing to add on top of the structure gate).
    assert gate.interp_findings(JUDGMENT_FORWARD) == []


def test_strict_mode_requires_anchor():
    # In --strict mode the fallback to §-sections is disabled, so a card whose interpretation lives
    # only in §-sections (no anchor) fails C1. (SLOT_FILLED has no anchor and thin sections.)
    passed_default, _ = gate.check_card_text(SLOT_FILLED, strict=False)
    passed_strict, res_strict = gate.check_card_text(SLOT_FILLED, strict=True)
    assert passed_default is False and passed_strict is False
    assert res_strict["C1 synthesis present+substantive"][0] is False


def test_experiment_detector_accepts_normal_inflected_language():
    positives = (
        "The resolving experiment is a knockout plus rescue.",
        "Resolution requires isotope feeding.",
        "Use a discriminating assay with purified material.",
        "HMM adjudication will distinguish the alternatives.",
        "Expression in a validated host is the next experiment.",
    )
    for phrase in positives:
        assert gate.EXP.search(phrase), phrase
    assert gate.EXP.search("The family remains uncertain.") is None
