"""v9.7.405 — structural-lock registry (proposals item 11).

The estate carries five load-bearing locks. None knew the others existed, so a lock could be
deleted quietly. This test asserts each lock's test FUNCTION is present in its file, so removing
one is a visible failure here rather than a silent loss of coverage.
"""
from __future__ import annotations

import ast
from pathlib import Path

TESTS = Path(__file__).resolve().parent

LOCKS = {
    "scoring_net handler persistence": ("test_scoring_net.py", "test_fingerprint_identical_after_breadcrumb_receipt"),
    "hermetic env / compile guard": ("test_hermetic_env_guard_v97404.py", None),
    "module accretion": ("test_module_accretion.py", "test_current_matches_manifest_exactly"),
    "print / swallow ratchets": ("test_repo_health_cli_output_classification_v97395.py", None),
    "release-manifest count provenance": ("test_release_manifest_count_provenance_v97404.py", "test_apply_without_any_count_is_refused"),
    "gate wiring invariant": ("test_gate_wiring_invariant.py", "test_operator_only_gates_are_not_silently_wired"),
    "lead propagation (v9.7.405)": ("test_lead_propagation_gate_v97405.py", "test_lead_missing_from_a_surface_fails_and_names_it"),
    "candidate census fail-closed": ("test_candidate_census_v97405.py", "test_census_fails_closed_when_walk_cannot_read_a_subtree"),
    "tier-set completeness": ("test_tier_parity_receipt.py", "test_check_tier_parity_refuses_an_incomplete_set"),
    "newest CHANGELOG prose gate": ("test_newest_changelog_composition_prose_v97406.py", "test_newest_changelog_entry_is_seal_ready"),
    "phylogeny evidence schema": ("test_phylo_evidence_producer_v97406.py", "test_producer_and_consumer_share_schema_and_exact_hashes"),
    "locus-map V8 receipt validation": ("test_locus_map_v8.py", "test_receipt_consumer_binds_triple_and_refuses_tampering"),
}


def _test_functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}


def test_every_lock_is_present():
    missing = []
    for label, (fname, fn) in LOCKS.items():
        f = TESTS / fname
        if not f.exists():
            missing.append(f"{label}: file {fname} absent"); continue
        fns = _test_functions(f)
        if not fns:
            missing.append(f"{label}: {fname} has no test functions"); continue
        if fn and fn not in fns:
            missing.append(f"{label}: {fname}::{fn} absent")
    assert not missing, "structural lock(s) missing: " + "; ".join(missing)


def test_ratchet_constants_equal_measured_on_shipped_tree():
    """The ratchet ceilings must be the measured truth, not a number with headroom."""
    import importlib.util, re, sys
    tool = TESTS.parent / "tools" / "repo_health.py"
    spec = importlib.util.spec_from_file_location("repo_health", tool)
    rh = importlib.util.module_from_spec(spec); sys.modules["repo_health"] = rh; spec.loader.exec_module(rh)
    results = {r.name: r for r in rh.run(TESTS.parent)}
    for metric, const in rh._RATCHETS.items():
        measured = int(re.match(r"(\d+)", results[metric].detail).group(1))
        ceiling = getattr(rh, const)
        waiver = rh.load_waivers(TESTS.parent / rh._WAIVER_DEFAULT_NAME).get(metric)
        assert measured <= ceiling or (
            waiver is not None and rh._waiver_covers(waiver, measured)
        ), f"{metric}: measured {measured} > ceiling {ceiling} without applicable signed waiver"
        assert ceiling - measured <= 0, (f"{metric}: ceiling {ceiling} has {ceiling - measured} headroom — "
                                          f"run tools/repo_health.py --ratchet-down")
