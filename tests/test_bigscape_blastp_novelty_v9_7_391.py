import csv
import importlib.util
import json
from pathlib import Path

import pytest


TOOL = Path(__file__).resolve().parents[1] / "tools" / "bigscape_blastp_novelty.py"
SPEC = importlib.util.spec_from_file_location("mibig_protein_context", TOOL)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def _strict_enrichment_fixture(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "strict_gene_modeb_enrichment", TOOL.with_name("gene_modeb_enrichment.py"),
    )
    enrichment = importlib.util.module_from_spec(spec); spec.loader.exec_module(enrichment)
    identity = "REF-001 / NODE_7_length_50000_cov_20.5 / region001 / BGC001"
    source_manifest = tmp_path / "db_source_manifest.tsv"
    source_manifest.write_text("source_gbk\tsha256\nBGC0000001.gbk\t" + "1" * 64 + "\n")
    metadata = tmp_path / "db_metadata.tsv"
    metadata.write_text("subject_id\tprotein_sha256\nref\t" + "2" * 64 + "\n")
    receipt = tmp_path / "db_build_receipt.json"
    receipt.write_text(json.dumps({
        "schema": "mibig_protein_context_db_v1", "mibig_release": "test-release",
        "metadata_sha256": MOD._sha_file(metadata), "source_manifest": str(source_manifest),
        "source_manifest_sha256": MOD._sha_file(source_manifest),
    }) + "\n")
    query_sha = MOD._sha_text("A" * 100)
    roster = tmp_path / "roster.tsv"
    roster.write_text(
        "complete_identity\tgene\tlength_aa\ttranslation_sha256\n"
        f"{identity}\tctg1_5\t100\t{query_sha}\n"
    )
    result = tmp_path / "context.tsv"
    with result.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=MOD.FIELDS, delimiter="\t")
        writer.writeheader(); writer.writerow({
            "query_id": "ctg1_5", "query_sha256": query_sha, "query_aa_length": 100,
            "hit_rank": 1, "mibig_accession": "BGC0000001", "pct_identity": "71.200",
            "query_coverage_pct": "96.000", "subject_coverage_pct": "90.000",
            "evalue": "1e-60", "evidence_state": "MIBIG_PROTEIN_HOMOLOG",
            "bounded_interpretation": "protein homology supports class or role context only",
            "database_metadata": f"{metadata};sha256={MOD._sha_file(metadata)}",
            "database_receipt": f"{receipt};sha256={MOD._sha_file(receipt)}",
        })
    return enrichment, identity, source_manifest, metadata, receipt, roster, result


def _metadata(sequence="M" * 100):
    return {
        "MIBIG__BGC0000001__refA__1": {
            "mibig_accession": "BGC0000001",
            "locus_tag": "refA",
            "product": "reference enzyme",
            "protein_sha256": MOD._sha_text(sequence),
        }
    }


def test_pident_is_identity_and_exact_match_requires_sha_and_full_coverage():
    query = "M" * 100
    blast = "q1\tMIBIG__BGC0000001__refA__1\t100\t100\t100\t100\t100\t1\t100\t1\t100\t0\t250"
    row = MOD.parse_blast_rows(blast, [("q1", query)], _metadata(query), 60.0, 1e-5)[0]
    assert row["pct_identity"] == "100.000"
    assert row["evidence_state"] == "EXACT_SEQUENCE_MATCH_TO_MIBIG_PROTEIN"
    assert "cluster/product equivalence not established" in row["bounded_interpretation"]


def test_tiny_high_identity_alignment_is_partial_not_self_hit():
    query = "A" * 100
    blast = "q1\tMIBIG__BGC0000001__refA__1\t99\t99\t20\t100\t100\t1\t20\t1\t20\t1e-20\t80"
    row = MOD.parse_blast_rows(blast, [("q1", query)], _metadata("M" * 100), 60.0, 1e-5)[0]
    assert row["query_coverage_pct"] == "20.000"
    assert row["evidence_state"] == "PARTIAL_OR_LOW_BIDIRECTIONAL_COVERAGE_HIT"
    assert "self-hit" not in row["bounded_interpretation"]


def test_low_identity_full_coverage_is_bounded_divergence_prior_not_novelty_claim():
    query = "A" * 100
    blast = "q1\tMIBIG__BGC0000001__refA__1\t40\t55\t100\t100\t100\t1\t100\t1\t100\t1e-30\t110"
    row = MOD.parse_blast_rows(blast, [("q1", query)], _metadata(), 60.0, 1e-5)[0]
    assert row["evidence_state"] == "DISTANT_MIBIG_PROTEIN_CONTEXT"
    assert "novelty prior, not proof" in row["bounded_interpretation"]
    assert "genuinely novel" not in row["bounded_interpretation"]


