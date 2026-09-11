"""A GCA_ query must find a row registered under GCF_ with the same nine-digit body — as a LOOKUP, said aloud.
2026-09-08: 19 of 40 'missing' Cameron genomes were on disk under the other prefix. Codex's review warns against
treating shared digits as IDENTITY; this test pins that the hit is reported with an explicit note, not silently."""
import importlib.util, io, sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import pytest
TOOL = Path(__file__).resolve().parent.parent / "tools" / "find_asset.py"
def _run(tmp_path, monkeypatch, q):
    if not TOOL.exists(): pytest.skip("absent")
    spec = importlib.util.spec_from_file_location("_fa416", TOOL); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    reg = tmp_path / "ASSET_REGISTRY.tsv"; (tmp_path / "x.fna").write_text(">x\nA\n")
    reg.write_text("asset_id\tkind\tpath\tsize\tguard_tokens\tnote\nembleya_gcf\tgenome\t" + str(tmp_path / "x.fna") + "\t1K\tGCF_000372745.1|Embleya\tEmbleya scabrispora assembly\n")
    monkeypatch.setattr(m, "REG", reg, raising=False); monkeypatch.setattr(m, "ROOT", tmp_path, raising=False)
    monkeypatch.setattr(m, "rows", lambda: [{"asset_id": "embleya_gcf", "kind": "genome", "path": "x.fna", "size": "1K", "guards": ["GCF_000372745.1", "Embleya"], "note": "Embleya scabrispora assembly"}])
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err): rc = m.main([q])
    return rc, out.getvalue() + err.getvalue()
def test_other_prefix_is_found_and_the_substitution_is_stated(tmp_path, monkeypatch):
    rc, text = _run(tmp_path, monkeypatch, "GCA_000372745.1")
    assert rc in (0, None) and "embleya_gcf" in text, text
    assert "assembly body" in text and "not an identity claim" in text
def test_same_prefix_still_found_without_the_note(tmp_path, monkeypatch):
    rc, text = _run(tmp_path, monkeypatch, "GCF_000372745")
    assert "embleya_gcf" in text and "assembly body" not in text
