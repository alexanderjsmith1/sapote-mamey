"""The receipt must say whether the protein-hash binding actually ran.

`docs/modules/DEEP_BGC_REPORT.md` states the contract precisely: protein hashes
"when supplied in the locus record, must agree".  Skipping the comparison when
the record omits a hash is therefore *documented, intended behaviour* -- not a
defect, and this file does not change it.

What the same doc also calls the output is a **"hash-bound receipt"**.  Before
this patch the receipt carried no field distinguishing a run where every
evidence row was hash-compared from one where none were, so that phrase could
not be checked.  It matters because the receipt is a gate:
`mamey/activity_decision_tree.py` admits a lead on `receipt["identity"]` alone,
and `mamey/thesis_handoff.py` packages artifacts keyed on the same receipt.

These tests pin the reporting, not the policy.
"""
from __future__ import annotations

import csv
import json

import pytest

from mamey.deep_bgc_report import DeepBGCReportError, build_deep_report

IDENT = {
    "strain": "SYNTHETIC-001",
    "full_node_or_contig": "contig_demo_0001_complete",
    "region": "region001",
    "bgc_alias": "BGC007",
}
TRUE_HASH = "a" * 64
OTHER_HASH = "b" * 64


def build(tmp_path, canonical_hash, evidence_hash, second_gene_hash=None):
    genes = [{"gene_id": "gene_001", "start": 1, "end": 900, "strand": "+", "role": "core"}]
    if canonical_hash:
        genes[0]["protein_sha256"] = canonical_hash
    if second_gene_hash is not None:
        gene2 = {"gene_id": "gene_002", "start": 1000, "end": 1900, "strand": "-", "role": "tailoring"}
        if second_gene_hash:
            gene2["protein_sha256"] = second_gene_hash
        genes.append(gene2)
    record = dict(IDENT, genes=genes, canonical_gene_count=len(genes),
                  boundary={"status": "COMPLETE", "note": ""})
    locus = tmp_path / "locus.json"
    locus.write_text(json.dumps(record))
    evidence = tmp_path / "evidence.tsv"
    with evidence.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t",
                                fieldnames=list(IDENT) + ["gene_id", "protein_sha256"])
        writer.writeheader()
        for gene in genes:
            writer.writerow(dict(IDENT, gene_id=gene["gene_id"], protein_sha256=evidence_hash))
    return locus, evidence


def test_fully_hash_bound_run_is_labelled(tmp_path):
    locus, evidence = build(tmp_path, TRUE_HASH, TRUE_HASH)
    receipt = build_deep_report(locus, tmp_path / "out", evidence)
    binding = receipt["protein_hash_binding"]
    assert binding["state"] == "PROTEIN_HASH_BOUND"
    assert binding["evidence_rows_hash_compared"] == binding["evidence_rows_total"] == 1


def test_identity_only_run_is_labelled_differently(tmp_path):
    """The case the receipt previously could not express."""
    locus, evidence = build(tmp_path, None, OTHER_HASH)
    receipt = build_deep_report(locus, tmp_path / "out", evidence)
    binding = receipt["protein_hash_binding"]
    assert binding["state"] == "EXACT_IDENTITY_BOUND_ONLY"
    assert binding["evidence_rows_hash_compared"] == 0
    assert binding["canonical_genes_carrying_hash"] == 0


def test_partial_binding_is_not_reported_as_full(tmp_path):
    locus, evidence = build(tmp_path, TRUE_HASH, TRUE_HASH, second_gene_hash="")
    receipt = build_deep_report(locus, tmp_path / "out", evidence)
    binding = receipt["protein_hash_binding"]
    assert binding["state"] == "PARTIALLY_PROTEIN_HASH_BOUND"
    assert binding["evidence_rows_hash_compared"] == 1
    assert binding["evidence_rows_total"] == 2


def test_no_evidence_is_its_own_state(tmp_path):
    locus, _ = build(tmp_path, TRUE_HASH, TRUE_HASH)
    receipt = build_deep_report(locus, tmp_path / "out", None)
    assert receipt["protein_hash_binding"]["state"] == "NO_EVIDENCE_SUPPLIED"


def test_two_runs_are_distinguishable_by_receipt_alone(tmp_path):
    """The load-bearing property: a consumer reading only the receipt can tell."""
    a_locus, a_ev = build(tmp_path / "a", TRUE_HASH, TRUE_HASH)
    b_locus, b_ev = build(tmp_path / "b", None, OTHER_HASH)
    a = build_deep_report(a_locus, tmp_path / "a/out", a_ev)
    b = build_deep_report(b_locus, tmp_path / "b/out", b_ev)
    assert a["evidence_row_count"] == b["evidence_row_count"]
    assert a["canonical_gene_count"] == b["canonical_gene_count"]
    assert a["boundary_status"] == b["boundary_status"]
    assert a["protein_hash_binding"]["state"] != b["protein_hash_binding"]["state"], (
        "both runs are identical on every other receipt field; without the "
        "binding state a consumer cannot tell them apart"
    )


def test_documented_refusal_still_fires(tmp_path):
    """Policy is unchanged: a supplied hash that disagrees still fails closed."""
    locus, evidence = build(tmp_path, TRUE_HASH, OTHER_HASH)
    with pytest.raises(DeepBGCReportError, match="protein hash mismatch"):
        build_deep_report(locus, tmp_path / "out", evidence)


@pytest.fixture(autouse=True)
def _mkdirs(tmp_path):
    for sub in ("a", "b"):
        (tmp_path / sub).mkdir(exist_ok=True)
