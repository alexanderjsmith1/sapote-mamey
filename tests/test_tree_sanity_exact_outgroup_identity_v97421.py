"""Bounded outgroup identity must agree across the hard gate and advisory mirror."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def _load(name: str):
    sys.path.insert(0, str(TOOLS))
    try:
        spec = importlib.util.spec_from_file_location(f"_bounded_{name}", TOOLS / f"{name}.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(TOOLS))


@pytest.mark.parametrize(
    "tip, term",
    [
        ("reference_withoutgroup_metadata", None),
        ("NR_118632_1_Pseudonocardia_sediminis", "Nocardia"),
        ("NR_1_Micromonosporaceae_x", "Micromonospora"),
        ("NR_1_Actinocorallia_herbida_16S", "Actinocoral"),
        ("OG_twosome", "OG_two"),
    ],
)
def test_containing_words_and_prefixes_are_not_outgroups(tip, term):
    assert _load("tree_sanity_check")._is_outgroup_tip(tip, term) is False


@pytest.mark.parametrize(
    "tip, term",
    [
        ("Ref_c_OUTGROUP_1", None),
        ("NR_041858_1_Nocardia_nova", "nocardia"),
        ("NOCARDIA_farcinica", "Nocardia"),
        ("complete explicit tip identity", "complete explicit tip identity"),
    ],
)
def test_explicit_tokens_and_full_identities_are_outgroups(tip, term):
    assert _load("tree_sanity_check")._is_outgroup_tip(tip, term) is True


def test_repeatable_and_comma_separated_terms_remain_supported():
    gate = _load("tree_sanity_check")
    assert gate._is_outgroup_tip("OG_two", ["OG_one", "OG_two"])
    assert gate._is_outgroup_tip("OG_two", "OG_one,OG_two")


def test_advisory_signoff_keeps_exact_parity_with_the_hard_gate():
    hard = _load("tree_sanity_check")
    advisory = _load("signoff_check")
    cases = [
        ("reference_withoutgroup_metadata", None),
        ("Ref_c_OUTGROUP_1", None),
        ("NR_118632_1_Pseudonocardia_sediminis", "Nocardia"),
        ("NR_041858_1_Nocardia_nova", "nocardia"),
        ("NR_1_Micromonosporaceae_x", "Micromonospora"),
    ]
    for tip, term in cases:
        assert advisory._is_outgroup_tip(tip, term) is hard._is_outgroup_tip(tip, term)


def test_wrong_containing_genus_keeps_long_branch_failures(tmp_path):
    gate = _load("tree_sanity_check")
    tree = tmp_path / "wrong-genus.nwk"
    tree.write_text(
        "(A:0.01,B:0.01,C_OUTGROUP_:0.10,"
        "NR_118632_1_Pseudonocardia_sediminis:1.00);",
        encoding="utf-8",
    )
    ok, report = gate.check(tree, outgroup="Nocardia")
    assert not ok
    assert "LONG_TERMINAL" in report
    assert "DOMINATING_BRANCH" in report


def test_true_explicit_outgroup_keeps_long_branch_exemption(tmp_path):
    gate = _load("tree_sanity_check")
    tree = tmp_path / "true-outgroup.nwk"
    tree.write_text(
        "(A:0.01,B:0.01,C:0.01,NR_041858_1_Nocardia_nova:1.00);",
        encoding="utf-8",
    )
    ok, report = gate.check(tree, outgroup="Nocardia")
    assert ok, report
    assert "outgroup-exempt" in report


def test_stem_aware_wrapper_inherits_matching_and_retains_terminal_guard(tmp_path):
    wrapper = _load("gate_stem_aware")
    wrong = tmp_path / "wrong-wrapper.nwk"
    wrong.write_text(
        "(A:0.01,B:0.01,C_OUTGROUP_:0.10,"
        "NR_118632_1_Pseudonocardia_sediminis:1.00);",
        encoding="utf-8",
    )
    ok, report = wrapper.gate(wrong, outgroup="Nocardia")
    assert not ok
    assert "LONG_TERMINAL" in report

    true = tmp_path / "true-wrapper.nwk"
    true.write_text(
        "(A:0.01,B:0.01,C:0.01,NR_041858_1_Nocardia_nova:1.00);",
        encoding="utf-8",
    )
    assert wrapper.gate(true, outgroup="Nocardia")[0]


def test_core_threshold_defaults_are_unchanged():
    gate = _load("tree_sanity_check")
    assert gate.check.__defaults__ is not None
    assert gate.check.__defaults__[0:3] == (0.25, 10.0, 0.50)
