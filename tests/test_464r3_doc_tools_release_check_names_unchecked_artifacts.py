"""Synthetic tree only: a PASS names the root release artifacts it did not check."""
import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "check_release_manifest.py"


def _tree(root):
    (root / "real_file.txt").write_text("hello", encoding="utf-8")
    (root / "BUILD_STAMP.txt").write_text("version=0.0.0\nbuild=SYNTHETIC\ntier=code\n", encoding="utf-8")
    (root / "TIER_MANIFEST.txt").write_text(
        "# TIER_MANIFEST tier=code version=0.0.0 stamp=SYNTHETIC\n./BUILD_STAMP.txt\n./real_file.txt\n",
        encoding="utf-8")
    (root / "SOURCE_CHECKSUMS_SHA256.txt").write_text("".join(
        hashlib.sha256((root / n).read_bytes()).hexdigest() + "  ./" + n + "\n"
        for n in ("BUILD_STAMP.txt", "TIER_MANIFEST.txt", "real_file.txt")), encoding="utf-8")


def _run(root):
    return subprocess.run([sys.executable, str(GATE), "--root", str(root)],
                          capture_output=True, text=True, cwd=str(ROOT))


def test_pass_lists_root_zip_it_did_not_check(tmp_path):
    _tree(tmp_path)
    (tmp_path / "bundle-CODE.zip").write_bytes(b"first")
    first = _run(tmp_path)
    (tmp_path / "bundle-CODE.zip").write_bytes(b"changed")
    second = _run(tmp_path)
    for result in (first, second):
        assert result.returncode == 0, result.stdout
        assert "not checked here: 1 root release artifact(s)" in result.stdout
        assert "bundle-CODE.zip" in result.stdout


def test_no_artifacts_no_extra_line(tmp_path):
    _tree(tmp_path)
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout
    assert "not checked here" not in result.stdout
