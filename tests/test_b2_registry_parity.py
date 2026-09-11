"""
B2 Phase 1 regression anchor.

Asserts the registry-backed detector reproduces the hardcoded source_scans.py
behavior bit-for-bit. If this fails, the registry inventory has drifted from the
in-code patterns and detection may have silently changed — STOP and reconcile
before shipping.

Covers:
  1. Dict-level parity: registry-built pattern dicts == hardcoded literals.
  2. Module-state parity: source_scans globals reflect the registry build.
  3. End-to-end parity: full run_source_scans output is identical with the
     registry active vs forced fallback (MAMEY_DISABLE_REGISTRY_DETECTOR=1).
  4. Phase boundary: only regex/motif fire; HMM/manual markers stay inactive.
"""
import ast
import json
import os
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ZIP = ROOT / "examples" / "test_data" / "smoke_antismash_small.zip"

# bundle_support/registry_inventory_v1.9.4.json is intentionally absent from the CODE / analysis-free tiers
# (it is shipped only in merged + sid). When absent, the validated hardcoded source_scans path is
# the detection truth, so these registry-parity tests skip rather than fail — mirroring the
# skipif on test_end_to_end_parity_registry_vs_fallback for the stripped smoke fixture.
_REGISTRY_JSON = ROOT / "bundle_support/registry_inventory_v1.9.4.json"
_needs_registry = pytest.mark.skipif(
    not _REGISTRY_JSON.exists(),
    reason="bundle_support/registry_inventory_v1.9.4.json absent in this tier; hardcoded source_scans fallback is the validated path (registry activation is Phase-2).",
)


# *_PATTERNS dicts in source_scans.py that are NOT detection-registry libraries and so are
# intentionally absent from registry_detector._REGISTRY_MAP. VETO_CONTEXT_PATTERNS is a
# related-family veto filter (consumed only by _region_context for cross-reaction suppression),
# not a marker library — registering it would corrupt detection. Keep this list in sync with any
# future non-registry pattern dicts.
_NON_REGISTRY = {"VETO_CONTEXT_PATTERNS", "PRIMARY_METABOLISM_PATTERNS", "MOBILE_ELEMENT_PATTERNS"}


def _hardcoded_literals() -> dict[str, dict]:
    """Parse the *_PATTERNS / *_MOTIFS dict literals straight from source (registry libraries only)."""
    src = (ROOT / "mamey" / "source_scans.py").read_text()
    out: dict[str, dict] = {}
    for node in ast.parse(src).body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Dict)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id.endswith(("PATTERNS", "MOTIFS"))
            and node.targets[0].id not in _NON_REGISTRY
        ):
            out[node.targets[0].id] = ast.literal_eval(node.value)
    return out


@_needs_registry
def test_registry_build_matches_hardcoded_literals():
    from mamey import registry_detector as rd

    built = rd.build_pattern_dicts()
    literals = _hardcoded_literals()
    assert set(built) == set(literals)
    for name in literals:
        assert built[name] == literals[name], f"{name} drifted from literal"


@_needs_registry
def test_module_globals_use_registry():
    from mamey import registry_detector as rd
    from mamey import source_scans as ss

    assert ss.REGISTRY_DETECTOR_ACTIVE is True
    built = rd.build_pattern_dicts()
    for name, d in built.items():
        assert getattr(ss, name) == d


def _run_full_scan():
    from mamey import parsers, source_scans

    bgcs = parsers.parse_bgcs_from_zip(str(ZIP))
    cds = parsers.extract_cds_features(str(ZIP))
    contigs = parsers.extract_contig_sequences(str(ZIP))
    domains = parsers.extract_domain_features(str(ZIP))
    bundle = source_scans.run_source_scans(bgcs, cds, contigs, domains)

    def ser(o):
        if hasattr(o, "__dict__"):
            return {k: ser(v) for k, v in vars(o).items()}
        if isinstance(o, dict):
            return {k: ser(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [ser(x) for x in o]
        return o

    active = source_scans.REGISTRY_DETECTOR_ACTIVE
    return active, json.dumps(ser(bundle), sort_keys=True, default=str)


def _reimport():
    """Re-import ONLY the registry-coupled modules.

    mamey.source_scans reads MAMEY_DISABLE_REGISTRY_DETECTOR at IMPORT time and mutates its
    own globals from the registry build, so toggling the flag requires a fresh import of
    source_scans and the registry modules it pulls in. The previous implementation purged
    EVERY ``mamey*`` entry from sys.modules, which orphaned the collection-time bindings of
    every other test module in the suite (a module-level cache elsewhere became unreachable
    from fresh imports — cost three diagnostic full-suite runs to trace in the .398 round).
    Purge only what the parity semantics need."""
    import sys

    pkg = sys.modules.get("mamey")
    for m in ("mamey.source_scans", "mamey.registry_detector", "mamey.registry_schema"):
        sys.modules.pop(m, None)
        # ``from mamey import source_scans`` returns the cached PACKAGE ATTRIBUTE without
        # re-importing when only the sys.modules entry is gone — drop the attribute too.
        if pkg is not None:
            try:
                delattr(pkg, m.rsplit(".", 1)[1])
            except AttributeError:
                pass


@pytest.mark.skipif(not ZIP.exists(), reason="smoke_antismash_small.zip fixture is stripped from the analysis-free tier")
@_needs_registry
def test_end_to_end_parity_registry_vs_fallback():
    _reimport()
    os.environ.pop("MAMEY_DISABLE_REGISTRY_DETECTOR", None)
    active_a, out_a = _run_full_scan()

    _reimport()
    os.environ["MAMEY_DISABLE_REGISTRY_DETECTOR"] = "1"
    try:
        active_b, out_b = _run_full_scan()
    finally:
        os.environ.pop("MAMEY_DISABLE_REGISTRY_DETECTOR", None)
        _reimport()

    assert active_a is True
    assert active_b is False
    assert out_a == out_b, "registry-driven scan diverged from hardcoded fallback"


@_needs_registry
def test_phase2_markers_inactive():
    """HMM/DIAMOND/BLASTP/manual markers must NOT fire in Phase 1."""
    from mamey import registry_detector as rd

    assert rd.ACTIVE_DETECTORS == frozenset({"regex", "motif"})
    worklist = rd.inactive_marker_worklist()
    # The known HMM-only TOMM/thiopeptide CCTT trigger must be on the inactive
    # worklist. Do not pin this to a single historical registry ID: the
    # JSON/CSV registry parity note records that the Phase-2 TOMM entry lives
    # in the JSON-only extension block, while older docs referred to it as
    # MMK-CCTT-015. The load-bearing invariant is that TOMM is defined but
    # HMM-only and therefore inactive in Phase 1.
    tomm_hits = [
        w for w in worklist
        if "TOMM" in str(w.get("name", "")).upper()
        or "THIOPEPTIDE" in str(w.get("name", "")).upper()
    ]
    assert tomm_hits, "HMM-only TOMM/thiopeptide CCTT trigger missing from inactive worklist"
    assert any("hmm" in set(w.get("target_types", [])) for w in tomm_hits)
    # No active detector type leaks into the inactive worklist.
    for w in worklist:
        assert not (set(w["target_types"]) & rd.ACTIVE_DETECTORS)
