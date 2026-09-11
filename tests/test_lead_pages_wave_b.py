"""Wave B (v9.7.341 follow-up) — lead-only §31–40 enrichment + related-genomes dossier pages.

Ported from the verified reference impl `reference_impl/build_lead_pages.py` (roadmap patch #4
dossier + #7 lead-enrichment) into `mamey/lead_pages.py`, reusing the shipped Wave A
`mamey.assembly_line` module for the predicted assembly walk.

These tests lock the two contracts the cards name:
  - #7: a stub/Inventory BGC never gets §31–40; a genuine lead does, with aSDomain-only module
    counts and resistance/transport surfaced.
  - #4: a lead page renders its MIBiG anchor and ≥1 NCBI related-genome reference from the package,
    under the fixed claim ceiling (similarity, not identity; reference metadata is the neighbour's).
"""

import os
import glob
import tempfile
from types import SimpleNamespace

import pytest

from mamey import lead_pages


def _find_sealed_package():
    """Locate any sealed package produced this session; skip if none is present in the tier."""
    for base in ("/tmp/sealship", "./seal338c", "./seal338b"):
        hits = glob.glob(os.path.join(base, "*", "package", "*_2_inventory.csv"))
        if hits:
            return os.path.dirname(hits[0])
    return None


PKG = _find_sealed_package()
needs_pkg = pytest.mark.skipif(PKG is None, reason="no sealed package present in this environment")


def test_module_imports_without_side_effects():
    """Import must not require the literature-table file (lazy load) — it degrades to GENERIC."""
    assert hasattr(lead_pages, "lead_pages_command")
    assert hasattr(lead_pages, "_asm_line")
    # the lazy loader returns a dict with at least GENERIC even if the data file is absent
    lit = lead_pages._load_lit()
    assert isinstance(lit, dict) and "GENERIC" in lit


def test_lead_only_gate_excludes_nonleads():
    """_is_lead is the §31–40 gate: only Exceptional/High/Medium pass."""
    for tier in ("Exceptional", "High", "Medium"):
        assert lead_pages._is_lead({"Lead_tier_auto": tier}) is True
    for tier in ("Inventory", "Low", "VOID", "", "Stub"):
        assert lead_pages._is_lead({"Lead_tier_auto": tier}) is False


@needs_pkg
def test_default_scope_emits_only_lead_pages():
    """A default run emits pages for leads only; non-leads are skipped, not rendered."""
    out = tempfile.mkdtemp(prefix="wb_lead_")
    rc = lead_pages.lead_pages_command(
        SimpleNamespace(package=PKG, out=out, bgc="ALL", all_tiers=False))
    assert rc == 0
    pages = glob.glob(os.path.join(out, "*.md"))
    # every emitted page must correspond to a lead tier
    import csv
    tri = {r["BGC_ID"]: r for r in lead_pages.rows(PKG, "_4_triage_board.csv")}
    for p in pages:
        bgc = os.path.basename(p).split("_")[-2]  # <strain>_<BGC>_LEAD.md
        # the emitted BGC id appears in the filename; its triage row must be a lead tier
        matches = [b for b in tri if b in os.path.basename(p)]
        assert matches, f"emitted page {p} has no triage row"
        assert lead_pages._is_lead(tri[matches[0]]), f"{matches[0]} is not a lead but got a page"


@needs_pkg
def test_lead_page_carries_enrichment_and_reference_context():
    """A rendered lead page carries the enrichment substance (#7) and reference context (#4)."""
    out = tempfile.mkdtemp(prefix="wb_content_")
    lead_pages.lead_pages_command(
        SimpleNamespace(package=PKG, out=out, bgc="ALL", all_tiers=True))
    pages = glob.glob(os.path.join(out, "*.md"))
    assert pages, "expected at least one page under --all-tiers"
    md = open(pages[0]).read().lower()
    # #7 enrichment substance
    assert "## the call" in md
    assert "tailoring" in md
    # #4 reference context: MIBiG anchor + ClusterBlast (NCBI) references
    assert "mibig" in md
    assert "clusterblast" in md or "related" in md
    # claim ceiling text is fixed in the template
    assert "similarity, not identity" in md


@needs_pkg
def test_assembly_line_adapter_uses_the_engine_module():
    """_asm_line must route through the shipped Wave A engine module, returning a string."""
    inv = lead_pages.rows(PKG, "_2_inventory.csv")
    assert inv, "package has no inventory"
    bgc = inv[0]["BGC_ID"]
    s = lead_pages._asm_line(PKG, bgc)
    assert isinstance(s, str)  # empty string if no domains, never an exception


# --- v9.7.347 release-health: NC-006/007/008 claim-safety regression guards ---
import re as _re
from pathlib import Path as _Path


def _lead_pages_src():
    return _Path(lead_pages.__file__).read_text()


def test_nc006_no_bare_except_in_lead_pages():
    """NC-006: no bare `except:` clauses (they swallow everything, including claim-safety branches)."""
    src = _lead_pages_src()
    assert not _re.search(r"^\s*except\s*:", src, _re.M), "lead_pages.py must not contain bare except:"


def test_nc007_length_fraction_not_coerced_to_one():
    """NC-007: an absent/invalid length_fraction must NOT be coerced to 1.0 (fail-open completeness)."""
    src = _lead_pages_src()
    assert "lff = 1.0" not in src, "absent length_fraction must not default to 1.0 (unresolved != complete)"
    assert "lff = None" in src, "absent length_fraction must resolve to None (UNRESOLVED)"
    assert "Completeness UNRESOLVED" in src, "must emit an explicit UNRESOLVED-completeness note"
    # the fragment/absence comparisons must be None-guarded
    assert "lff is not None and lff < 0.5" in src


def test_nc008_no_genuinely_absent_when_completeness_unresolved():
    """NC-008: 'genuinely absent' resistance wording only when the window is resolved-complete."""
    src = _lead_pages_src()
    # the genuinely-absent branch must be gated behind an explicit else (resolved), with an UNRESOLVED path
    assert "not evidence of absence" in src, "UNRESOLVED completeness must be labelled 'not evidence of absence'"
    idx_unresolved = src.index("window completeness UNRESOLVED")
    idx_absent = src.index("genuinely absent on current evidence")
    # the UNRESOLVED elif must precede the genuinely-absent else in the self-resistance block
    assert idx_unresolved < idx_absent
