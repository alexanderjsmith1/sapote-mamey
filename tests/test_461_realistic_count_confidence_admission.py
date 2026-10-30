"""Confidence-token admission only; symbolic keys are not biological loci."""
import csv
import importlib.util
from pathlib import Path
import pytest

_SPEC = importlib.util.spec_from_file_location("rc461", Path(__file__).resolve().parents[1] / "tools/realistic_bgc_count.py")
rc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(rc)


@pytest.mark.parametrize("confidence,accepted", [
    ("NOT_HIGH_CONFIDENCE", False), ("HIGHLY_UNCERTAIN", False),
    ("LOW", False), ("MODERATE_RG_GMCI_RESCUE", False), ("", False),
    ("HIGH_RG_GMCI_RESCUE", True), ("HIGH", True),
    (" high_rG_gmci_rescue ", True), (" high ", True),
])
def test_admission_matches_existing_high_token_contract(tmp_path, confidence, accepted):
    with (tmp_path / "PUBLIC_4A_RGGMCI_ranked_pairs.csv").open("w", newline="") as h:
        w = csv.writer(h)
        w.writerow(["bgc_a", "bgc_b", "rggmci_confidence"])
        w.writerow(["left", "right", confidence])
    assert rc._high_rggmci_pairs(str(tmp_path)) == ([("left", "right")] if accepted else [])
