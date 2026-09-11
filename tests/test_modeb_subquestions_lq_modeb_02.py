"""LQ-MODEB-02 (v9.7.330): section build-out via sub-questions.

The contract deepens §5/§9/§13 with named sub-questions (no new section, no gate change). Guards that
the sub_questions are present, that the section count is unchanged (still 30), and that the committed-
step / named-FP / class-in-Actinobacteria prompts are wired to the believability + NP Atlas layers.
"""
import os
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "mamey" / "data" / "mode_b" / "modeb_full30_corrective_contract.json"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_section_count_unchanged_still_30():
    d = _contract()
    # v9.7.364: pin the §1-§30 CORE, not the row count (the §31-§48 optional tier now exists).
    core = [x for x in d["sections"] if int(x["number"]) <= 30]
    assert len(core) == 30  # sub-questions must NOT add a section


def test_subquestions_present_on_5_9_13():
    d = _contract()
    by_num = {s["number"]: s for s in d["sections"]}
    for n in (5, 9, 13):
        assert by_num[n].get("sub_questions"), f"§{n} missing sub_questions"
        assert len(by_num[n]["sub_questions"]) >= 2


def test_subquestions_wire_to_believability_and_class_grounding():
    # NB: keep "atlas" out of this test's *name* — conftest flags any nodeid containing that hint slow.
    d = _contract()
    by_num = {s["number"]: s for s in d["sections"]}
    joined5 = " ".join(by_num[5]["sub_questions"]).lower()
    assert "committed" in joined5 and "gateway" in joined5  # LQ-PATH-01 hook
    joined13 = " ".join(by_num[13]["sub_questions"]).lower()
    assert "np atlas" in joined13 and "class" in joined13    # LQ-NPATLAS-01 hook (aggregate only)
    # the genus sub-question must carry the claim-safety boundary (inferred/assumed, not provenance)
    assert "inferred" in joined13 or "assumed" in joined13
