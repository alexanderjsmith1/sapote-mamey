"""Tests for the reference-BGC concordance check + library integrity."""
import json
import os

from mamey import concordance as C

LIB = os.path.join(os.path.dirname(__file__), "..", "mamey", "data", "reference_bgc_library.json")


def _lib():
    return C.load_reference_library()


# ---- library integrity --------------------------------------------------------------------------
def test_library_loads_and_has_entries():
    lib = _lib()
    assert lib["schema_version"] == "1.0"
    assert len(lib["entries"]) >= 17
    for e in lib["entries"]:
        # required keys present on every entry
        for k in ("compound", "class", "genus", "accession", "found_size_kb",
                  "found_markers", "expected_marker_set", "marker_set_source"):
            assert k in e, f"{e.get('compound')} missing {k}"


def test_no_fabricated_genus_uses_unresolved_sentinel():
    # honest UNRESOLVED rather than a guessed genus. A-94964 (LC431526) and
    # lipopeptide 8D1 (KT362047) were UNRESOLVED until their GBKs were supplied; both
    # now carry a genus read from /organism (Streptomyces) - an observed resolution, not
    # a guess. onnamide A is an uncultured sponge symbiont with no clean taxonomy and
    # must stay UNRESOLVED.
    lib = _lib()
    genera = {e["compound"]: e["genus"] for e in lib["entries"]}
    assert genera["onnamide A"] == "UNRESOLVED"
    # no genus is left as an empty/placeholder string
    assert all(g and g.strip() for g in genera.values())
    # genus-targeted reference is present and correctly attributed
    assert genera["nocardicin"] == "Nocardia"


def test_lit_and_marker_fields_are_well_formed():
    # after LIT load: mibig_accession is populated (not the PENDING sentinel), expected_marker_set is the
    # T43-level set for concordance_check, lit_diagnostic_genes (when present) holds the gene/domain set.
    lib = _lib()
    for e in lib["entries"]:
        assert isinstance(e.get("expected_marker_set", []), list)
        for m in e.get("expected_marker_set", []):
            assert str(m).startswith("T43-"), f"{e['compound']} expected_marker_set must be T43-level, got {m}"
        assert "mibig_accession" in e
    # the three definitional-marker references carry their T43 marker
    by = {e["compound"]: e for e in lib["entries"]}
    assert "T43-ENE" in by["C-1027"]["expected_marker_set"]
    assert "T43-PTM" in by["HSAF"]["expected_marker_set"]


# ---- anchor resolution --------------------------------------------------------------------------
def test_resolve_anchor_exact_and_alias():
    lib = _lib()
    assert C.resolve_anchor("nocardicin A", lib)["compound"] == "nocardicin"
    assert C.resolve_anchor("C-1027", lib)["compound"] == "C-1027"


def test_resolve_anchor_unknown_returns_none():
    assert C.resolve_anchor("totally-novel-cluster-xyz", _lib()) is None


# ---- concordance verdicts -----------------------------------------------------------------------
def test_concordant_when_expected_marker_present():
    # C-1027 seed-expects T43-ENE; engine found it -> CONCORDANT
    r = C.concordance_check("BGC001", "C-1027", ["T43-ENE_enediyne", "T43-HAL_halogenase"], 73.1, _lib())
    assert r.matched_compound == "C-1027"
    assert r.verdict == "CONCORDANT"
    assert "T43-ENE" in r.markers_present
    assert r.markers_present_of_expected == 1.0


def test_hsaf_concordant():
    r = C.concordance_check("BGC001", "heat-stable antifungal factor", ["T43-PTM_hsaf_tetramate"], 20.3, _lib())
    assert r.matched_compound == "HSAF"
    assert r.verdict == "CONCORDANT"


def test_discordant_when_anchor_matches_but_no_expected_marker():
    # synthetic library entry with an expected marker the BGC does NOT have -> misanchor warning
    lib = {"entries": [{"compound": "fakeomycin", "aliases": ["fakeomycin"], "class": "x", "genus": "X",
                        "expected_marker_set": ["T43-ENE"], "expected_size_kb": 50.0}]}
    r = C.concordance_check("BGC009", "fakeomycin", ["T43-HAL"], 48.0, lib)
    assert r.verdict == "DISCORDANT"
    assert r.markers_present_of_expected == 0.0
    assert "similarity only" in r.notes


def test_pending_lit_when_no_reference_truth():
    # pacidamycin has no seed markers and no expected size -> pending
    r = C.concordance_check("BGC001", "pacidamycin", [], 32.2, _lib())
    assert r.matched_compound == "pacidamycin"
    assert r.verdict == "EXPECTED_PENDING_LIT"


def test_no_reference_for_unknown_anchor():
    r = C.concordance_check("BGC001", "totally-novel-cluster-xyz", ["T43-LAN"], 40.0, _lib())
    assert r.verdict == "NO_REFERENCE"
    assert r.matched_compound is None


def test_size_mismatch_flagged():
    lib = {"entries": [{"compound": "bigref", "aliases": ["bigref"], "class": "x", "genus": "X",
                        "expected_marker_set": ["T43-ENE"], "expected_size_kb": 100.0}]}
    # found 3.9kb vs expected 100kb -> fragment note even though marker present
    r = C.concordance_check("BGC001", "bigref", ["T43-ENE"], 3.9, lib)
    assert r.size_ratio is not None and r.size_ratio < 0.3
    assert "fragment" in r.notes
    # marker present but size far off -> not CONCORDANT (size gate fails)
    assert r.verdict == "PARTIAL"


