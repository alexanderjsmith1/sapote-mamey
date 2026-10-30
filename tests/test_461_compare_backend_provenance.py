"""Comparison metadata describes returned alignment evidence, not installation selection."""
import copy
import csv
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mamey import compare, parsers


def _hit(backend="diamond", **extra):
    result = {"sseqid": "reference_gene", "pident": 97.0, "qcovhsp": 90.0,
              "scovhsp": 85.0, "bitscore": 20.0, "backend": backend}
    result.update(extra)
    return result


def _run(monkeypatch, tmp_path, hits, selected="diamond"):
    genes = [SimpleNamespace(locus_tag=name, translation="MA") for name in ("query_1", "query_2")]
    monkeypatch.setattr(parsers, "extract_cds_features", lambda path: genes)
    monkeypatch.setattr(compare, "_aligner_backend", lambda: selected)
    calls = []

    def align(query, reference, threads=1):
        calls.append(threads)
        return copy.deepcopy(hits)

    def no_native(*args, **kwargs):
        raise AssertionError("metadata test attempted native alignment")

    monkeypatch.setattr(compare, "align_genes_to_proteome", align)
    monkeypatch.setattr(compare, "_align_diamond", no_native)
    monkeypatch.setattr(compare, "_align_pyswrd", no_native)
    monkeypatch.setattr(compare, "_align_biopython", no_native)
    out = tmp_path / "comparison"
    args = SimpleNamespace(strain_a="query_fixture.zip", strain_b="reference_fixture.zip",
                           out=str(out), alignment_threads=1)
    code = compare.compare_command(args)
    summary_path = out / "gemini_summary.json"
    table_path = out / "S5_gene_level_similarity.csv"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else None
    rows = list(csv.DictReader(table_path.open())) if table_path.exists() else []
    assert calls == [1]
    return code, summary, rows


def test_diamond_metadata_comes_from_measured_rows(monkeypatch, tmp_path):
    code, summary, rows = _run(monkeypatch, tmp_path, {
        "query_1": _hit(), "query_2": _hit(),
    })
    assert code == 0 and summary["backend"] == "diamond"
    assert "pyswrd/biopython" not in summary["diamond_status"]
    assert "diamond" in summary["diamond_status"]
    assert summary["backend_provenance"]["effective_backend_counts"] == {"diamond": 2}
    assert summary["backend_provenance"]["status"] == "OBSERVED"
    assert {row["backend"] for row in rows} == {"diamond"}


def test_runtime_fallback_is_not_reported_as_selected_diamond(monkeypatch, tmp_path):
    code, summary, rows = _run(monkeypatch, tmp_path, {
        "query_1": _hit("biopython"), "query_2": _hit("biopython"),
    })
    assert code == 0 and summary["backend"] == "biopython"
    assert summary["backend_selected"] == "diamond"
    assert summary["backend_provenance"]["effective_backends"] == ["biopython"]
    assert {row["backend"] for row in rows} == {"biopython"}
    assert summary["genes_present_in_B"] == 2


def test_mixed_backends_are_retained(monkeypatch, tmp_path):
    _, summary, rows = _run(monkeypatch, tmp_path, {
        "query_1": _hit("diamond"), "query_2": _hit("biopython"),
    })
    assert summary["backend"] == "mixed"
    assert summary["backend_provenance"]["effective_backends"] == ["biopython", "diamond"]
    assert summary["backend_provenance"]["effective_backend_counts"] == {"biopython": 1, "diamond": 1}
    assert summary["backend_provenance"]["status"] == "MIXED"
    assert [row["backend"] for row in rows] == ["diamond", "biopython"]


def test_missing_backend_tag_does_not_inherit_availability(monkeypatch, tmp_path):
    unknown = _hit()
    del unknown["backend"]
    _, summary, rows = _run(monkeypatch, tmp_path, {"query_1": unknown, "query_2": _hit()})
    assert summary["backend"] == "diamond"
    assert summary["backend_provenance"]["status"] == "PARTIAL"
    assert summary["backend_provenance"]["unattributed_result_genes"] == ["query_1"]
    assert rows[0]["backend"] == "unknown"


def test_empty_result_has_no_observed_effective_backend(monkeypatch, tmp_path):
    code, summary, rows = _run(monkeypatch, tmp_path, {})
    assert code == 0 and summary["backend"] == "unknown"
    assert summary["backend_selected"] == "diamond"
    assert summary["backend_provenance"]["status"] == "UNOBSERVED"
    assert summary["backend_provenance"]["effective_backends"] == []
    assert summary["backend_provenance"]["missing_result_genes"] == ["query_1", "query_2"]
    assert {row["backend"] for row in rows} == {"unknown"}
    assert all("unrecorded" in row["note"] for row in rows)


def test_all_skipped_results_stay_not_computed(monkeypatch, tmp_path):
    note = "alignment skipped: fixture query exceeds MAX_ALIGN_AA"
    skipped = _hit("biopython", sseqid=None, pident=None, qcovhsp=None, scovhsp=None,
                   bitscore=None, note=note)
    _, summary, rows = _run(monkeypatch, tmp_path, {"query_1": skipped, "query_2": skipped})
    assert summary["backend"] == "not_computed"
    assert summary["backend_provenance"]["status"] == "NOT_COMPUTED"
    assert summary["backend_provenance"]["not_computed_genes"] == ["query_1", "query_2"]
    assert summary["backend_provenance"]["effective_backends"] == []
    assert all(row["backend"] == "biopython" and row["note"] == note for row in rows)


def test_unmeasured_result_is_not_mislabeled_as_skipped(monkeypatch, tmp_path):
    unknown = _hit("biopython", sseqid=None, pident=None, qcovhsp=None,
                   note="runtime measurement unavailable")
    _, summary, rows = _run(monkeypatch, tmp_path, {"query_1": unknown, "query_2": unknown})
    assert summary["backend"] == "unknown"
    assert summary["backend_provenance"]["unmeasured_result_genes"] == ["query_1", "query_2"]
    assert summary["backend_provenance"]["not_computed_genes"] == []
    assert all(row["note"] == "runtime measurement unavailable" for row in rows)


def test_missing_query_result_keeps_partial_provenance(monkeypatch, tmp_path):
    _, summary, rows = _run(monkeypatch, tmp_path, {"query_1": _hit()})
    assert summary["backend"] == "diamond"
    assert summary["backend_provenance"]["status"] == "PARTIAL"
    assert summary["backend_provenance"]["missing_result_genes"] == ["query_2"]
    assert rows[1]["backend"] == "unknown"
    assert rows[1]["call"] == "no_hit" and rows[1]["pct_identity"] == ""


def test_unavailable_backend_refusal_is_preserved(monkeypatch, tmp_path):
    code, summary, rows = _run(monkeypatch, tmp_path, {}, selected="none")
    assert code == 1 and summary is None and rows == []


def test_numeric_results_calls_and_existing_notes_are_preserved(monkeypatch, tmp_path):
    hits = {"query_1": _hit(pident=53.0, qcovhsp=80.0, note="retained source note"),
            "query_2": _hit("biopython", pident=95.0, qcovhsp=90.0)}
    _, summary, rows = _run(monkeypatch, tmp_path, hits)
    assert [(row["pct_identity"], row["pct_coverage"], row["call"]) for row in rows] == [
        ("53.0", "80.0", "divergent_candidate"), ("95.0", "90.0", "present"),
    ]
    assert summary["genes_present_in_B"] == 1 and summary["genes_present_pct"] == 50.0
    assert "retained source note" in rows[0]["note"]
