"""Hermetic comparison resource-control regressions; no native aligner required."""
from types import SimpleNamespace
import json
import sys

import pytest

from mamey import compare, diamond_align, parsers
from mamey.cli import build_parser


def _args(tmp_path, **extra):
    return SimpleNamespace(strain_a="query with spaces.zip",
                           strain_b="reference with spaces.zip",
                           out=str(tmp_path / "comparison with spaces"), **extra)


@pytest.mark.parametrize("option,expected", [([], 1), (["--alignment-threads", "3"], 3)])
def test_parser_exposes_alignment_threads(option, expected):
    args = build_parser().parse_args([
        "compare", "--strain-a", "query.zip", "--strain-b", "ref.zip", *option])
    assert args.alignment_threads == expected


@pytest.mark.parametrize("value", ["many", "1.5"])
def test_parser_rejects_noninteger_threads(value):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args([
            "compare", "--strain-a", "query.zip", "--strain-b", "ref.zip",
            "--alignment-threads", value])
    assert exc.value.code == 2


@pytest.mark.parametrize("extra,expected", [({}, 1), ({"alignment_threads": 1}, 1),
                                            ({"alignment_threads": 3}, 3)])
def test_command_forwards_and_records_threads(tmp_path, monkeypatch, extra, expected):
    args = _args(tmp_path, **extra)
    monkeypatch.setattr(parsers, "extract_cds_features", lambda _: [
        SimpleNamespace(locus_tag="gene", translation="MPEPTIDE")])
    monkeypatch.setattr(compare, "_aligner_backend", lambda: "pyswrd")
    calls = []

    def align(query, reference, threads):
        calls.append(threads)
        return {"gene": {"sseqid": "reference_gene", "pident": 99.0,
                         "qcovhsp": 100.0, "backend": "pyswrd"}}

    monkeypatch.setattr(compare, "align_genes_to_proteome", align)
    assert compare.compare_command(args) == 0
    assert calls == [expected]
    summary = json.loads((tmp_path / "comparison with spaces" / "gemini_summary.json").read_text())
    assert summary["alignment_threads"] == expected
    assert summary["genes_present_in_B"] == 1


@pytest.mark.parametrize("value", [0, -1, None, True, 1.5, "2"])
def test_invalid_threads_fail_before_io(tmp_path, monkeypatch, value):
    def forbidden(*a, **kw):
        pytest.fail("invalid resource control must fail before extraction/backend probing")
    monkeypatch.setattr(parsers, "extract_cds_features", forbidden)
    monkeypatch.setattr(compare, "_aligner_backend", forbidden)
    assert compare.compare_command(_args(tmp_path, alignment_threads=value)) == 2
    assert not (tmp_path / "comparison with spaces").exists()


def test_pyswrd_receives_limit_for_every_batch(monkeypatch):
    calls = []
    def search(query, target, threads):
        calls.append((len(query), threads))
        return []
    monkeypatch.setitem(sys.modules, "pyswrd", SimpleNamespace(search=search))
    monkeypatch.setattr(compare, "_aligner_backend", lambda: "pyswrd")
    compare.align_genes_to_proteome([(str(i), "MPEPTIDE") for i in range(251)],
                                    [("ref", "MPEPTIDE")], threads=3)
    assert calls == [(250, 3), (1, 3)]


def test_diamond_receives_limit_and_cleans_workspace(monkeypatch):
    from pathlib import Path
    workspaces = []
    def align(query, reference, threads):
        assert threads == 3
        assert Path(query).is_file() and Path(reference).is_file()
        workspaces.append(Path(query).parent)
        return {"ok": True, "hits": []}
    monkeypatch.setattr(compare, "_aligner_backend", lambda: "diamond")
    monkeypatch.setattr(diamond_align, "align_fasta", align)
    assert compare.align_genes_to_proteome([("q", "MPEPTIDE")],
                                          [("r", "MPEPTIDE")], threads=3) == {}
    assert len(workspaces) == 1 and not workspaces[0].exists()


def test_biopython_remains_serial_fallback(monkeypatch):
    monkeypatch.setattr(compare, "_aligner_backend", lambda: "biopython")
    monkeypatch.setattr(compare, "_align_biopython", lambda q, r: {"serial": {}})
    assert compare.align_genes_to_proteome([], [], threads=3) == {"serial": {}}
