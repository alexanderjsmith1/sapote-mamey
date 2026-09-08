"""test_ingest_modeb_verdicts_merge.py — BC2-408: ingest_package.py must merge the per-package
modeb_verdicts.csv into a cohort-level <banked_dir>/modeb_verdicts.csv.

mamey/cli.py's `_write_package` writes `modeb_verdicts.csv` into each sealed PACKAGE directory
(gold mode only). Six downstream cohort-level tools (`tools/build_modeb_deepdive.py`,
`tools/generate_bgc_atlas.py`, `tools/build_thesis_vignettes.py`, `tools/build_subset_panel.py`,
`tools/lead_board.py`, `tools/build_lead_tiers.py`) all read that same filename from the COHORT
path, `<banked_dir>/modeb_verdicts.csv` — but before this fix, no tool anywhere in the codebase
ever merged the per-package rows into that cohort file, so every one of those six tools silently
(or, for build_lead_tiers.py pre-.408, fatally — a separate, already-landed card) got an empty
verdict map on any bank built purely via the documented `ingest_package.py --package <pkg>
--merge` workflow.

This verifies: (1) build_entry() lifts modeb_verdicts.csv off the package dir when present, and
is silently empty when absent (pkg_dir=None, or a package with no such file — non-gold-mode
packages don't emit one); (2) merge() writes those rows into the cohort-level
<banked_dir>/modeb_verdicts.csv with the engine's own MODEB_VERDICT_HEADERS; (3) a re-ingest of
the same strain REPLACES that strain's rows (the same per-strain replace-on-reingest semantics
already used for bgc_data.json/tfbs_coupling.json) without disturbing any other strain's rows;
(4) a strain with no verdicts to contribute leaves the cohort file's other strains untouched.
"""
from __future__ import annotations

import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import ingest_package as ip  # noqa: E402


def _minimal_snapshot(sid="SIDTEST1"):
    return {
        "strain_id": sid,
        "taxonomy": f"Streptomyces sp. {sid}",
        "assembly": {"contigs": 10, "n50": 500000, "genome_bp": 8000000,
                     "gc_pct": 71.2, "largest_contig": 900000},
        "bgc_counts": {"raw": 1, "corrected": 1.0, "interior": 1,
                       "full_contig": 0, "edge": 0},
        "bgcs": [
            {"bgc_id": "BGC001", "region_number": 1, "contig": "ctg1",
             "products": ["NRPS"], "edge_status": "Interior", "start": 1000, "end": 21000},
        ],
        "source_scans": {
            "tfbs": {"counts": {}, "total_hits": 0},
            "rggmci": {"status": "NULL_NO_RGGMCI_PAIRS"},
        },
    }


