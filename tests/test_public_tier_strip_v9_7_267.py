"""v9.7.267/.271 — harness for the PUBLIC-RELEASE tier content.

Runs the real `make_public_tier.sh public` on the source tree (with the tree's own build stamp so the
version/manifest gates pass) and asserts the produced zip is COMPLETE: since Pfam is CC0 and the
teicoplanin fixtures were retired for a small public fixture, nothing is withheld from the public tier
anymore (v9.7.271), so it ships the Pfam HMM and the Micromonospora humida fixture in place and leaves
no `.REMOVED.txt` download stubs — it is content-identical to the code tier. Skips if the
toolchain/stamp is absent (e.g. a partial checkout)."""
import os
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _build_stamp():
    f = ROOT / "BUILD_STAMP.txt"
    if not f.exists():
        return None
    m = re.search(r"build=(\S+)", f.read_text(encoding="utf-8"))
    return m.group(1) if m else None


@pytest.mark.skipif(not shutil.which("bash"), reason="bash unavailable")
def test_public_tier_does_not_ship_user_provisioned_hmm(tmp_path):
    stamp = _build_stamp()
    if not stamp or not (ROOT / "tools" / "make_public_tier.sh").exists():
        pytest.skip("build stamp or make_public_tier.sh unavailable")
    out = tmp_path / "pub"; out.mkdir()
    env = {**os.environ, "BUILD_STAMP": stamp, "SKIP_INTIER_PYTEST": "1", "PYTHON": sys.executable}  # v9.7.410: the cut script honours $PYTHON
    r = subprocess.run(
        ["bash", "tools/make_public_tier.sh", "public", str(ROOT), str(out)],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=420,
    )
    combined = r.stdout + r.stderr
    governance = json.loads((ROOT / "GOVERNANCE_DECISIONS.json").read_text(encoding="utf-8"))
    gov001 = next(item for item in governance["decisions"] if item.get("id") == "GOV-001")
    authorized = gov001.get("status") == "ACTIVE" and gov001.get("condition_currently_true") is False
    if not authorized:
        assert r.returncode == 8, combined[-3000:]
        assert "GOVERNANCE_DECISION_NOT_ACTIVE" in combined or "GOVERNANCE_DECISION_INVALIDATED" in combined
        assert not list(out.glob("*.zip")), "an unauthorized PUBLIC_RELEASE attempt must emit no ZIP"
        return
    assert r.returncode == 0, combined[-3000:]
    # the fail-closed strip check must have run and passed
    assert "content-identical to the code tier" in combined, combined[-2000:]

    zips = list(out.glob("*.zip"))
    assert len(zips) == 1, [p.name for p in zips]
    names = zipfile.ZipFile(zips[0]).namelist()

    # v9.7.274 (audit BLOCKER regression): BUILD_STAMP.txt and TIER_MANIFEST.txt must agree on the
    # tier. Before the fix the public bundle's BUILD_STAMP said tier=CODE while TIER_MANIFEST said
    # tier=public — a provenance contradiction.
    import io
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
    installs = [n for n in names if n.split("/")[-1] == "INSTALL.md"]
    mh_fixture = [n for n in names if n.endswith("micromonospora_humida_JAFEUC01.zip")]

    # nothing is withheld anymore: the HMM (CC0) ships, and there are no download stubs
    assert not hmm, ("v9.7.362: the Pfam HMM is USER-PROVISIONED, not redistributed — the tier must "
                     "not ship it (see docs/EXTERNAL_DATA.md)")
    assert not stubs, f"public tier must have no .REMOVED.txt stubs, found: {stubs}"
    assert installs, "public tier must ship INSTALL.md"
    assert mh_fixture, "public tier must ship the Micromonospora humida fixture"


def test_public_tier_content_matches_code_tier(tmp_path):
    # the public tier is now a labelled alias of the code tier — both ship the HMM. Guards against a
    # regression that re-introduces a strip (which would silently diverge the two).
    stamp = _build_stamp()
    if not stamp or not (ROOT / "tools" / "make_public_tier.sh").exists():
        pytest.skip("build stamp or make_public_tier.sh unavailable")
    out = tmp_path / "code"; out.mkdir()
    env = {**os.environ, "BUILD_STAMP": stamp, "SKIP_INTIER_PYTEST": "1", "PYTHON": sys.executable}  # v9.7.410: the cut script honours $PYTHON
    r = subprocess.run(
        ["bash", "tools/make_public_tier.sh", "code", str(ROOT), str(out)],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=420,
    )
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
    names = zipfile.ZipFile(next(out.glob("*.zip"))).namelist()
    assert not [n for n in names if n.endswith("scanner_pfam.hmm")], "v9.7.362: HMM is user-provisioned"
