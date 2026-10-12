"""Caption/operator separation with the unchanged publication wording guard."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def helper(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    spec = importlib.util.spec_from_file_location("figure_methods_caption_subject", ROOT / "tools/figure_methods.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

@pytest.mark.parametrize("workflow", ["phylo_placement", "gtotree_coregenome", "iqtree_ml", "domain_tree", "ani_fastani"])
def test_every_builtin_default_caption_passes_real_guard(helper, workflow):
    from caption_guard import check_caption
    caption = helper.caption(workflow)
    assert caption and helper.blurb(workflow) in caption and "References:" in caption
    assert check_caption(caption) == []
    assert helper.CLAIM_SAFETY not in caption
    notes = helper.operator_notes(workflow)
    assert helper.OPERATOR_NOTES[workflow] in notes and helper.CLAIM_SAFETY in notes
    assert check_caption(notes, raises=False), "operator notes remain outside publication text"

@pytest.mark.parametrize("field", ["result", "extra"])
@pytest.mark.parametrize("text", ["judgment deferred", "NOT compound identity"])
def test_caller_governance_text_remains_intact_and_is_refused(helper, field, text):
    from caption_guard import check_caption, CaptionGovernanceError
    caption = helper.caption("phylo_placement", **{field: text})
    assert text in caption
    with pytest.raises(CaptionGovernanceError): check_caption(caption)


def test_caller_metadata_preserved_without_version_discovery(helper, monkeypatch):
    from caption_guard import check_caption
    def fail(): pytest.fail("caption must not probe tools")
    monkeypatch.setattr(helper, "detect_versions", fail)
    text = helper.caption("phylo_placement", versions={"epa-ng": "0.3.8"},
                          params={"model": "RECORDED_MODEL", "n_reference": 3},
                          result="Three records retained.", extra="Selected reference panel.")
    assert "epa-ng v0.3.8" in text and "model=RECORDED_MODEL" in text
    assert "n_reference=3" in text and "Result: Three records retained." in text
    assert "Selected reference panel." in text and check_caption(text) == []


def test_defaults_do_not_assert_unverified_procedures_or_taxonomic_certainty(helper):
    placement = helper.caption("phylo_placement")
    assert "high-quality type-strain" not in placement and "confidence" not in placement
    assert "relative likelihood weight" in placement and "reference sampling" in placement
    iqtree = helper.caption("iqtree_ml")
    assert "selected automatically" not in iqtree and "recorded substitution model" in iqtree
    domain = helper.caption("domain_tree")
    assert "Tips represent domain sequences" in domain and "paralogy" in domain
    assert "mapped fragments" in helper.caption("ani_fastani")


def test_unknown_workflow_fails_in_both_reader_and_operator_interfaces(helper):
    with pytest.raises(KeyError): helper.caption("unknown_workflow")
    with pytest.raises(KeyError): helper.operator_notes("unknown_workflow")