def test_low_subject_coverage_is_partial_even_when_query_coverage_is_complete():
    query = "A" * 100
    metadata = _metadata("M" * 1000)
    blast = "q1\tMIBIG__BGC0000001__refA__1\t70\t80\t100\t100\t1000\t1\t100\t1\t100\t1e-30\t200"
    row = MOD.parse_blast_rows(blast, [("q1", query)], metadata, 60.0, 1e-5)[0]
    assert row["query_coverage_pct"] == "100.000"
    assert row["subject_coverage_pct"] == "10.000"
    assert row["evidence_state"] == "PARTIAL_OR_LOW_BIDIRECTIONAL_COVERAGE_HIT"


def test_every_query_is_emitted_and_no_hit_is_not_biological_absence():
    rows = MOD.parse_blast_rows("", [("q1", "AAA"), ("q2", "CCC")], {}, 60.0, 1e-5)
    assert [row["query_id"] for row in rows] == ["q1", "q2"]
    assert all(row["evidence_state"] == "NO_ADMITTED_MIBIG_PROTEIN_HIT" for row in rows)
    assert all("not biological absence" in row["bounded_interpretation"] for row in rows)


def test_best_hit_is_ranked_by_bitscore_not_percent_identity():
    query = "A" * 100
    metadata = _metadata()
    metadata["MIBIG__BGC0000002__refB__1"] = {
        "mibig_accession": "BGC0000002", "locus_tag": "refB", "product": "other",
        "protein_sha256": MOD._sha_text("C" * 100),
    }
    blast = "\n".join([
        "q1\tMIBIG__BGC0000001__refA__1\t95\t97\t60\t100\t100\t1\t60\t1\t60\t1e-20\t100",
        "q1\tMIBIG__BGC0000002__refB__1\t70\t80\t100\t100\t100\t1\t100\t1\t100\t1e-60\t220",
    ])
    rows = MOD.parse_blast_rows(blast, [("q1", query)], metadata, 60.0, 1e-5)
    assert rows[0]["mibig_accession"] == "BGC0000002"
    assert rows[0]["hit_rank"] == 1


def test_modeb_renderer_routes_stream_without_turning_it_into_product_novelty(tmp_path):
    result = tmp_path / "context.tsv"
    with result.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=MOD.FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerow({
            "query_id": "geneA", "hit_rank": 1, "mibig_accession": "BGC0000001",
            "subject_locus_tag": "refA", "pct_identity": "72.000",
            "query_coverage_pct": "95.000", "subject_coverage_pct": "91.000",
            "evalue": "1e-50", "evidence_state": "MIBIG_PROTEIN_HOMOLOG",
            "bounded_interpretation": "protein homology supports class or role context only",
        })
    out = tmp_path / "modeb.md"
    text = MOD.render_modeb(str(result), str(out))
    assert "Mode B §4" in text and "§24" in text and "§28" in text
    assert "% identity" in text
    assert "do not establish the BGC product" in text
    assert "genuinely novel" not in text


def test_modeb_renderer_escapes_untrusted_markdown_cells(tmp_path):
    result = tmp_path / "context.tsv"
    with result.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=MOD.FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerow({
            "query_id": "gene|injected", "query_sha256": MOD._sha_text("AAA"),
            "query_aa_length": 3, "hit_rank": 0,
            "evidence_state": "NO_ADMITTED_MIBIG_PROTEIN_HIT",
            "bounded_interpretation": "typed | display",
        })
    text = MOD.render_modeb(str(result), str(tmp_path / "modeb.md"))
    line = next(line for line in text.splitlines() if "gene\\|injected" in line)
    assert "typed \\| display" in line
    assert line.count("|") == 11  # nine columns plus the two escaped source pipes


def test_database_builder_default_retains_small_ripp_scale_cds(tmp_path, monkeypatch):
    from mamey._gbk_shim import SeqIO

    monkeypatch.setattr(MOD, "_seqio", lambda: SeqIO)
    gbk = tmp_path / "BGC0009999.gbk"
    gbk.write_text(
        "LOCUS       BGC0009999 300 bp\n"
        "FEATURES             Location/Qualifiers\n"
        "     CDS             1..120\n"
        "                     /locus_tag=\"small_precursor\"\n"
        "                     /product=\"precursor peptide\"\n"
        "                     /translation=\"MAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\"\n"
        "ORIGIN\n//\n",
        encoding="utf-8",
    )
    rows = list(MOD.iter_mibig_proteins(tmp_path))
    assert len(rows) == 1
    assert rows[0]["locus_tag"] == "small_precursor"
    assert rows[0]["aa_length"] == 40


def test_portable_locator_does_not_embed_personal_absolute_root(tmp_path):
    artifact = tmp_path / "db" / "mibig_metadata.tsv"
    artifact.parent.mkdir(); artifact.write_text("header\n")
    locator = MOD._portable_locator(artifact, tmp_path / "results")
    assert not Path(locator).is_absolute()
    assert str(tmp_path) not in locator


