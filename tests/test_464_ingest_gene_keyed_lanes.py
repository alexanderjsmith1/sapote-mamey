"""Card 464_ingest_gene_keyed_lanes: --rekey-by-locus reads gene-keyed gap-lane troves.

Single-protein ClusteredNR gap lanes keep results in one folder per query panel (not BGC folders), write gene IDs
such as 'AS-TEST__ctg109_3', and leave aa_length blank. With query roots, a blank length is taken from the query
FASTA the lane ledger names, only when its bytes match the ledger's query_sha256 and its sequence equals the
package protein. Synthetic IDs only."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from mamey.blastp_ingest import ingest_blastp_trove

SEQ = "M" + "A" * 299


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        w = csv.DictWriter(handle, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def _package(tmp_path: Path) -> Path:
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "AS-TEST"}), encoding="utf-8")
    records = [{"bgc_id": "BGC001", "cds": [{"locus_tag": "ctg101_1", "aa_length": 210}]},
               {"bgc_id": "BGC002", "cds": [{"locus_tag": "ctg109_3", "aa_length": 300}]}]
    (pkg / "AS-TEST_gene_context.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    _write_csv(pkg / "AS-TEST_cds_table.csv",
               [{"strain": "AS-TEST", "bgc_id": "BGC001", "locus_tag": "ctg101_1", "length_aa": "210"},
                {"strain": "AS-TEST", "bgc_id": "BGC002", "locus_tag": "ctg109_3", "length_aa": "300"}])
    (pkg / "AS-TEST_proteins.faa").write_text(f">ctg101_1\n{'M' * 210}\n>ctg109_3\n{SEQ}\n", encoding="utf-8")
    return pkg


def _lane(tmp_path: Path, gene: str = "ctg109_3", aa: str = "", query_seq: str = SEQ, ledger_sha: str | None = None):
    """A gene-keyed lane (<lane>/results/AS-TEST/<panel>/...) with its ledger, and its queue folder."""
    panel = "AS-TEST_gapK_p0001"
    queue = tmp_path / "queue"
    qfile = queue / "AS-TEST" / panel / "AS-TEST__gapK__ctg109_3.faa"
    qfile.parent.mkdir(parents=True)
    qfile.write_bytes(f">ctg109_3\n{query_seq}\n".encode())
    lane = tmp_path / "lane"
    _write_csv(lane / "results" / "AS-TEST" / panel / f"{panel}_top_hit_per_gene.csv",
               [{"strain": "AS-TEST", "bgc_id": panel, "gene": gene, "aa_length": aa, "hit_rank": "1",
                 "subject_acc": "WP_1", "subject_organism": "Example bacterium", "subject_def": "hypothetical protein",
                 "pct_identity": "71.5", "evalue": "1e-50", "bitscore": "200"}])
    _write_csv(lane / "_ledger.csv",
               [{"strain": "AS-TEST", "bgc": panel, "file": f"AS-TEST/{panel}/AS-TEST__gapK__ctg109_3.faa",
                 "status": "fetched", "query_sha256": ledger_sha or hashlib.sha256(qfile.read_bytes()).hexdigest()}])
    return lane / "results", queue


def _overlay(pkg: Path, bgc: str) -> list[dict]:
    path = pkg / "blastp_online" / f"{bgc}_online_blastp.csv"
    return list(csv.DictReader(path.open())) if path.exists() else []


def test_bound_query_supplies_the_length(tmp_path):
    pkg = _package(tmp_path); trove, queue = _lane(tmp_path)
    res = ingest_blastp_trove(pkg, trove, "clustered_nr", "AS-TEST", rekey_by_locus=True, query_roots=[queue])
    assert res["query_length_binding"] == {"LENGTH_FROM_LEDGER_BOUND_QUERY": 1}
    rows = _overlay(pkg, "BGC002")
    assert [(r["locus_tag"], r["aa_length"], r["channel"]) for r in rows] == [("ctg109_3", "300", "clustered_nr")]


def test_composite_gene_id_is_reduced_to_the_locus(tmp_path):
    pkg = _package(tmp_path); trove, queue = _lane(tmp_path, gene="AS-TEST__ctg109_3 aa=300 why=t1", aa="300")
    ingest_blastp_trove(pkg, trove, "clustered_nr", "AS-TEST", rekey_by_locus=True)
    assert [r["locus_tag"] for r in _overlay(pkg, "BGC002")] == ["ctg109_3"]


def test_query_differing_from_package_protein_is_held(tmp_path):
    pkg = _package(tmp_path); trove, queue = _lane(tmp_path, query_seq="M" + "C" * 299)
    res = ingest_blastp_trove(pkg, trove, "clustered_nr", "AS-TEST", rekey_by_locus=True, query_roots=[queue])
    assert res["query_length_binding"] == {"QUERY_SEQUENCE_DIFFERS_FROM_PACKAGE": 1}
    assert res["genes"] == 0 and not _overlay(pkg, "BGC002")
    reasons = {r["reason"] for r in csv.DictReader(open(res["quarantine"]))}
    assert reasons == {"QUERY_SEQUENCE_DIFFERS_FROM_PACKAGE"}


def test_ledger_hash_mismatch_keeps_the_blank_length_hold(tmp_path):
    pkg = _package(tmp_path); trove, queue = _lane(tmp_path, ledger_sha="0" * 64)
    res = ingest_blastp_trove(pkg, trove, "clustered_nr", "AS-TEST", rekey_by_locus=True, query_roots=[queue])
    assert res["query_length_binding"] == {"QUERY_FILE_HASH_MISMATCH": 1}
    assert res["genes"] == 0
    assert {r["reason"] for r in csv.DictReader(open(res["quarantine"]))} == {"ZERO_OR_BLANK_AA_LENGTH"}


def test_without_query_roots_a_blank_length_is_still_held(tmp_path):
    pkg = _package(tmp_path); trove, _ = _lane(tmp_path)
    res = ingest_blastp_trove(pkg, trove, "clustered_nr", "AS-TEST", rekey_by_locus=True)
    assert res["genes"] == 0 and res["query_length_binding"] == {}


def test_query_roots_require_rekey(tmp_path):
    pkg = _package(tmp_path); trove, queue = _lane(tmp_path)
    with pytest.raises(ValueError, match="rekey_by_locus"):
        ingest_blastp_trove(pkg, trove, "clustered_nr", "AS-TEST", query_roots=[queue])


def test_strict_mode_still_ignores_panel_folders(tmp_path):
    pkg = _package(tmp_path); trove, _ = _lane(tmp_path, aa="300")
    res = ingest_blastp_trove(pkg, trove, "clustered_nr", "AS-TEST")
    assert res.get("status") == "NO_SOURCES_DISCOVERED"
