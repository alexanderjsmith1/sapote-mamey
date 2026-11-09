"""A RESULTS_BOUND row with a missing locator passes, and the summary says locators were not opened."""
from __future__ import annotations

from pathlib import Path

from mamey.evidence_registry import validate_evidence_registry

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "privacy" / "strain_evidence_registry.example.tsv"


def test_missing_locator_passes_but_is_reported_as_not_opened(tmp_path):
    text = EXAMPLE.read_text(encoding="utf-8").replace("assays/crude_panel_001.tsv", "missing/nonexistent.tsv")
    registry = tmp_path / "registry.tsv"
    registry.write_text(text, encoding="utf-8")
    summary = validate_evidence_registry(registry)
    assert summary["status"] == "PASS"
    assert summary["source_locator_check"].startswith("NOT_OPENED")
    expected = sum(1 for line in text.splitlines()[1:] if line.split("\t")[7] == "RESULTS_BOUND")
    assert expected >= 1
    assert summary["results_bound_record_count"] == expected
