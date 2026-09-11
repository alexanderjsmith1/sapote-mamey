"""BC2-CRM-01 (v9.7.396): check_release_manifest.py must not silently skip a malformed/
unparseable line in SOURCE_CHECKSUMS_SHA256.txt.

This tool's own docstring exists specifically because "a bundle whose checksum manifest fails on
128 files... passe[d]" every other governance gate, and it warns that "a hand-zipped working tree
carries whatever manifest was last written" — a plausible source of exactly this failure class. A
line with no filename field (`len(parts) != 2` — a truncated or corrupted entry, e.g. from an
interrupted regeneration or a bad merge) was silently `continue`d with no count and no mention
anywhere in the tool's output, so a checksums file containing genuine corruption still reported
"PASS (artifacts describe the tree)".

Reproduced live against the unpatched tools/check_release_manifest.py before this fix.
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "check_release_manifest.py"


def _run(root):
    return subprocess.run(
        [sys.executable, str(GATE), "--root", str(root)],
        capture_output=True, text=True, cwd=str(ROOT),
    )


def test_malformed_line_fails_closed(tmp_path):
    (tmp_path / "real_file.txt").write_text("hello world", encoding="utf-8")
    import hashlib
    digest = hashlib.sha256(b"hello world").hexdigest()
    (tmp_path / "SOURCE_CHECKSUMS_SHA256.txt").write_text(
        f"{digest}  real_file.txt\n"
        "this_is_a_malformed_truncated_line_with_no_filename_field\n",
        encoding="utf-8",
    )
    r = _run(tmp_path)
    assert r.returncode == 1, (
        f"a malformed checksums line must fail the gate closed, not report a clean pass; "
        f"stdout={r.stdout!r}"
    )
    assert "malformed" in r.stdout.lower()


def test_genuinely_clean_checksums_file_still_passes(tmp_path):
    (tmp_path / "real_file.txt").write_text("hello world", encoding="utf-8")
    import hashlib
    digest = hashlib.sha256(b"hello world").hexdigest()
    (tmp_path / "SOURCE_CHECKSUMS_SHA256.txt").write_text(
        f"{digest}  real_file.txt\n", encoding="utf-8",
    )
    r = _run(tmp_path)
    assert r.returncode == 0, r.stdout
    assert "malformed" not in r.stdout.lower()
