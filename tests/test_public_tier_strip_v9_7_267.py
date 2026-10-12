"""Narrow synthetic public/code cut contracts, using the real gate chain.

These checks do not certify the full source tree or biological fixture content.
A synthetic user-provisioned legacy HMM is seeded deliberately, so the no-HMM
assertions detect a missing strip rule rather than passing on absent input.
The disabled public branch is enabled only for this disposable source fixture.
"""
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from tests._public_cut_fixture import (
    HMM_PAYLOAD, HMM_RELATIVE, assert_scanner_archive_policy,
    public_cut_env, public_cut_source,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not shutil.which("bash"), reason="bash unavailable")
def test_public_tier_does_not_ship_user_provisioned_hmm(tmp_path):
    source = public_cut_source(tmp_path, with_hmm=True)
    assert (source / HMM_RELATIVE).read_bytes() == HMM_PAYLOAD
    out = tmp_path / "pub"
    out.mkdir()
    env = public_cut_env()
    r = subprocess.run(
        ["bash", str(ROOT / "tools/make_public_tier.sh"), "public", str(source), str(out)],
        cwd=source, env=env, capture_output=True, text=True, timeout=420,
    )
    combined = r.stdout + r.stderr
    governance = json.loads((source / "GOVERNANCE_DECISIONS.json").read_text(encoding="utf-8"))
    gov001 = next(item for item in governance["decisions"] if item.get("id") == "GOV-001")
    authorized = gov001.get("status") == "ACTIVE" and gov001.get("condition_currently_true") is False
    assert authorized, "synthetic fixture must reach the real public content gates"
    assert r.returncode == 0, combined[-3000:]
    # Retain the builder branch witness; it does not establish that HMM stripping exists.
    assert "operator-provisioned scanner databases/indexes excluded" in combined, combined[-2000:]

    zips = list(out.glob("*.zip"))
    assert len(zips) == 1, [p.name for p in zips]
    names = zipfile.ZipFile(zips[0]).namelist()

    # v9.7.274 (audit BLOCKER regression): BUILD_STAMP.txt and TIER_MANIFEST.txt must agree on the
    # tier. Before the fix the public bundle's BUILD_STAMP said tier=CODE while TIER_MANIFEST said
    # tier=public — a provenance contradiction.
    with zipfile.ZipFile(zips[0]) as zf:
        def _read(suffix):
            n = next(x for x in zf.namelist() if x.endswith(suffix))
            return zf.read(n).decode("utf-8", "replace")
        bs = _read("BUILD_STAMP.txt")
        tm_head = _read("TIER_MANIFEST.txt").splitlines()[0]
    bs_tier = next((l.split("=",1)[1].strip() for l in bs.splitlines() if l.startswith("tier=")), None)
    tm_tier = next((tok.split("=",1)[1] for tok in tm_head.split() if tok.startswith("tier=")), None)
    assert bs_tier == "public", f"public bundle BUILD_STAMP tier should be 'public', got {bs_tier!r}"
    assert bs_tier == tm_tier, f"BUILD_STAMP tier ({bs_tier!r}) must match TIER_MANIFEST tier ({tm_tier!r})"

    hmm = [n for n in names if n.endswith("scanner_pfam.hmm")]
    stubs = [n for n in names if n.endswith(".REMOVED.txt")]
    installs = [n for n in names if n.endswith("/docs/INSTALL.md") or n == "docs/INSTALL.md"]
    mh_fixture = [n for n in names if n.endswith("micromonospora_humida_JAFEUC01.zip")]

    # A present user-provisioned payload must not be redistributed; no download stubs are expected.
    assert not hmm, ("v9.7.362: the Pfam HMM is USER-PROVISIONED, not redistributed — the tier must "
                     "not ship it (see docs/EXTERNAL_DATA.md)")
    assert (source / HMM_RELATIVE).read_bytes() == HMM_PAYLOAD
    assert not stubs, f"public tier must have no .REMOVED.txt stubs, found: {stubs}"
    assert installs, "public tier must ship docs/INSTALL.md"
    assert mh_fixture, "public tier must ship the Micromonospora humida fixture"
    assert_scanner_archive_policy(zips[0], source)


def test_public_tier_content_matches_code_tier(tmp_path):
    # Check the code branch independently; both branches must omit provisioned HMMs.
    # This historical node name does not claim byte parity between whole releases.
    source = public_cut_source(tmp_path, with_hmm=True)
    assert (source / HMM_RELATIVE).read_bytes() == HMM_PAYLOAD
    out = tmp_path / "code"
    out.mkdir()
    env = public_cut_env()
    r = subprocess.run(
        ["bash", str(ROOT / "tools/make_public_tier.sh"), "code", str(source), str(out)],
        cwd=source, env=env, capture_output=True, text=True, timeout=420,
    )
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    names = zipfile.ZipFile(next(out.glob("*.zip"))).namelist()
    assert not [n for n in names if n.endswith("scanner_pfam.hmm")], "v9.7.362: HMM is user-provisioned"
    assert_scanner_archive_policy(next(out.glob("*.zip")), source)

