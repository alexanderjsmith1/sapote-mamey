"""F10 regression: ingest_package must lift per-BGC regulator coupling from the
snapshot (source_scans.regulators.bgc_coupling) into cohort/tfbs_coupling.json.

Before F10, ingest never wrote the coupling bank, so every newly-ingested strain
was absent from tfbs_coupling.json and lead_board left all its CONFIRMs at Class
B — a silent lock-out from Class A/C. These tests assert the coupling is written,
keyed per BGC, and that a SARP-coupled BGC is detectable (the Class-A signal).

Run standalone (pytest-free):  python3 tests/test_ingest_coupling.py
"""
from __future__ import annotations
import json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tools.ingest_package as ip


def _minimal_snapshot():
    """A minimal but build_entry-valid snapshot with a SARP-coupled BGC001 and
    an unregulated BGC002."""
    return {
        "strain_id": "SIDTEST1",
        "taxonomy": "Streptomyces sp. SIDTEST1",
        "assembly": {"contigs": 10, "n50": 500000, "genome_bp": 8000000,
                     "gc_pct": 71.2, "largest_contig": 900000},
        "bgc_counts": {"raw": 2, "corrected": 2.0, "interior": 1,
                       "full_contig": 1, "edge": 0},
        "bgcs": [
            {"bgc_id": "BGC001", "region_number": 1, "contig": "ctg1",
             "products": ["NRPS"], "edge_status": "Interior", "start": 1000, "end": 21000},
            {"bgc_id": "BGC002", "region_number": 1, "contig": "ctg2",
             "products": ["terpene"], "edge_status": "Full-contig", "start": 0, "end": 5000},
        ],
        "source_scans": {
            "tfbs": {"counts": {"DasR_like_palindrome": 3}, "total_hits": 3},
            "rggmci": {"status": "NULL_NO_RGGMCI_PAIRS"},
            "regulators": {
                "status": "SOURCE_DERIVED",
                "bgc_coupling": {"BGC001": ["DasR_GntR", "SARP", "TetR"]},
                # BGC002 intentionally absent -> assessed, no regulator
            },
        },
    }


def _fresh_banked_dir(tmp):
    """Create the minimal bank files merge() expects, all empty."""
    json.dump({"strains": {}, "bgcs": []}, open(f"{tmp}/bgc_data.json", "w"))
    json.dump({"scan_agg": {}, "tfbs": {}}, open(f"{tmp}/gene_data.json", "w"))
    json.dump({}, open(f"{tmp}/rggmci_full.json", "w"))
    json.dump({}, open(f"{tmp}/tigrfam.json", "w"))
    json.dump({}, open(f"{tmp}/strains.json", "w"))
    # tfbs_coupling.json intentionally NOT created — F10 must create/extend it


def test_build_entry_lifts_coupling():
    entry = ip.build_entry(_minimal_snapshot(), ww="WWTEST00000000", pkg_dir=None)
    assert "coupling" in entry, "build_entry must emit a coupling field"
    assert entry["coupling"].get("BGC001") == ["DasR_GntR", "SARP", "TetR"], \
        f"BGC001 coupling wrong: {entry['coupling']}"
    assert "BGC002" not in entry["coupling"], "BGC002 had no regulators; must not appear"


def test_merge_writes_coupling_bank():
    with tempfile.TemporaryDirectory() as tmp:
        _fresh_banked_dir(tmp)
        entry = ip.build_entry(_minimal_snapshot(), ww="WWTEST00000000", pkg_dir=None)
        ip.merge(entry, tmp)
        cp = json.load(open(f"{tmp}/tfbs_coupling.json"))
        assert "SIDTEST1" in cp, "strain absent from tfbs_coupling.json after merge (F10 not fixed)"
        assert "SARP" in cp["SIDTEST1"]["BGC001"], "SARP coupling not written"
        # the lead_board Class-A test: a SARP-coupled BGC must be detectable
        regs = cp["SIDTEST1"]["BGC001"]
        sarp_supported = any("SARP" in x for x in regs)
        assert sarp_supported, "SARP-coupled BGC not flagged — Class A still blocked"


def test_tigrfam_panel_includes_section8():
    """tigr8 second instance: ingest's panel must not be the stale 4-ID list."""
    panel = ip._diagnostic_tigrfam_ids()
    for acc in ("TIGR04462", "TIGR03550", "TIGR04363", "TIGR01181"):
        assert acc in panel, f"{acc} missing from ingest TIGRFAM panel (tigr8 regressed)"


if __name__ == "__main__":
    tests = [test_build_entry_lifts_coupling,
             test_merge_writes_coupling_bank,
             test_tigrfam_panel_includes_section8]
    passed = 0
    for t in tests:
        try:
            t(); passed += 1; print(f"PASS {t.__name__}")
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
        except Exception as e:
            import traceback; print(f"ERROR {t.__name__}: {e}"); traceback.print_exc()
    print(f"\n{passed}/{len(tests)} passed")
