"""Fresh table output must not pair an earlier map after a skipped current map.

Exercise the actual fresh caller, table writer and standalone replay caller using
saved synthetic rows. Map/table rendering and composition are portable spies.
"""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.test_450_gap_rescue_fresh_split_families import fresh_saved_split


@pytest.fixture
def pairing(fresh_saved_split, monkeypatch):
    f = fresh_saved_split
    f.out.mkdir()
    names = ("gap_rescue.png", "gap_rescue.pdf", "gene_table.png", "gene_table.pdf",
             "map_and_table.png", "map_and_table.pdf")
    previous = {}
    for name in names:
        path = f.out / name
        path.write_bytes(("prior artifact: " + name + "\n").encode())
        previous[path] = path.read_bytes()
    b = SimpleNamespace(f=f, previous=previous, map_calls=[], table_calls=[], pair_calls=[],
                        writer_calls=[], results=[], admitted_maps=None)

    def draw_table(table, title, label, png, pdf, caption):
        b.table_calls.append((png, pdf, caption))
        png.write_bytes(b"fresh table PNG\n")
        pdf.write_bytes(b"fresh table PDF\n")
        return True

    def pair(out):
        b.pair_calls.append(out)
        assert b.admitted_maps is not None, "A fresh caller must not compose an unadmitted prior map"
        assert {path: path.read_bytes() for path in b.admitted_maps} == b.admitted_maps
        assert (out / "gene_table.png").read_bytes() == b"fresh table PNG\n"
        assert (out / "gene_table.pdf").read_bytes() == b"fresh table PDF\n"
        made = [out / "map_and_table.png", out / "map_and_table.pdf"]
        for path in made:
            path.write_bytes(b"fresh composed output\n")
        return made

    original_writer = f.table.write_gene_table

    def capture_writer(*args, **kwargs):
        b.writer_calls.append((args, kwargs))
        result = original_writer(*args, **kwargs)
        b.results.append(result)
        return result

    monkeypatch.setattr(f.table, "_draw", draw_table)
    monkeypatch.setattr(f.table, "pair_with_map", pair)
    monkeypatch.setattr(f.table, "write_gene_table", capture_writer)
    return b


def _analyse(b, *, figure, gene_table=True):
    f = b.f
    return f.gdr.analyse_region(
        "SYNTHETIC", f.prots, f.regions, f.core, f.reference, "Explicit reference", "saved fixture", f.out,
        hits=f.hits, threads=3, sensitivity="sensitive", mibig_db=f.db, pfam=f.pfam,
        figure=figure, write_proteins=False, anchor="r_split", gene_table=gene_table)


def _old_maps_and_pairs(b):
    return {path: value for path, value in b.previous.items()
            if path.name.startswith(("gap_rescue.", "map_and_table."))}


def _admit_current_draw(b, monkeypatch, same_bytes=False):
    b.admitted_maps = {
        b.f.out / name: (b.previous[b.f.out / name] if same_bytes else ("current " + name + "\n").encode())
        for name in ("gap_rescue.png", "gap_rescue.pdf")
    }

    def draw(*args, **kwargs):
        b.map_calls.append((args, kwargs))
        assert args[8:] == (b.f.out / "gap_rescue.png", b.f.out / "gap_rescue.pdf")
        assert kwargs == {"anchor": "r_split", "print_width": "double"}
        for path, payload in b.admitted_maps.items():
            path.write_bytes(payload)
        return {"contigs_drawn": [b.f.core["contig"]], "not_drawn": 0}

    monkeypatch.setattr(b.f.gdr, "draw_locus_map", draw)


@pytest.mark.parametrize("mode", ["disabled", "skipped_none", "skipped_false"])
def test_fresh_table_does_not_pair_old_map_when_current_map_is_not_drawn(pairing, monkeypatch, mode):
    b = pairing

    def skip(*args, **kwargs):
        b.map_calls.append((args, kwargs))
        if mode == "disabled":
            raise AssertionError("figure=False must never call the map renderer")
        return None if mode == "skipped_none" else False

    monkeypatch.setattr(b.f.gdr, "draw_locus_map", skip)
    receipt = _analyse(b, figure=mode != "disabled")
    assert len(b.map_calls) == (0 if mode == "disabled" else 1)
    assert len(b.table_calls) == 1 and b.pair_calls == []
    assert b.writer_calls[0][1] == {"pair_map": False}
    assert receipt["map_outputs"] == []
    assert json.loads((b.f.out / "gap_rescue_receipt.json").read_text())["map_outputs"] == []
    assert {path: path.read_bytes() for path in _old_maps_and_pairs(b)} == _old_maps_and_pairs(b)
    result = b.results[0]
    assert [Path(path).name for path in result["files"]] == [
        "gene_table.tsv", "gene_table_counts.tsv", "gene_table.png", "gene_table.pdf"]
    assert (b.f.out / "gene_table.png").read_bytes() == b"fresh table PNG\n"
    assert (b.f.out / "gene_table.pdf").read_bytes() == b"fresh table PDF\n"
    assert set(result) == {"rows", "files", "counts", "caption", "rendered_caption"}
    assert result["rows"] == 1 and result["counts"]["reference_genes"] == 1


