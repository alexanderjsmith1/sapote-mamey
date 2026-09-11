"""v9.7.224 (Part B / QA join-key fix): list-bgcs --json must emit `assembly_locator` as the canonical
cohort join key — {full contig} {regionNNN}, matching the precompute architecture tables' Assembly_Locator
exactly (full contig incl. .cov, region label, NO bgc_id parenthetical). A node_id-based key returned 0
matches against the architecture tables; this locks the format so tally<->architecture join at read time."""
from mamey.package_inspector import _cohort_locator

def test_joinkey_is_full_contig_region_no_paren():
    r = {"BGC_ID": "BGC065", "Contig": "NODE_9_length_167436_cov_37",
         "Node_ID": "NODE_9", "antiSMASH_Region": "region003"}
    assert _cohort_locator(r) == "NODE_9_length_167436_cov_37 region003"

def test_joinkey_matches_architecture_full_cov_decimal():
    # architecture table sample: 'NODE_1_length_435651_cov_87.875631 region001'
    r = {"Contig": "NODE_1_length_435651_cov_87.875631", "antiSMASH_Region": "region001"}
    assert _cohort_locator(r) == "NODE_1_length_435651_cov_87.875631 region001"

def test_joinkey_normalizes_bare_number_region():
    r = {"Contig": "NODE_5_length_1000_cov_10", "antiSMASH_Region": "2"}
    assert _cohort_locator(r) == "NODE_5_length_1000_cov_10 region002"

def test_joinkey_distinct_from_boss_label_helper():
    # the boss-facing crosswalk helper truncates to node_id + adds (BGC_ID); the join key must NOT
    from mamey.crosswalk import assembly_locator
    r = {"BGC_ID": "BGC065", "Contig": "NODE_9_length_167436_cov_37",
         "Node_ID": "NODE_9", "antiSMASH_Region": "region003"}
    assert "(" not in _cohort_locator(r) and "length" in _cohort_locator(r)
    assert _cohort_locator(r) != assembly_locator(r)
