"""Enhancement (Aquarius .436): a receipt must surface when an evidence row SUPPLIED a
protein hash the canonical gene had none to check against — the exact case Black Cherry-3
demonstrated. Admission stays the documented accept-when-optional behaviour; the claimed-but-
unverifiable hash is made visible (evidence_rows_hash_unverifiable) instead of refused."""
from __future__ import annotations
import csv, json
from mamey.deep_bgc_report import build_deep_report

IDENT = {"strain": "SYN-1", "full_node_or_contig": "contig_0001_complete",
         "region": "region001", "bgc_alias": "BGC007"}

def build(tmp_path, canonical_hash, evidence_hash):
    gene = {"gene_id": "gene_001", "start": 1, "end": 900, "strand": "+", "role": "core"}
    if canonical_hash:
        gene["protein_sha256"] = canonical_hash
    record = dict(IDENT, genes=[gene], canonical_gene_count=1, boundary={"status": "COMPLETE", "note": ""})
    locus = tmp_path / "locus.json"; locus.write_text(json.dumps(record))
    ev = tmp_path / "evidence.tsv"
    with ev.open("w", newline="") as h:
        w = csv.DictWriter(h, delimiter="\t", fieldnames=list(IDENT) + ["gene_id", "protein_sha256"])
        w.writeheader(); w.writerow(dict(IDENT, gene_id="gene_001", protein_sha256=evidence_hash))
    return locus, ev

def test_supplied_hash_for_hashless_gene_is_surfaced(tmp_path):
    """BC-3's bogus-evidence case: accepted, but the receipt flags it as unverifiable."""
    locus, ev = build(tmp_path, None, "c" * 64)
    r = build_deep_report(locus, tmp_path / "out", ev)["protein_hash_binding"]
    assert r["evidence_rows_hash_unverifiable"] == 1
    assert r["evidence_rows_hash_compared"] == 0
    assert r["state"] == "EXACT_IDENTITY_BOUND_ONLY"   # admission unchanged

def test_hashless_gene_with_no_supplied_hash_is_not_flagged(tmp_path):
    locus, ev = build(tmp_path, None, "")
    r = build_deep_report(locus, tmp_path / "out", ev)["protein_hash_binding"]
    assert r["evidence_rows_hash_unverifiable"] == 0

def test_fully_bound_run_has_zero_unverifiable(tmp_path):
    locus, ev = build(tmp_path, "a" * 64, "a" * 64)
    r = build_deep_report(locus, tmp_path / "out", ev)["protein_hash_binding"]
    assert r["evidence_rows_hash_unverifiable"] == 0
    assert r["state"] == "PROTEIN_HASH_BOUND"