def test_failed_current_map_never_reaches_table_or_pairing(pairing, monkeypatch):
    b = pairing

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic current map failure")

    monkeypatch.setattr(b.f.gdr, "draw_locus_map", fail)
    with pytest.raises(RuntimeError, match="synthetic current map failure"):
        _analyse(b, figure=True)
    assert b.writer_calls == b.table_calls == b.pair_calls == []
    assert {path: path.read_bytes() for path in b.previous} == b.previous
    assert json.loads((b.f.out / "gap_rescue_receipt.json").read_text())["map_outputs"] == []


@pytest.mark.parametrize("same_bytes", [False, True])
def test_successful_current_map_and_table_pair_even_when_redraw_is_identical(pairing, monkeypatch, same_bytes):
    b = pairing
    _admit_current_draw(b, monkeypatch, same_bytes)
    receipt = _analyse(b, figure=True)
    assert len(b.map_calls) == len(b.table_calls) == len(b.pair_calls) == 1
    assert b.writer_calls[0][1] == {"pair_map": True}
    assert receipt["core"] == b.f.core_id
    assert receipt["map_outputs"] == [
        {"path": path.name, "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
        for path, payload in b.admitted_maps.items()
    ]
    result = b.results[0]
    assert [Path(path).name for path in result["files"]] == [
        "gene_table.tsv", "gene_table_counts.tsv", "gene_table.png", "gene_table.pdf",
        "map_and_table.png", "map_and_table.pdf"]
    assert set(result) == {"rows", "files", "counts", "caption", "rendered_caption"}
    assert result["rows"] == 1 and result["counts"]["reference_genes"] == 1


@pytest.mark.parametrize("table_outcome", ["skipped", "failed"])
def test_admitted_current_map_does_not_override_table_render_failure(pairing, monkeypatch, table_outcome):
    b = pairing
    _admit_current_draw(b, monkeypatch)

    def no_table(*args, **kwargs):
        b.table_calls.append((args, kwargs))
        if table_outcome == "failed":
            raise OSError("synthetic current table failure")
        return False

    monkeypatch.setattr(b.f.table, "_draw", no_table)
    if table_outcome == "failed":
        with pytest.raises(OSError, match="synthetic current table failure"):
            _analyse(b, figure=True)
        assert b.results == []
    else:
        receipt = _analyse(b, figure=True)
        assert len(receipt["map_outputs"]) == 2
        assert [Path(path).name for path in b.results[0]["files"]] == ["gene_table.tsv", "gene_table_counts.tsv"]
    assert b.writer_calls[0][1] == {"pair_map": True}
    assert b.pair_calls == []
    for name in ("map_and_table.png", "map_and_table.pdf"):
        assert (b.f.out / name).read_bytes() == b.previous[b.f.out / name]


def test_standalone_saved_map_replay_preserves_legacy_default_pairing(pairing, monkeypatch):
    b = pairing
    # Save current synthetic homology tables without replacing the earlier maps.
    receipt = _analyse(b, figure=False, gene_table=False)
    assert receipt["map_outputs"] == [] and b.writer_calls == []
    before_stage_calls = list(b.f.calls)
    b.admitted_maps = {b.f.out / name: b.previous[b.f.out / name]
                       for name in ("gap_rescue.png", "gap_rescue.pdf")}
    monkeypatch.setattr(b.f.gdr, "load_genome", lambda path, label: (b.f.prots, b.f.regions))
    assert b.f.table.main(["--run", str(b.f.out), "--zip", str(b.f.out.parent / "SYNTHETIC.zip"),
                           "--reference", str(b.f.reference)]) == 0
    assert b.f.calls == before_stage_calls
    assert len(b.table_calls) == len(b.pair_calls) == 1
    assert b.writer_calls[0][1] == {}, "Standalone replay retains the default saved-map pairing contract"
    assert {path: path.read_bytes() for path in b.admitted_maps} == b.admitted_maps
    assert {Path(path).name for path in b.results[0]["files"]} >= {"map_and_table.png", "map_and_table.pdf"}
