"""v9.7.247 (F5): LICENSE-DOCS.txt granted CC-BY-4.0 over three files that do not ship."""
import subprocess, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_every_granted_doc_exists():
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "check_license_docs.py")],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stdout + r.stderr


def test_guard_fails_when_a_granted_doc_is_missing(tmp_path):
    lic = ROOT / "LICENSE-DOCS.txt"
    orig = lic.read_text(encoding="utf-8")
    try:
        lic.write_text(orig + "\ndocs/DEFINITELY_NOT_SHIPPED.md\n", encoding="utf-8")
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "check_license_docs.py")],
                           capture_output=True, text=True, cwd=str(ROOT))
        assert r.returncode == 1 and "DEFINITELY_NOT_SHIPPED" in r.stdout
    finally:
        lic.write_text(orig, encoding="utf-8")
