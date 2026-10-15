"""Batch map PDFs must come from the current successful drawing attempt.

The actual direct/batch callers run against saved synthetic search rows. Drawings,
PDF concatenation and optional workbook emission are replaced, never executed.
"""
import hashlib
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.test_450_gap_rescue_fresh_split_families import fresh_saved_split


@pytest.fixture
def batch_maps(fresh_saved_split, monkeypatch):
    f = fresh_saved_split
    allr = importlib.import_module("gap_rescue_all_regions")
    monkeypatch.setattr(allr, "gdr", f.gdr)
    monkeypatch.setattr(f.gdr, "load_genome", lambda path, label: (f.prots, f.regions))
    monkeypatch.setattr(f.gdr, "kcb_reference", lambda path, core, directory: (f.reference, "Explicit reference"))
    def saved_hits(ref, prots, threads, sensitivity):
        assert prots is f.prots and threads == 3 and sensitivity == "sensitive"
        return f.hits
    monkeypatch.setattr(f.gdr, "run_diamond", saved_hits)
    # Optional workbook capability is absent in this portable fixture.
    monkeypatch.setitem(sys.modules, "openpyxl", None)
    appended, written = [], []
    class FakePdfWriter:
        def append(self, path):
            appended.append(Path(path))
        def write(self, path):
            written.append(Path(path))
            Path(path).write_bytes(b"synthetic combined PDF\n")
    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfWriter=FakePdfWriter))
    folder = f.out / "BGC001_vs_SYNTHETIC_REFERENCE"
    folder.mkdir(parents=True)
    png, pdf = folder / "gap_rescue.png", folder / "gap_rescue.pdf"
    png.write_bytes(b"prior PNG\n")
    pdf.write_bytes(b"prior PDF\n")
    combined = f.out / "SYNTHETIC_all_locus_maps.pdf"
    combined.write_bytes(b"prior combined PDF remains until a new one is produced\n")
    return SimpleNamespace(f=f, allr=allr, folder=folder, png=png, pdf=pdf, combined=combined,
                           appended=appended, written=written)


def _run(fixture, figure):
    f = fixture.f
    rows = fixture.allr.run_all(f.out.parent / "SYNTHETIC.zip", "SYNTHETIC", f.out, f.reference.parent,
                               f.db, {}, f.pfam, False, "sensitive", 3, figure)
    assert len(rows) == 1 and rows[0]["bgc"] == f.core_id
    assert f.calls == ["reference", "search", "splits", "checks"]
    return json.loads((f.out / "run_receipt.json").read_text())


@pytest.mark.parametrize("mode", ["disabled", "skipped_none", "skipped_false"])
def test_disabled_or_skipped_drawing_never_collects_prior_pdfs(batch_maps, monkeypatch, mode):
    b = batch_maps
    before = {p: p.read_bytes() for p in (b.png, b.pdf, b.combined)}
    draw_calls = []
    def skip(*args, **kwargs):
        draw_calls.append((args, kwargs))
        if mode == "disabled":
            raise AssertionError("figure=False must not invoke the map renderer")
        return None if mode == "skipped_none" else False
    monkeypatch.setattr(b.f.gdr, "draw_locus_map", skip)
    receipt = _run(b, mode != "disabled")
    assert len(draw_calls) == (0 if mode == "disabled" else 1)
    assert b.appended == b.written == []
    assert receipt["map_pdfs"] == [] and receipt["combined_map_pdf"] == ""
    assert json.loads((b.folder / "gap_rescue_receipt.json").read_text())["map_outputs"] == []
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize("same_bytes", [False, True])
def test_successful_current_drawing_admits_even_identical_redraw(batch_maps, monkeypatch, same_bytes):
    b = batch_maps
    png_bytes = b.png.read_bytes() if same_bytes else b"current PNG\n"
    pdf_bytes = b.pdf.read_bytes() if same_bytes else b"current PDF\n"
    def draw(*args, **kwargs):
        assert args[8:] == (b.png, b.pdf) and kwargs == {"anchor": None, "print_width": "double"}
        b.png.write_bytes(png_bytes)
        b.pdf.write_bytes(pdf_bytes)
        return {"contigs_drawn": [b.f.core["contig"]], "not_drawn": 0}
    monkeypatch.setattr(b.f.gdr, "draw_locus_map", draw)
    receipt = _run(b, True)
    assert b.appended == [b.pdf] and b.written == [b.combined]
    assert b.combined.read_bytes() == b"synthetic combined PDF\n"
    assert receipt["map_pdfs"] == [b.pdf.relative_to(b.f.out).as_posix()]
    assert receipt["combined_map_pdf"] == b.combined.name
    direct = json.loads((b.folder / "gap_rescue_receipt.json").read_text())
    assert direct["core"] == b.f.core_id
    assert direct["map_outputs"] == [
        {"path": b.png.name, "sha256": hashlib.sha256(png_bytes).hexdigest(), "bytes": len(png_bytes)},
        {"path": b.pdf.name, "sha256": hashlib.sha256(pdf_bytes).hexdigest(), "bytes": len(pdf_bytes)},
    ]


