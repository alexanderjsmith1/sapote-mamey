"""v9.7.398 — tools/build_bgc_markers.py's `_diagnostic_tigrfam_ids()` fallback (reached only if
`from mamey.antismash_evidence import DIAGNOSTIC_TIGRFAM` fails) had re-collapsed to the stale
4-ID panel this exact bug class was already named and fixed for once in the sibling
tools/ingest_package.py ("the v9.6.15 tigr8 fix; this was its second instance" — a comment that
existed in ingest_package.py but was never propagated to this file). Mirrors
tests/test_ingest_coupling.py::test_tigrfam_panel_includes_section8, the existing regression
guard for the sibling file's own copy of this bug.
"""
from __future__ import annotations

import tools.build_bgc_markers as bm


def test_tigrfam_panel_includes_section8():
    """tigr8 second instance, this file's own copy: the panel must not be the stale 4-ID list."""
    panel = bm._diagnostic_tigrfam_ids()
    for acc in ("TIGR04462", "TIGR03550", "TIGR04363", "TIGR01181", "TIGR02353"):
        assert acc in panel, f"{acc} missing from build_bgc_markers TIGRFAM panel (tigr8 regressed)"


def test_tigrfam_panel_matches_canonical_count():
    from mamey.antismash_evidence import DIAGNOSTIC_TIGRFAM
    assert set(bm._diagnostic_tigrfam_ids()) == set(DIAGNOSTIC_TIGRFAM)


def test_tigr_names_dict_has_entries_for_every_panel_id():
    """The module-level TIGR name-lookup dict must not silently fall back to the raw accession
    for the 9 IDs the stale panel was missing."""
    panel = bm._diagnostic_tigrfam_ids()
    for acc in panel:
        assert acc in bm._TIGR_NAMES, f"{acc} has no human-readable name in _TIGR_NAMES"


def test_tigr_module_level_dict_reflects_the_full_panel():
    assert len(bm.TIGR) == 13
    assert "TIGR02353" in bm.TIGR


def test_fallback_source_contains_all_thirteen_ids():
    """Source-level regression guard for the degraded-environment path specifically: forcing the
    real `from mamey.antismash_evidence import ...` to fail from a standalone test isn't
    practical (the module import already succeeded when this test file loaded), so this checks
    the actual except-branch body contains the full 13-ID panel, not the stale 4-ID one."""
    import inspect
    src = inspect.getsource(bm._diagnostic_tigrfam_ids)
    except_idx = src.index("except Exception:")
    fallback_body = src[except_idx:]
    for acc in ("TIGR04462", "TIGR04460", "TIGR03550", "TIGR03551", "TIGR03620",
                "TIGR04363", "TIGR04364", "TIGR01181", "TIGR02353"):
        assert acc in fallback_body, f"{acc} missing from the degraded-environment fallback list"
