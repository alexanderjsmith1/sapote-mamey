"""Evidence presence, supplied-fact section rendering and privacy regressions.

Imported cohort admission is held separately; section fixtures are fabricated
renderer inputs, not evidence that an unbound table is admitted.
"""
import csv, os, tempfile, sys, pathlib
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mamey.modeb_structure_gate import lint_card
from mamey.modeb_template_emitter import _precompute_facts, _section_body

def _eg(fs): return [x for x in fs if (x.get("code") if isinstance(x, dict) else "") == "EVIDENCE_GAP"]

def test_evidence_gap_only_when_panel_and_no_table():
    no4 = "## §4 Gene-by-gene interpretation\nGenes described in prose only.\n"
    with4 = ("## §4 Gene-by-gene interpretation\n| gene | antiSMASH | BLASTp top hit | %id | verdict |\n"
             "|--|--|--|--|--|\n| ctg1_5 | KS | polyketide synthase | 61 | CONFIRM |\n")
    assert _eg(lint_card(no4, bgc_context={"has_blastp_panel": True}, check_evidence_presence=True))
    assert not _eg(lint_card(with4, bgc_context={"has_blastp_panel": True}, check_evidence_presence=True))
    assert not _eg(lint_card(no4, bgc_context={"has_blastp_panel": False}, check_evidence_presence=True))

def _pc_fixture(root):
    def w(fn, header, rows):
        with open(os.path.join(root, fn), "w", newline="") as f:
            wr = csv.writer(f); wr.writerow(header); wr.writerows(rows)
    LOC = "NODE_1_length_100_cov_9 region001"
    w("COHORT_domain_architecture_by_bgc.csv", ["Strain","BGC_ID","Assembly_Locator","architecture_archetype","archetype_note","domain_architecture_string"],
      [["AS-1","BGC001",LOC,"hybrid NRPS-PKS","","KS-AT-C-A"]])
    w("COHORT_module_architecture_by_bgc.csv", ["Strain","BGC_ID","Assembly_Locator","aSModule_count","module_types"],
      [["AS-1","BGC001",LOC,"3","PKS;NRPS"]])
    w("COHORT_domain_roles_by_bgc.csv", ["Strain","BGC_ID","Assembly_Locator","domain_role_category","count"],
      [["AS-1","BGC001",LOC,"ACP / acyl carrier","4"]])
    w("COHORT_resistance_signals_by_bgc.csv", ["strain","bgc_id","resistance_genes","provenance"],
      [["AS-1","BGC001","Beta_lactamase_fold","x"]])
    w("COHORT_nrps_adomain_substrates.csv", ["strain","bgc_id","node_region","locus_tag","domain","stachelhaus_signature","substrate","confidence","substrate_class_or_alts","provenance"],
      [["AS-1","BGC001","NODE_1","ctg1_5","AMP-binding.1","DAWQCATIDK","Gln","high","","x"]])
    return LOC

def test_unbound_cohort_table_import_is_held():
    with tempfile.TemporaryDirectory() as root:
        loc = _pc_fixture(root)
        with pytest.raises(ValueError, match="COHORT_PREFILL_SOURCE_BINDING_UNAVAILABLE"):
            _precompute_facts(root, loc, strain="AS-1", bgc_id="BGC001")


def test_partc_sections_render_supplied_facts():
    # Presentation-only fixture. No cohort reader/admission path is bypassed.
    f = {
        "pc_roles": "ACP / acyl carrier×4", "pc_archetype": "hybrid NRPS-PKS",
        "pc_archetype_note": "", "pc_domain_string": "KS-AT-C-A",
        "pc_module_count": "3", "pc_module_types": "PKS;NRPS",
        "pc_resistance": "Beta_lactamase_fold",
        "pc_substrates": [{"strain": "AS-1", "bgc_id": "BGC001", "node_region": "NODE_1",
            "locus_tag": "ctg1_5", "domain": "AMP-binding.1", "stachelhaus_signature": "DAWQCATIDK",
            "substrate": "Gln", "confidence": "high", "substrate_class_or_alts": "", "provenance": "fabricated"}],
    }
    assert "grounded" in _section_body(4, f, {})    # roles census
    assert "grounded" in _section_body(5, f, {})    # architecture
    assert "grounded" in _section_body(7, f, {})    # resistance
    assert "grounded" in _section_body(16, f, {})   # substrate table
    assert "Gln" in _section_body(16, f, {})        # fabricated supplied substrate
    assert "never a phenotype" in _section_body(7, f, {})  # discipline preserved

def test_unknown_figure_identity_defaults_private():
    from mamey.cohort_figures import is_private
    assert is_private("AS-" + "987654") is True
    assert is_private("AJS-" + "987654") is True
