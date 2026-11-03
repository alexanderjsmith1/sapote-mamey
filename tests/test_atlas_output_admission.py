"""Additive output admission using tiny software fixtures; no document rendering."""
import hashlib
import importlib.util
import os
from pathlib import Path
import sqlite3
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("atlas_candidate", ROOT / "tools/refresh_literature_atlas.py")
atlas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atlas)


def make_store(path):
    with sqlite3.connect(path) as db:
        for name in ("current_locus", "owner_record", "locus_binding", "document"):
            db.execute(f"CREATE TABLE {name}(fixture TEXT)")
        db.execute("CREATE TABLE metadata(key TEXT,value TEXT)")
        db.execute("INSERT INTO metadata VALUES('authority_ceiling','SOFTWARE_FIXTURE')")


def setup(tmp_path, store_in_output=False):
    legacy = tmp_path / "legacy"
    source = legacy / "AS-999" / "software.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Historical software fixture\nNo ranked biological records.\n")
    out = tmp_path / "output"
    out.mkdir()
    store = out / "REFRESH_INDEX.tsv" if store_in_output else tmp_path / "evidence.sqlite"
    make_store(store)
    return legacy, source, out, store


def invoke(monkeypatch, legacy, out, store):
    monkeypatch.setattr(sys, "argv", ["refresh_literature_atlas.py", "--legacy-strain-reports", str(legacy), "--evidence-store", str(store), "--output-root", str(out)])
    return atlas.main()


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("alias", ["md_symlink", "md_hardlink", "directory_symlink", "store_direct"] + [f"{name}_{kind}" for name in ("REFRESH_INDEX.tsv", "LOCUS_REFRESH_LEDGER.tsv", "UNBOUND_REPORT_HOLDS.tsv", "REFRESH_SUMMARY.json") for kind in ("symlink", "hardlink")])
def test_alias_refuses_before_any_writes(tmp_path, monkeypatch, alias):
    legacy, source, out, store = setup(tmp_path, alias == "store_direct")
    report = out / "strain_reports" / "AS-999" / "AS-999_CURRENT_EVIDENCE_LITERATURE_ATLAS_CURRENT_R001.md"
    if alias == "directory_symlink":
        (out / "strain_reports").symlink_to(legacy, target_is_directory=True)
    elif alias.startswith("md_"):
        report.parent.mkdir(parents=True)
        report.symlink_to(source) if alias.endswith("symlink") else os.link(source, report)
    elif alias != "store_direct":
        target = out / alias.rsplit("_", 1)[0]
        target.symlink_to(store) if alias.endswith("symlink") else os.link(store, target)
    before = snapshot(tmp_path)
    refused = False
    try:
        invoke(monkeypatch, legacy, out, store)
    except ValueError as error:
        refused = True
        assert "output" in str(error)
    after = snapshot(tmp_path)
    assert refused and before == after, {"refused": refused, "changed_paths": [key for key in before if before.get(key) != after.get(key)], "new_paths": sorted(after.keys() - before.keys())}


@pytest.mark.parametrize("existing_file", [False, True])
def test_additive_regular_output_preserves_inputs(tmp_path, monkeypatch, existing_file):
    legacy, source, out, store = setup(tmp_path)
    source_before, store_before = source.read_bytes(), store.read_bytes()
    if existing_file:
        (out / "REFRESH_SUMMARY.json").write_text("previous generated summary")
    assert invoke(monkeypatch, legacy, out, store) == 0
    assert source.read_bytes() == source_before
    assert store.read_bytes() == store_before
    assert (out / "REFRESH_INDEX.tsv").is_file()


def test_missing_paired_docx_creates_no_output(tmp_path, monkeypatch):
    legacy, source, out, store = setup(tmp_path)
    new_out = tmp_path / "not_created"
    monkeypatch.setattr(sys, "argv", ["refresh_literature_atlas.py", "--legacy-strain-reports", str(legacy), "--evidence-store", str(store), "--output-root", str(new_out), "--emit-docx"])
    with pytest.raises(FileNotFoundError, match="paired DOCX"):
        atlas.main()
    assert not new_out.exists()


@pytest.mark.parametrize("kind", ["symlink", "hardlink"])
def test_docx_alias_refuses_without_document_rendering(tmp_path, monkeypatch, kind):
    legacy, source, out, store = setup(tmp_path)
    docx = source.with_suffix(".docx")
    docx.write_bytes(b"opaque synthetic source; must never be parsed")
    target = out / "strain_reports/AS-999/AS-999_CURRENT_EVIDENCE_LITERATURE_ATLAS_CURRENT_R001.docx"
    target.parent.mkdir(parents=True)
    target.symlink_to(docx) if kind == "symlink" else os.link(docx, target)
    def forbidden(*args):
        pytest.fail("DOCX processing reached before alias refusal")
    monkeypatch.setattr(atlas, "refresh_docx", forbidden)
    monkeypatch.setattr(sys, "argv", ["refresh_literature_atlas.py", "--legacy-strain-reports", str(legacy), "--evidence-store", str(store), "--output-root", str(out), "--emit-docx"])
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match="output"):
        atlas.main()
    assert snapshot(tmp_path) == before