def test_as_evidence_is_claim_safe_string():
    r = C.concordance_check("BGC001", "C-1027", ["T43-ENE"], 73.1, _lib())
    s = r.as_evidence()
    assert "CONCORDANT" in s and "C-1027" in s
    assert "produces" not in s.lower()  # claim-safe: no production language


# ---- C1 v9.7.58: pipeline wiring tests ----------------------------------------

def test_concordance_per_bgc_field_on_scanbundle():
    """SourceScanBundle has the concordance_per_bgc field (C1 wiring contract)."""
    from mamey.models import SourceScanBundle
    import dataclasses
    fields = {f.name for f in dataclasses.fields(SourceScanBundle)}
    assert "concordance_per_bgc" in fields, "concordance_per_bgc field missing from SourceScanBundle"


def test_concordance_verdict_field_on_triagerecord():
    """TriageRecord carries concordance_verdict field (C1 → serialize.py contract)."""
    from mamey.models import TriageRecord
    import dataclasses
    fields = {f.name for f in dataclasses.fields(TriageRecord)}
    assert "concordance_verdict" in fields, "concordance_verdict missing from TriageRecord"


# ---- v9.7.352 AMBER_CORRECTNESS FIX 1: end-to-end concordance wiring ----------
#
# Regression for two defects in the run_source_scans C1 concordance block
# (source_scans.py ~1742): (a) the `_found` marker set was built through an INVERTED
# `isinstance(..., dict)` ternary against cctt["per_bgc"] — a dict-of-LISTS from
# bgc_coupling — so `_found` was [] for 100% of BGCs, forcing every anchor-resolving
# cluster to DISCORDANT; and (b) the per-BGC result dict referenced attributes
# (matched_class/marker_frac/size_ok/details) that ConcordanceResult never carried, so
# it threw AttributeError and every BGC was stored as NO_REFERENCE. Together they
# silently corrupted concordance_verdict and killed the antimicrobial-recall boost for
# exactly the well-anchored antimicrobial clusters it exists to help.

def test_run_source_scans_concordance_uses_real_found_markers():
    """A BGC whose anchor's expected markers are actually present must come back
    non-DISCORDANT with frac>0 — proving _found reads the real coupling set."""
    from mamey.models import BGCRecord, CDSFeature
    from mamey.source_scans import run_source_scans
    bgc = BGCRecord(bgc_id="BGC001", contig="ctg1", region_number=1, start=0, end=73100,
                    contig_length=200000, products=["T1PKS", "enediyne"])
    bgc.closest_candidate_kcb_product = "C-1027"  # library entry expects T43-ENE
    cds = [
        CDSFeature("ctg1", 1000, 5000, 1, "ctg1_1", "enediyne polyketide synthase"),
        CDSFeature("ctg1", 6000, 8000, 1, "ctg1_2", "flavin-dependent halogenase"),
    ]
    ss = run_source_scans([bgc], cds, {"ctg1": "ACGT" * 60000})
    # the coupling really is a dict-of-lists (the shape the inverted ternary mishandled)
    assert ss.cctt["per_bgc"]["BGC001"] == ["T43-ENE_enediyne", "T43-HAL_halogenase"]
    conc = ss.concordance_per_bgc["BGC001"]
    assert conc["verdict"] != "DISCORDANT", conc
    assert conc["verdict"] == "CONCORDANT", conc
    assert conc["marker_frac"] and conc["marker_frac"] > 0
    assert conc["matched_compound"] == "C-1027"
    # the dict-build no longer collapses to the swallowed-error sentinel
    assert conc.get("details") != "per-bgc error"


def test_concordant_verdict_enables_antimicrobial_recall():
    """The corrected non-DISCORDANT verdict lets the antimicrobial-recall boost apply;
    a DISCORDANT verdict (the pre-fix behavior) suppresses it. This is the downstream
    consequence the HIGH-severity finding was about."""
    from mamey import antimicrobial_recall as A
    acc = next(iter(A._FAMBYACC))  # any accession resolving to a family with a profile
    applied = A.recall_scores(10.0, 10.0, closest_mibig_accession=acc,
                              closest_kcb_product="someantibiotic",
                              concordance_verdict="CONCORDANT")
    suppressed = A.recall_scores(10.0, 10.0, closest_mibig_accession=acc,
                                 closest_kcb_product="someantibiotic",
                                 concordance_verdict="DISCORDANT")
    assert applied["recall_applied"] is True, applied
    assert suppressed["recall_applied"] is False, suppressed


def test_verdicts_payload_includes_concordance_verdict():
    """verdicts_payload serialises concordance_verdict into the JSON (C1 → serialize.py)."""
    from mamey.serialize import verdicts_payload
    from mamey.models import TriageRecord
    t = TriageRecord("BGC001", 55.0, 30.0, 40.0, "Medium", "Moderate", "rationale")
    t.concordance_verdict = "CONCORDANT"
    payload = verdicts_payload("test_strain", [t])
    v = payload["verdicts"][0]
    assert "concordance_verdict" in v, "concordance_verdict missing from verdicts_payload output"
    assert v["concordance_verdict"] == "CONCORDANT"
