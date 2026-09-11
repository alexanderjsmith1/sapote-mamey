import re, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent

def test_build_stamp_single_source():
    bs = (ROOT / "BUILD_STAMP.txt").read_text(encoding="utf-8")
    ver = re.search(r"version=([0-9.a-z]+)", bs).group(1)
    assert re.search(r"build=\d{8}[a-z]", bs), "BUILD_STAMP build= must be <YYYYMMDD><letter>"
    pyver = re.search(r'bundle_version\s*=\s*"([0-9.a-z]+)"', (ROOT / "pyproject.toml").read_text()).group(1)
    assert ver == pyver, f"BUILD_STAMP {ver} != pyproject {pyver}"
    assert ver in (ROOT / "TAG").read_text(encoding="utf-8"), f"TAG missing version {ver}"

def test_release_manifest_build_stamp_consistent():
    """F002': every build-stamp restatement inside RELEASE_MANIFEST.md must equal the
    BUILD_STAMP.txt build= value. Catches the stale 'all four tiers share <old>' drift
    that test_build_stamp_single_source did not police (it never read the manifest body)."""
    bs = (ROOT / "BUILD_STAMP.txt").read_text(encoding="utf-8")
    stamp = re.search(r"build=(\d{8}v\d+[a-z])", bs).group(1)
    man = (ROOT / "RELEASE_MANIFEST.md").read_text(encoding="utf-8")
    stamps = set(re.findall(r"(\d{8}v\d+[a-z])", man))
    assert stamps, "RELEASE_MANIFEST.md has no build-stamp restatement"
    assert stamps == {stamp}, \
        f"RELEASE_MANIFEST.md build stamps {stamps} disagree with BUILD_STAMP {stamp}"

def test_release_manifest_sync_anchor_bundle_matches():
    """Defense-in-depth alongside gen_release_manifest.py: the sync_version anchor row's
    bundle must equal pyproject bundle_version. Catches a stale anchor even if the render
    tool is not re-run at cut time."""
    py = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    bundle = re.search(r'bundle_version\s*=\s*"([0-9.a-z]+)"', py).group(1)
    man = (ROOT / "RELEASE_MANIFEST.md").read_text(encoding="utf-8")
    anchors = re.findall(r"sync_version --check.*?bundle\s+([0-9.a-z]+)", man)
    assert anchors, "RELEASE_MANIFEST.md has no sync_version bundle anchor row"
    assert all(a == bundle for a in anchors), \
        f"RELEASE_MANIFEST.md sync anchor states bundle {set(anchors)}, expected {bundle}"
