"""test_write_narrative_and_toc.py — tests for W3 + W6 (v9.7.149c).

W3 covers:
- `mamey write-narrative` subcommand: validates section name, runs claim-
  safety linter, writes to judgment/, refuses on findings unless --force
- `--toc-depth` flag on compile-report
- Single source of truth: session_resume's strict-runnable probe agrees
  with compile_report.STRICT_NARRATIVE_KEYS

W6 covers (regression-pin, since v9.7.149b already inlines correctly):
- compile_report._ferm_section inlines from judgment/<strain>_fermentation_section.md
  when present, and falls back to the SAPOTE slot when absent

Fixtures use AS-XXX only.
"""
from __future__ import annotations

import json
import pathlib

import pytest


def _bare_pkg(tmp_path: pathlib.Path,
              strain_id: str = "AS-XXX") -> pathlib.Path:
    pkg = tmp_path / strain_id / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": strain_id}))
    (pkg / "manifest_short.json").write_text(json.dumps(
        {"strain_id": strain_id}))
    return pkg


# ---------------------------------------------------------------------------
# W3 — write_narrative()
# ---------------------------------------------------------------------------

def test_write_narrative_clean_content_writes_to_judgment(tmp_path):
    from mamey.compile_report import write_narrative
    pkg = _bare_pkg(tmp_path)
    content = (
        "The strain shows biosynthetic capacity consistent with a Type II "
        "PKS pathway based on the architecture of the locus."
    )
    res = write_narrative(pkg, "executive_summary", content)
    assert res["status"] == "WRITTEN"
    assert res["findings"] == []
    target = pkg / "judgment" / "AS-XXX_execsummary_section.md"
    assert target.exists()
    assert "biosynthetic capacity" in target.read_text(encoding="utf-8")


def test_write_narrative_refuses_overclaim_without_force(tmp_path):
    from mamey.compile_report import write_narrative
    pkg = _bare_pkg(tmp_path)
    # "produces erythromycin" trips the claim-safety linter
    content = "The strain produces erythromycin in moderate yield."
    res = write_narrative(pkg, "executive_summary", content)
    assert res["status"] == "REFUSED"
    assert res["findings"], "linter should have surfaced an overclaim"
    target = pkg / "judgment" / "AS-XXX_execsummary_section.md"
    assert not target.exists(), "refused write must not produce a file"


def test_write_narrative_force_cannot_bypass_claim_safety(tmp_path):
    # v9.7.409 (CLAUDE narrative-gates): --force must NOT ship an overclaiming narrative. A
    # claim-safety finding is a HARD refusal regardless of force. (Before .409 this returned WRITTEN
    # and dropped the overclaim into judgment/ — the bug this patch closes.)
    from mamey.compile_report import write_narrative
    pkg = _bare_pkg(tmp_path)
    content = "The strain produces erythromycin in moderate yield."
    res = write_narrative(pkg, "executive_summary", content, force=True)
    assert res["status"] == "REFUSED", "force must not override a claim-safety finding"
    assert res["findings"], "the overclaim must still be surfaced"
    target = pkg / "judgment" / "AS-XXX_execsummary_section.md"
    assert not target.exists(), "a force-refused write must not produce a file"


def test_write_narrative_rejects_unknown_section(tmp_path):
    from mamey.compile_report import write_narrative
    pkg = _bare_pkg(tmp_path)
    res = write_narrative(pkg, "not_a_real_section", "anything")
    assert res["status"] == "UNKNOWN_SECTION"
    assert "valid_sections" in res
    assert "executive_summary" in res["valid_sections"]


def test_write_narrative_covers_all_four_strict_sections(tmp_path):
    """All four sections that strict-runnable requires must be writable
    via this command — otherwise --strict is unsatisfiable through the
    documented path."""
    from mamey.compile_report import write_narrative, STRICT_NARRATIVE_KEYS
    pkg = _bare_pkg(tmp_path)
    content = "A clean, capacity-based description of the strain's potential."
    for key in STRICT_NARRATIVE_KEYS:
        res = write_narrative(pkg, key, content)
        assert res["status"] == "WRITTEN", f"failed: {key} -> {res}"


