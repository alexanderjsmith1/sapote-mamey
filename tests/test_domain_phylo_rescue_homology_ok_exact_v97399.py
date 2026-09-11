"""Regression: domain_phylo_rescue._HOMOLOGY_OK is exactly the two real confidence values (v9.7.399).

`_HOMOLOGY_OK` shipped five literals, three of which are DEAD — the engine only ever emits
`HIGH_RG_GMCI_RESCUE`, `MODERATE_RG_GMCI_CANDIDATE`, `LOW_SHARED_REFERENCE_SIGNAL`
(verified in mamey/rggmci.py). The real MODERATE value matched only by the `.startswith("MODERATE")`
fallback, so the exact set alone would have missed it — working by coincidence. This pins the guard
to the two real exact values (the canonical pattern already used at scoring.py, rescue_two_proof.py,
cli.py) and drops the `.startswith` fallback, which also removed a real FALSE-POSITIVE: any bogus
`HIGH*`/`MODERATE*` string previously corroborated by prefix.

GOVERNING two-proof guard (rggmci-two-proof). Class-level linkage evidence; judgment deferred.
"""
from pathlib import Path
import csv
import sys

_TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
import domain_phylo_rescue as dpr  # noqa: E402


def _csv(tmp_path, rows):
    p = tmp_path / "rggmci.csv"
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["query_bgc", "partner_bgc", "rggmci_confidence"])
        w.writeheader()
        for a, b, c in rows:
            w.writerow({"query_bgc": a, "partner_bgc": b, "rggmci_confidence": c})
    return p


def test_the_two_real_values_corroborate(tmp_path):
    pairs = dpr.load_rggmci_pairs(_csv(tmp_path, [
        ("BGC_A", "BGC_B", "HIGH_RG_GMCI_RESCUE"),
        ("BGC_C", "BGC_D", "MODERATE_RG_GMCI_CANDIDATE"),
    ]))
    assert frozenset(("BGC_A", "BGC_B")) in pairs
    assert frozenset(("BGC_C", "BGC_D")) in pairs


def test_low_shared_reference_signal_does_not_corroborate(tmp_path):
    pairs = dpr.load_rggmci_pairs(_csv(tmp_path, [
        ("BGC_E", "BGC_F", "LOW_SHARED_REFERENCE_SIGNAL"),
    ]))
    assert pairs == set()


def test_no_false_positive_prefix_match(tmp_path):
    # the whole point of dropping .startswith: a bogus HIGH*/MODERATE* must NOT corroborate
    pairs = dpr.load_rggmci_pairs(_csv(tmp_path, [
        ("BGC_G", "BGC_H", "HIGHER_NOISE"),
        ("BGC_I", "BGC_J", "MODERATELY_CONVERGENT"),
    ]))
    assert pairs == set(), f"prefix false-positive leaked through: {pairs}"


def test_homology_ok_is_exactly_the_two_real_values():
    assert dpr._HOMOLOGY_OK == {"HIGH_RG_GMCI_RESCUE", "MODERATE_RG_GMCI_CANDIDATE"}
