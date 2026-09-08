"""Meta-invariant: the gate system cannot silently develop orphans (audit root-cause fix, v9.7.97).

This is the test that would have caught the orphaned sync_version and verify_tier_derivation gates.
It asserts two things about every correctness/safety CHECK tool in tools/:
  1. it is classified in tools/gate_registry.tsv (no un-accounted gate), and
  2. if classified WIRED, it is actually referenced by a test or a *.sh cut/release script
     (a 'wired' gate that loses its wiring goes red here).
Builders (build_/gen_/export_/merge_/hub_/ingest_) and analysis scans are intentionally out of scope.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
TESTS = ROOT / "tests"

# A tool is a CHECK/GATE if its name matches a gate verb, OR it is an *_audit/_check/_qa helper.
# v9.7.374 fix: added |guard -- a _guard-suffixed tool (e.g. modeb_card_guard.py, a real
# identity-vs-STRAIN_CARD.md safety check) was invisible to this enumeration and so never
# entered the orphan-gate tripwire below at all. See gate_registry.tsv's new modeb_card_guard row.
GATE_NAME = re.compile(r"^(check_|verify_|audit_|sync_)|_(audit|check|qa|qa_v\d+|gate|guard)$")
# Explicitly NOT gates (builders / analysis), even if they exit nonzero on error:
NOT_GATE = re.compile(r"^(build_|gen_|export_|merge_|hub_|ingest_|render_|seed_|scan_|dark_|edge_|cluster_|topology_|fragment_|cohort_|lead_|intake_)")


def _gate_tools():
    out = []
    for f in sorted(TOOLS.glob("*.py")):
        b = f.stem
        if NOT_GATE.match(b):
            continue
        if GATE_NAME.search(b):
            out.append(b)
    return out


def _registry():
    reg = {}
    for line in (TOOLS / "gate_registry.tsv").read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split("\t")
        reg[parts[0]] = (parts[1], parts[2] if len(parts) > 2 else "")
    return reg


def _is_referenced_in(tool, tests_dir, tools_dir, *, skip_self="test_gate_wiring_invariant"):
    """G2: the reverse-check primitive, parameterized so it can be proven correct against a
    synthetic fixture as well as run against the real tree (see _is_referenced below and
    test_orphan_detection_fires_when_a_reference_is_removed)."""
    pat = re.compile(rf"\b{re.escape(tool)}\b")
    for d, globs in ((tests_dir, ["test_*.py"]), (tools_dir, ["*.sh"])):
        for g in globs:
            for f in d.glob(g):
                if skip_self and f.stem == skip_self:
                    # This meta-test's own docstrings/comments/allowlist narrate dozens of tool
                    # names for documentation purposes (e.g. "check_module_accretion was
                    # reclassified WIRED in .321"). Counting THOSE mentions as "referenced by a
                    # test" would let a WIRED gate with zero real wiring pass silently, merely by
                    # being named in this file's own prose -- self-defeating the wiring invariant
                    # this test exists to enforce. Skip this file; real wiring must live elsewhere.
                    continue
                if pat.search(f.read_text()):
                    return True
    return False


def _is_referenced(tool):
    return _is_referenced_in(tool, TESTS, TOOLS)


def find_wired_orphans(*, registry, tests_dir, tools_dir, skip_self="test_gate_wiring_invariant"):
    """G2: for every WIRED registry row with no test/.sh reference, a typed WIRED_ORPHAN finding.
    Parameterized (not hardcoded to the real repo) so the tripwire's own correctness can be
    proven against a disposable fixture -- see test_orphan_detection_fires_when_a_reference_is_removed."""
    findings = []
    for tool, (status, _reason) in registry.items():
        if status != "WIRED":
            continue
        if not _is_referenced_in(tool, tests_dir, tools_dir, skip_self=skip_self):
            findings.append({"tool": tool, "code": "WIRED_ORPHAN"})
    return findings


def test_every_gate_tool_is_registered():
    reg = _registry()
    missing = [t for t in _gate_tools() if t not in reg]
    assert not missing, (
        f"un-registered gate tool(s): {missing}. Add a row to tools/gate_registry.tsv "
        f"classifying each as WIRED or OPERATOR_ONLY (this is the orphan-gate tripwire)."
    )


def test_wired_gates_are_actually_wired():
    reg = _registry()
    findings = find_wired_orphans(registry=reg, tests_dir=TESTS, tools_dir=TOOLS)
    broken = [f["tool"] for f in findings]
    assert not broken, (
        f"gate(s) marked WIRED but not referenced by any test or *.sh script: {broken}. "
        f"Either wire it back or reclassify it OPERATOR_ONLY with a reason."
    )


def test_orphan_detection_fires_when_a_reference_is_removed(tmp_path):
    """G2 done-when: prove the tripwire itself works, on a disposable fixture rather than the
    real tree -- a WIRED tool referenced by one test is clean; deleting that test flips the row
    to a typed WIRED_ORPHAN finding."""
    tests_dir = tmp_path / "tests"
    tools_dir = tmp_path / "tools"
    tests_dir.mkdir()
    tools_dir.mkdir()
    referencing_test = tests_dir / "test_fixture_gate.py"
    referencing_test.write_text("import fixture_check_tool  # exercises the fixture gate\n")
    registry = {"fixture_check_tool": ("WIRED", "fixture-only row for this test")}

    clean = find_wired_orphans(registry=registry, tests_dir=tests_dir, tools_dir=tools_dir)
    assert clean == [], "a genuinely-referenced WIRED tool must not be flagged"

    referencing_test.unlink()
    orphaned = find_wired_orphans(registry=registry, tests_dir=tests_dir, tools_dir=tools_dir)
    assert orphaned == [{"tool": "fixture_check_tool", "code": "WIRED_ORPHAN"}], (
        "deleting the referencing test must flip the row to a typed WIRED_ORPHAN finding"
    )


# GATE-WIRE-2 (v9.7.323): close the invariant's asymmetry. It enforced WIRED->referenced but not the
# reverse, so an OPERATOR_ONLY gate that quietly GAINED a test kept a stale label with nothing to catch
# it (how check_module_accretion sat mislabeled until .321). The reverse check: an OPERATOR_ONLY gate
# that is test/.sh-referenced is either a mislabeled cut gate (reclassify -> WIRED) or a
# unit-tested-but-not-cut helper (enumerate it here with a reason). A NEW such gate not on this list
# fails the test, forcing the call rather than letting it drift.
_UNIT_TESTED_OPERATOR_GATES = {
    # figure_check: reclassified WIRED in .401 (AMBER_401_figure_check_render_wiring) — now
    # hooked into tools/render_clean_tree.py before any figure render, so it is no longer
    # operator-only (the check_module_accretion .321 path, as the .400 note prescribed).
    "check_chatgpt_next_paths": "bunny-hop next-path helper; logic unit-tested, not run at cut",
    "check_deliverable_suite": "operator deliverable spot-check; fail-closed logic unit-tested, not a cut gate",
    # cohort_scoring_version_gate: reclassified WIRED in .338 (COH-01) — now hooked into
    # mamey.cohort_deliverable before cross-strain aggregation, so it is no longer operator-only.
    "run_chatgpt_surrogate_gate": "surrogate-gate manifest check; unit-tested, operator-run",
    "reclass_check": "reclassification helper exercised by bgc_reconcile tests; not a cut gate",
    # v9.7.372: gained regression tests via the Codex exact-locus filename-gate patch; still an
    # operator-run naming checker, not wired into the cut path.
    "check_bgc_naming": "exact-locus filename checker; unit-tested (test_check_bgc_naming_exact_locus), operator-run",
    "file_atlas": "file-atlas import-safety helper; import-tested, not a cut gate",
    "modeb_evidence_gate": "advisory Mode B authoring lint (v9.7.354, Codex governance state machine); "
                           "adversarial unit tests, run by the authoring chat before promotion, not a cut gate",
    # v9.7.395: gained regression tests via the eco-regex precedence fix (v9.7.395 pool); still an
    # operator-run identity checker, not wired into the cut path.
    "modeb_card_guard": "card-vs-STRAIN_CARD identity checker; unit-tested (test_modeb_card_guard_eco_regex_v97395), operator-run",
    "tree_sanity_check": "HARD pre-render tree gate (v9.7.355); branch-sanity unit-tested, run at render time / by the phylo chat, not a cut gate",
    # v9.7.395: gained regression tests via the v9.7.395 pool's empty-CSV schema-check fix
    # (test_check_registry_ids_unique_empty_csv_v97395); still an operator-run registry
    # diagnostic, not release-blocking until registry policy is finalized (see the tool's own
    # gate_registry.tsv reason).
    "check_registry_ids_unique": "registry uniqueness diagnostic (v9.7.141 JSON/CSV parity follow-up); "
                                 "unit-tested (test_check_registry_ids_unique_empty_csv_v97395), operator-run",
    # v9.7.405: revived June-2026 lead-propagation audit as a post-seal, operator-run receipt tool.
    "lead_propagation_gate": "lead-propagation audit (triage-board leads vs lead-listing surfaces); unit-tested (test_lead_propagation_gate_v97405), operator-run, advisory unless --strict",
    "generated_surface_ownership": "check-only cut-surface phase/owner validator; unit-tested for fail-closed stage mismatch, operator-run and not wired into release.sh",
    # v9.7.395: gained regression tests via the v9.7.395 pool's identify()-convention fix
    # (test_session_cost_audit_identify_v97395); still an operator-run cost/token analysis tool
    # (review lane C07, workhorse-scoped subagent governance), not an engine build gate.
    "session_cost_audit": "session token/cost ledger auditor (review lane C07); "
                          "unit-tested (test_session_cost_audit_identify_v97395), operator-run",
    # BC2-407: gained regression tests for its --run-slow pytest-args construction
    # (test_cut_audit_pytest_args_v97407) after a false-PASS was found (rebase-verify silently
    # never invoked slow-gated tests); still the operator-run rebase-verify harness itself
    # (gate_registry.tsv: OPERATOR_ONLY, "operator-run, not engine-wired"), not a cut gate.
    "cut_audit": "cut-audit + rebase-verify harness; unit-tested (test_cut_audit_pytest_args_v97407), operator-run",
    # AMBER-407: new process/QC tool that flags patch cards falling out of the cut cadence.
    # Ships with its own unit tests (test_parked_card_audit); read-only, runs patch --dry-run,
    # never imported by engine code and not wired into release.sh -- operator-run, not a cut gate.
    "parked_card_audit": "parked patch-card cadence auditor (AMBER-407); unit-tested (test_parked_card_audit), operator-run",
}


def test_operator_only_gates_are_not_silently_wired():
    reg = _registry()
    offenders = [t for t, (s, _) in reg.items()
                 if s == "OPERATOR_ONLY" and _is_referenced(t) and t not in _UNIT_TESTED_OPERATOR_GATES]
    assert not offenders, (
        f"OPERATOR_ONLY gate(s) now test/.sh-referenced but unacknowledged: {offenders}. "
        f"If it is a cut gate, reclassify it WIRED (as check_module_accretion was in .321); if it is "
        f"unit-tested-but-not-cut, add it to _UNIT_TESTED_OPERATOR_GATES with a one-line reason."
    )


def test_unit_tested_operator_allowlist_has_no_stale_entries():
    # keep the allowlist honest: every entry must still be OPERATOR_ONLY and still referenced.
    reg = _registry()
    stale = [t for t in _UNIT_TESTED_OPERATOR_GATES
             if reg.get(t, ("", ""))[0] != "OPERATOR_ONLY" or not _is_referenced(t)]
    assert not stale, (
        f"_UNIT_TESTED_OPERATOR_GATES entries no longer OPERATOR_ONLY-and-referenced: {stale}. "
        f"Remove them (the gate was reclassified or its test dropped).")


def test_operator_only_gates_have_a_reason():
    reg = _registry()
    no_reason = [t for t, (s, r) in reg.items() if s == "OPERATOR_ONLY" and not r.strip()]
    assert not no_reason, f"OPERATOR_ONLY gates need a reason: {no_reason}"


def test_registry_has_no_stale_rows():
    """A registry row pointing at a tool that no longer exists is itself drift."""
    gates = set(_gate_tools()) | {"redact_public_tier", "verify_tier_derivation", "sync_version",
                                  "sapote_md_preflight", "audit_public_cut"}
    stale = [t for t in _registry() if not (TOOLS / f"{t}.py").exists()]
    assert not stale, f"registry rows for missing tools: {stale}"
