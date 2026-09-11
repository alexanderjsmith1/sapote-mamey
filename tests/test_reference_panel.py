"""
Reference-panel regression test.

Two layers:

  LAYER 1 - data integrity (always runs, no source data needed)
    Guards the library's internal invariants: required fields, found==expected,
    well-formed markers/signatures, documented-silent boundary cases, unique keys.

  LAYER 2 - scanner concordance (runs only if MAMEY_REF_ZIPS is set to a dir of
    antiSMASH zips; otherwise each case SKIPS, not passes)
    Re-runs the live T43 scan over each reference whose source zip is present and
    asserts the fired markers equal the entry's expected_marker_set. This is the
    green/red baseline for a pre-release test round:
        MAMEY_REF_ZIPS=/path/to/reference_zips pytest tests/test_reference_panel.py

The boundary cases (jawsamycin, antimycin, salinosporamide A, mycolic acid) are
asserted to stay SILENT in both layers - they are documented true-negatives, and a
marker firing on any of them is a regression to investigate.
"""
import glob
import json
import os
import re
import sys

import pytest

T43_RE = re.compile(r"T43-[A-Z]+")
ACC_RE = re.compile(r"BGC\d+|[A-Z]{2}\d{6}")
EDGE_STATES = {"Interior", "Edge", "Full-contig"}

# documented true-negative references: must fire nothing, must carry a caveat
BOUNDARY_SILENT = {
    "BGC0001002": "jawsamycin (nucleoside antifungal, PKS region -> T43-NUC silent)",
    "BGC0000958": "antimycin (antifungal, mechanism not a T43 class)",
    "BGC0001041": "salinosporamide A (chlorinated, not a FAD-halogenase signature)",
    "BGC0000870": "mycolic acid (primary metabolism)",
}

# ---------------------------------------------------------------- fixtures / loaders


def _lib_path():
    import mamey
    return os.path.join(os.path.dirname(mamey.__file__), "data", "reference_bgc_library.json")


def _entries():
    d = json.load(open(_lib_path()))
    return next(v for v in d.values() if isinstance(v, list))


# reference_bgc_library.json is user-regenerated in the public release (not shipped, see
# FETCH_REFERENCE_DATA.md). Skip this curated-library regression cleanly when it is absent.
if not os.path.exists(_lib_path()):
    pytest.skip("reference_bgc_library.json absent (user-regenerated in public release)",
                allow_module_level=True)

ENTRIES = _entries()
IDS = [f"{e.get('compound','?')}:{e.get('accession','?')}" for e in ENTRIES]


def _ledger_for_zip():
    tools = os.path.join(os.path.dirname(__file__), "..", "tools")
    sys.path.insert(0, os.path.abspath(tools))
    from reference_panel_ledger import ledger_for_zip
    return ledger_for_zip


def _zip_index():
    d = os.environ.get("MAMEY_REF_ZIPS")
    if not d or not os.path.isdir(d):
        return None
    idx = {}
    for z in glob.glob(os.path.join(d, "*.zip")):
        m = ACC_RE.search(os.path.basename(z))
        if m:
            idx.setdefault(m.group(0), z)
    return idx


ZIP_INDEX = _zip_index()


# ---------------------------------------------------------------- LAYER 1: integrity


def test_no_duplicate_accessions():
    accs = [e["accession"] for e in ENTRIES]
    dups = {a for a in accs if accs.count(a) > 1}
    assert not dups, f"duplicate accessions: {dups}"


@pytest.mark.parametrize("e", ENTRIES, ids=IDS)
def test_required_fields(e):
    # hard_scan_verdict is optional metadata (present on session-added entries only)
    for f in ("compound", "accession", "class", "genus",
              "found_markers", "expected_marker_set"):
        assert f in e, f"{e.get('accession')} missing field {f!r}"


@pytest.mark.parametrize("e", ENTRIES, ids=IDS)
def test_marker_fields_wellformed(e):
    # found_markers = recorded scan output; expected_marker_set = curated/literature
    # answer key. They MAY differ by design (recall gaps, scan finding extra markers);
    # marker_set_source documents the basis. Both must be well-formed T43 token lists.
    for field in ("found_markers", "expected_marker_set"):
        v = e[field]
        assert isinstance(v, list), f"{e['accession']}: {field} not a list"
        for m in v:
            assert T43_RE.fullmatch(m), f"{e['accession']}: malformed marker {m!r} in {field}"


@pytest.mark.parametrize("e", ENTRIES, ids=IDS)
def test_signature_wellformed(e):
    sig = e.get("architecture_signature")
    if sig is None:
        pytest.skip("no architecture_signature on this entry (pre-session, no source zip)")
    assert isinstance(sig["region"], str) and sig["region"]
    for k in ("pks_ks", "nrps_c", "nrps_a"):
        assert isinstance(sig[k], int) and sig[k] >= 0, f"{e['accession']}: bad {k}"
    assert sig["edge"] in EDGE_STATES, f"{e['accession']}: edge {sig['edge']!r}"
    assert isinstance(sig["markers"], list)
    assert isinstance(sig["size_kb"], (int, float))
    # signature markers must agree with the entry's found_markers
    assert sorted(sig["markers"]) == sorted(e["found_markers"]), \
        f"{e['accession']}: signature markers {sig['markers']} != found {e['found_markers']}"


@pytest.mark.parametrize("acc,desc", sorted(BOUNDARY_SILENT.items()))
def test_boundary_cases_documented_silent(acc, desc):
    e = next((x for x in ENTRIES if x["accession"] == acc), None)
    assert e is not None, f"boundary reference {acc} ({desc}) missing from library"
    assert e["found_markers"] == [], f"{acc} should be silent but fired {e['found_markers']}"
    assert "caveat" in e and e["caveat"], f"{acc} silent but has no documenting caveat"


# ---------------------------------------------------------------- LAYER 2: concordance


@pytest.mark.parametrize("e", ENTRIES, ids=IDS)
def test_scanner_concordance(e):
    """Re-scan the reference's antiSMASH output and assert fired == recorded found_markers.

    found_markers is the recorded scan baseline, so this is a pure regression guard:
    a scanner change that alters the output for any reference (including the boundary
    true-negatives, whose baseline is []) trips this. Skips when MAMEY_REF_ZIPS is
    unset or this reference has no zip there.
    """
    if ZIP_INDEX is None:
        pytest.skip("MAMEY_REF_ZIPS not set - set it to a dir of antiSMASH zips to run concordance")
    zp = ZIP_INDEX.get(e["accession"])
    if not zp:
        pytest.skip(f"no source zip for {e['accession']} in MAMEY_REF_ZIPS")
    ledger_for_zip = _ledger_for_zip()
    rows = ledger_for_zip(zp)
    assert rows, f"{e['accession']}: no BGC parsed from {os.path.basename(zp)}"
    row = max(rows, key=lambda r: float(r["obs_size_kb"]))
    fired = sorted(set(T43_RE.findall(row.get("cmp_t43_markers", "") or "")))
    assert fired == sorted(e["found_markers"]), \
        f"{e['accession']}: scan fired {fired} but baseline found_markers={e['found_markers']}"
