"""BC2 .401 audit: tools/evidence_conservation_audit.py's own docstring states its design
principle is "LOCUS-level presence checks (not bare string matching, which false-positives on
product labels)". `check_tigrfam()` did not actually follow that principle -- it used a bare
`acc not in pkg_blob` boolean-presence check, not a locus-aware one.

Reproduced live against the real pristine function: the SAME diagnostic TIGRFAM accession
(e.g. TIGR01454) hit at two DISTINCT loci in the raw evidence (two separate BGCs both showing
this diagnostic), with the package retaining only ONE of the two hits. The boolean check finds
the accession string present (from the surviving hit) and reports "2/2 conserved" -- silently
missing that the other locus's diagnostic hit was entirely dropped from the package. This is
the identical false-conservation shape the v9.7.115 (NRPS substrates, `check_nrps_substrates`)
and v9.7.374 (RiPP cores, `check_ripp_cores`) fixes already closed for their own checks --
`check_tigrfam` was never fixed the same way, despite TIGRFAM diagnostics being the evidence
class behind this tool's own motivating incident (the buried AHBA signal).

Fixed via occurrence COUNTING (`_count_in_blob`) rather than boolean presence: if raw shows a
diagnostic accession N times (across N distinct loci) but the package blob contains it fewer
than N times, the shortfall is flagged -- catching an aggregate drop even without parsing the
package's own JSON structure (this auditor deliberately treats the package as an opaque blob).

No prior test exercised `check_tigrfam` at all (confirmed: existing tests
`test_substring_containment_fixes_v9_7_115.py` only cover `check_nrps_substrates` /
`_token_in_blob`) -- first coverage for this specific check.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import evidence_conservation_audit as E  # noqa: E402


def _raw_two_loci_same_accession(acc="TIGR01454"):
    return {
        "records": [{
            "modules": {
                "antismash.detection.tigrfam": {
                    "hits": [
                        {"identifier": acc, "domain": acc, "locus_tag": "gene_5_bgc1"},
                        {"identifier": acc, "domain": acc, "locus_tag": "gene_12_bgc2"},
                    ]
                }
            }
        }]
    }


def test_partial_drop_of_a_multi_locus_accession_now_caught():
    """The actual regression this fix closes: one of two loci sharing the same diagnostic
    accession is dropped from the package; the surviving locus's occurrence must not mask it."""
    raw = _raw_two_loci_same_accession()
    pkg_blob = json.dumps({"evidence": {"TIGRFAM_hits": [
        {"accession": "TIGR01454", "locus_tag": "gene_5_bgc1"},
        # gene_12_bgc2's hit is intentionally absent -- silently dropped
    ]}})
    name, seen, dropped = E.check_tigrfam(raw, pkg_blob)
    assert seen == 2
    assert dropped, "a partial multi-locus drop was silently reported as fully conserved"
    assert any("1 of 2" in d for d in dropped)


def test_both_loci_present_reports_clean():
    """No regression / no false positive: both loci's hits genuinely survive."""
    raw = _raw_two_loci_same_accession()
    pkg_blob = json.dumps({"evidence": {"TIGRFAM_hits": [
        {"accession": "TIGR01454", "locus_tag": "gene_5_bgc1"},
        {"accession": "TIGR01454", "locus_tag": "gene_12_bgc2"},
    ]}})
    name, seen, dropped = E.check_tigrfam(raw, pkg_blob)
    assert seen == 2
    assert not dropped


def test_single_locus_still_works_as_before():
    """No regression: the common, single-locus case (what the old boolean check already
    handled correctly) still works both ways."""
    raw = {"records": [{"modules": {"antismash.detection.tigrfam": {"hits": [
        {"identifier": "TIGR01454", "domain": "TIGR01454", "locus_tag": "gene_1"},
    ]}}}]}
    conserved_blob = json.dumps({"evidence": [{"accession": "TIGR01454"}]})
    name, seen, dropped = E.check_tigrfam(raw, conserved_blob)
    assert seen == 1 and not dropped

    dropped_blob = json.dumps({"evidence": []})
    name, seen, dropped = E.check_tigrfam(raw, dropped_blob)
    assert seen == 1 and dropped


def test_no_diagnostic_hits_reports_nothing_to_conserve():
    raw = {"records": [{"modules": {"antismash.detection.tigrfam": {"hits": [
        {"identifier": "TIGR99999", "domain": "TIGR99999", "locus_tag": "gene_1"},  # not diagnostic
    ]}}}]}
    name, seen, dropped = E.check_tigrfam(raw, json.dumps({}))
    assert seen == 0 and not dropped


def test_count_in_blob_is_word_bounded():
    """_count_in_blob must not count a diagnostic token as present when it only occurs as a
    substring of an unrelated, longer identifier -- the same word-boundary discipline
    `_token_in_blob` already established for the other checks."""
    blob = json.dumps({"note": "TIGR01454X is a different, unrelated accession"})
    assert E._count_in_blob("TIGR01454", blob) == 0


def test_end_to_end_audit_reports_fail_on_the_repro_case():
    """Full audit() integration, not just the unit-level check function."""
    import tempfile
    raw = _raw_two_loci_same_accession()
    pkg = {"evidence": {"TIGRFAM_hits": [{"accession": "TIGR01454", "locus_tag": "gene_5_bgc1"}]}}
    with tempfile.TemporaryDirectory() as d:
        raw_path = pathlib.Path(d) / "raw.json"
        pkg_path = pathlib.Path(d) / "pkg.json"
        raw_path.write_text(json.dumps(raw))
        pkg_path.write_text(json.dumps(pkg))
        rc = E.audit(str(raw_path), str(pkg_path))
    assert rc == 1, "expected the end-to-end audit to FAIL on a genuine multi-locus drop"