def test_write_narrative_satisfies_strict_runnable(tmp_path):
    """End-to-end: writing all four sections via write_narrative makes
    `mamey resume`'s strict_runnable flag True."""
    from mamey.compile_report import write_narrative, STRICT_NARRATIVE_KEYS
    from mamey.session_resume import build_resume
    pkg = _bare_pkg(tmp_path)
    content = "A clean, capacity-based description."
    for key in STRICT_NARRATIVE_KEYS:
        write_narrative(pkg, key, content)
    result = build_resume(pkg)
    assert result["strict_runnable"] is True
    assert result["strict_missing_sections"] == []


# ---------------------------------------------------------------------------
# W3 — single source of truth (W1-F5)
# ---------------------------------------------------------------------------

def test_strict_section_list_matches_compile_report(tmp_path):
    """session_resume's strict list must derive from compile_report — no
    silent drift if compile_report adds or renames a section."""
    from mamey import session_resume, compile_report
    # session_resume should have used the imported list, not the fallback
    # Resolve both lists in a strain-agnostic way and compare
    resume_filenames = set(
        s.format(strain="X") for s in session_resume._STRICT_NARRATIVE_SECTIONS
    )
    cr_filenames = set(
        compile_report.narrative_filename(k, "X")
        for k in compile_report.STRICT_NARRATIVE_KEYS
        if compile_report.narrative_filename(k, "X")
    )
    assert resume_filenames == cr_filenames, (
        f"strict-section drift: resume={resume_filenames} vs "
        f"compile_report={cr_filenames}"
    )


# ---------------------------------------------------------------------------
# W3 — --toc-depth
# ---------------------------------------------------------------------------

def test_toc_depth_default_is_1(tmp_path):
    from mamey.compile_report import build_report
    pkg = _bare_pkg(tmp_path)
    md = build_report(pkg, generate_figures=False)
    assert "toc-depth: 1" in md


def test_toc_depth_configurable(tmp_path):
    from mamey.compile_report import build_report
    pkg = _bare_pkg(tmp_path)
    md = build_report(pkg, generate_figures=False, toc_depth=3)
    assert "toc-depth: 3" in md


# ---------------------------------------------------------------------------
# W6 — fermentation section regression (already-correct behaviour)
# ---------------------------------------------------------------------------

def test_ferm_section_inlines_from_disk_when_present(tmp_path):
    """W6 regression: when judgment/<strain>_fermentation_section.md exists,
    compile-report inlines its content rather than emitting the SAPOTE slot.
    This behaviour was already implemented in v9.7.149b — the wishlist text
    describing W6 as a gap was incorrect. This test pins it so any future
    regression is caught."""
    from mamey.compile_report import build_report
    pkg = _bare_pkg(tmp_path)
    (pkg / "judgment").mkdir()
    (pkg / "judgment" / "AS-XXX_fermentation_section.md").write_text(
        "## BGC001\n\nInlined fermentation note for BGC001."
    )
    md = build_report(pkg, generate_figures=False)
    # §11 must contain the inlined text, not the SAPOTE slot
    assert "Inlined fermentation note for BGC001" in md
    assert "SAPOTE:fermentation" not in md


def test_ferm_section_falls_back_to_slot_when_absent(tmp_path):
    """v9.7.344: with no authored fermentation file present, the section now fills with a
    deterministic genus/class bench DRAFT (the author refines it) instead of an open
    SAPOTE:fermentation narrative slot. `fermentation` is a deterministic-source slot, not a
    narrative one — so the fallback is a draft, never the unfilled marker."""
    from mamey.compile_report import build_report
    pkg = _bare_pkg(tmp_path)
    md = build_report(pkg, generate_figures=False)
    # No authored file → deterministic draft fills the section; the open marker is NOT emitted.
    assert "SAPOTE:fermentation" not in md
    assert "11. Fermentation and wet-lab guidance" in md
    assert "Deterministic starting-point draft" in md
