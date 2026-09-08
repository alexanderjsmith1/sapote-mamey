"""v9.7.372 publication-quality repair — Aquarius complementary-layer tests.

The gate-side program (broken tables, §§5-7 scaffolds, stream dispositions, section matrix,
readiness cap) is implemented and tested by the Codex combined patch
(tests/test_modeb_publication_quality_v9_7_372.py + the matrix/emitter/readiness files). These
tests pin the AQUARIUS layers that patch does not touch: front-door named-profile alignment,
the contract JSON profile block, and the channel-separated matrix schema constants.
"""
import json
import pathlib

from mamey.mode_b.schema import (
    canonical_matrix_columns, MODEB_MATRIX_CHANNELS, MODEB_MATRIX_MISSING_STATES)

ROOT = pathlib.Path(__file__).resolve().parents[1]

FRONT_DOORS = [
    "SESSION_START_MANIFEST.md",
    "skills/sapote-mamey/SKILL.md",
    "CHATGPT_START_HERE.md",
    "CLAUDE_START_HERE.md",
    "docs/MODE_B_30_SECTION_CANONICAL_TITLES.md",
    "docs/FULL_MODEB_30_SECTION_CONTRACT_v97150.md",
]


def test_front_doors_teach_the_named_profiles():
    for rel in FRONT_DOORS:
        text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
        assert "FINISHED_FULL48_CURRENT_EVIDENCE" in text, f"{rel} does not name the strict profile"


def test_contract_json_is_full48_with_profiles():
    d = json.loads((ROOT / "mamey/data/mode_b/modeb_full30_corrective_contract.json").read_text())
    assert d["schema_version"] == "modeb_corrective_full48_v1"
    assert "FINISHED_FULL48_CURRENT_EVIDENCE" in d.get("profiles", {})
    assert any("Character counts" in q for q in d["quality_gate"])


def test_matrix_schema_keeps_channels_separate():
    cols = canonical_matrix_columns()
    for ch in MODEB_MATRIX_CHANNELS:
        assert f"{ch}_pct_identity" in cols and f"{ch}_accession" in cols
    assert "pct_identity" not in cols
    assert "NR" in MODEB_MATRIX_MISSING_STATES and "NOT_RUN" in MODEB_MATRIX_MISSING_STATES


def test_mechanical_states_never_claim_release():
    """Codex combined cap: highest deterministic state is EVIDENCE_MATRIX_VALIDATED."""
    from mamey.modeb_structure_gate import readiness_state
    state = readiness_state([], "FULL")
    for banned in ("RELEASE", "PUBLICATION"):
        assert banned not in state
