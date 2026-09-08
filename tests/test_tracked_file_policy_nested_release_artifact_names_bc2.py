"""BC2-TFP-01 (v9.7.396): tracked_file_policy.py's is_tracked() must not exclude a NESTED file
just because its basename matches a release-artifact pattern meant for root-level cut output.

_RELEASE_ARTIFACT_RE (SHA256SUMS*.txt / cut_*_log.txt) matched on the basename alone, with no
path context — exactly the bug shape v9.7.374's _ROOT_LEVEL_ZIP_RE fix was built to close for the
tier ZIP, left unfixed in this sibling rule sitting right next to it. A real cut log or SHA256SUMS
manifest produced by the cut process always lands at the tier root, but a nested file with a
matching basename is a real, governed document — e.g. an archived historical cut log or checksum
reference under docs/archive/, matching this project's own documented archival convention (the
v9.7.395 CHANGELOG's own top entry: "archives... root documents to docs/archive/"). Excluding it
is the exact SEAL-01 two-sources-of-truth drift this module's own docstring says it exists to
prevent.

Reproduced live against the unpatched tools/tracked_file_policy.py before this fix.
"""
import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _pol():
    spec = importlib.util.spec_from_file_location(
        "tracked_file_policy", _ROOT / "tools" / "tracked_file_policy.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["tracked_file_policy"] = m
    spec.loader.exec_module(m)
    return m


def test_nested_archived_cut_log_is_tracked():
    p = _pol()
    assert p.is_tracked("docs/archive/cut_20260617_log.txt"), (
        "a nested, archived cut log is a real governed document and must be tracked"
    )


def test_nested_archived_sha256sums_reference_is_tracked():
    p = _pol()
    assert p.is_tracked("docs/archive/SHA256SUMS_20260617a.txt"), (
        "a nested, archived checksum reference is a real governed document and must be tracked"
    )


def test_root_level_release_artifacts_still_correctly_excluded():
    # Regression guard: the actual cut-produced release artifacts (always root-level) must
    # remain excluded — this fix is scoped by path depth, not by disabling the rule.
    p = _pol()
    for rel in ("SHA256SUMS.txt", "SHA256SUMS_20260802.txt", "cut_v9_7_347_code_log.txt"):
        assert not p.is_tracked(rel), rel


def test_ordinary_source_and_build_cruft_unaffected():
    # Regression guard: this file's other exclusion rules (build cruft, manifest self-files,
    # nested zips) and ordinary governed source are all untouched by this fix.
    p = _pol()
    assert p.is_tracked("mamey/cli.py")
    assert p.is_tracked("docs/guide.md")
    assert not p.is_tracked("x/__pycache__/y.pyc")
    assert not p.is_tracked(".DS_Store")
    assert not p.is_tracked("TIER_MANIFEST.txt")
    assert p.is_tracked("tests/fixtures/synthetic_single_contig_antismash.zip")
