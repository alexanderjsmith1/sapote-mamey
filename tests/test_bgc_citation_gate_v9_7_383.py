"""v9.7.383 — fail-closed node·region citation gate (WAC-01375 fatal-error class).

A node-less `strain + BGC-number` citation merged two distinct AS-162 loci and mis-attributed an AB
prior. This gate makes the "cite by node·region, never by BGC number" rule mechanical. Tests pin that
it flags the exact failure form, stays clean on the corrected node·region form, and never trips on
count phrases.
"""
from mamey.bgc_citation_gate import find_nodeless_bgc_citations as f, gate_text


def test_flags_bare_strain_plus_bgc():
    hits = f("- atratumycin (AS-162 BGC011), AB 94\n- candicidin (AS-385 · BGC016)")
    assert len(hits) == 2


def test_node_region_form_is_clean():
    good = "AS-162 / NODE_35_length_72712_cov_100.179280 / region001 / BGC016 — atratumycin-family"
    assert f(good) == []


def test_ctg_token_also_satisfies():
    assert f("AS-162 BGC016 driven by ctg35_27/30/33 (thioamide-NRPS)") == []


def test_count_phrases_do_not_trip():
    assert f("AS-385 has 37 BGCs total; 30 are real BGCs after dedup.") == []


def test_gate_text_message_names_the_rule():
    msgs = gate_text("atratumycin (AS-162 BGC011)")
    assert msgs and "node" in msgs[0].lower() and "never by bare BGC number" in msgs[0]


def test_the_exact_e02_conflation_line_is_caught():
    # the literal shortcut that merged two AS-162 loci
    assert f("atratumycin (AS-162 BGC011)")  # non-empty -> refused
