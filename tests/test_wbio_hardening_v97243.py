"""v9.7.243 — bunny-hop findings on tools/_wbio.py (85 loc, 38 importers, 1 test before this file).

os.replace() adopts the TEMP file's permissions, so rewriting a 0600 deliverable left it 0644 — real
widening in a bundle that ships a MERGED-PRIVATE tier. And three of the four helpers leaked a .tmp when
the write raised; only atomic_open cleaned up. Both reproduced before the fix.
"""
import json, os, stat, sys, pathlib, pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import _wbio


def _mode(p):
    return stat.S_IMODE(os.stat(p).st_mode)


def test_atomic_write_text_preserves_restrictive_mode(tmp_path):
    p = tmp_path / "private.md"
    p.write_text("secret"); os.chmod(p, 0o600)
    _wbio.atomic_write_text(p, "still secret")
    assert _mode(p) == 0o600, "PRIVATE-tier deliverable must not be widened by a rewrite"


def test_atomic_dump_json_preserves_mode_and_cleans_tmp_on_failure(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{}"); os.chmod(p, 0o600)
    _wbio.atomic_dump_json({"a": 1}, p)
    assert _mode(p) == 0o600 and json.loads(p.read_text()) == {"a": 1}
    with pytest.raises(TypeError):
        _wbio.atomic_dump_json({"k": set()}, p)          # not serializable
    assert not (tmp_path / "x.json.tmp").exists(), "failed write must not leave a stray .tmp"
    assert json.loads(p.read_text()) == {"a": 1}, "original must survive a failed write"


def test_atomic_save_keep_bak_never_leaves_the_target_missing(tmp_path):
    """The old code did os.replace(path, path+'.bak') BEFORE moving the temp in — a window in which
    the target did not exist. .bak is now a copy."""
    p = tmp_path / "wb.xlsx"
    p.write_bytes(b"old")

    class FakeWB:
        def save(self, dest):
            pathlib.Path(dest).write_bytes(b"new")

    _wbio.atomic_save(FakeWB(), p, keep_bak=True)
    assert p.read_bytes() == b"new"
    assert (tmp_path / "wb.xlsx.bak").read_bytes() == b"old"


def test_atomic_save_cleans_tmp_when_save_raises(tmp_path):
    p = tmp_path / "wb.xlsx"
    p.write_bytes(b"original")

    class Boom:
        def save(self, dest):
            pathlib.Path(dest).write_bytes(b"partial")
            raise RuntimeError("interrupted")

    with pytest.raises(RuntimeError):
        _wbio.atomic_save(Boom(), p)
    assert not (tmp_path / "wb.xlsx.tmp").exists()
    assert p.read_bytes() == b"original"


def test_atomic_open_still_discards_tmp_on_exception(tmp_path):
    p = tmp_path / "out.txt"
    p.write_text("keep me")
    with pytest.raises(ValueError):
        with _wbio.atomic_open(p) as f:
            f.write("partial")
            raise ValueError
    assert p.read_text() == "keep me" and not (tmp_path / "out.txt.tmp").exists()
