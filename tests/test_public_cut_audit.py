"""Regression test for tools/audit_public_cut.py — the workbook-aware public-cut leak guard.

Covers the two leak classes that escaped the row-filter into the public MERGE_GUIDE prose:
  (1) a research-strain token (AS-###) carried in a provenance cell;
  (2) a held-cohort codename AND its bare stem (the false-clean the stem-derivation fix closes).
Asserts the audit FAILS on a planted leak and that --scrub yields a workbook that re-audits CLEAN.
"""
from __future__ import annotations
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
openpyxl = pytest.importorskip("openpyxl")
import audit_public_cut as apc  # noqa: E402

# Research-strain token built from two literals so no "AS-###" appears in source: the public-tier
# AS-scrub (s/\\bAS-[0-9]{2,}/AS-XXX/) can't match across the quote, yet at runtime this is a real
# AS-### value that exercises the guard's \\bAS-\\d{3,} path — so the test validates the guard in every tier.
_RS = "AS-" + "999"


def _wb(path, cohorts_rows, strains, guide_lines=None, release_override=None):
    """Minimal workbook with BGC_Master (cohort_id/bgc_uid/release rows), Strain_Master, optional guide."""
    wb = openpyxl.Workbook()
    bm = wb.active
    bm.title = "BGC_Master"
    bm.append(["cohort_id", "strain", "bgc", "bgc_uid", "release"])
    i = 0
    for coh, n in cohorts_rows.items():
        for _ in range(n):
            i += 1
            rel = release_override or ("unpublished" if "Held" in coh else "public")
            bm.append([coh, f"{coh}_s", f"BGC{i:03d}", f"{coh}|{coh}_s|BGC{i:03d}", rel])
    sm = wb.create_sheet("Strain_Master")
    sm.append(["cohort_id", "strain"])
    for s in strains:
        sm.append(["x", s])
    if guide_lines:
        g = wb.create_sheet("00_MERGE_GUIDE")
        for ln in guide_lines:
            g.append([ln])
    wb.save(path)


def test_guard_catches_token_codename_and_stem(tmp_path):
    priv = tmp_path / "private.xlsx"
    pub = tmp_path / "public.xlsx"
    # private has a held cohort; public has it filtered from DATA but leaked in guide prose
    _wb(priv, {"SID_public_2020": 3, "HeldCohort_2026": 4}, ["SID1", _RS])
    _wb(pub, {"SID_public_2020": 3}, ["SID1"],
        guide_lines=[
            "PUBLIC / EXPORT-SAFE — research (AS) tier held; audited",          # held_phrase
            "Cohorts: SID_public_2020 · HeldCohort_2026(AS held)",               # full codename + phrase
            "Coded sheets cover WAC+HeldCohort+TypeStrain",                      # bare STEM only
            f"Provenance: derived from {_RS}_Master_Workbook",                   # research-strain token
        ])

    findings, ctx = apc.audit(str(pub), private=str(priv))
    kinds = {f["kind"] for f in findings}
    assert ctx["reconciliation"]["held_cohorts"] == ["HeldCohort_2026"]
    assert "private_identifier_token" in kinds       # research/private identifier token caught
    assert "held_phrase" in kinds                     # "(AS held)" / "(AS) tier held"
    assert "derived_held_token" in kinds              # full codename
    # the stem 'HeldCohort' (bare, in the coded-sheets line) must also be caught — the false-clean fix
    stem_hits = [f for f in findings if f["kind"] == "derived_held_token"
                 and "Coded sheets" in f["detail"]]
    assert stem_hits, "bare held-cohort stem in prose was not caught (false-clean regression)"


