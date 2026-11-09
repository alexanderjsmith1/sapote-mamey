# Synthetic regression inputs only.
"""The strain_id provenance row does not claim a user-supplied, high-confidence identity.

The engine can take strain_id from --strain, the archive organism name or the ZIP filename, and the
cell-provenance writer is not told which. The row and the glossary must say so.
"""
from __future__ import annotations

from types import SimpleNamespace

from mamey.cell_provenance import STATUS_GLOSSARY, build_cell_provenance


def _strain_row(tmp_path):
    run = SimpleNamespace(context=SimpleNamespace(strain_id="Example_strain_1"), bgcs=[])
    rows = build_cell_provenance(run, tmp_path)
    return next(r for r in rows if r["cell_or_field"] == "strain_id")


def test_strain_row_names_every_derivation_and_is_not_high_confidence(tmp_path):
    row = _strain_row(tmp_path)
    assert row["confidence"] != "high"
    assert "not verified" in row["confidence"]
    assert "ZIP filename" in row["derived_from"] and "does not record which" in row["derived_from"]
    assert "not a verified identity" in row["notes_for_llm"]


def test_user_metadata_glossary_does_not_claim_user_supplied_only():
    text = STATUS_GLOSSARY["COMPLETE_USER_METADATA"]
    assert text != "Filled from user-supplied metadata."
    assert "ZIP filename" in text and "Not verified" in text
