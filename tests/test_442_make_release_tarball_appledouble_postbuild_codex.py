"""The producer must inspect archive members, including ones hidden by tar -t."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/make_release_tarball.sh"


def test_postbuild_check_refuses_hidden_appledouble_member(tmp_path):
    source = tmp_path / "bundle"
    source.mkdir()
    (source / "BUILD_STAMP.txt").write_text("fixture\n")
    (source / "SOURCE_CHECKSUMS_SHA256.txt").write_text("fixture\n")
    (source / "payload.txt").write_text("payload\n")
    output = tmp_path / "dist"
    shimdir = tmp_path / "shim"
    shimdir.mkdir()
    shim = shimdir / "tar"
    shim.write_text(f'''#!{sys.executable}
import io, os, subprocess, sys, tarfile
args = sys.argv[1:]
real = "/usr/bin/tar"
if "-czf" in args:
    result = subprocess.run([real, *args])
    if result.returncode:
        sys.exit(result.returncode)
    archive = args[args.index("-czf") + 1]
    temporary = archive + ".inject"
    with tarfile.open(archive, "r:gz") as original, tarfile.open(temporary, "w:gz") as rewritten:
        for member in original:
            rewritten.addfile(member, original.extractfile(member) if member.isfile() else None)
        added = tarfile.TarInfo(args[-1] + "/._injected")
        added.size = 1
        rewritten.addfile(added, io.BytesIO(b"x"))
    os.replace(temporary, archive)
    sys.exit(0)
if "-tzf" in args:
    result = subprocess.run([real, *args], capture_output=True, text=True)
    sys.stdout.write("".join(line for line in result.stdout.splitlines(keepends=True)
                             if not line.rsplit("/", 1)[-1].startswith("._")))
    sys.stderr.write(result.stderr)
    sys.exit(result.returncode)
sys.exit(subprocess.run([real, *args]).returncode)
''')
    shim.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = str(shimdir) + os.pathsep + env["PATH"]
    result = subprocess.run(["bash", str(TOOL), str(source), str(output)],
                            env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "AppleDouble" in result.stderr
    assert not (output / "bundle.tar.gz").exists()
    assert not (output / "bundle.tar.gz.sha256").exists()
