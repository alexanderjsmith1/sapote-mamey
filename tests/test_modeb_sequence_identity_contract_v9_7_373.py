from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / "docs" / "MODEB_PUBLICATION_SECTION_REQUIREMENTS_v9_7_372.md"
SUPPORT = ROOT / "docs" / "MODE_B_SUPPORT_CARD_CONTRACT.md"


def test_publication_contract_requires_sequence_first_positive_identity():
    text = " ".join(PUBLICATION.read_text(encoding="utf-8").split())
    required = (
        "amino-acid sequence SHA-256 is the positive identity key",
        "Protein length is rejection-only",
        "ordered neighborhood signature",
        "result-job receipt",
        "OBSERVED_UNBOUND",
        "Observed and admitted channel counts are reported separately",
    )
    for phrase in required:
        assert phrase in text


def test_support_contract_rejects_label_and_length_only_joins():
    text = " ".join(SUPPORT.read_text(encoding="utf-8").split())
    required = (
        "Equal length is never positive identity",
        "query sequence exactly matches the current raw translation by SHA-256",
        "minimal ordered-neighborhood signature",
        "query, channel/database, and result-job receipts",
        "locus label, BGC alias, gene label, or amino-acid length alone is insufficient",
        "observed versus admitted coverage for every channel",
    )
    for phrase in required:
        assert phrase in text


def test_contract_keeps_claim_authority_separate():
    publication = PUBLICATION.read_text(encoding="utf-8")
    assert "may not assign owner acceptance" in publication
    assert "publication approval" in publication
