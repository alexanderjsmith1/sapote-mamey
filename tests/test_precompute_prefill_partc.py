"""Part C import hold and supplied-fact renderer coverage (§11/§14).

Renderer facts are fabricated presentation inputs, not admitted cohort evidence.
"""
import csv, os, tempfile, sys, pathlib
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mamey.modeb_template_emitter import _precompute_facts, _section_body

LOC = "NODE_9_length_167436_cov_37.933144 region003"

def _fixture(root):
    def w(fn, header, row):
        with open(os.path.join(root, fn), "w", newline="") as f:
            wr = csv.writer(f); wr.writerow(header); wr.writerow(row)
    w("COHORT_domain_architecture_by_bgc.csv",
      ["Strain", "BGC_ID", "Assembly_Locator", "architecture_archetype", "archetype_note", "domain_architecture_string"],
      ["AS-777", "BGC065", LOC, "lasso/other RiPP", "lasso or other RiPP maturation present", "AA_permease - Gly_kinase"])
    w("COHORT_domain_claim_ceiling_by_bgc.csv",
      ["Strain", "BGC_ID", "Assembly_Locator", "Safe_domain_claims", "Unsafe_domain_claims", "Domain_claim_ceiling"],
      ["AS-777", "BGC065", LOC, "RiPP maturation/tailoring", "confirmed RiPP product without precursor validation", "architecture/family-level; not product identity"])

def test_imported_prefill_is_explicitly_held():
    with tempfile.TemporaryDirectory() as root:
        _fixture(root)
        with pytest.raises(ValueError, match="COHORT_PREFILL_SOURCE_BINDING_UNAVAILABLE"):
            _precompute_facts(root, LOC)


def test_absent_precompute_leaves_authoring_prompt():
    # Supplying an unavailable imported capability holds; default prompts remain.
    with pytest.raises(ValueError, match="COHORT_PREFILL_SOURCE_BINDING_UNAVAILABLE"):
        _precompute_facts("/nonexistent", LOC)
    assert "Author:" in _section_body(14, {}, {})
    assert "Author:" in _section_body(11, {}, {})


def test_section11_and_section14_render_supplied_facts():
    # Keep renderer coverage separate from the unavailable cohort import.
    f = {
        "pc_archetype": "lasso/other RiPP",
        "pc_archetype_note": "lasso or other RiPP maturation present",
        "pc_domain_string": "AA_permease - Gly_kinase",
        "pc_safe_claims": "RiPP maturation/tailoring",
        "pc_unsafe_claims": "confirmed RiPP product without precursor validation",
        "pc_claim_ceiling": "architecture/family-level; not product identity",
    }
    assert f["pc_archetype"] == "lasso/other RiPP"
    assert "family-level" in f["pc_claim_ceiling"]
    # §11 archetype and grounded wording remain renderer responsibilities.
    s11 = _section_body(11, f, {})
    assert "lasso/other RiPP" in s11 and "grounded" in s11
    # §14 displays the ceiling and unsafe language without promoting production.
    s14 = _section_body(14, f, {})
    assert "confirmed RiPP product without precursor validation" in s14
    assert "never 'produces'" in s14
    assert "architecture/family-level; not product identity" in s14