def _write_pkg_modeb_verdicts(pkg_dir, rows):
    """Write a per-package modeb_verdicts.csv exactly as mamey/cli.py::_write_package does:
    header from MODEB_VERDICT_HEADERS, one row per BGC."""
    path = os.path.join(pkg_dir, "modeb_verdicts.csv")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["strain", "bgc", "status", "modeb_class", "note"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


def _fresh_banked_dir(tmp):
    """The minimal bank files merge() expects, all empty — modeb_verdicts.csv intentionally
    NOT created, mirroring the real first-time-bank case this bug was found against."""
    json.dump({"strains": {}, "bgcs": []}, open(f"{tmp}/bgc_data.json", "w"))
    json.dump({"scan_agg": {}, "tfbs": {}}, open(f"{tmp}/gene_data.json", "w"))
    json.dump({}, open(f"{tmp}/rggmci_full.json", "w"))
    json.dump({}, open(f"{tmp}/tigrfam.json", "w"))
    json.dump({}, open(f"{tmp}/strains.json", "w"))


def test_modeb_verdict_headers_matches_engine():
    """_modeb_verdict_headers() must resolve to the engine's own MODEB_VERDICT_HEADERS
    (mamey/deep_data.py) — the exact schema mamey/cli.py::_write_package writes."""
    assert ip._modeb_verdict_headers() == ["strain", "bgc", "status", "modeb_class", "note"]


def test_build_entry_lifts_modeb_verdicts_from_package(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    _write_pkg_modeb_verdicts(str(pkg), [
        {"strain": "SIDTEST1", "bgc": "BGC001", "status": "CONFIRM",
         "modeb_class": "nrps", "note": "no exclusion flag"},
    ])
    entry = ip.build_entry(_minimal_snapshot(), ww="WWTEST00000000", pkg_dir=str(pkg))
    assert "modeb_verdicts" in entry, "build_entry must emit a modeb_verdicts field"
    assert entry["modeb_verdicts"] == [
        {"strain": "SIDTEST1", "bgc": "BGC001", "status": "CONFIRM",
         "modeb_class": "nrps", "note": "no exclusion flag"},
    ]


def test_build_entry_modeb_verdicts_empty_when_absent(tmp_path):
    # no pkg_dir at all
    entry = ip.build_entry(_minimal_snapshot(), ww="WWTEST00000000", pkg_dir=None)
    assert entry["modeb_verdicts"] == []
    # a package dir that exists but has no modeb_verdicts.csv (e.g. a non-gold-mode package,
    # or a package sealed before mamey/cli.py started emitting the file)
    pkg = tmp_path / "pkg_no_verdicts"
    pkg.mkdir()
    entry2 = ip.build_entry(_minimal_snapshot(), ww="WWTEST00000000", pkg_dir=str(pkg))
    assert entry2["modeb_verdicts"] == []


def test_merge_writes_cohort_level_modeb_verdicts_csv(tmp_path):
    bank = tmp_path / "bank"
    bank.mkdir()
    _fresh_banked_dir(str(bank))
    assert not (bank / "modeb_verdicts.csv").exists()

    pkg = tmp_path / "pkg"
    pkg.mkdir()
    _write_pkg_modeb_verdicts(str(pkg), [
        {"strain": "SIDTEST1", "bgc": "BGC001", "status": "CONFIRM",
         "modeb_class": "nrps", "note": "no exclusion flag"},
    ])
    entry = ip.build_entry(_minimal_snapshot(), ww="WWTEST00000000", pkg_dir=str(pkg))
    ip.merge(entry, str(bank))

    mv_path = bank / "modeb_verdicts.csv"
    assert mv_path.exists(), "merge() must create the cohort-level modeb_verdicts.csv (BC2-408)"
    rows = list(csv.DictReader(open(mv_path, encoding="utf-8")))
    assert rows == [
        {"strain": "SIDTEST1", "bgc": "BGC001", "status": "CONFIRM",
         "modeb_class": "nrps", "note": "no exclusion flag"},
    ]
    # this is what every one of the six downstream consumers actually keys on
    vmap = {(r["strain"], r["bgc"]): r["status"] for r in rows}
    assert vmap[("SIDTEST1", "BGC001")] == "CONFIRM"


def test_merge_replaces_only_this_strains_rows_on_reingest(tmp_path):
    """Re-ingesting a strain must drop its OLD rows and write its NEW rows, while another
    strain's rows already in the cohort file are left untouched — the same per-strain
    replace-on-reingest contract merge() already applies to bgc_data.json/tfbs_coupling.json."""
    bank = tmp_path / "bank"
    bank.mkdir()
    _fresh_banked_dir(str(bank))
    # pre-seed the cohort file as if a prior ingest had already run: one row for the strain
    # under test (now stale — a re-run changed its verdict) and one row for a different strain.
    with open(bank / "modeb_verdicts.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["strain", "bgc", "status", "modeb_class", "note"])
        w.writeheader()
        w.writerow({"strain": "SIDTEST1", "bgc": "BGC999", "status": "DROP",
                    "modeb_class": "", "note": "stale — superseded by re-run"})
        w.writerow({"strain": "OTHERSID", "bgc": "BGCX", "status": "CONFIRM",
                    "modeb_class": "terpene", "note": "unrelated strain"})

    pkg = tmp_path / "pkg"
    pkg.mkdir()
    _write_pkg_modeb_verdicts(str(pkg), [
        {"strain": "SIDTEST1", "bgc": "BGC001", "status": "CONFIRM",
         "modeb_class": "nrps", "note": "no exclusion flag"},
    ])
    entry = ip.build_entry(_minimal_snapshot(), ww="WWTEST00000000", pkg_dir=str(pkg))
    ip.merge(entry, str(bank))

    rows = list(csv.DictReader(open(bank / "modeb_verdicts.csv", encoding="utf-8")))
    keyed = {(r["strain"], r["bgc"]): r for r in rows}
    assert ("SIDTEST1", "BGC999") not in keyed, "stale SIDTEST1 row must be replaced, not accumulated"
    assert ("SIDTEST1", "BGC001") in keyed and keyed[("SIDTEST1", "BGC001")]["status"] == "CONFIRM"
    assert ("OTHERSID", "BGCX") in keyed, "a different strain's rows must survive this strain's re-ingest"
    assert keyed[("OTHERSID", "BGCX")]["status"] == "CONFIRM"


def test_merge_with_no_package_verdicts_leaves_other_strains_untouched(tmp_path):
    """A strain ingested from a package with no modeb_verdicts.csv (e.g. non-gold mode)
    contributes zero rows and must not disturb any other strain already banked."""
    bank = tmp_path / "bank"
    bank.mkdir()
    _fresh_banked_dir(str(bank))
    with open(bank / "modeb_verdicts.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["strain", "bgc", "status", "modeb_class", "note"])
        w.writeheader()
        w.writerow({"strain": "OTHERSID", "bgc": "BGCX", "status": "CONFIRM",
                    "modeb_class": "terpene", "note": "unrelated strain"})

    entry = ip.build_entry(_minimal_snapshot(), ww="WWTEST00000000", pkg_dir=None)
    assert entry["modeb_verdicts"] == []
    ip.merge(entry, str(bank))

    rows = list(csv.DictReader(open(bank / "modeb_verdicts.csv", encoding="utf-8")))
    keyed = {(r["strain"], r["bgc"]): r for r in rows}
    assert ("OTHERSID", "BGCX") in keyed and keyed[("OTHERSID", "BGCX")]["status"] == "CONFIRM"
    assert not any(r["strain"] == "SIDTEST1" for r in rows), \
        "a strain with no package verdicts must contribute no rows"


if __name__ == "__main__":
    import tempfile
    from pathlib import Path

    tests = [
        test_modeb_verdict_headers_matches_engine,
        test_build_entry_lifts_modeb_verdicts_from_package,
        test_build_entry_modeb_verdicts_empty_when_absent,
        test_merge_writes_cohort_level_modeb_verdicts_csv,
        test_merge_replaces_only_this_strains_rows_on_reingest,
        test_merge_with_no_package_verdicts_leaves_other_strains_untouched,
    ]
    passed = 0
    for t in tests:
        try:
            import inspect
            if "tmp_path" in inspect.signature(t).parameters:
                with tempfile.TemporaryDirectory() as _tmp:
                    t(Path(_tmp))
            else:
                t()
            passed += 1
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
        except Exception as e:
            import traceback
            print(f"ERROR {t.__name__}: {e}")
            traceback.print_exc()
    print(f"\n{passed}/{len(tests)} passed")
