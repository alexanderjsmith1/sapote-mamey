"""Bundle regression for VGP-398: tree_sanity_check outgroup awareness (shipped module).

Asserts the SHIPPED `tools/tree_sanity_check.py` (post-VGP-398) behaviour:
  A correct sister-genus outgroup (long branch to *_OUTGROUP, tight ingroup) -> PASS (was the false-FAIL bug)
  B bad ingroup query (AS-150 dominates, non-outgroup)                        -> FAIL (true defect still caught)
  C no outgroup tag, real dominator                                          -> FAIL (backward compatible)
  D outgroup present AND a real ingroup dominator                            -> FAIL (exemption never masks it)
  E untagged outgroup exempted only via an explicit --outgroup token or identity

NOTE (Aquarius, .398 cut staging): VGP-398's packet-local test loaded `tree_sanity_check.py.before`
and `.after` as sibling files, which are not present in the bundle `tests/` dir and errored on
collection (would break the bundle suite). This is the equivalent bundle test against the shipped
(patched) module; the fail-before half was verified in the VGP packet. VGP should repackage its
patch to add a shippable test. Class-level taxonomy context; judgment deferred.
"""
from pathlib import Path
import sys

_TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
import tree_sanity_check as tsc  # noqa: E402

OUTGROUP_OK = "((A:0.01,B:0.01):0.01,(C:0.01,D:0.01):0.01,Rhodococcus_erythropolis_OUTGROUP:0.31);"
BAD_QUERY = "((A:0.01,B:0.01):0.01,(C:0.01,AS-150:0.33):0.01,Ref_OUTGROUP:0.08);"
NO_OUTGROUP_DOMINATOR = "((A:0.01,B:0.01):0.01,(C:0.01,D:0.01):0.01,E:0.40);"
OUTGROUP_PLUS_QUERY = "((A:0.01,AS-150:0.35):0.01,(C:0.01,D:0.01):0.01,Ref_OUTGROUP:0.31);"


def _tree(tmp_path, newick, name):
    p = tmp_path / f"{name}.treefile"
    p.write_text(newick)
    return str(p)


def test_A_correct_outgroup_passes(tmp_path):
    ok, msg = tsc.check(_tree(tmp_path, OUTGROUP_OK, "outgroup_ok"))
    assert ok is True, f"correct sister-genus outgroup should PASS:\n{msg}"
    assert "outgroup-exempt" in msg


def test_B_bad_query_fails(tmp_path):
    ok, msg = tsc.check(_tree(tmp_path, BAD_QUERY, "bad_query"))
    assert ok is False, f"bad ingroup query MUST FAIL:\n{msg}"
    assert "AS-150" in msg


def test_C_no_outgroup_dominator_fails(tmp_path):
    ok, _ = tsc.check(_tree(tmp_path, NO_OUTGROUP_DOMINATOR, "no_outgroup"))
    assert ok is False


def test_D_exemption_never_masks_ingroup_dominator(tmp_path):
    ok, msg = tsc.check(_tree(tmp_path, OUTGROUP_PLUS_QUERY, "outgroup_plus_query"))
    assert ok is False, f"exemption must not hide a real ingroup dominator:\n{msg}"
    assert "AS-150" in msg
    assert "outgroup-exempt" in msg


def test_E_explicit_outgroup_flag(tmp_path):
    newick = "((A:0.01,B:0.01):0.01,(C:0.01,D:0.01):0.01,Nonomuraea_pusilla_ref:0.65);"
    t = _tree(tmp_path, newick, "untagged_outgroup")
    ok_default, _ = tsc.check(t)
    ok_named, msg = tsc.check(t, outgroup="Nonomuraea")
    assert ok_default is False, "untagged long outgroup still FAILs without --outgroup"
    assert ok_named is True, f"named outgroup should be exempt:\n{msg}"


# ---------------------------------------------------------------------------
# v9.7.413 — NO_OUTGROUP. Standing rule (Alex, 2026-09-07): a tree with no recognisable outgroup is
# itself a gate failure. Cases F/G/H per EGGPLANT_413_gate_outgroup_awareness. F is the deliberate
# behaviour change (PASS -> FAIL); the rest assert the two escape hatches, the truncation case that
# motivated the rule, and the CLI. Class-level structural check; judgment deferred.
# ---------------------------------------------------------------------------

TIGHT_NO_TAG = "((A:0.01,B:0.01):0.01,(C:0.01,D:0.01):0.01,(E:0.01,F:0.01):0.01);"
TRUNCATED_MARKER = "((A:0.01,B:0.01):0.01,(C:0.01,D:0.01):0.01,Rhodococcus_erythropolis_outg:0.31);"


def test_F_tight_healthy_tree_with_no_outgroup_tag_now_fails(tmp_path):
    ok, msg = tsc.check(_tree(tmp_path, TIGHT_NO_TAG, "tight_no_tag"))
    assert ok is False, f"a tree with no recognisable outgroup must FAIL:\n{msg}"
    assert "NO_OUTGROUP" in msg
    # the remedy must be to declare the outgroup, never to prune a possibly-legitimate stem
    assert "prune" not in msg
    assert "--outgroup" in msg and "--allow-no-outgroup" in msg