def test_failed_drawing_retains_prior_pdf_and_never_aggregates(batch_maps, monkeypatch):
    b = batch_maps
    before_pdf, before_combined = b.pdf.read_bytes(), b.combined.read_bytes()
    def fail(*args, **kwargs):
        raise RuntimeError("synthetic drawing failure")
    monkeypatch.setattr(b.f.gdr, "draw_locus_map", fail)
    with pytest.raises(RuntimeError, match="synthetic drawing failure"):
        _run(b, True)
    assert b.appended == b.written == []
    assert b.pdf.read_bytes() == before_pdf and b.combined.read_bytes() == before_combined
    assert json.loads((b.folder / "gap_rescue_receipt.json").read_text())["map_outputs"] == []


def test_successful_return_without_required_output_refuses(batch_maps, monkeypatch):
    b = batch_maps
    # New empty output path, so no prior artifact can satisfy the successful result.
    b.pdf.unlink()
    monkeypatch.setattr(b.f.gdr, "draw_locus_map", lambda *args, **kwargs: {"contigs_drawn": []})
    with pytest.raises(ValueError, match="GAP_RESCUE_MAP_OUTPUT_UNREADABLE"):
        _run(b, True)
    assert b.appended == b.written == []


@pytest.mark.parametrize("change", ["missing", "different_bytes", "different_size", "duplicate_record"])
def test_current_map_admission_refuses_damaged_receipt_or_output(batch_maps, change):
    b = batch_maps
    payload = b.pdf.read_bytes()
    record = {"path": "gap_rescue.pdf", "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
    receipt = {"map_outputs": [record]}
    if change == "missing":
        b.pdf.unlink()
    elif change == "different_bytes":
        b.pdf.write_bytes(b"changed bytes\n")
    elif change == "different_size":
        record["bytes"] += 1
    else:
        receipt["map_outputs"].append(dict(record))
    with pytest.raises(ValueError, match="GAP_RESCUE_MAP_OUTPUT_(UNREADABLE|CHANGED|AMBIGUOUS)"):
        b.allr._current_map_pdf(receipt, b.folder, True)
    assert b.appended == b.written == []


def test_missing_optional_pdf_writer_does_not_advertise_prior_aggregate(batch_maps, monkeypatch):
    b = batch_maps
    before = b.combined.read_bytes()
    monkeypatch.setitem(sys.modules, "pypdf", None)
    def draw(*args, **kwargs):
        b.png.write_bytes(b"current PNG\n")
        b.pdf.write_bytes(b"current PDF\n")
        return {"contigs_drawn": [b.f.core["contig"]]}
    monkeypatch.setattr(b.f.gdr, "draw_locus_map", draw)
    receipt = _run(b, True)
    assert receipt["map_pdfs"] == [b.pdf.relative_to(b.f.out).as_posix()]
    assert receipt["combined_map_pdf"] == ""
    assert b.combined.read_bytes() == before and b.appended == b.written == []


@pytest.mark.parametrize("failure", ["input", "draw", "merge"])
def test_failed_rerun_supersedes_previous_success_receipt(batch_maps, monkeypatch, failure):
    b = batch_maps
    prior = b'{"status":"SUCCEEDED","map_pdfs":["old.pdf"],"combined_map_pdf":"old_combined.pdf"}\n'
    (b.f.out / "run_receipt.json").write_bytes(prior)
    previous_combined = b.combined.read_bytes()
    def fail(*args, **kwargs):
        raise RuntimeError("synthetic " + failure + " failure")
    def draw(*args, **kwargs):
        b.png.write_bytes(b"current PNG\n"); b.pdf.write_bytes(b"current PDF\n")
        return {"contigs_drawn": []}
    monkeypatch.setattr(b.f.gdr, "draw_locus_map", fail if failure == "draw" else draw)
    if failure == "input": monkeypatch.setattr(b.f.gdr, "load_genome", fail)
    if failure == "merge":
        class FailedWriter:
            def append(self, path): pass
            def write(self, path): fail()
        monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfWriter=FailedWriter))
    with pytest.raises(RuntimeError, match="synthetic " + failure): _run(b, True)
    current = json.loads((b.f.out / "run_receipt.json").read_text())
    assert current["status"] == "FAILED" and current["error_type"] == "RuntimeError"
    assert current["map_pdfs"] == [] and current["combined_map_pdf"] == ""
    assert (b.f.out / current["superseded_receipt"]).read_bytes() == prior
    assert len(list(b.f.out.glob("run_receipt.superseded.*.json"))) == 1
    assert b.combined.read_bytes() == previous_combined


def test_tools_preflight_invalidates_prior_receipt_once(batch_maps, monkeypatch):
    b = batch_maps
    prior = b'{"status":"SUCCEEDED","map_pdfs":["old.pdf"]}\n'
    (b.f.out / "run_receipt.json").write_bytes(prior)
    monkeypatch.delenv("SAPOTE_MIBIG_GBK_DIR", raising=False)
    with pytest.raises(SystemExit, match="--mibig-dir"):
        b.allr.main(["--zip", str(b.f.out / "absent.zip"), "--label", "SYNTHETIC", "--out", str(b.f.out)])
    current = json.loads((b.f.out / "run_receipt.json").read_text())
    assert current["status"] == "FAILED" and current["map_pdfs"] == []
    assert (b.f.out / current["superseded_receipt"]).read_bytes() == prior
    assert len(list(b.f.out.glob("run_receipt.superseded.*.json"))) == 1
