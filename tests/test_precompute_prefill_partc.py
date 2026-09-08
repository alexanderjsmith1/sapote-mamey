"""v9.7.225 Part C: the card assembler pre-fills grounded facts from the cohort precompute tables,
joined on assembly_locator (Part B key). Hermetic synthetic fixture."""
import csv, os, tempfile, sys, pathlib
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

def test_join_and_prefill_sections():
    with tempfile.TemporaryDirectory() as root:
        _fixture(root)
        f = _precompute_facts(root, LOC)
        assert f["pc_archetype"] == "lasso/other RiPP"
        assert "family-level" in f["pc_claim_ceiling"]
        # §11 pre-fills the archetype (grounded)
        s11 = _section_body(11, f, {})
        assert "lasso/other RiPP" in s11 and "grounded" in s11
        # §14 pre-fills the claim ceiling + unsafe claims, keeps capacity language
        s14 = _section_body(14, f, {})
        assert "confirmed RiPP product without precursor validation" in s14
        assert "never 'produces'" in s14

def test_absent_precompute_leaves_authoring_prompt():
    # no precompute dir -> sections keep their author prompt (non-fatal)
    assert _precompute_facts("/nonexistent", LOC) == {}
    assert "Author:" in _section_body(14, {}, {})
    assert "Author:" in _section_body(11, {}, {})
