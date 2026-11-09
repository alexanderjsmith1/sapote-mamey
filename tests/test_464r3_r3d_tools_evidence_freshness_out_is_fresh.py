"""The freshness receipt goes to a new file through --out; an existing receipt is never truncated."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "tools" / "evidence_freshness.py"
SPEC = importlib.util.spec_from_file_location("freshness_out_r3d", PATH)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def _manifest(tmp_path):
    (tmp_path / "source.tsv").write_text("x\n")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema": M.SCHEMA, "artifacts": [
        {"id": "source", "path": "source.tsv", "sha256": M.digest(tmp_path / "source.tsv"),
         "unit": "artifact", "source_revision": "fixture", "depends_on": []}]}))
    return manifest


def _run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = M.main(argv)
    return code, json.loads(buf.getvalue())


def test_out_writes_a_new_receipt(tmp_path):
    manifest = _manifest(tmp_path)
    out = tmp_path / "recheck.json"
    code, shown = _run([str(manifest), "--out", str(out)])
    assert code == 0
    assert shown["receipt"] == str(out.absolute())
    assert json.loads(out.read_text())["status"] == "PASS_BYTES_AND_DECLARED_DEPENDENCIES"


def test_out_refuses_an_existing_receipt_and_keeps_its_bytes(tmp_path):
    manifest = _manifest(tmp_path)
    out = tmp_path / "old_receipt.json"
    out.write_text("retained receipt\n")
    code, shown = _run([str(manifest), "--out", str(out)])
    assert code == 2
    assert shown["status"] == "OUTPUT_REFUSED"
    assert out.read_text() == "retained receipt\n"


def test_out_refuses_the_manifest_and_listed_artifacts(tmp_path):
    manifest = _manifest(tmp_path)
    before = manifest.read_bytes()
    for target in (manifest, tmp_path / "source.tsv"):
        code, shown = _run([str(manifest), "--out", str(target)])
        assert code == 2 and shown["status"] == "OUTPUT_REFUSED"
    assert manifest.read_bytes() == before
    assert (tmp_path / "source.tsv").read_text() == "x\n"
