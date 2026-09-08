"""EFLS scan-state reporting must distinguish the full total from the capped listed records.

`source_scans.scan_efls()` returns two different things:

    "candidate_pairs":      sorted(candidates, key=score, reverse=True)[:500]   <- TRUNCATED
    "candidate_pair_count": len(candidates)                                     <- the real total

The retained-list cap is deliberate and unchanged. Current payloads expose the complete total
alongside that list. Legacy payloads may lack the total; their detail must state that the total is
unavailable while still reporting how many records are listed.

Every assertion below drives the REAL production function. An earlier draft of this file tested a
local helper that duplicated the fixed logic — it passed before the fix and was therefore worthless.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.external_adapters import run_external_scan_pack  # noqa: E402
from mamey.models import SourceScanBundle  # noqa: E402
from mamey.source_scans import scan_efls  # noqa: E402

_EMPTY = {"status": "NULL", "counts": {}, "bgc_coupling": {}}


def _bundle(efls: dict) -> SourceScanBundle:
    """A bundle whose only interesting member is EFLS; every other scan is inert."""
    return SourceScanBundle(
        chitinase=dict(_EMPTY), tfbs=dict(_EMPTY), blda_tta=dict(_EMPTY),
        regulators=dict(_EMPTY), transporters=dict(_EMPTY), resistance=dict(_EMPTY),
        cctt=dict(_EMPTY), flbr=dict(_EMPTY), cassettes=dict(_EMPTY), umed={"per_bgc": {}},
        efls=efls, domain_architecture=dict(_EMPTY), resistance_tiers={"per_bgc": {}},
        wetlab_rows={}, qs_signals=dict(_EMPTY), glycosylation_arms=dict(_EMPTY),
        per_bgc_dss={}, rggmci={},
    )


def _efls_row(efls: dict):
    """Run the real adapter and return its ('EFLS', state, detail) row."""
    out = run_external_scan_pack(_bundle(efls), antismash_evidence={})
    rows = [r for r in out["scans"] if r and str(r[0]).upper() == "EFLS"]
    assert rows, f"no EFLS row emitted; got {[r[0] for r in out['scans']]}"
    return rows[0]


def _efls(n_total: int, n_listed: int) -> dict:
    return {
        "status": "SOURCE_DERIVED_PRELIMINARY_LINKAGE",
        "candidate_pairs": [{"bgc_a": f"BGC{i:03d}", "bgc_b": f"BGC{i + 1:03d}", "score": 1}
                            for i in range(n_listed)],
        "candidate_pair_count": n_total,
    }


def test_capped_list_reports_total_and_listed_counts_separately():
    """A generic over-cap fixture must expose both the complete and retained quantities."""
    _, state, detail = _efls_row(_efls(n_total=780, n_listed=500))
    assert state == "PASS"
    assert detail == "780 candidate pairs total; 500 listed", detail


def test_untruncated_case_is_unchanged():
    """Below the cap, the two equal quantities remain explicitly labeled."""
    assert _efls_row(_efls(17, 17))[2] == "17 candidate pairs total; 17 listed"


def test_zero_pairs_reads_as_null():
    _, state, detail = _efls_row(_efls(0, 0))
    assert state == "NULL"
    assert detail == "0 candidate pairs total; 0 listed"


def test_missing_count_field_labels_total_unavailable_and_reports_listed_count():
    """Legacy payloads must not present the retained-list length as a verified total."""
    _, state, detail = _efls_row({"candidate_pairs": [
        {"bgc_a": "FIXTURE_A", "bgc_b": "FIXTURE_B"},
        {"bgc_a": "FIXTURE_C", "bgc_b": "FIXTURE_D"},
        {"bgc_a": "FIXTURE_E", "bgc_b": "FIXTURE_F"},
    ]})
    assert state == "PASS"
    assert detail == "total candidate pairs unavailable (legacy); 3 listed", detail


def test_missing_count_and_empty_list_is_legacy_null_not_known_zero_total():
    _, state, detail = _efls_row({"candidate_pairs": []})
    assert state == "NULL"
    assert detail == "total candidate pairs unavailable (legacy); 0 listed"


def test_scan_efls_really_caps_the_list_but_not_the_count():
    """Pin the precondition against the real scan, so this file cannot rot into a tautology if
    the cap is ever removed or re-tuned."""
    class _B:
        def __init__(self, i):
            self.bgc_id = f"BGC{i:03d}"
            self.edge_status = "Edge"      # never Interior+Interior, so no pair is filtered out
            self.products = ["nrps"]       # one shared product -> every pair scores
            self.mibig_hits = []
            self.contig = "c1"

    out = scan_efls([_B(i) for i in range(40)], {}, {}, {})   # 40*39/2 = 780 pairs
    assert out["candidate_pair_count"] == 780
    assert len(out["candidate_pairs"]) == 500
    assert out["candidate_pair_count"] != len(out["candidate_pairs"])


def test_end_to_end_scan_efls_into_the_adapter():
    """The two halves joined: a real scan_efls result, over the cap, must be reported by the real
    adapter at its true size."""
    class _B:
        def __init__(self, i):
            self.bgc_id = f"BGC{i:03d}"
            self.edge_status = "Edge"
            self.products = ["nrps"]
            self.mibig_hits = []
            self.contig = "c1"

    efls = scan_efls([_B(i) for i in range(40)], {}, {}, {})
    assert _efls_row(efls)[2] == "780 candidate pairs total; 500 listed"
