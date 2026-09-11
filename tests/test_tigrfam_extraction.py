"""Regression test for the v9.4.1-tigrfix defect.

The package evidence extractor was Pfam-centric and dropped TIGRFAM diagnostics
(AHBA_synth_RP, ene_KS, TIGR03604, NikJ-family) that antiSMASH stores in the
JSON antismash.detection.tigrfam module rather than in GBK sec_met_domain
qualifiers. This caused false-negative class calls for ansamycin / enediyne /
thiopeptide / nucleoside.

These tests assert the diagnostics are now surfaced as tier-1 hits.

Run standalone (pytest-free):  python3 tests/test_tigrfam_extraction.py
"""
from __future__ import annotations
from tests._uploads_fixture import UPLOADS as _UPLOADS, OUTPUTS as _OUTPUTS  # v9.7.416
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mamey.antismash_evidence import (
    extract_tigrfam_hits, merge_tigrfam_into_pfam_hits,
    DIAGNOSTIC_TIGRFAM, _TIER1_DOMAIN_NAMES, _tigrfam_from_rec,
)

# Real rifamycini genomic antiSMASH zip used to find the defect. If absent
# (CI without the fixture), the structural tests below still run.
_RIF_ZIP = (_UPLOADS + "/Actinomadura_rifamycini_DSM_43936_ASM42506v1_genomic.zip")


def _skip_if_no_fixture(reason: str) -> None:
    """Emit a proper pytest skip when run under pytest; stay a no-op for the
    pytest-free standalone runner (see module docstring). Detecting pytest via
    sys.modules avoids importing it at top level, so `python3 tests/...` still
    works without pytest installed."""
    if "pytest" in sys.modules:
        import pytest
        pytest.skip(reason)


def test_tigrfam_diagnostics_in_tier1():
    """Tier-1-flagged diagnostics must be in the tier-1 set; non-tier-1
    diagnostics (NAPAA housekeeping) must NOT be (excluded from comparative
    claims per standing rule)."""
    for acc, (_cls, _desc, tier1) in DIAGNOSTIC_TIGRFAM.items():
        if tier1:
            assert acc in _TIER1_DOMAIN_NAMES, f"{acc} tier-1 but missing from tier-1 set"
        else:
            assert acc not in _TIER1_DOMAIN_NAMES, f"{acc} non-tier-1 but present in tier-1 set"


def test_section8_diagnostic_ids_surfaced():
    """v9.6.15-tigr8: the §8 diagnostic-combination TIGRFAM accessions must all
    be in the allowlist, or the §8 combos silently never fire (the 943->4
    collapse). Guards against re-narrowing the allowlist."""
    section8 = {
        "TIGR04462", "TIGR04460",               # enduracididine NRPS
        "TIGR03550", "TIGR03551", "TIGR03620",  # F420-embedded polyketide
        "TIGR04363", "TIGR04364",               # FxLD class-I lanthipeptide
        "TIGR01181",                            # glycosylated T2PKS
        "TIGR03604",                            # TOMM heterocyclic RiPP
    }
    missing = section8 - set(DIAGNOSTIC_TIGRFAM)
    assert not missing, f"§8 diagnostic TIGRFAM IDs dropped from allowlist: {sorted(missing)}"


def test_merge_is_append_only():
    """Merging must not drop pre-existing Pfam hits for a region."""
    gbk = {"ctgX_c1": [{"domain_name": "HAD_2", "tier1_diagnostic": False,
                         "locus_tag": "ctgX_9"}]}
    tf = {"ctgX_c1": [{"domain_name": "TIGR01454", "tier1_diagnostic": True,
                        "locus_tag": "ctgX_9", "tigrfam_class": "ansamycin"}]}
    merged = merge_tigrfam_into_pfam_hits(gbk, tf)
    names = [h["domain_name"] for h in merged["ctgX_c1"]]
    assert "HAD_2" in names and "TIGR01454" in names, \
        "merge must retain BOTH the generic Pfam and the TIGRFAM diagnostic"


def test_tigrfam_diagnostics_recovered_synthetic():
    """v9.7.6: exercise the JSON tigrfam extraction path (the v9.4.1-tigrfix
    defect surface) in EVERY tier via a tiny shipped synthetic antiSMASH zip —
    no proprietary genome needed. Covers ansamycin/enediyne/thiopeptide and
    confirms a non-diagnostic accession is filtered out. The rifamycini test
    below stays as a local-only exact-value deep guard."""
    synth = Path(__file__).resolve().parent / "fixtures" / "synthetic_tigrfam_antismash.zip"
    if not synth.exists():
        _skip_if_no_fixture("synthetic tigrfam fixture missing from bundle")
        print("  [skip] synthetic tigrfam fixture missing"); return
    tf = extract_tigrfam_hits(str(synth))
    flat = [h for hits in tf.values() for h in hits]
    by_acc = {h["domain_name"]: h for h in flat}
    # ansamycin diagnostic recovered tier-1 at the expected locus/bitscore
    assert "TIGR01454" in by_acc, "AHBA_synth_RP (TIGR01454) not recovered from JSON tigrfam module"
    ahba = by_acc["TIGR01454"]
    assert ahba["tier1_diagnostic"] is True and ahba["tigrfam_class"] == "ansamycin"
    assert ahba["locus_tag"] == "synthctgA_9"
    assert float(ahba["bitscore"]) > 300
    # multi-class coverage: enediyne + thiopeptide diagnostics also surface
    assert "TIGR03828" in by_acc and by_acc["TIGR03828"]["tigrfam_class"] == "enediyne"
    assert "TIGR03604" in by_acc and by_acc["TIGR03604"]["tigrfam_class"] == "thiopeptide"
    # non-diagnostic housekeeping accession must be filtered out
    assert "TIGR99999" not in by_acc, "non-diagnostic TIGRFAM accession leaked into hits"


