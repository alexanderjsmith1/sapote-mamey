"""test_t2pks_core_requires_ks_clf_v97401.py — lock the type-II PKS minimal-core gate.

A lone polyketide cyclase (Polyketide_cyc) with NO ketosynthase/CLF is NOT a type-II PKS core;
a genuine type-II core needs the KSalpha/KSbeta(CLF)/ACP minimal triad.

Rationale: a 2026-09-01 corpus audit found card1652 regions where a single Polyketide_cyc gene was
labelled TYPE_II_PKS_CORE (two motivating cohort cases; receipts in the BC-3 .401 card — IDs kept out of tests per lane convention). The current engine already handles
this (architecture_first: a lone cyclase -> 'unknown', not T2PKS); this test prevents regression.
"""
from mamey.architecture_first import architecture_first_assessment as run


def _pc(genes):
    a, c, s = run(genes, "Interior", "", 1)
    return s.product_class


def test_lone_polyketide_cyclase_not_t2pks_core():
    genes = [{'locus_tag': 'g1', 'aa_length': '270', 'sec_met_domains': 'Polyketide_cyc'}]
    assert "T2PKS" not in _pc(genes)


def test_ks_clf_acp_triad_is_t2pks_core():
    genes = [{'locus_tag': 'g1', 'aa_length': '420', 'sec_met_domains': 'PKS_KS; ketoacyl-synt'},
             {'locus_tag': 'g2', 'aa_length': '415', 'sec_met_domains': 'PKS_KS; Ketoacyl-synt_C'},
             {'locus_tag': 'g3', 'aa_length': '85', 'sec_met_domains': 'PP-binding'},
             {'locus_tag': 'g4', 'aa_length': '270', 'sec_met_domains': 'Polyketide_cyc'}]
    assert _pc(genes) == "T2PKS (aromatic polyketide)"
