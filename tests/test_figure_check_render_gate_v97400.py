"""Regression test — v97400: tools/figure_check.py, the HARD pre-render FIGURE gate.

Exists because on 2026-09-01 a figure shipped with a query tip (AS-660) missing its host marker — a
defect the operator had noticed, captioned as a "nit", and sent anyway. The tree gates
(tree_sanity_check / pre/postflight) check branches and taxonomy, NOT what the renderer draws; this
tool closes that gap mechanically. Each check below reproduces a defect that reached a REAL rendered
figure at least once (receipts in the PATCH_CARD).

Place in tests/: `pytest tests/test_figure_check_render_gate_v97400.py`.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import figure_check as fc  # noqa: E402


def _tree(tmp_path, tips):
    tf = tmp_path / "labeled.treefile"
    tf.write_text("(" + ",".join(f"{t}:0.01" for t in tips) + ");\n", encoding="utf-8")
    return str(tf)


def test_missing_marker_fails_F1_the_AS660_case_v97400(tmp_path):
    tf = _tree(tmp_path, ['Streptomyces_AS-971_other-bee', 'Streptomyces_AS-972_bumblebee',
                          "Streptomyces_griseofuscus_DSM40191", "Kitasatospora_setae_OUTGROUP"])
    hm = tmp_path / "hostmap.json"
    hm.write_text(json.dumps({'Streptomyces_AS-972_bumblebee': "bumblebee"}))  # fabricated query marker absent
    ok, msg = fc.check(tf, hostmap=str(hm))
    assert not ok and 'AS-971' in msg and "F1 MARKER_COVERAGE" in msg


def test_unknown_category_fails_F2_v97400(tmp_path):
    tf = _tree(tmp_path, ['Streptomyces_AS-972_bumblebee'])
    hm = tmp_path / "hostmap.json"
    hm.write_text(json.dumps({'Streptomyces_AS-972_bumblebee': "bumble-bee"}))  # typo'd category
    ok, msg = fc.check(tf, hostmap=str(hm))
    assert not ok and "F2 KNOWN_CATEGORIES" in msg


def test_bare_AS_and_cruft_fail_F3_the_11_lost_ids_and_SID_cruft_v97400(tmp_path):
    tf = _tree(tmp_path, ["Streptomyces_sp_AS",                       # lost strain number (11-ID case)
                          "Streptomyces_sp._SID5947_SID5947.c1",      # doubled SID + contig
                          "Nocardia_callitridis_JCM18298_DNA_"])      # raw header token (shipped twice)
    ok, msg = fc.check(tf, marker_checks=False, max_label_len=80)
    assert not ok and "BARE 'AS'" in msg and "doubled SID" in msg and "_DNA_" in msg


def test_verbose_synthetic_label_fails_F4_v97400(tmp_path):
    tf = _tree(tmp_path, [("SYNTHETIC_REFERENCE_VERBOSE_" + "SYNTHETIC_FIELD_" * 5)])
    ok, msg = fc.check(tf, marker_checks=False, max_label_len=60)
    assert not ok and "F4 LABEL_VERBOSITY" in msg


def test_undeclared_synthetic_omission_fails_F5_and_ack_passes_v97400(tmp_path):
    tf = _tree(tmp_path, ['Streptomyces_AS-972_bumblebee'])
    spec = tmp_path / "TREE_SPEC.json"
    spec.write_text(json.dumps({"omitted_strains": {"SYNTHETIC_REFERENCE_02": 'synthetic omission reason'}}))
    ok, msg = fc.check(tf, spec=str(spec), marker_checks=False)
    assert not ok and "F5 OMISSIONS_DECLARED" in msg and "SYNTHETIC_REFERENCE_02" in msg
    ok2, _ = fc.check(tf, spec=str(spec), marker_checks=False,
                      omitted='SYNTHETIC_REFERENCE_02 omitted for synthetic fixture coverage.')
    assert ok2


def test_clean_inputs_pass_v97400(tmp_path):
    tf = _tree(tmp_path, ['Nocardia_AS-973_bumblebee', "Nocardia_iowensis_NRRL5646",
                          "Rhodococcus_erythropolis_OUTGROUP"])
    hm = tmp_path / "hostmap.json"
    hm.write_text(json.dumps({'Nocardia_AS-973_bumblebee': "bumblebee"}))
    ok, msg = fc.check(tf, hostmap=str(hm))
    assert ok and "PASS" in msg
