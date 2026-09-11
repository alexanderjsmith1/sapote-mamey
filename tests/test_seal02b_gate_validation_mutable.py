"""SEAL-02b (v9.7.338 follow-up) — a fresh seal must pass its own checksum gate.

SEAL-02 (v9.7.338) made `_phase_package_seal` REWRITE `gate_validation.json` with the final
post-seal re-validation result — which is correct, it is what lets a late gate regression fail the
seal. But `write_manifest()` had already hashed `gate_validation.json` (mid-build content) into
`checksums_sha256.txt`, and `gate_validation.json` was NOT in the writer's `MUTABLE_NAMES` set. So
every fresh .338 seal wrote a file whose content no longer matched its own recorded hash, and then
failed its own `checksum_integrity` gate with status FAIL — a package that fails to seal itself.

Root of the coupling: the "files rewritten after checksum capture" set was copy-pasted into FIVE
places (two in packaging.py, four in validate.py) and had already drifted — two validator copies
lacked `repro_fingerprint.json`. The fix defines the set once as
`packaging.MUTABLE_RECEIPT_NAMES` and points every site at it, so the writer's exclusions and the
validator's exemptions can never disagree again.

These tests assert the end-to-end invariant (a fresh gold seal validates clean) and the structural
one (single source of truth, and it contains the file SEAL-02 rewrites).
"""

import json

import pytest

from mamey import packaging
from mamey.validate import verify_checksums, validate_package


def test_mutable_receipt_names_is_the_single_source_of_truth():
    assert hasattr(packaging, "MUTABLE_RECEIPT_NAMES")
    # the file SEAL-02 rewrites post-manifest must be in the set, or a fresh seal fails itself
    assert "gate_validation.json" in packaging.MUTABLE_RECEIPT_NAMES
    # and the historically-drifted member must be present too
    assert "repro_fingerprint.json" in packaging.MUTABLE_RECEIPT_NAMES


def test_writer_and_validator_reference_the_same_set():
    """The validator's is_checksum_excluded (validate.py) must exempt every receipt the writer
    excludes from the manifest, or an excluded file reads as untracked-present on validation."""
    from mamey.validate import _checksum_reciprocal_exempt as _validator_excluded
    for name in packaging.MUTABLE_RECEIPT_NAMES:
        assert _validator_excluded(name), (
            f"{name} is excluded from the checksum manifest by the writer but the validator's "
            f"is_checksum_excluded does not exempt it — the two have drifted again"
        )


def _seal_a_gold_package(tmp_path):
    """Run a real gold seal on the bundled micromonospora fixture; return the package dir."""
    from pathlib import Path
    from mamey.cli import run_one_strain

    fixture = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / \
        "micromonospora_humida_JAFEUC01.zip"
    if not fixture.exists():
        pytest.skip("micromonospora fixture not present in this tier")

    outdir = tmp_path / "out"
    run_one_strain(
        strain_id="SEALTEST", display_name="Micromonospora humida", input_zip=str(fixture),
        outdir=str(outdir), mode="gold", taxonomy="Micromonospora humida",
        source="reference genome", bioactivity="", master_path=None, release="PUBLIC",
        json_mode="off", brief="none",
    )
    return outdir / "SEALTEST" / "package"


def test_fresh_gold_seal_passes_its_own_checksum_gate(tmp_path):
    """KNOWN-BAD (pre-fix): a fresh .338 gold seal returned checksum_integrity FAIL on
    gate_validation.json — the file SEAL-02 rewrites after the manifest was hashed."""
    pkg = _seal_a_gold_package(tmp_path)

    errors = verify_checksums(pkg)
    assert errors == [], f"fresh seal failed its own checksum gate: {errors}"

    result = validate_package(pkg, enrichment_check=True)
    assert result["checksum_integrity"] == "PASS", result.get("checksum_errors")
    assert result["status"] in {"MAMEY_COMPLETE", "MAMEY_COMPLETE_WITH_ISSUES",
                                "PASS", "PASS_WITH_ISSUES"}, result


def test_rewriting_gate_validation_after_seal_does_not_break_the_checksum_gate(tmp_path):
    """The whole point of the mutable exemption: overwriting gate_validation.json post-seal
    (as SEAL-02 does) must not turn the package red."""
    pkg = _seal_a_gold_package(tmp_path)
    gv = pkg / "gate_validation.json"
    # simulate SEAL-02's rewrite one more time with different bytes
    data = json.loads(gv.read_text())
    data["_seal02b_probe"] = "rewritten after checksum capture"
    gv.write_text(json.dumps(data, indent=2), encoding="utf-8")

    errors = verify_checksums(pkg)
    assert errors == [], (
        f"rewriting the documented-mutable gate_validation.json must not fail the checksum "
        f"gate, but got: {errors}"
    )
