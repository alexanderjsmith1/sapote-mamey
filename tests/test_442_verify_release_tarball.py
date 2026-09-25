"""A release tarball passes only when it carries exactly the sealed ZIP's files, byte for byte."""
import io
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "verify_release_tarball.py"
TOP = "sapote-mamey-vX-CODE-fixture"
FILES = {"AGENTS.md": b"contract\n", "tools/a.py": b"x = 1\n", "tests/test_a.py": b"def test(): pass\n"}


def _zip(tmp_path: Path) -> Path:
    p = tmp_path / f"{TOP}.zip"
    with zipfile.ZipFile(p, "w") as z:
        for name, data in FILES.items():
            z.writestr(name, data)
    return p


def _tar(tmp_path: Path, files: dict, extra_members: dict | None = None) -> Path:
    p = tmp_path / f"{TOP}.tar.gz"
    with tarfile.open(p, "w:gz") as t:
        for name, data in {**{f"{TOP}/{k}": v for k, v in files.items()}, **(extra_members or {})}.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    return p


def _run(tar: Path, zp: Path):
    return subprocess.run([sys.executable, str(TOOL), str(tar), "--zip", str(zp)],
                          capture_output=True, text=True, timeout=60)


def test_identical_tarball_passes(tmp_path):
    r = _run(_tar(tmp_path, FILES), _zip(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS" in r.stdout


def test_appledouble_members_are_refused(tmp_path):
    ad = b"\x00\x05\x16\x07" + b"\x00" * 30
    r = _run(_tar(tmp_path, FILES, {f"{TOP}/tools/._a.py": ad, f"._{TOP}": ad}), _zip(tmp_path))
    assert r.returncode == 2
    assert "2 junk member(s)" in r.stdout


def test_changed_missing_and_extra_files_are_each_refused(tmp_path):
    zp = _zip(tmp_path)
    files = dict(FILES)
    files["AGENTS.md"] = b"edited\n"
    del files["tests/test_a.py"]
    files["tools/b.py"] = b"y = 2\n"
    r = _run(_tar(tmp_path, files), zp)
    assert r.returncode == 2
    for reason in ("differ from the sealed ZIP", "missing from the tarball", "not in the sealed ZIP"):
        assert reason in r.stdout, r.stdout


def test_member_outside_the_bundle_folder_is_refused(tmp_path):
    r = _run(_tar(tmp_path, FILES, {"stray.txt": b"x"}), _zip(tmp_path))
    assert r.returncode == 2
    assert "outside" in r.stdout