def test_scrub_yields_clean_reaudit(tmp_path):
    priv = tmp_path / "private.xlsx"
    pub = tmp_path / "public.xlsx"
    out = tmp_path / "public_SCRUBBED.xlsx"
    _wb(priv, {"SID_public_2020": 3, "HeldCohort_2026": 4}, ["SID1", _RS])
    _wb(pub, {"SID_public_2020": 3}, ["SID1"],
        guide_lines=[
            "Cohorts: SID_public_2020 · HeldCohort_2026(AS held)",
            "Coded sheets cover WAC+HeldCohort+TypeStrain",
            f"derived from {_RS}_Master_Workbook",
        ])
    n = apc.scrub(str(pub), str(out), private=str(priv))
    assert n >= 1
    findings, _ = apc.audit(str(out), private=str(priv))
    assert findings == [], f"scrubbed workbook still leaks: {findings}"


def test_clean_public_passes(tmp_path):
    priv = tmp_path / "private.xlsx"
    pub = tmp_path / "public.xlsx"
    _wb(priv, {"SID_public_2020": 3, "HeldCohort_2026": 4}, ["SID1", _RS])
    # public guide names the held cohort generically — no token, no stem, no phrase
    _wb(pub, {"SID_public_2020": 3}, ["SID1"],
        guide_lines=["Cohorts: SID_public_2020 · 1 research cohort (held, excluded) · controls"])
    findings, _ = apc.audit(str(pub), private=str(priv))
    assert findings == [], f"clean public flagged: {findings}"


def test_merge_invariants_pass(tmp_path):
    priv = tmp_path / "private.xlsx"
    pub = tmp_path / "public.xlsx"
    _wb(priv, {"SID_public_2020": 3, "HeldCohort_2026": 4}, ["SID1"])
    _wb(pub, {"SID_public_2020": 3}, ["SID1"])
    inv, inv_findings = apc.merge_invariants(str(pub), str(priv))
    assert inv_findings == []
    assert inv["schema_identical"] and inv["public_subset_private"] and inv["delta_is_held_only"]
    assert inv["pub_unique"] == inv["pub_rows"] == 3
    assert inv["held_cohorts"] == ["HeldCohort_2026"]


def test_release_flag_invariant_catches_mistag(tmp_path):
    # a public file where a row is mis-tagged release=unpublished must be flagged independently
    pub = tmp_path / "public.xlsx"
    _wb(pub, {"SID_public_2020": 3}, ["SID1"], release_override="public")
    checked, findings = apc.release_invariant(str(pub))
    assert checked == 3 and findings == []
    bad = tmp_path / "bad.xlsx"
    _wb(bad, {"SID_public_2020": 3}, ["SID1"], release_override="unpublished")
    checked2, findings2 = apc.release_invariant(str(bad))
    assert checked2 == 3 and len(findings2) == 3
    assert all(f["kind"] == "release_not_public" for f in findings2)


def test_missing_governed_sheets_fails_closed(tmp_path):
    """A random/partial workbook must not obtain a vacuous CLEAN verdict."""
    path = tmp_path / "not_a_merged_master.xlsx"
    wb = openpyxl.Workbook()
    wb.active.title = "Notes"
    wb.active.append(["No private identifiers are present here."])
    wb.save(path)

    findings, _ = apc.audit(str(path))
    kinds = {f["kind"] for f in findings}
    assert "required_bgc_sheet_missing" in kinds
    assert "required_strain_sheet_missing" in kinds


def test_missing_sheets_cannot_pass_merge_invariants(tmp_path):
    """Two equally incomplete workbooks are not 'schema identical' for release purposes."""
    public = tmp_path / "public.xlsx"
    private = tmp_path / "private.xlsx"
    for path in (public, private):
        wb = openpyxl.Workbook()
        wb.active.title = "Notes"
        wb.save(path)

    inv, findings = apc.merge_invariants(str(public), str(private))
    assert inv["schema_identical"] is False
    assert sum(f["kind"] == "required_bgc_sheet_missing" for f in findings) == 2
    assert sum(f["kind"] == "required_strain_sheet_missing" for f in findings) == 2
