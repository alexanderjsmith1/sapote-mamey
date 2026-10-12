"""Small synthetic source for narrow, real public-cut integration checks.

This is not a fixture for certifying the complete evolving bundle. Gate tools
and their import dependencies are copied unchanged; payload and governance
authority belong solely to the disposable synthetic source. No privacy-profile
exclusions, allowlist extensions or mocked successful gates are used.
"""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import shutil
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
STAMP = "20261010v00000a"
TOOL_FILES = (
    "cut_preflight.sh", "redact_public_tier.py", "public_release_audit.py",
    "archive_leak_scan.py", "_safe_walk.py", "_wbio.py", "_console.py",
    "tracked_file_policy.py", "check_release_manifest.py",
    "verify_tier_derivation.py", "test_synthetic_ids.txt",
    "scanner_hmm_release_policy.py",
)
PACKAGE_FILES = (
    "__init__.py", "privacy_profile.py", "registry_schema.py",
    "mamey_cassettes.py", "sapote_cassettes.py",
)
HMM_RELATIVE = Path("Wheelhouse/hmm/scanner_pfam.hmm")
HMM_PAYLOAD = b"synthetic user-provisioned payload; not a biological model\n"
SCANNER_FIXTURE_ASSETS = {
    Path(directory) / (base + suffix): HMM_PAYLOAD + suffix.encode()
    for directory, base in (
        ("Wheelhouse/hmm", "scanner_pfam.hmm"),
        ("sapote_addons/hmm", "scanner_pfam_150.hmm"),
    )
    for suffix in ("", ".h3f", ".h3i", ".h3m", ".h3p")
}
GENERIC_HMM_ASSETS = {
    Path("Wheelhouse/hmm/generic_fixture.hmm"): b"generic nonbiological HMM fixture\n",
    Path("Wheelhouse/hmm/generic_fixture.hmm.h3i"): b"generic index fixture\n",
}


def public_cut_source(tmp_path: Path, *, with_hmm: bool = False) -> Path:
    """Satisfy the builder's identity, audit/import and manifest contracts.

    The full bundle's optional sync_version.py restatement catalogue is outside
    this small fixture. The always-on engine literal check still runs. An empty
    checksum seed makes the real builder regenerate and verify final checksums.
    The real builder/finalizer are invoked from ROOT, not replaced in the source.
    """
    source = tmp_path / "source"
    for directory in ("tools", "mamey", "docs", "tests", "fixtures"):
        (source / directory).mkdir(parents=True, exist_ok=True)
    for name in TOOL_FILES:
        shutil.copy2(ROOT / "tools" / name, source / "tools" / name)
    for name in PACKAGE_FILES:
        shutil.copy2(ROOT / "mamey" / name, source / "mamey" / name)
    (source / "BUILD_STAMP.txt").write_text(
        f"version=0.0.0\nbuild={STAMP}\ntier=CODE\n", encoding="utf-8",
    )
    (source / "CITATION.cff").write_text("version: 0.0.0\n", encoding="utf-8")
    (source / "SOURCE_CHECKSUMS_SHA256.txt").write_text("", encoding="utf-8")
    (source / "docs/INSTALL.md").write_text(
        "Synthetic installation document for builder membership checks.\n", encoding="utf-8",
    )
    (source / "tests/test_synthetic_payload.py").write_text(
        "def test_synthetic_payload():\n    assert 2 + 2 == 4\n", encoding="utf-8",
    )
    # This ledger authorizes only these invented fixture bytes, never ROOT or a
    # real disclosure decision. The real governance checker must accept it.
    (source / "GOVERNANCE_DECISIONS.json").write_text(json.dumps({"decisions": [{
        "id": "GOV-001", "status": "ACTIVE", "condition_currently_true": False,
        "asserted_signer": "Synthetic fixture owner", "asserted_date": "2026-10-10",
        "scope": "Disposable synthetic builder test source only",
    }]}), encoding="utf-8")
    # Historical filename membership contract only: no research archive is
    # copied and this tiny ZIP makes no antiSMASH or scientific-validity claim.
    with zipfile.ZipFile(source / "fixtures/micromonospora_humida_JAFEUC01.zip", "w") as archive:
        archive.writestr("README.txt", "Synthetic archive membership fixture only.\n")
    if with_hmm:
        for relative, payload in {**SCANNER_FIXTURE_ASSETS, **GENERIC_HMM_ASSETS}.items():
            target = source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
    return source


def assert_scanner_archive_policy(archive: Path, source: Path, *, stripped: bool = True):
    """Check actual archive bytes, both integrity inventories and immutable inputs."""
    expected = {**SCANNER_FIXTURE_ASSETS, **GENERIC_HMM_ASSETS}
    for relative, payload in expected.items():
        assert (source / relative).read_bytes() == payload, f"source changed: {relative}"
    with zipfile.ZipFile(archive) as zipped:
        members = set(zipped.namelist())
        manifest = {line.removeprefix("./") for line in
                    zipped.read("TIER_MANIFEST.txt").decode().splitlines()
                    if not line.startswith("#")}
        checksums = {}
        for line in zipped.read("SOURCE_CHECKSUMS_SHA256.txt").decode().splitlines():
            digest, relative = line.split(None, 1)
            checksums[relative.removeprefix("./")] = digest
        for relative, payload in expected.items():
            name = relative.as_posix()
            if stripped and relative in SCANNER_FIXTURE_ASSETS:
                assert name not in members
                assert name not in manifest
                assert name not in checksums
            else:
                assert name in members
                assert name in manifest
                assert zipped.read(name) == payload
                assert checksums[name] == hashlib.sha256(payload).hexdigest()


def public_cut_env(*, python: str = sys.executable, skip_pytest: bool = True) -> dict[str, str]:
    """Pin test controls rather than inheriting an operator's cut policy."""
    env = dict(os.environ)
    for name in ("CONTIG_ROSTER", "CONTIG_LEAK_FAIL", "AS_GUARD_RETIRED", "AS_SCRUB"):
        env.pop(name, None)
    env.update({
        "BUILD_STAMP": STAMP, "PYTHON": python,
        "SAPOTE_ENABLE_DISABLED_TIERS": "1", "AS_SCRUB": "1", "AS_GUARD_RETIRED": "0",
        "SKIP_INTIER_PYTEST": "1" if skip_pytest else "0",
    })
    return env