def test_gene_modeb_enrichment_prefers_sequence_bound_tsv_over_manual_scalar(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "gene_modeb_enrichment",
        TOOL.with_name("gene_modeb_enrichment.py"),
    )
    enrichment = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(enrichment)
    identity = "REF-001 / NODE_7_length_50000_cov_20.5 / region001 / BGC001"
    source_manifest = tmp_path / "db_source_manifest.tsv"
    source_manifest.write_text("source_gbk\tsha256\nBGC0000001.gbk\t" + "1" * 64 + "\n")
    metadata = tmp_path / "db_metadata.tsv"
    metadata.write_text("subject_id\tprotein_sha256\nref\t" + "2" * 64 + "\n")
    receipt = tmp_path / "db_build_receipt.json"
    receipt.write_text(json.dumps({
        "schema": "mibig_protein_context_db_v1", "mibig_release": "test-release",
        "metadata_sha256": MOD._sha_file(metadata), "source_manifest": str(source_manifest),
        "source_manifest_sha256": MOD._sha_file(source_manifest),
    }) + "\n")
    roster = tmp_path / "roster.tsv"
    query_sha = MOD._sha_text("A" * 100)
    roster.write_text(
        "complete_identity\tgene\tlength_aa\ttranslation_sha256\n"
        f"{identity}\tctg1_5\t100\t{query_sha}\n"
    )
    result = tmp_path / "context.tsv"
    with result.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=MOD.FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerow({
            "query_id": "ctg1_5", "query_sha256": query_sha, "query_aa_length": 100,
            "hit_rank": 1, "mibig_accession": "BGC0000001",
            "pct_identity": "71.200", "query_coverage_pct": "96.000",
            "subject_coverage_pct": "90.000", "evalue": "1e-60",
            "evidence_state": "MIBIG_PROTEIN_HOMOLOG",
            "bounded_interpretation": "protein homology supports class or role context only",
            "database_metadata": f"{metadata};sha256={MOD._sha_file(metadata)}",
            "database_receipt": f"{receipt};sha256={MOD._sha_file(receipt)}",
        })
    rows = enrichment._mibig_context_rows(
        result, expected_tsv_sha256=MOD._sha_file(result), roster_path=roster,
        expected_roster_sha256=MOD._sha_file(roster), complete_identity=identity,
    )
    assert rows[0]["query_id"] == "ctg1_5"
    assert rows[0]["query_coverage_pct"] == "96.000"


def test_gene_modeb_section_displays_complete_four_part_identity(tmp_path, monkeypatch):
    enrichment, identity, _, _, _, roster, result = _strict_enrichment_fixture(tmp_path)
    monkeypatch.setattr(enrichment.GAL, "catalog_region", lambda _: [{
        "gene": "ctg1_5", "modules": 1, "kind": "NRPS", "complete": True,
    }])
    monkeypatch.setattr(enrichment.NS, "region_signature", lambda _: ([], "", {}))
    text = enrichment.make_section(
        str(tmp_path / "NODE_7_length_50000_cov_20.5.region001.gbk"),
        mibig_protein_tsv=str(result),
        mibig_protein_tsv_sha256=MOD._sha_file(result),
        mibig_protein_roster=str(roster),
        mibig_protein_roster_sha256=MOD._sha_file(roster),
        complete_identity=identity,
    )
    assert f"Locus {identity}." in text


def test_gene_modeb_enrichment_rejects_unbound_three_column_tsv(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "gene_modeb_enrichment", TOOL.with_name("gene_modeb_enrichment.py"),
    )
    enrichment = importlib.util.module_from_spec(spec); spec.loader.exec_module(enrichment)
    result = tmp_path / "unbound.tsv"
    result.write_text("query_id\thit_rank\tevidence_state\nmade_up\t1\tMIBIG_PROTEIN_HOMOLOG\n")
    roster = tmp_path / "roster.tsv"; roster.write_text("complete_identity\tgene\tlength_aa\ttranslation_sha256\n")
    with pytest.raises(ValueError, match="required columns|no rows"):
        enrichment._mibig_context_rows(
            result, expected_tsv_sha256=MOD._sha_file(result), roster_path=roster,
            expected_roster_sha256=MOD._sha_file(roster),
            complete_identity="REF-001 / NODE_7_length_50000_cov_20.5 / region001 / BGC001",
        )


def test_gene_modeb_enrichment_rejects_database_receipt_drift(tmp_path):
    enrichment, identity, _, _, receipt, roster, result = _strict_enrichment_fixture(tmp_path)
    receipt.write_text('{"schema":"tampered"}\n')
    with pytest.raises(ValueError, match="database receipt path is missing or hash-drifted"):
        enrichment._mibig_context_rows(
            result, expected_tsv_sha256=MOD._sha_file(result), roster_path=roster,
            expected_roster_sha256=MOD._sha_file(roster), complete_identity=identity,
        )


def test_gene_modeb_enrichment_rejects_roster_hash_or_query_mismatch(tmp_path):
    enrichment, identity, _, _, _, roster, result = _strict_enrichment_fixture(tmp_path)
    original_sha = MOD._sha_file(roster)
    roster.write_text(roster.read_text().replace("\t100\t", "\t99\t"))
    with pytest.raises(ValueError, match="protein roster is missing or hash-drifted"):
        enrichment._mibig_context_rows(
            result, expected_tsv_sha256=MOD._sha_file(result), roster_path=roster,
            expected_roster_sha256=original_sha, complete_identity=identity,
        )
