"""test_compilation_gate.py — contract test for the compendium PDF compilation gate.

The gate (tools/compilation_gate.py, PDF_COMPILATION_GATE_20260624) must:
  - FAIL a stub compendium (thin cards, partial Mode B coverage, placeholder manifest)
  - PASS a full compendium (every scorable BGC carded at depth, full 13-item contract)
  - FAIL on G3 when a rendered PDF is below the genome-size-scaled page floor
  - scale the page floor correctly with BGC count

These assertions are the structural guarantee that a half-compendium can never be handed
over as a "compendium" — the PDF analogue of the "never say complete" rule.
"""
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))

import compilation_gate as cg  # noqa: E402

FIX = _ROOT / "tests" / "fixtures" / "compilation_gate"


def test_page_floor_scales_with_bgc_count():
    # Lower bound, scaled to genome size. Boundaries matter.
    assert cg.page_floor(10) == 30      # small / fragmented
    assert cg.page_floor(14) == 30
    assert cg.page_floor(15) == 60      # typical small genome
    assert cg.page_floor(35) == 60
    assert cg.page_floor(36) == 100     # full mid-size actinomycete
    assert cg.page_floor(70) == 100
    assert cg.page_floor(71) == 140     # large
    assert cg.page_floor(110) == 140
    assert cg.page_floor(111) == 180    # very large / fragmented
    assert cg.page_floor(139) == 180


def test_stub_compendium_fails_pre_render():
    """A stub must fail — partial coverage, stub-depth cards, placeholder manifest."""
    receipt = cg.run_gate(
        md_path=str(FIX / "stub_compendium.md"),
        manifest=str(FIX / "manifest_fail.md"),
        scorable_bgcs=5,
        pdf=None,
        mode="standard",
    )
    assert receipt["gate"] == "FAIL"
    # the specific gates that must catch a stub:
    assert receipt["checks"]["G1"] is False  # placeholder manifest row
    assert receipt["checks"]["G2"] is False  # 2 of 5 carded
    assert receipt["checks"]["G4"] is False  # stub-depth cards
    assert receipt["checks"]["G5"] is False  # no §-sections / gene rows
    assert receipt["mode_b_cards"] == 2


def test_full_compendium_passes_pre_render():
    """A full compendium with all 13 contract items and every BGC carded must pass."""
    receipt = cg.run_gate(
        md_path=str(FIX / "full_compendium.md"),
        manifest=str(FIX / "manifest_pass.md"),
        scorable_bgcs=5,
        pdf=None,
        mode="standard",
    )
    assert receipt["gate"] == "PASS"
    assert all(receipt["checks"].values())
    assert receipt["mode_b_cards"] == 5


def test_g2_denominator_is_full_scorable_count():
    """Coverage is judged against the full scorable count, never the carded count.

    The full fixture has 5 cards; if the strain actually has 8 scorable BGCs, the gate
    must fail G2 — a strain that cards 5 of 8 is not a compendium.
    """
    receipt = cg.run_gate(
        md_path=str(FIX / "full_compendium.md"),
        manifest=str(FIX / "manifest_pass.md"),
        scorable_bgcs=8,          # more scorable than carded
        pdf=None,
        mode="standard",
    )
    assert receipt["gate"] == "FAIL"
    assert receipt["checks"]["G2"] is False
    assert receipt["mode_b_cards"] == 5


def test_g3_fails_when_pdf_below_floor(tmp_path):
    """A rendered PDF below the page floor fails G3 (post-render)."""
    pytest.importorskip("reportlab")
    import shutil
    if not shutil.which("pdfinfo"):
        pytest.skip("pdfinfo binary unavailable; G3 page-count check cannot run")
    from reportlab.pdfgen import canvas

    pdf = tmp_path / "thin.pdf"
    c = canvas.Canvas(str(pdf))
    for i in range(3):  # 3 pages, well below the floor of 30 for 5 BGCs
        c.drawString(72, 720, f"page {i + 1}")
        c.showPage()
    c.save()

    receipt = cg.run_gate(
        md_path=str(FIX / "full_compendium.md"),
        manifest=str(FIX / "manifest_pass.md"),
        scorable_bgcs=5,
        pdf=str(pdf),
        mode="standard",
    )
    assert receipt["gate"] == "FAIL"
    assert receipt["checks"]["G3"] is False
    assert receipt["page_count"] == 3
    assert receipt["page_floor"] == 30


def test_pre_render_defers_g3_not_fails_it():
    """Without a PDF, G3 is deferred (True), not failed — pre-render checks stand alone."""
    receipt = cg.run_gate(
        md_path=str(FIX / "full_compendium.md"),
        manifest=str(FIX / "manifest_pass.md"),
        scorable_bgcs=5,
        pdf=None,
        mode="standard",
    )
    assert receipt["checks"]["G3"] is True
    assert receipt["page_count"] is None
    assert receipt["post_render"] is False


# v9.7.150f — Bunny Hop finding #9/#51: G2 must cross-check against
# modeb_structure_gate.py's §1–§30 contract, not just count card headers.
# A card present-but-legacy-scaffold must not count as "carded".

def test_g2_rejects_legacy_scaffold_card_even_if_present():
    """A card with §1 Identity / §2 Assembly headers (old scaffold) is
    present (passes naive counting) but must fail G2 since it doesn't
    satisfy the §1-30 structure gate."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'compilation_gate', __file__.replace('tests/test_compilation_gate.py',
                                              'tools/compilation_gate.py'))
    cg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cg)

    legacy_card = (
        "## BGC001\n"
        "**§1 Identity**\nSome text.\n"
        "**§2 Assembly**\nMore text.\n"
    )
    ok, msgs, n = cg.g2_modeb_coverage(legacy_card, scorable_bgcs=1)
    assert ok is False, "Legacy-scaffold card should fail G2, not pass"
    assert any("structurally invalid" in m for m in msgs)


def test_g2_structure_gate_uses_absolute_import():
    """Regression guard: tools/compilation_gate.py is a standalone script,
    not part of the mamey package — a relative import of modeb_structure_gate
    silently fails in that context. This caused the structure cross-check to
    never fire (found and fixed in the same patch, v9.7.150f)."""
    src = open('tools/compilation_gate.py').read()
    assert 'from .modeb_structure_gate import' not in src, (
        "Relative import will silently fail in this standalone-script context"
    )
    assert 'from mamey.modeb_structure_gate import' in src