def test_F2_declared_outgroup_less_tree_passes(tmp_path):
    ok, msg = tsc.check(_tree(tmp_path, TIGHT_NO_TAG, "declared"), require_outgroup=False)
    assert ok is True, f"a DECLARED outgroup-less tree must still PASS:\n{msg}"
    assert "declared outgroup-less" in msg


def test_G_explicit_outgroup_token_still_satisfies_the_rule(tmp_path):
    t = _tree(tmp_path, "((A:0.01,B:0.01):0.01,(C:0.01,D:0.01):0.01,Nonomuraea_pusilla_ref:0.65);",
              "named_outgroup")
    ok, msg = tsc.check(t, outgroup="Nonomuraea")
    assert ok is True, f"the --outgroup escape hatch must keep working:\n{msg}"
    assert "NO_OUTGROUP" not in msg
    assert "[outgroup-marker] matched: nonomuraea" in msg


def test_H_truncated_marker_fails_as_NO_OUTGROUP_not_as_a_prune_instruction(tmp_path):
    """The rect2 regression: a fixed-width tip-label cut severed '_outgroup' to '_outg', the
    exemption silently lapsed, and the operator was told to prune the real outgroup."""
    t = _tree(tmp_path, TRUNCATED_MARKER, "truncated")
    ok, msg = tsc.check(t)
    assert ok is False
    assert "NO_OUTGROUP" in msg
    assert "prune" not in msg, f"must not tell the operator to prune the outgroup:\n{msg}"
    assert "TRUNCATED" in msg, "the report must point at the truncation as a likely cause"
    # v9.7.413 addendum: the offender block must not ALSO fire on this same untrusted branch --
    # not just the ACTION line's wording. Pre-addendum this printed a second [DOMINATING_BRANCH]
    # block naming the real outgroup stem "100% of tree depth", which is the exact "misleading
    # DOMINATING_BRANCH on the outgroup's own stem" case H exists to rule out.
    assert "DOMINATING_BRANCH" not in msg, f"must not ALSO fire on the same untrusted branch:\n{msg}"
    assert "LONG_TERMINAL" not in msg, f"must not ALSO fire on the same untrusted branch:\n{msg}"
    ok2, msg2 = tsc.check(t, outgroup="Rhodococcus")
    assert ok2 is True and "outgroup-exempt" in msg2


def test_I_matched_marker_is_reported_on_a_passing_tree(tmp_path):
    ok, msg = tsc.check(_tree(tmp_path, OUTGROUP_OK, "marker_report"))
    assert ok is True
    assert "[outgroup-marker] matched: outgroup" in msg


def test_J_cli_exposes_the_declaration_and_exits_2_without_it(tmp_path):
    t = _tree(tmp_path, TIGHT_NO_TAG, "cli_case")
    assert tsc.main([t]) == 2
    assert tsc.main([t, "--allow-no-outgroup"]) == 0


# ---------------------------------------------------------------------------
# v9.7.415 — NO_OUTGROUP must SAY that the branch-length checks were skipped.
# The .413 addendum suppresses LONG_TERMINAL/DOMINATING_BRANCH when NO_OUTGROUP fires. That is the
# right call (un-exempted they flag the undeclared outgroup's own stem), but it was silent: measured
# across the 168 EPA-ng/placement trees the engine gates at tools/phylo_place.py, 8 carry a genuine
# LONG_TERMINAL *and* DOMINATING_BRANCH that the report stopped mentioning. Class-level structural
# check; judgment deferred.
# ---------------------------------------------------------------------------

# One long terminal AND one dominating branch, and no outgroup marker anywhere.
PATHOLOGICAL_UNTAGGED = "((A:0.01,B:0.01):0.01,(C:0.01,D:0.90):0.01,E:0.60);"


def test_K_no_outgroup_report_states_that_branch_checks_were_skipped(tmp_path):
    ok, msg = tsc.check(_tree(tmp_path, PATHOLOGICAL_UNTAGGED, "patho_untagged"))
    assert ok is False
    assert "NO_OUTGROUP" in msg
    # the suppression itself is unchanged — those classes must NOT be reported
    assert "LONG_TERMINAL" not in msg and "DOMINATING_BRANCH" not in msg
    # ...but the report must now SAY they were skipped, and how to get them
    assert "branch-length checks SKIPPED" in msg
    assert "--allow-no-outgroup" in msg


def test_L_declaring_the_anchor_restores_the_branch_checks(tmp_path):
    """The notice must be true: declaring the anchor really does bring the checks back."""
    t = _tree(tmp_path, PATHOLOGICAL_UNTAGGED, "patho_declared")
    ok, msg = tsc.check(t, require_outgroup=False)
    assert ok is False
    assert "branch-length checks SKIPPED" not in msg
    assert "LONG_TERMINAL" in msg or "DOMINATING_BRANCH" in msg


def test_M_a_clean_tagged_tree_never_mentions_skipped_checks(tmp_path):
    ok, msg = tsc.check(_tree(tmp_path, OUTGROUP_OK, "clean_tagged"))
    assert ok is True
    assert "SKIPPED" not in msg