def test_tigrfam_hit_resolves_to_its_own_region_not_always_region1():
    """BC2-408: a real gap found while auditing (not merely a regression guard). Before this
    fix, `_tigrfam_from_rec` keyed EVERY TIGRFAM hit under `f"{rec_id}_c1"` unconditionally --
    correct only by coincidence when a contig carries exactly one antiSMASH region. On any
    contig with >=2 regions, a hit belonging to region002 (or later) was silently mis-keyed
    into region001's bucket, cross-contaminating region001's BGC and starving the hit's own
    true BGC of a diagnostic it should have had. Downstream consumers (lead_board.py's
    `_tigrfam_hits_for_region`, antismash_tables.py's `build_hmm_table`) do an EXACT region_key
    dict lookup against this output, so both silently inherited the misattribution.

    Fix: resolve the hit's true region via genomic coordinate overlap against `rec['areas']`
    (index i = region i+1, the SAME convention nrps_predictions.py::extract_region_polymers
    already relies on in the forward direction) using the hit's own `location` field, which
    real antiSMASH JSON does carry per hit (verified against a real antiSMASH output; not an
    assumption about the schema)."""
    rec = {
        "id": "NODE_1",
        "areas": [
            {"start": 0, "end": 20000},      # region001
            {"start": 40000, "end": 60000},  # region002
        ],
        "modules": {"antismash.detection.tigrfam": {"hits": [
            {"identifier": "TIGR03828", "description": "ene_KS enediyne", "evalue": "1e-50",
             "score": "200", "locus_tag": "ctg1_45", "location": "[45000:45900](-)"},  # region002
            {"identifier": "TIGR01454", "description": "AHBA_synth_RP", "evalue": "1e-40",
             "score": "150", "locus_tag": "ctg1_5", "location": "[5000:5900](+)"},     # region001
        ]}},
    }
    out: dict = {}
    _tigrfam_from_rec(rec, "NODE_1.json", out)
    assert set(out.keys()) == {"NODE_1_c1", "NODE_1_c2"}, (
        f"both hits collapsed onto one region key: {sorted(out.keys())}")
    assert [h["domain_name"] for h in out["NODE_1_c1"]] == ["TIGR01454"]
    assert [h["domain_name"] for h in out["NODE_1_c2"]] == ["TIGR03828"]


def test_tigrfam_hit_falls_back_to_region1_when_unresolvable():
    """Graceful degradation: no `location` field, or no `areas` -- surface the hit under the
    historical "_c1" fallback rather than dropping it silently (matches the pre-fix behaviour
    exactly for the case it can't be improved on)."""
    rec_no_location = {"id": "NODE_2", "areas": [{"start": 0, "end": 1000}],
                       "modules": {"antismash.detection.tigrfam": {"hits": [
                           {"identifier": "TIGR01454", "locus_tag": "ctg2_1"}]}}}
    out: dict = {}
    _tigrfam_from_rec(rec_no_location, "NODE_2.json", out)
    assert set(out.keys()) == {"NODE_2_c1"}

    rec_no_areas = {"id": "NODE_3",
                    "modules": {"antismash.detection.tigrfam": {"hits": [
                        {"identifier": "TIGR01454", "locus_tag": "ctg3_1",
                         "location": "[500:900](+)"}]}}}
    out2: dict = {}
    _tigrfam_from_rec(rec_no_areas, "NODE_3.json", out2)
    assert set(out2.keys()) == {"NODE_3_c1"}


def test_ahba_recovered_from_rifamycini():
    """On the real rifamycini genome, AHBA_synth_RP must surface tier-1."""
    if not Path(_RIF_ZIP).exists():
        _skip_if_no_fixture("rifamycini fixture not present (local-only data file)")
        print("  [skip] rifamycini fixture not present")
        return
    tf = extract_tigrfam_hits(_RIF_ZIP)
    flat = [h for hits in tf.values() for h in hits]
    ahba = [h for h in flat if h["domain_name"] == "TIGR01454"]
    assert ahba, "AHBA_synth_RP (TIGR01454) not recovered — defect regressed"
    h = ahba[0]
    assert h["tier1_diagnostic"] is True
    assert h["locus_tag"] == "ctg23_9", f"unexpected locus {h['locus_tag']}"
    assert float(h["bitscore"]) > 300, "AHBA bitscore should be ~372"
    print(f"  AHBA recovered: {h['locus_tag']} score={h['bitscore']}")


if __name__ == "__main__":
    tests = [test_tigrfam_diagnostics_in_tier1,
             test_section8_diagnostic_ids_surfaced,
             test_merge_is_append_only,
             test_tigrfam_diagnostics_recovered_synthetic,
             test_tigrfam_hit_resolves_to_its_own_region_not_always_region1,
             test_tigrfam_hit_falls_back_to_region1_when_unresolvable,
             test_ahba_recovered_from_rifamycini]
    passed = 0
    for t in tests:
        try:
            t(); passed += 1; print(f"PASS {t.__name__}")
        except AssertionError as e:
            print(f"FAIL {t.__name__}: {e}")
        except Exception as e:
            print(f"ERROR {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
