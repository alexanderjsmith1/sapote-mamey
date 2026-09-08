"""test_exclusions_ssot.py — the exclusion set is single-sourced (AMBER_RELEASE_DRIFT Part B).

Pins the AS-922 dual state (RATIFIED into GOVERNED 2026-08-05, raw package still void),
the AS-921 omission (the Developer or User ruling 2026-08-09, duplicate of SID10815), the AS-923 QC hold,
and that previously-hardcoded ``EXCLUDE_STRAINS`` copies read from the accessor.

**Why this file was reworked at .358.** The prior version asserted ``governed_excluded() ==
{"AS-920"}`` and ``strains == 45`` as bare literals. ``exclusions.py`` resolves from
``OFFICIAL_DATA/exclusions.json`` when one is reachable, so after the AS-921 ruling those
three assertions FAILED when the suite ran inside the operator workspace while still passing
in a clean extraction (which falls back to ``_DEFAULT``). Correct behaviour was being reported
as a defect — the exact way a governance ruling gets "fixed" back out of the data.

So: literals are pinned ONCE (``_RULED``, mirroring the ratified SSOT), and a drift guard
asserts ``_DEFAULT`` still mirrors the JSON when the JSON is reachable. A future ruling must
update the JSON, ``_DEFAULT`` and ``_RULED`` together, and this file says so when it does not.
"""
import json

from mamey import exclusions

# The ratified SSOT, pinned in exactly one place.
# Source of truth: OFFICIAL_DATA/EXCLUSIONS.md (human) + OFFICIAL_DATA/exclusions.json (machine).
_RULED = {
    "hard_excluded": {"AS-920", "AS-921"},
    "raw_assembly_void": {"AS-922"},
    "qc_hold_audit_only": {"AS-923"},
    "governed": {"strains": 9, "regions": 99},
}


def _reachable_json():
    """The OFFICIAL_DATA/exclusions.json the module would actually load, or None."""
    for p in exclusions._candidate_json_paths():
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))
    return None


def test_governed_excluded_matches_ruling():
    # AS-922 was ratified INTO governed (decontam strain-of-record).
    # AS-920 contaminated; AS-921 omitted 2026-08-09 (duplicate of SID10815).
    assert exclusions.governed_excluded() == _RULED["hard_excluded"]


def test_raw_analysis_excluded_is_hard_plus_raw_void():
    # Semantic, not a literal list: raw modules skip hard-excluded PLUS raw-void.
    assert exclusions.raw_analysis_excluded() == (
        _RULED["hard_excluded"] | _RULED["raw_assembly_void"]
    )


def test_as683_dual_state():
    # The whole point of the original card: IN governed, OUT of raw analysis.
    assert "AS-922" not in exclusions.governed_excluded()
    assert "AS-922" in exclusions.raw_analysis_excluded()
    assert exclusions.strain_of_record("AS-922") == "synthetic_strain_of_record"


def test_as216_omitted_and_sid10815_not_withdrawn():
    # AS-921 is out of governed. SID10815 is a DISTINCT strain and must never be
    # swept into an exclusion set as a side effect of the AS-921 ruling.
    assert "AS-921" in exclusions.governed_excluded()
    assert "SID10815" not in exclusions.governed_excluded()
    assert "SID10815" not in exclusions.raw_analysis_excluded()


def test_qc_hold_is_not_hard_exclusion():
    # AS-923 is inadmissible pending a clean re-run -- held, not hard-excluded.
    qc = exclusions.qc_hold_audit_only()
    assert qc == _RULED["qc_hold_audit_only"]
    assert not (qc & exclusions.hard_excluded())


def test_governed_denominator():
    d = exclusions.governed_denominator()
    assert d["strains"] == _RULED["governed"]["strains"]
    assert d["regions"] == _RULED["governed"]["regions"]


def test_module_default_mirrors_official_data_json():
    """Drift guard: the in-module fallback must equal the machine SSOT.

    Skips when no OFFICIAL_DATA/exclusions.json is reachable (a clean code-only
    extraction) -- there is nothing to compare against there, and _DEFAULT is then
    the operative source, already pinned by the tests above.
    """
    # v9.7.381 generic-source: the SHIPPED _DEFAULT is intentionally EMPTY (a public install
    # excludes nothing until a cohort pack is bound). So _DEFAULT no longer mirrors the pack JSON;
    # it must be empty, and the reachable pack/JSON must carry the ruled values.
    assert exclusions._DEFAULT["hard_excluded"] == []
    assert exclusions._DEFAULT["governed"] == {}
    data = _reachable_json()
    if data is None:
        import pytest

        pytest.skip("no OFFICIAL_DATA/exclusions.json reachable (generic no-pack tree)")
    for key in ("hard_excluded", "raw_assembly_void", "qc_hold_audit_only"):
        assert set(data.get(key, [])) == set(_RULED[key]), (
            f"cohort pack {key!r} has drifted from the ratified SSOT (_RULED)"
        )
    assert data["governed"] == _RULED["governed"], (
        "cohort pack 'governed' has drifted from the ratified SSOT (_RULED)"
    )
    # strain_of_record is a dict (not a list) -- compare it directly so the
    # JSON<->_DEFAULT mirror is fully locked (Amber refinement, .358).
    assert data.get("strain_of_record", {}) == {"AS-922": "synthetic_strain_of_record"}, (
        "cohort pack 'strain_of_record' has drifted from the ratified SSOT"
    )


def test_routed_modules_read_from_accessor():
    # Each raw-data module's EXCLUDE_STRAINS must equal the SSOT accessor, not a local literal.
    from mamey import dualpass_ledger, p450_tailoring, assembly_line, compound_family_report

    expected = exclusions.raw_analysis_excluded()
    assert dualpass_ledger.EXCLUDE_STRAINS == expected
    assert p450_tailoring.EXCLUDE_STRAINS == expected
    assert assembly_line.EXCLUDE_STRAINS == expected
    assert compound_family_report.EXCLUDE_STRAINS == expected


def test_widget_data_governance_overrides_sourced_from_ssot():
    from mamey.interactive_figures import widget_data

    # Same strain keys as the SSOT raw set; distinct governance labels preserved.
    assert set(widget_data.GOVERNANCE_OVERRIDES) == exclusions.raw_analysis_excluded()
    assert widget_data.GOVERNANCE_OVERRIDES["AS-920"] == "EXCLUSION_ONLY"
    assert widget_data.GOVERNANCE_OVERRIDES["AS-922"] == "AUDIT_ONLY_QUARANTINED"

