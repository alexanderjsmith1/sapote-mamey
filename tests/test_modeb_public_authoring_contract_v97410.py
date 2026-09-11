from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_full_run_profile_does_not_present_front_matter_as_full48_structure():
    text = _text("prompts/FULL_RUN_PROFILE.md")
    assert "not the complete section structure" in text
    assert "does not replace the exact ordered §1–§48 contract" in text
    assert "emit-modeb-template" in text
    assert "MODEB_GATE_CLEAN_AUTHORING.md" in text


def test_public_authoring_contract_names_source_bound_requirements_for_four_sections():
    text = _text("docs/MODEB_GATE_CLEAN_AUTHORING.md")
    for section in (39, 40, 42, 48):
        assert f"§{section}" in text
    for requirement in (
        "separate denominators",
        "canonical qualified-family",
        "declared baseline population",
        "complete validated upstream receipt inventory",
        "exactly one",
        "support and refute consequences",
    ):
        assert requirement in text


def test_public_contract_marks_private_gate_material_as_non_authoring_input():
    text = _text("docs/MODEB_GATE_CLEAN_AUTHORING.md")
    assert "not authoring inputs" in text
    for secret_class in (
        "Private scoring weights",
        "phrase dictionaries",
        "holdout identities",
        "per-feature score",
    ):
        assert secret_class in text


def test_context_hygiene_separates_receipts_from_owner_secrets():
    text = _text("docs/MODEB_LLM_AUTHORING_CONTEXT_HYGIENE.md")
    assert "validated source-specific receipts" in text
    assert "owner authentication keys" in text
    assert "private attempt ledgers" in text
    assert "private calibration manifests" in text
    assert "Feedback boundary" in text


def test_feedback_is_coarse_and_replay_resistant():
    text = _text("docs/MODEB_LLM_AUTHORING_CONTEXT_HYGIENE.md")
    for route in (
        "PASS_TO_HUMAN_REVIEW",
        "HOLD_FOR_REWRITE",
        "UNSCORABLE_EVIDENCE_UNBOUND",
    ):
        assert route in text
    assert "Do not expose exact" in text
    assert "repeated probing" in text
