"""Finished-run gene-table replay refuses incompatible genome identities before writing.

All sequence loaders and renderers are stubs; no searches or plotting run.
"""
import csv
import json
from pathlib import Path
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gap_rescue_gene_table as gt  # noqa: E402

CORE = "SYNTHETIC / CONTIG_A / region001 / BGC001"
COLS = ["reference_gene", "name", "status", "best_locus", "best_protein", "best_contig"]


def _prepare(tmp_path, monkeypatch, rows, *, include_core=True):
    run = tmp_path / "run"
    run.mkdir()
    (run / "gap_rescue_receipt.json").write_text(json.dumps(
        {"label": "SYNTHETIC", "core": CORE, "reference_name": "Saved reference"}))
    with (run / "gap_rescue.tsv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    zip_path = tmp_path / "synthetic.zip"
    reference = tmp_path / "reference.gbk"
    zip_path.write_bytes(b"stub genome")
    reference.write_bytes(b"stub reference")
    proteins = {"q1": {"tag": "gene_a", "family": "Saved family"}}
    core = {"identity": CORE}
    loader_calls, table_calls, edge_calls = [], [], []

    def load_genome(path, label):
        loader_calls.append((path, label))
        return proteins, [core] if include_core else []

    def edge_shares(got_rows, got_proteins, got_core):
        edge_calls.append((got_rows, got_proteins, got_core))
        return {"gene_a": 75}

    def write_gene_table(*args):
        table_calls.append(args)
        return {"rows": len(args[1]), "files": []}

    monkeypatch.setitem(sys.modules, "gap_directed_rescue", types.SimpleNamespace(load_genome=load_genome))
    monkeypatch.setattr(gt, "edge_shares", edge_shares)
    monkeypatch.setattr(gt, "write_gene_table", write_gene_table)
    monkeypatch.setattr(gt._OUT, "info", lambda *args, **kwargs: None)
    argv = ["--run", str(run), "--zip", str(zip_path), "--reference", str(reference)]
    return run, argv, proteins, core, loader_calls, table_calls, edge_calls


def _row(status="PRESENT_IN_CORE", tag="gene_a"):
    return dict(reference_gene="1", name="ref_a", status=status, best_locus=tag,
                best_protein="q1", best_contig="CONTIG_A")


def _files(run):
    return {p.relative_to(run).as_posix(): p.read_bytes() for p in run.rglob("*") if p.is_file()}


def test_absent_receipt_core_refuses_before_outputs(tmp_path, monkeypatch):
    run, argv, _, _, _, calls, edges = _prepare(tmp_path, monkeypatch, [_row()], include_core=False)
    before = _files(run)
    with pytest.raises(SystemExit, match="not a region of this zip"):
        gt.main(argv)
    assert not calls and not edges
    assert _files(run) == before


@pytest.mark.parametrize("status", ["PRESENT_IN_CORE", "MISSING_FOUND_CLEAR", "MISSING_FOUND_AMBIGUOUS", "FUTURE_STATE"])
def test_absent_saved_found_locus_refuses_before_outputs(tmp_path, monkeypatch, status):
    run, argv, _, _, _, calls, edges = _prepare(tmp_path, monkeypatch, [_row(status, "missing_gene")])
    before = _files(run)
    with pytest.raises(SystemExit, match="Saved gap-rescue found loci are not in this zip: missing_gene"):
        gt.main(argv)
    assert not calls and not edges
    assert _files(run) == before


def test_missing_loci_are_unique_and_sorted(tmp_path, monkeypatch):
    rows = [_row(tag="missing_z"), _row(tag="missing_a"), _row(tag="missing_z")]
    run, argv, _, _, _, calls, edges = _prepare(tmp_path, monkeypatch, rows)
    before = _files(run)
    with pytest.raises(SystemExit) as error:
        gt.main(argv)
    assert str(error.value) == ("Saved gap-rescue found loci are not in this zip: missing_a, missing_z"
                                "; check --zip and the saved run receipt")
    assert not calls and not edges
    assert _files(run) == before


def test_valid_replay_preserves_delegation_and_return_code(tmp_path, monkeypatch):
    rows = [_row()]
    run, argv, proteins, core, loaders, calls, edges = _prepare(tmp_path, monkeypatch, rows)
    assert gt.main(argv) == 0
    assert loaders == [(tmp_path / "synthetic.zip", "SYNTHETIC")]
    assert edges == [(rows, proteins, core)]
    assert calls == [(run, rows, [], CORE, "SYNTHETIC", tmp_path / "reference.gbk",
                      {"q1": "Saved family", "gene_a": "Saved family"}, "Saved reference",
                      {"gene_a": 75}, {"gene_a"})]


def test_not_found_row_is_not_reclassified_by_replay_guard(tmp_path, monkeypatch):
    rows = [_row("MISSING_NOT_FOUND", "unused_stale_tag")]
    _, argv, _, _, _, calls, _ = _prepare(tmp_path, monkeypatch, rows)
    assert gt.main(argv) == 0
    assert calls[0][1] == rows


def test_explicit_reference_name_still_overrides_saved_name(tmp_path, monkeypatch):
    _, argv, _, _, _, calls, _ = _prepare(tmp_path, monkeypatch, [_row()])
    assert gt.main(argv + ["--reference-name", "Explicit reference"]) == 0
    assert calls[0][7] == "Explicit reference"
