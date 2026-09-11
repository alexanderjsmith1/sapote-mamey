"""test_build_stamp_consistency.py — v9.7.62

Guards against BUILD_STAMP letter drift: BUILD_STAMP.txt, mamey/__init__.py, and
RELEASE_MANIFEST.md must all agree on engine version and build stamp. The prior
failure mode (v9.7.57): BUILD_STAMP.txt said 20260617b; the clean cut used 20260617c.
The build-stamp format test passed (format was valid) but no test caught the cross-file
drift. This test closes that gap.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read_build_stamp() -> dict:
    """Parse BUILD_STAMP.txt -> {version, build, engine}."""
    txt = (ROOT / "BUILD_STAMP.txt").read_text(encoding="utf-8")
    result = {}
    for line in txt.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


def test_build_stamp_engine_matches_init():
    """BUILD_STAMP.txt engine must match mamey/__init__.py __version__."""
    stamp = _read_build_stamp()
    init_txt = (ROOT / "mamey" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', init_txt)
    assert m, "mamey/__init__.py: __version__ not found"
    assert stamp.get("engine") == m.group(1), (
        f"ENGINE mismatch: BUILD_STAMP.txt engine={stamp.get('engine')!r} "
        f"but mamey/__init__.py __version__={m.group(1)!r}"
    )


def test_build_stamp_engine_matches_pyproject():
    """BUILD_STAMP.txt engine must match pyproject.toml [project] version."""
    stamp = _read_build_stamp()
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"', pyproject)
    assert m, "pyproject.toml: [project] version not found"
    assert stamp.get("engine") == m.group(1), (
        f"ENGINE mismatch: BUILD_STAMP.txt engine={stamp.get('engine')!r} "
        f"but pyproject.toml version={m.group(1)!r}"
    )


def test_build_stamp_bundle_matches_pyproject():
    """BUILD_STAMP.txt bundle version must match pyproject.toml bundle_version."""
    stamp = _read_build_stamp()
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'(?m)^\s*bundle_version\s*=\s*"([^"]+)"', pyproject)
    assert m, "pyproject.toml: bundle_version not found"
    assert stamp.get("version") == m.group(1), (
        f"BUNDLE mismatch: BUILD_STAMP.txt version={stamp.get('version')!r} "
        f"but pyproject.toml bundle_version={m.group(1)!r}"
    )


def test_release_manifest_engine_matches_build_stamp():
    """RELEASE_MANIFEST.md **Engine:** line must match BUILD_STAMP.txt engine.
    This is the specific cross-file check that would have caught the v9.7.57 drift.
    """
    stamp = _read_build_stamp()
    manifest = (ROOT / "RELEASE_MANIFEST.md").read_text(encoding="utf-8")
    m = re.search(r"\*\*Engine:\*\* Mamey v([\d.]+)", manifest)
    if not m:
        return  # manifest may not have this line in all tiers — skip rather than fail
    assert stamp.get("engine") == m.group(1), (
        f"ENGINE mismatch: BUILD_STAMP.txt engine={stamp.get('engine')!r} "
        f"but RELEASE_MANIFEST.md Engine={m.group(1)!r}\n"
        f"Run: python3 tools/sync_version.py"
    )


def test_release_manifest_build_stamp_matches_build_stamp_txt():
    """RELEASE_MANIFEST.md **Build stamp:** must match BUILD_STAMP.txt build field."""
    stamp = _read_build_stamp()
    manifest = (ROOT / "RELEASE_MANIFEST.md").read_text(encoding="utf-8")
    m = re.search(r"\*\*Build stamp:\*\* (\w+)", manifest)
    if not m:
        return  # may not be present in all configurations
    assert stamp.get("build") == m.group(1), (
        f"STAMP mismatch: BUILD_STAMP.txt build={stamp.get('build')!r} "
        f"but RELEASE_MANIFEST.md Build stamp={m.group(1)!r}\n"
        f"Run: python3 tools/sync_version.py"
    )


def test_build_stamp_format():
    """BUILD_STAMP.txt must contain version, build, engine keys and non-empty values."""
    stamp = _read_build_stamp()
    for key in ("version", "build", "engine"):
        assert key in stamp and stamp[key], (
            f"BUILD_STAMP.txt missing or empty key: {key!r}"
        )
    # Build stamp should look like the legacy 8 digits + a letter (e.g.
    # 20260617i) OR the signed-candidate suffix form used after v9.7.140d
    # (e.g. 20260627v97140d). The stricter old regex falsely failed signed
    # research candidates whose identity was otherwise internally consistent.
    import re as _re
    assert _re.match(r"^\d{8}(?:[a-z]|v\d{3,}[a-z])$", stamp["build"]), (
        f"BUILD_STAMP.txt build={stamp['build']!r} — expected YYYYMMDD[a-z] "
        "or YYYYMMDDv<digits><letter>"
    )


def _changelog_head_build() -> str:
    """Pull the build token from the CHANGELOG top entry's `# vX · … · build <token> · …` line."""
    first = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").splitlines()[0]
    m = re.search(r"\bbuild\s+(\S+)", first)
    return m.group(1) if m else ""


def test_changelog_head_build_matches_stamp():
    """v9.7.373: the CHANGELOG top-entry build token must equal BUILD_STAMP.build.

    Closes the .372 E-01 drift class (head said ...v97372a, stamp was ...v97372b). At seal,
    tools/rewrite_release_identity.py rewrites the head token to the actual $STAMP; this test is the
    always-on ratchet so a hand-edited head that drifts from BUILD_STAMP fails the suite, not just a cut.
    """
    stamp = _read_build_stamp()
    head = _changelog_head_build()
    assert head, "CHANGELOG.md top entry has no `build <token>` on its header line"
    assert head == stamp.get("build"), (
        f"CHANGELOG head build={head!r} but BUILD_STAMP.txt build={stamp.get('build')!r}\n"
        f"Run: python3 tools/rewrite_release_identity.py <bundle> <stamp> --root ."
    )


def test_rewrite_release_identity_only_touches_the_top_changelog_entry(tmp_path):
    """The head-token rewrite must be anchored to the top entry: historical `build …` tokens on
    older `# vX` entries must never be clobbered (a whole-file `s/build \\S+/` would corrupt history)."""
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    from rewrite_release_identity import desired_files  # noqa: E402

    # a minimal tree with two changelog entries carrying different build tokens
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nversion = "1.0.0"\n[tool.sapote]\nbundle_version = "9.9.9"\n', encoding="utf-8")
    (tmp_path / "BUILD_STAMP.txt").write_text(
        "version=9.9.9\nbuild=20260101v9999a\nengine=1.0.0\n", encoding="utf-8")
    (tmp_path / "TIER_MANIFEST.txt").write_text(
        "# TIER_MANIFEST tier=code version=9.9.9 stamp=20260101v9999a\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(
        "# v9.9.9 · 2026-01-01 · build 20251231v9999z · engine 1.0.0 (head)\n\n"
        "- **x.**\n\n"
        "# v9.9.8 · 2025-12-01 · build 20251201v9998a · engine 0.9.0 (old)\n", encoding="utf-8")

    desired = desired_files(tmp_path, "9.9.9", "20260101v9999a")
    new_changelog = desired[tmp_path / "CHANGELOG.md"]
    assert "build 20260101v9999a" in new_changelog          # top token rewritten to the stamp
    assert "build 20251201v9998a" in new_changelog          # historical token untouched
    assert "20251231v9999z" not in new_changelog            # provisional top token replaced
