"""F4/F5: manifest prose and tier admission share one exact archive identity."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_tier_parity as parity

SPEC = importlib.util.spec_from_file_location(
    "gen_release_manifest_v97406", ROOT / "tools" / "gen_release_manifest.py"
)
manifest = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(manifest)

STAMP = "20260903v97406a"


def archive(tier):
    return f"sapote-mamey-v9.7.406-{tier}-{STAMP}.zip"


def generated_tier_sentence(names=()):
    rule = next(
        replacement
        for label, _pattern, replacement in manifest.build_rules(
            "1.9.145", "9.7.406", STAMP, 1, 0, names
        )
        if label == "shared tier-count/build-stamp line"
    )
    return rule


def test_required_count_comes_from_parity_gate():
    assert generated_tier_sentence() == (
        f"All {manifest.tier_count_word(len(parity.REQUIRED_TIERS))} tiers "
        f"share build stamp `{STAMP}`."
    )


def test_public_promotion_adds_one_only_when_archive_is_present():
    assert generated_tier_sentence([archive("PUBLIC-RELEASE")]).startswith("All five tiers")
    assert generated_tier_sentence([archive("CODE")]).startswith("All four tiers")


@pytest.mark.parametrize(
    ("tier", "expected"),
    [
        ("CODE", "code"),
        ("CODE-analysis-free", "clean"),
        # v9.7.408: COHORT-public is what a new cut emits; SID-public is the retired label that
        # every bundle up to v9.7.407 carries, and must still bind to the same tier.
        ("COHORT-public", "cohort"),
        ("SID-public", "cohort"),
        ("MERGED-PRIVATE-scaffold", "merged"),
        ("PUBLIC-RELEASE", "public"),
    ],
)
def test_tier_of_accepts_only_complete_governed_names(tier, expected):
    assert parity.tier_of(archive(tier)) == expected


@pytest.mark.parametrize(
    "name",
    [
        "sapote-mamey-v9.7.406-CODE.zip",
        "notes-CODE-20260903v97406a.zip",
        "sapote-mamey-v9.7.406-CODE-20260903v97406a.zip.backup",
    ],
)
def test_tier_of_rejects_partial_or_decorated_names(name):
    with pytest.raises(parity.TierArchiveNameError) as exc:
        parity.tier_of(name)
    assert exc.value.code == "UNRECOGNIZED_TIER_ARCHIVE_NAME"


def test_ambiguous_name_has_typed_code():
    name = "sapote-mamey-v9.7.406-CODE-SID-public-20260903v97406a.zip"
    with pytest.raises(parity.TierArchiveNameError) as exc:
        parity.tier_of(name)
    assert exc.value.code == "AMBIGUOUS_TIER_ARCHIVE_NAME"


def test_inspection_preserves_ambiguous_name_as_typed_finding(tmp_path):
    path = tmp_path / "sapote-mamey-v9.7.406-CODE-SID-public-20260903v97406a.zip"
    with zipfile.ZipFile(path, "w") as archive_file:
        archive_file.writestr("bundle/mamey/__init__.py", "")
    info = parity.inspect(path)
    assert info["tier"] == "?"
    assert info["tier_name_finding"] == {
        "code": "AMBIGUOUS_TIER_ARCHIVE_NAME",
        "archive": path.name,
        "message": f"AMBIGUOUS_TIER_ARCHIVE_NAME: archive={path.name!r}",
    }
