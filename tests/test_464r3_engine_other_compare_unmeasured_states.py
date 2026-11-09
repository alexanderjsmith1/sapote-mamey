"""`mamey compare`: unmeasured rows are not no-hits, and fallback coverage counts query residues.

Before:
- a skipped query, a query whose every pairwise alignment raised, and a query with no returned row
  were all written as `no_hit`, and the present percentage gave no measured denominator;
- the Biopython fallback divided the alignment length (gap columns included) by the query length,
  so a gapped alignment could report more than 100% query coverage.
"""
import copy
import csv
import json
import os
from types import SimpleNamespace

import pytest

from mamey import compare, parsers

Bio = pytest.importorskip("Bio.Align")


def _hit(**extra):
    row = {"sseqid": "ref", "pident": 97.0, "qcovhsp": 90.0, "scovhsp": None,
           "bitscore": 20.0, "backend": "biopython"}
    row.update(extra)
    return row


def _run(monkeypatch, tmp_path, hits, names):
    genes = [SimpleNamespace(locus_tag=n, translation="MA") for n in names]
    monkeypatch.setattr(parsers, "extract_cds_features", lambda path: genes)
    monkeypatch.setattr(compare, "_aligner_backend", lambda: "biopython")
    monkeypatch.setattr(compare, "align_genes_to_proteome",
                        lambda q, r, threads=1: copy.deepcopy(hits))
    out = tmp_path / "cmp"
    assert compare.compare_command(SimpleNamespace(strain_a="a.zip", strain_b="b.zip",
                                                   out=str(out), alignment_threads=1)) == 0
    rows = list(csv.DictReader((out / "S5_gene_level_similarity.csv").open()))
    return json.loads((out / "gemini_summary.json").read_text()), {r["query_gene"]: r for r in rows}


def test_unmeasured_rows_get_their_own_calls_and_denominator(monkeypatch, tmp_path):
    hits = {
        "present": _hit(),
        "skipped": _hit(sseqid=None, pident=None, qcovhsp=None, bitscore=None,
                        note="alignment skipped: query length 20000 exceeds MAX_ALIGN_AA=10000"),
        "errored": _hit(sseqid=None, pident=None, qcovhsp=None, bitscore=None,
                        note="alignment error: 3 reference alignment(s) raised an error"),
    }
    summary, rows = _run(monkeypatch, tmp_path, hits, ["present", "skipped", "errored", "missing"])
    assert rows["present"]["call"] == "present"
    assert rows["skipped"]["call"] == "not_computed"
    assert rows["errored"]["call"] == "error"
    assert rows["missing"]["call"] == "no_result"
    assert "not an observed no-hit" in rows["missing"]["note"]
    assert summary["call_counts"] == {"error": 1, "no_result": 1, "not_computed": 1, "present": 1}
    assert summary["genes_present_pct"] == 25.0
    assert summary["genes_measured"] == 1 and summary["genes_present_pct_of_measured"] == 100.0
    assert "biopython" in summary["coverage_definitions"]


def test_biopython_query_coverage_counts_query_residues_not_gap_columns():
    query = "MKTAYIAKQRQISFVKSHFSRQ"
    reference = "MKTAYIAKQRQ" + "GGGGGGGGGG" + "ISFVKSHFSRQ"   # forces a gap in the query row
    out = compare._align_biopython([("q", query)], [("r", reference)])
    hit = out["q"]
    assert hit["pident"] is not None
    assert 0 < hit["qcovhsp"] <= 100.0


def test_biopython_all_pairs_failing_is_an_error_not_a_no_hit(monkeypatch):
    from Bio import Align

    def boom(self, a, b):
        raise RuntimeError("fixture alignment failure")

    monkeypatch.setattr(Align.PairwiseAligner, "align", boom)
    out = compare._align_biopython([("q", "MKTAYIAK")], [("r1", "MKTAYIAK"), ("r2", "MKTA")])
    assert out["q"]["pident"] is None
    assert out["q"]["note"].startswith("alignment error:")
    assert compare.result_call(out["q"]) == "error"


def test_biopython_all_references_over_cap_is_not_computed(monkeypatch):
    monkeypatch.setenv("MAMEY_MAX_ALIGN_AA", "10")
    out = compare._align_biopython([("q", "MKTAYIAK")], [("r1", "M" * 50)])
    assert out["q"]["note"].startswith("alignment not computed:")
    assert compare.result_call(out["q"]) == "not_computed"
