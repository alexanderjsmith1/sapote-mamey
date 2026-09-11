"""Regression: gold figures must not be silently skipped when manifest_short.json
is absent.

Real bug (v9.7.155): `mamey run --mode gold` auto-emits single-strain gold figures
via cohort_figures.generate() at a point in cli.py (~line 1293) that runs BEFORE
manifest_short.json is written (~line 1529). cohort_figures.load() did an unguarded
`json.load(open(f"{pkg}/manifest_short.json"))`, which raised FileNotFoundError; the
caller swallowed it into a blanket "Gold figures: SKIPPED" note. Net effect: the entire
gold figure suite could NEVER render through the auto-emit path, because the file it
required did not exist yet — and the data it needed (raw_bgcs, assembly_tier, taxonomy)
was already sitting in the full manifest.json, written earlier.

Fix: cohort_figures._load_manifest_short() falls back to manifest.json (and to safe
defaults) instead of raising.
"""
import json
import os
import tempfile

from mamey.cohort_figures import _load_manifest_short, load


def _make_pkg(runs, sid, with_manifest_short=False, with_manifest=True):
    pkg = os.path.join(runs, sid, "package")
    os.makedirs(pkg)
    json.dump({"bgcs": []}, open(f"{pkg}/deep_data.json", "w"))
    json.dump({"strain_id": sid}, open(f"{pkg}/gene_data.json", "w"))
    json.dump({sid: {}}, open(f"{pkg}/{sid}_1_intake.json", "w"))
    if with_manifest:
        json.dump({"taxonomy": "Streptomyces sp.", "assembly_tier": "GOOD",
                   "raw_bgcs": 42, "corrected_bgcs": 41.5, "bgcs": [{}] * 42},
                  open(f"{pkg}/manifest.json", "w"))
    if with_manifest_short:
        json.dump({"taxonomy": "Micromonospora sp.", "assembly_tier": "MODERATE",
                   "raw_bgcs": 7, "corrected_bgcs": 6.5},
                  open(f"{pkg}/manifest_short.json", "w"))
    return pkg


def test_manifest_short_present_is_used_verbatim():
    with tempfile.TemporaryDirectory() as d:
        pkg = _make_pkg(d, "AS-901", with_manifest_short=True)
        ms = _load_manifest_short(pkg, "AS-901")
        assert ms["raw_bgcs"] == 7
        assert ms["assembly_tier"] == "MODERATE"
        assert ms["taxonomy"] == "Micromonospora sp."


def test_missing_manifest_short_falls_back_to_manifest():
    """The exact failing condition: deep_data + manifest present, manifest_short absent."""
    with tempfile.TemporaryDirectory() as d:
        pkg = _make_pkg(d, "AS-901", with_manifest_short=False)
        ms = _load_manifest_short(pkg, "AS-901")
        assert ms["raw_bgcs"] == 42          # reconstructed from manifest.json
        assert ms["assembly_tier"] == "GOOD"
        assert ms["taxonomy"] == "Streptomyces sp."


def test_load_does_not_raise_without_manifest_short():
    """The whole point: load() must succeed (not FileNotFoundError) so the caller
    doesn't swallow the entire suite into a SKIPPED note."""
    with tempfile.TemporaryDirectory() as d:
        runs = os.path.join(d, "runs")
        _make_pkg(runs, "AS-901", with_manifest_short=False)
        S = load(runs, only=["AS-901"])
        assert "AS-901" in S
        assert int(S["AS-901"]["ms"]["raw_bgcs"]) == 42


def test_no_manifest_at_all_refuses_instead_of_inventing_defaults():
    """Missing authority is typed missingness, not a scientific zero/UNKNOWN row."""
    with tempfile.TemporaryDirectory() as d:
        pkg = _make_pkg(d, "AS-901", with_manifest_short=False, with_manifest=False)
        import pytest
        with pytest.raises(FileNotFoundError, match="MANIFEST_METADATA_UNAVAILABLE"):
            _load_manifest_short(pkg, "AS-901")


def test_corrupt_manifest_short_falls_back():
    """A partial/corrupt manifest_short write (interrupted mid-flush) must not crash —
    fall through to manifest.json."""
    with tempfile.TemporaryDirectory() as d:
        pkg = _make_pkg(d, "AS-901", with_manifest_short=False)
        open(f"{pkg}/manifest_short.json", "w").write("{ this is not valid json")
        import pytest
        with pytest.warns(RuntimeWarning, match="MANIFEST_SHORT_UNREADABLE_FALLBACK"):
            ms = _load_manifest_short(pkg, "AS-901")
        assert ms["raw_bgcs"] == 42  # recovered from manifest.json
