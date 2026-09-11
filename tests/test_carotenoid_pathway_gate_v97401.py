"""test_carotenoid_pathway_gate_v97401.py — lock the architecture_first carotenoid gate.

A terpene-dominated region WITHOUT phytoene synthase (SQS_PSY) or lycopene cyclase
(Lycopene_cycl) must NOT be classified CAROTENOID — it is a plain terpene cyclase.

Rationale: a 2026-09-01 corpus audit found ~75% (33/44) of card1652 TERPENE_CAROTENOID_CORE
regions carried NO committed carotenoid enzyme. The current engine already gates this
correctly (architecture_first.assess_architecture: CAROTENOID requires
has_phytoene_synt or has_lycopene_cyclase). This test prevents that gate from regressing.
"""
from mamey.architecture_first import architecture_first_assessment as run, PathwayType


def _pt(genes):
    a, c, s = run(genes, "Interior", "", 1)
    return a.pathway_type


def test_terpene_cyclase_alone_not_carotenoid():
    genes = [{'locus_tag': 'g1', 'aa_length': '350', 'sec_met_domains': 'Terpene_syn_C_2'}]
    assert _pt(genes) != PathwayType.CAROTENOID
    assert _pt(genes) == PathwayType.TERPENE_CYCLIZED


def test_phytoene_synthase_makes_carotenoid():
    genes = [{'locus_tag': 'g1', 'aa_length': '350', 'sec_met_domains': 'Terpene_syn_C_2'},
             {'locus_tag': 'g2', 'aa_length': '300', 'sec_met_domains': 'SQS_PSY'}]
    assert _pt(genes) == PathwayType.CAROTENOID


def test_lycopene_cyclase_makes_carotenoid():
    genes = [{'locus_tag': 'g1', 'aa_length': '350', 'sec_met_domains': 'Terpene_syn_C_2'},
             {'locus_tag': 'g2', 'aa_length': '400', 'sec_met_domains': 'Lycopene_cycl'}]
    assert _pt(genes) == PathwayType.CAROTENOID
