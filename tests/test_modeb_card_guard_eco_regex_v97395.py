"""v9.7.395: modeb_card_guard's strain-phrase ecology pattern must work for
EVERY genus in its alternation, not only the last one.

Regression cover for the .394 hole: in `card_identity()` the ecology pattern
`rf"{GEN} sp\\.? \\(([a-z\\- ]+?)[-\\s]associated"` interpolated the genus alternation WITHOUT
wrapping parentheses. Regex alternation binds at top level, so the ` sp. (...-associated` tail —
and the eco capture group inside it — attached only to the final alternative (Nocardiopsis).
For all other genera, a card that states its ecology solely via the strain phrase
"<Genus> sp. (bee-associated)" extracted NO ecology; `check()` then skipped the ecology
comparison entirely (`if aeco and ceco`), so a fabricated ecology PASSED the guard whose header
says it exists to catch exactly that (the 2026-08-17 incident class: 1,559 cards with a
hardcoded wrong host).

Reproduced on pristine .394: the identical bee-for-moss fabrication FAILed when phrased with
Nocardiopsis but PASSed when phrased with Streptomyces.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"


@pytest.fixture()
def guard(tmp_path, monkeypatch):
    """Load the module with AS_STRAIN_MASTER pointed at a synthetic strain-data root."""
    asm = tmp_path / "strain_data"
    for strain, genus in (("AS-940", "Streptomyces"), ("AS-941", "Nocardiopsis")):
        d = asm / strain
        d.mkdir(parents=True)
        (d / "STRAIN_CARD.md").write_text(
            f"| **Genus** | {genus} |\n| **Host / location** | moss (Ontario) |\n")
    monkeypatch.setenv("AS_STRAIN_MASTER", str(asm))
    spec = importlib.util.spec_from_file_location(
        "modeb_card_guard_under_test", TOOLS / "modeb_card_guard.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fab_card(tmp_path, strain, genus):
    p = tmp_path / f"{strain}_ModeB_card.md"
    p.write_text(f"## S1\nThis BGC sits in {genus} sp. (bee-associated) strain {strain}.\n")
    return p


def test_strain_phrase_eco_extracted_for_nonfinal_genus(guard):
    """The strain-phrase pattern must extract ecology for a NON-final alternation branch."""
    gen, eco = guard.card_identity(
        "This BGC sits in Streptomyces sp. (bee-associated) strain AS-940.")
    assert gen == "Streptomyces"
    assert "bee" in eco, "strain-phrase ecology not extracted for a non-final genus branch"


def test_fabricated_ecology_fails_for_nonfinal_genus(guard, tmp_path):
    """A bee-associated claim on a moss strain must FAIL regardless of which genus phrases it."""
    card = _fab_card(tmp_path, "AS-940", "Streptomyces")
    status, _path, msg = guard.check(str(card))
    assert status == "FAIL" and "ECOLOGY" in msg, (status, msg)


def test_fabricated_ecology_still_fails_for_final_genus(guard, tmp_path):
    """Control (worked pre-fix): the final alternation branch keeps failing the fabrication."""
    card = _fab_card(tmp_path, "AS-941", "Nocardiopsis")
    status, _path, msg = guard.check(str(card))
    assert status == "FAIL" and "ECOLOGY" in msg, (status, msg)


def test_truthful_card_still_passes(guard, tmp_path):
    """A card agreeing with the STRAIN_CARD (moss) must PASS — the fix adds no false FAILs."""
    p = tmp_path / "AS-940_ModeB_card.md"
    p.write_text("## S1\nThis BGC sits in Streptomyces sp. (moss-associated) strain AS-940.\n")
    status, _path, msg = guard.check(str(p))
    assert status == "PASS", (status, msg)
