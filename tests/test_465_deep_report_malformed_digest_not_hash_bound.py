"""Equal text that is not a SHA-256 digest must not make a deep report read PROTEIN_HASH_BOUND."""
from __future__ import annotations
import csv
import json

from mamey.deep_bgc_report import build_deep_report

IDENT = {"strain": "SYN-1", "full_node_or_contig": "contig_0001_complete",
         "region": "region001", "bgc_alias": "BGC007"}


def _build(tmp_path, hashes):
    genes = [{"gene_id": f"gene_{i:03d}", "start": 1 + 1000 * i, "end": 900 + 1000 * i, "strand": "+",
              "role": "core", "protein_sha256": h} for i, h in enumerate(hashes)]
    record = dict(IDENT, genes=genes, canonical_gene_count=len(genes), boundary={"status": "COMPLETE", "note": ""})
    locus = tmp_path / "locus.json"
    locus.write_text(json.dumps(record))
    ev = tmp_path / "evidence.tsv"
    with ev.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=list(IDENT) + ["gene_id", "protein_sha256"])
        writer.writeheader()
        for gene in genes:
            writer.writerow(dict(IDENT, gene_id=gene["gene_id"], protein_sha256=gene["protein_sha256"]))
    return build_deep_report(locus, tmp_path / "out", ev)["protein_hash_binding"]


def test_equal_placeholder_text_is_admitted_but_not_hash_bound(tmp_path):
    binding = _build(tmp_path, ["pending"])
    assert binding["state"] == "EXACT_IDENTITY_BOUND_ONLY"
    assert binding["evidence_rows_hash_compared"] == 0
    assert binding["evidence_rows_hash_malformed"] == 1


def test_one_malformed_digest_makes_the_report_partial(tmp_path):
    binding = _build(tmp_path, ["a" * 64, "a" * 63])
    assert binding["state"] == "PARTIALLY_PROTEIN_HASH_BOUND"
    assert (binding["evidence_rows_hash_compared"], binding["evidence_rows_hash_malformed"]) == (1, 1)


def test_well_formed_digests_stay_hash_bound_and_say_how_they_were_compared(tmp_path):
    binding = _build(tmp_path, ["a" * 64, "B" * 64])
    assert binding["state"] == "PROTEIN_HASH_BOUND"
    assert binding["evidence_rows_hash_malformed"] == 0
    assert binding["comparison"] == "TEXT_EQUALITY_OF_SUPPLIED_SHA256_NOT_RECOMPUTED_FROM_SEQUENCE"
