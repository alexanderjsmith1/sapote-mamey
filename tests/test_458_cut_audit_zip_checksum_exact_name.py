"""cut_audit verify --zip takes the hash listed for exactly that file name.

It took the first SHA256SUMS line containing the name as a substring, so an earlier line
for "old-cut.zip" supplied the expected hash for "cut.zip".
"""
import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _tool(monkeypatch):
    spec = importlib.util.spec_from_file_location("cut_audit_458", ROOT / "tools/cut_audit.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "_run", lambda *a, **k: (0, "OK\n"))
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/synthetic/sha256sum" if name == "sha256sum" else None)
    return mod


def _tree(tmp_path):
    root = tmp_path / "tree"
    (root / "tools").mkdir(parents=True)
    (root / "SOURCE_CHECKSUMS_SHA256.txt").write_text("synthetic\n")
    (root / "tools/sync_version.py").write_text("# mocked\n")
    return root


def test_exact_name_line_is_used(tmp_path, monkeypatch, capsys):
    mod = _tool(monkeypatch)
    z = tmp_path / "cut.zip"
    z.write_bytes(b"sealed bytes")
    good = hashlib.sha256(b"sealed bytes").hexdigest()
    sums = tmp_path / "SHA256SUMS.txt"
    sums.write_text(f"{'0' * 64}  old-cut.zip\n{good}  cut.zip\n")
    mod.main(["verify", "--tree", str(_tree(tmp_path)), "--zip", str(z), "--sha256", str(sums)])
    out = capsys.readouterr().out
    assert "[zip     ] OK cut.zip" in out


def test_usage_lists_no_unknown_option():
    assert "--full" not in (ROOT / "tools/cut_audit.py").read_text().split('"""')[1]
