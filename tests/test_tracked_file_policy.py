"""NC-001/002/003: one shared tracked-file policy for the tier builder + manifest checker."""
import importlib.util
import re
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


def test_policy_keeps_source_excludes_artifacts_and_cruft():
    p = _pol()
    assert p.is_tracked("mamey/cli.py") and p.is_tracked("docs/guide.md")
    for rel in ["SHA256SUMS.txt", "SHA256SUMS_20260802.txt", "cut_v9_7_347_code_log.txt",
                "sapote-mamey-v9.7.347-CODE.zip", "TIER_MANIFEST.txt", "SOURCE_CHECKSUMS_SHA256.txt",
                "x/__pycache__/y.pyc", ".DS_Store", "a.bak", "b.orig", "c.rej"]:
        assert not p.is_tracked(rel), rel


def test_checker_and_builder_share_the_one_policy():
    # NC-001: neither re-implements the exclusion set; both consume tracked_file_policy
    assert "from tracked_file_policy import is_tracked" in \
        (_ROOT / "tools" / "check_release_manifest.py").read_text()
    sh = (_ROOT / "tools" / "make_public_tier.sh").read_text()
    assert "tracked_file_policy.py" in sh and "--emit-manifest" in sh


def test_shipped_tier_manifest_excludes_release_artifacts():
    tm = (_ROOT / "TIER_MANIFEST.txt").read_text()
    # v9.7.375 (patch chat): scope the ZIP check to ROOT-LEVEL zips only ([^/]*), matching the
    # shipped tracked_file_policy._ROOT_LEVEL_ZIP_RE + its `"/" not in rel` guard. The prior
    # `.*\.zip` alternative matched a zip at any depth, contradicting the same fold's policy fix
    # that deliberately governs nested source fixtures (e.g. examples/test_data/*.zip,
    # tests/fixtures/*.zip) — the release-cut's own single output ZIP is always root-level.
    assert not re.search(r"(?m)^\./(SHA256SUMS.*\.txt|cut_.*_log\.txt|[^/]*\.zip)$", tm)
