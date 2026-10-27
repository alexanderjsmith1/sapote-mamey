"""The public-tier denylist loops skip blank and comment lines.

tools/release_denylist.example.txt tells the user to copy it to tools/release_denylist.txt.
Its "#" lines were read as terms: "#" alone scrubbed every "#" from staged code, deleted every
file with "#" in its name, and the leak audit then failed on every tier.
"""
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "make_public_tier.sh"
DENYLIST = "# release_denylist.example.txt - template\n#\n\n  realterm  \n"


def _block(start_marker, indent):
    lines = SCRIPT.read_text().splitlines()
    i = next(n for n, line in enumerate(lines) if start_marker in line)
    j = next(n for n in range(i + 1, len(lines)) if lines[n] == indent + "fi")
    return "\n".join(lines[i:j + 1]) + "\n"


def _setup(tmp_path):
    src = tmp_path / "src"
    (src / "tools").mkdir(parents=True)
    (src / "tools" / "release_denylist.txt").write_text(DENYLIST)
    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "keep.py").write_text("x = 1  # a comment\n")
    (stage / "a#b.txt").write_text("plain\n")
    return src, stage


def test_scrub_loop_uses_only_real_terms(tmp_path):
    src, stage = _setup(tmp_path)
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    log = tmp_path / "sed_i.log"
    fake = fakebin / "sed"
    fake.write_text(
        '#!/bin/bash\nif [ "$1" = "-i" ]; then printf "%s\\n" "$2" >> "' + str(log) + '"; exit 0; fi\n'
        'exec /usr/bin/sed "$@"\n'
    )
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    body = 'set -uo pipefail\nTIER=code\n' + _block('[ -f "$SRC/tools/release_denylist.txt" ]', "")
    env = dict(os.environ, SRC=str(src), STAGE=str(stage), PATH=f"{fakebin}:{os.environ['PATH']}")
    subprocess.run(["bash", "-c", body], env=env, check=True)
    assert log.read_text().split("\n")[:-1] == ["s/realterm//g"]
    assert (stage / "a#b.txt").exists()


def test_leak_audit_ignores_comment_lines(tmp_path):
    src, stage = _setup(tmp_path)
    body = 'set -uo pipefail\nFAIL=0\n' + _block('DENY="$SRC/tools/release_denylist.txt"', "  ") + 'echo "FAIL=$FAIL"\n'
    env = dict(os.environ, SRC=str(src), STAGE=str(stage), TIER="code")
    out = subprocess.run(["bash", "-c", body], env=env, capture_output=True, text=True, check=True)
    assert "FAIL=0" in out.stdout, out.stderr
    assert "LEAK" not in out.stderr
