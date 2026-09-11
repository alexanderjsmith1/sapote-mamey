from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXEMPLAR = ROOT / "docs/reference/modeb_exemplars/phosphonate_reference_full48_no_blastp_exemplar.md"
README = ROOT / "docs/reference/modeb_exemplars/README.md"
INDEX = ROOT / "docs/MODE_B_DOCUMENT_INDEX.md"


def test_exemplar_declares_typed_terminal_calibration_boundary():
    text = EXEMPLAR.read_text(encoding="utf-8")
    assert "Calibration boundary" in text
    assert "typed-terminal format exemplar" in text
    assert "not positive substantive calibration" in text
    assert "§§20, 39, 40, 42, or 48" in text
    assert "MODEB_GATE_CLEAN_AUTHORING.md" in text


def test_exemplar_registry_uses_same_role():
    text = README.read_text(encoding="utf-8")
    assert "CURRENT_TYPED_TERMINAL_FORMAT_EXEMPLAR" in text
    assert "not positive calibration for §§20/39/40/42/48" in text


def test_mode_b_document_index_does_not_call_it_unqualified_current_gold():
    text = INDEX.read_text(encoding="utf-8")
    matching = [line for line in text.splitlines() if "phosphonate_reference_full48_no_blastp_exemplar.md" in line]
    assert matching
    assert "typed-terminal format exemplar" in matching[0]
    assert "not positive substantive calibration" in matching[0]
