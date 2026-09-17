import csv
import json
from pathlib import Path

import pytest

from mamey.protein_signature import SignatureError, compare, main, package_signature, signature


def test_sequence_multiset_distinguishes_relabeling_from_changed_assembly(tmp_path):
    a = tmp_path / "a.faa"
    b = tmp_path / "b.faa"
    c = tmp_path / "c.faa"
    a.write_text(">ctg1_1\nMKTA\n>ctg1_2\nMKTA\n>ctg1_3\nGHI*\n")
    b.write_text(">ctg9_3\nGHI\n>ctg9_1\nMKTA\n>ctg9_2\nMKTA\n")
    c.write_text(">ctg9_3\nGHI\n>ctg9_1\nMKTA\n>ctg9_2\nMKTG\n")
    assert compare(a, b)["state"] == "SAME_SEQUENCE_MULTISET_RELABELED"
    assert compare(a, b)["shared_sequence_copies"] == 3
    assert compare(a, c)["state"] == "PARTIAL_OR_DIFFERENT"
    assert compare(a, c)["shared_sequence_copies"] == 2


def test_query_gene_field_binds_to_package_sequence(tmp_path):
    package = tmp_path / "package.faa"
    query = tmp_path / "query.faa"
    package.write_text(">ctg101_3 bgc=BGC001\nMQWERT\n")
    query.write_text(">AS-XXX|BGC012|slot=1|gene=ctg101_3|node=NODE_1|region=region001\nMQWERT\n")
    result = compare(query, package)
    assert result["state"] == "EXACT_GENE_AND_SEQUENCE"
    assert result["same_gene_and_sequence"] == 1


def test_duplicate_gene_refuses_without_writing(tmp_path):
    bad = tmp_path / "bad.faa"
    good = tmp_path / "good.faa"
    out = tmp_path / "comparison.json"
    bad.write_text(">ctg1_1\nAAA\n>ctg1_1\nBBB\n")
    good.write_text(">ctg1_1\nAAA\n")
    with pytest.raises(SignatureError, match="Duplicate gene label"):
        signature(bad)
    with pytest.raises(SystemExit):
        main([str(bad), str(good), "--out", str(out)])
    assert not out.exists()


def test_same_display_label_does_not_hide_changed_sequence(tmp_path):
    first = tmp_path / "first.faa"
    second = tmp_path / "second.faa"
    first.write_text(">ctg1_1\nAAA\n")
    second.write_text(">ctg1_1\nAAG\n")
    result = compare(first, second)
    assert result["state"] == "PARTIAL_OR_DIFFERENT"
    assert result["same_gene_changed_sequence"] == 1
    assert result["claim_ceiling"].startswith("Protein provenance")


def test_exact_query_subset_is_reported_without_claiming_whole_assembly_identity(tmp_path):
    query = tmp_path / "query.faa"
    assembly = tmp_path / "assembly.faa"
    query.write_text(">ctg1_1\nAAA\n")
    assembly.write_text(">ctg1_1\nAAA\n>ctg1_2\nBBB\n")
    result = compare(query, assembly)
    assert result["state"] == "LEFT_GENE_SEQUENCE_SUBSET"
    assert result["same_gene_and_sequence"] == 1
    assert result["right_only_gene_labels"] == 1


def test_package_signature_keeps_full_locus_and_input_identity(tmp_path):
    strain = "TEST"
    (tmp_path / "manifest.json").write_text(json.dumps({
        "strain_id": strain, "input_zip_sha256": "a" * 64,
        "bgcs": [
            {"contig": "NODE_1_length_100_cov_22.5", "antismash_region": "region001", "bgc_id": "BGC001"},
            {"contig": "NODE_2_length_200_cov_24.1", "antismash_region": "region002", "bgc_id": "BGC002"},
        ],
    }))
    (tmp_path / "TEST_proteins.faa").write_text(">g1 bgc=BGC001\nMKTA*\n>g2 bgc=BGC002\nAAAC\n")
    with (tmp_path / "TEST_cds_table.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["strain", "contig", "region", "bgc_id", "locus_tag"])
        writer.writeheader()
        writer.writerow({"strain": strain, "contig": "NODE_1_length_100_cov_22.5", "region": "region001", "bgc_id": "BGC001", "locus_tag": "g1"})
        writer.writerow({"strain": strain, "contig": "NODE_2_length_200_cov_24.1", "region": "region002", "bgc_id": "BGC002", "locus_tag": "g2"})
    out = tmp_path / "signature.json"
    assert main(["--package", str(tmp_path), "--out", str(out)]) == 0
    result = json.loads(out.read_text())
    assert result == package_signature(tmp_path)
    assert result["scope"] == "BGC_MEMBER_PROTEINS_ONLY"
    assert result["input_zip_sha256"] == "a" * 64
    assert result["proteins"][0]["loci"] == [{"strain": "TEST", "contig": "NODE_1_length_100_cov_22.5", "region": "region001", "bgc_alias": "BGC001"}]
    assert result["proteins"][0]["aa_length"] == 4
    assert not any("/" in value for key, value in result.items() if key in {"protein_fasta", "cds_table"})


def test_package_signature_refuses_unbound_fasta_gene(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"strain_id": "TEST", "input_zip_sha256": "a" * 64,
        "bgcs": [{"contig": "NODE_1", "antismash_region": "region001", "bgc_id": "BGC001"}]}))
    (tmp_path / "TEST_proteins.faa").write_text(">g1\nMKTA\n")
    (tmp_path / "TEST_cds_table.csv").write_text("strain,contig,region,bgc_id,locus_tag\n")
    with pytest.raises(SignatureError, match="lack complete CDS identity"):
        package_signature(tmp_path)


def test_package_signature_refuses_cds_locus_drift(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"strain_id": "TEST", "input_zip_sha256": "a" * 64,
        "bgcs": [{"contig": "NODE_1", "antismash_region": "region001", "bgc_id": "BGC001"}]}))
    (tmp_path / "TEST_proteins.faa").write_text(">g1\nMKTA\n")
    (tmp_path / "TEST_cds_table.csv").write_text("strain,contig,region,bgc_id,locus_tag\nTEST,NODE_2,region001,BGC001,g1\n")
    with pytest.raises(SignatureError, match="differs from manifest"):
        package_signature(tmp_path)
