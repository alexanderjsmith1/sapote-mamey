"""Ruling 12: contract JSON wording matches the code; no requirement changed.

The `has_measured_assembly_line` descriptions said a PKS/NRPS class token triggers
§32-§34, which `_build_predicates` excludes. The full48 JSON also addressed LLMs,
carried a release prefix and cited the model-specific execution slice.
"""
import json
from pathlib import Path

from mamey.modeb_structure_gate import _build_predicates

DATA = Path(__file__).resolve().parents[1] / "mamey" / "data" / "mode_b"
FULL48 = json.loads((DATA / "modeb_full30_corrective_contract.json").read_text(encoding="utf-8"))
V2 = json.loads((DATA / "modeb_current50_v2_contract.json").read_text(encoding="utf-8"))


def test_measured_assembly_line_descriptions_match_the_predicate():
    for contract in (FULL48, V2):
        rows = [s for s in contract["sections"] if s.get("condition_key") == "has_measured_assembly_line"]
        assert [s["number"] for s in rows] == [32, 33, 34]
        for s in rows:
            assert "class token" not in s["condition_human"]
            assert "class label alone does not trigger" in s["condition_human"]
    # The code agrees: a class label alone is not a measured assembly line.
    assert _build_predicates({"products": "T1PKS,NRPS"})["has_measured_assembly_line"] is False
    assert _build_predicates({"module_count": 3})["has_measured_assembly_line"] is True


def test_full48_prose_fields_have_no_assistant_or_release_wording():
    assert "LLM" not in FULL48["section_policy"]
    assert "Keep the exact section titles and order" in FULL48["section_policy"]
    assert not FULL48["profile_note"].startswith("v9.")
    assert "CHATGPT" not in FULL48["source_protocol"]
