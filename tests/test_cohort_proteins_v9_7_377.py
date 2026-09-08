import csv
import json
import sqlite3
from pathlib import Path

import pytest

from mamey.cohort_proteins import build_catalog, compare_catalog


def _write_package(root: Path, strain: str, node: str, region: str, alias: str,
                   proteins: list[tuple[str, str, str]]) -> Path:
    package = root / strain / "package"
    package.mkdir(parents=True)
    (package / f"{strain}_1_intake.json").write_text(
        json.dumps({"strain_id": strain}) + "\n", encoding="utf-8"
    )
    with (package / f"{strain}_2_inventory.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["BGC_ID", "Contig", "antiSMASH_Region"])
        writer.writeheader()
        writer.writerow({"BGC_ID": alias, "Contig": node, "antiSMASH_Region": region})
    with (package / f"{strain}_proteins.faa").open("w", encoding="utf-8") as handle:
        for gene, _, sequence in proteins:
            handle.write(f">{gene} bgc={alias}\n{sequence}\n")
    fields = [
        "bgc_id", "rank", "locus_tag", "cds_start", "cds_end", "strand",
        "product_qualifier", "gene_function_inference", "sec_met_domains",
        "edge_core_overlap", "resistance_tier",
    ]
    with (package / f"{strain}_gene_by_gene_all_bgcs.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for rank, (gene, role, sequence) in enumerate(proteins, 1):
            writer.writerow({
                "bgc_id": alias, "rank": rank, "locus_tag": gene,
                "cds_start": rank * 100, "cds_end": rank * 100 + len(sequence) * 3,
                "strand": "+", "product_qualifier": role,
                "gene_function_inference": role, "sec_met_domains": "",
                "edge_core_overlap": "core" if "core" in role else "",
                "resistance_tier": "T2" if "resistance" in role else "",
            })
    return package


def test_build_catalog_preserves_full_identity_and_cohort_denominators(tmp_path):
    as_root, sid_root = tmp_path / "as", tmp_path / "sid"
    _write_package(as_root, "AS-A", "NODE_1_length_999_cov_1.0", "region001", "BGC001", [
        ("a1", "core synthase", "MKTAYIAKQRQISFVKSHFSRQDILDLWIYHTQGYFP"),
    ])
    _write_package(as_root, "AS-B", "NODE_2_length_888_cov_2.0", "region002", "BGC004", [
        ("b1", "core synthase", "MKTAYIAKQRQISFVKSHFSRQDILDLWVYHTQGYFP"),
    ])
    _write_package(sid_root, "SID9", "WWAA01000001.1", "region003", "BGC007", [
        ("s1", "core synthase", "MKTAYIAKQRQISFVKSHFSRQDILDLWIYHTQGYFA"),
    ])
    database = tmp_path / "catalog.sqlite"
    receipt = build_catalog([("AS", as_root), ("SID", sid_root)], database)
    assert receipt["status"] == "PASS"
    assert receipt["cohorts"]["AS"]["distinct_strains"] == 2
    assert receipt["cohorts"]["SID"]["distinct_strains"] == 1
    con = sqlite3.connect(database)
    displays = {row[0] for row in con.execute("SELECT exact_locus FROM protein_occurrence")}
    con.close()
    assert "AS-A / NODE_1_length_999_cov_1.0 / region001 / BGC001" in displays
    assert "SID9 / WWAA01000001.1 / region003 / BGC007" in displays


def test_compare_keeps_count_first_closest_hits_and_excludes_query_strain(tmp_path):
    as_root, sid_root = tmp_path / "as", tmp_path / "sid"
    query_pkg = _write_package(as_root, "AS-A", "NODE_1_length_999_cov_1.0", "region001", "BGC001", [
        ("a1", "core synthase", "MKTAYIAKQRQISFVKSHFSRQDILDLWIYHTQGYFP"),
        ("a2", "ABC transporter resistance", "MNNIRRVAILAVAGAAAGSTAAEQLKQLAAAGADVVVV"),
    ])
    _write_package(as_root, "AS-B", "NODE_2_length_888_cov_2.0", "region002", "BGC004", [
        ("b1", "core synthase", "MKTAYIAKQRQISFVKSHFSRQDILDLWVYHTQGYFP"),
        ("b2", "ABC transporter", "MNNIRRVAILAVAGAAAGSTAAEQLKQLAAAGADVVVI"),
    ])
    _write_package(sid_root, "SID9", "WWAA01000001.1", "region003", "BGC007", [
        ("s1", "core synthase", "MKTAYIAKQRQISFVKSHFSRQDILDLWIYHTQGYFA"),
        ("s2", "ABC transporter", "MNNIRRVAILAVAGAAAGSTAAEQLKQLAAAGADVVVA"),
    ])
    database = tmp_path / "catalog.sqlite"
    build_catalog([("AS", as_root), ("SID", sid_root)], database)
    try:
        import Bio  # noqa: F401
    except ImportError:
        pytest.skip("optional bio extra unavailable")
    out = tmp_path / "comparison"
    receipt = compare_catalog(database, query_pkg, "BGC001", out, query_cohort="AS")
    assert receipt["status"] == "PASS"
    matches_path = next(out.glob("*__COHORT_PROTEIN_MATCHES.tsv"))
    rows = list(csv.DictReader(matches_path.open(), delimiter="\t"))
    assert rows
    assert all(row["comparator_exact_locus"].split(" / ")[0] != "AS-A" for row in rows)
    assert {row["comparator_cohort"] for row in rows} == {"AS", "SID"}
    assert all("/" in row["identical_residues"] + "/" + row["alignment_columns_including_gaps"] for row in rows)
    payload = next(out.glob("*__MODEB_SECTION45_PAYLOAD.md")).read_text(encoding="utf-8")
    assert "AS-B / NODE_2_length_888_cov_2.0 / region002 / BGC004" in payload
    assert "SID9 / WWAA01000001.1 / region003 / BGC007" in payload
    assert "Weak closest-available rows are retained" in payload


def test_missing_protein_fasta_is_typed_quarantine_not_silent_absence(tmp_path):
    root = tmp_path / "legacy"
    package = root / "SID1" / "package"
    package.mkdir(parents=True)
    (package / "SID1_2_inventory.csv").write_text(
        "BGC_ID,Contig,antiSMASH_Region\nBGC001,WWBB01000001.1,region001\n",
        encoding="utf-8",
    )
    database = tmp_path / "catalog.sqlite"
    receipt = build_catalog([("SID", root)], database)
    assert receipt["status"] == "PASS_WITH_TYPED_QUARANTINE"
    assert receipt["typed_quarantine_rows"] == 1
    con = sqlite3.connect(database)
    state = con.execute("SELECT state FROM quarantine").fetchone()[0]
    con.close()
    assert "expected exactly one *_proteins.faa" in state


def test_register_driven_gbk_adapter_uses_declared_exact_identity(tmp_path):
    try:
        from Bio import SeqIO
        from Bio.Seq import Seq
        from Bio.SeqFeature import FeatureLocation, SeqFeature
        from Bio.SeqRecord import SeqRecord
    except ImportError:
        pytest.skip("optional bio extra unavailable")
    gbk = tmp_path / "opaque_source_name.gbk"
    record = SeqRecord(Seq("ATG" * 30), id="OPAQUE", name="OPAQUE", description="test")
    record.annotations["molecule_type"] = "DNA"
    record.features.append(SeqFeature(
        FeatureLocation(0, 30, strand=1), type="CDS",
        qualifiers={"locus_tag": ["sid_gene_1"], "translation": ["MKTAYIAKQ"], "product": ["test synthase"]},
    ))
    SeqIO.write(record, gbk, "genbank")
    register = tmp_path / "gbk_register.tsv"
    register.write_text(
        "cohort\tstrain\tfull_node_or_contig\tregion\tbgc_alias\tgbk_path\n"
        f"SID\tSID10\tWWCC01000001.1\tregion004\tBGC012\t{gbk}\n",
        encoding="utf-8",
    )
    database = tmp_path / "catalog.sqlite"
    receipt = build_catalog([], database, gbk_registers=[register])
    assert receipt["status"] == "PASS"
    assert receipt["gbk_register_rows_by_cohort"] == {"SID": 1}
    con = sqlite3.connect(database)
    display, gene = con.execute("SELECT exact_locus,locus_tag FROM protein_occurrence").fetchone()
    con.close()
    assert display == "SID10 / WWCC01000001.1 / region004 / BGC012"
    assert gene == "sid_gene_1"
