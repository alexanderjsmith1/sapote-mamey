from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


MODULE = Path(__file__).parents[1] / "mamey" / "bgc_report_builder.py"
SPEC = importlib.util.spec_from_file_location("candidate_bgc_report_builder", MODULE)
assert SPEC and SPEC.loader
BR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BR
SPEC.loader.exec_module(BR)


def make_db(path: Path, include_relaxed_source: bool = False, mixed_version: bool = False) -> None:
    con = sqlite3.connect(path)
    con.executescript("""
    CREATE TABLE sources(source_id TEXT PRIMARY KEY,strain TEXT,profile TEXT,archive_sha256 TEXT,antismash_version TEXT,embedded_assembly_sha256 TEXT);
    CREATE TABLE regions(region_key TEXT PRIMARY KEY,strain TEXT,assembly_sha256 TEXT,node_id TEXT,sequence_sha256 TEXT,coordinate_frame TEXT,region_record_start INTEGER,region_record_end INTEGER);
    CREATE TABLE region_calls(call_key TEXT,region_key TEXT,source_id TEXT,profile TEXT,region_id TEXT,products_json TEXT,contig_edge TEXT);
    CREATE TABLE genes(gene_key TEXT PRIMARY KEY,locus_tag TEXT,strand INTEGER,protein_sha256 TEXT,aa_length INTEGER,nucleotide_sha256 TEXT,nucleotide_length INTEGER,product TEXT,gene_functions TEXT);
    CREATE TABLE gene_region_membership(region_key TEXT,gene_key TEXT,start_region_record_relative INTEGER,end_region_record_relative INTEGER);
    CREATE TABLE domains(domain_key TEXT,region_key TEXT,gene_key TEXT,feature_type TEXT,label TEXT,start_region_record_relative INTEGER,end_region_record_relative INTEGER,start_gene_relative INTEGER,end_gene_relative INTEGER,strand INTEGER,binding_state TEXT);
    CREATE TABLE aliases(alias_key TEXT,region_key TEXT,alias_type TEXT,alias_value TEXT,alias_state TEXT,evidence TEXT);
    CREATE VIEW region_summary AS SELECT r.region_key,r.strain,r.assembly_sha256,r.node_id,'loose' profiles,'region001' source_region_ids,1 gene_count,1 domain_count,'BGC001' aliases FROM regions r;
    INSERT INTO sources VALUES('S_LOOSE','AS-TEST','loose','archive-loose','8.0.4','asm');
    INSERT INTO regions VALUES('REGION_X','AS-TEST','asm','NODE_X','seq','REGION_GBK_RECORD_RELATIVE',1,301);
    INSERT INTO region_calls VALUES('C','REGION_X','S_LOOSE','loose','region001','["fixture"]','false');
    INSERT INTO genes VALUES('G','gene1',1,'prot',100,'nt',300,'enzyme','biosynthetic-additional');
    INSERT INTO gene_region_membership VALUES('REGION_X','G',1,301);
    INSERT INTO domains VALUES('D','REGION_X','G','PFAM_domain','DomainX',10,90,9,89,1,'SOURCE_LOCUS_TAG');
    INSERT INTO aliases VALUES('A','REGION_X','HISTORICAL','BGC001','PROPOSED_ALIAS_NOT_ACCEPTED','fixture');
    """)
    if include_relaxed_source:
        version = "8.0.5" if mixed_version else "8.0.4"
        con.execute(
            "INSERT INTO sources VALUES(?,?,?,?,?,?)",
            ("S_RELAXED", "AS-TEST", "relaxed", "archive-relaxed", version, "asm"),
        )
    con.commit(); con.close()


class BuilderTests(unittest.TestCase):
    def args(
        self,
        td: str,
        release: str = "INTERNAL",
        strain: str = "AS-TEST",
        include_relaxed_source: bool = False,
        mixed_version: bool = False,
    ) -> argparse.Namespace:
        root = Path(td)
        db = root / "db.sqlite"
        make_db(db, include_relaxed_source=include_relaxed_source, mixed_version=mixed_version)
        catalog = root / "source_catalog.json"
        catalog.write_text(json.dumps({
            "schema_version": "sapote-source-discovery-catalog-v1",
            "status": "PASS_COMPLETE",
            "root_id": "TEST_ROOT",
            "collections": [{
                "collection_id": "COLLECTION_TEST_MODEB",
                "collection_type": "MODE_B_COMPILATION",
                "relative_path": "modeb",
                "strain_keys_observed": ["AS-TEST"],
            }],
        }) + "\n", encoding="utf-8")
        decisions = root / "source_decisions.tsv"
        with decisions.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(["collection_id", "decision", "reason", "evidence_receipt"])
            writer.writerow(["COLLECTION_TEST_MODEB", "CONSUME", "", ""])
        digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
        return argparse.Namespace(
            identity_db=db, strain=strain, alias=["BGC001"], region_key=[],
            blastp_reconciliation=None, modeb_ledger=None,
            expected_blastp_channel=[],
            literature_json=None, literature_record_number=[],
            locus_project=[], release=release, out_root=root / "out",
            captured_at_utc="2026-08-08T12:00:00+00:00",
            source_discovery_catalog=catalog,
            expected_source_discovery_catalog_sha256=digest(catalog),
            source_discovery_decisions=decisions,
            expected_source_discovery_decisions_sha256=digest(decisions),
            required_collection_type=["MODE_B_COMPILATION"],
        )

    def test_missing_source_discovery_preflight_fails_before_output(self):
        with tempfile.TemporaryDirectory() as td:
            args = self.args(td)
            args.required_collection_type = []
            with self.assertRaisesRegex(ValueError, "required collection types"):
                BR.build(args)
            self.assertFalse(args.out_root.exists())

    def test_stale_source_discovery_catalog_fails_before_output(self):
        with tempfile.TemporaryDirectory() as td:
            args = self.args(td)
            args.expected_source_discovery_catalog_sha256 = "0" * 64
            with self.assertRaisesRegex(
                ValueError, "SOURCE_DISCOVERY_PREFLIGHT_FAILED:STALE_OR_UNBOUND_CATALOG"
            ):
                BR.build(args)
            self.assertFalse(args.out_root.exists())

    def test_exact_alias_build_and_missing_profile_hold(self):
        with tempfile.TemporaryDirectory() as td:
            args = self.args(td)
            manifest = BR.build(args)
            report = (args.out_root / "AS-TEST_refreshable_bgc_report.md").read_text()
            self.assertEqual(manifest["region_keys"], ["REGION_X"])
            self.assertIn("MISSING_PROFILE_ARCHIVE_NOT_BIOLOGICAL_ABSENCE", manifest["holds"])
            self.assertIn("BGC001 [PROPOSED_ALIAS_NOT_ACCEPTED]", report)
            self.assertIn("Protein/CDS hashes", report)
            self.assertIn("## Locus 1: `NODE_X / region001`", report)
            self.assertIn("- Exact region key: `REGION_X`", report)
            self.assertNotIn("## Locus 1: `REGION_X`", report)

    def test_private_prefix_public_export_refused(self):
        # v9.7.409 N1: AJS-/PENDING- are the withheld prefixes; AS- is PUBLIC (GOV-001).
        with tempfile.TemporaryDirectory() as td:
            args = self.args(td, release="PUBLIC", strain="AJS-TEST")
            with self.assertRaisesRegex(ValueError, "PUBLIC export refused"):
                BR.build(args)

    def test_public_as_prefix_export_is_not_refused_by_prefix(self):
        # v9.7.409 N1: the pre-governance tuple listed "AS-" and refused every cohort strain.
        self.assertFalse("AS-TEST".startswith(BR.PRIVATE_PREFIXES))
        self.assertTrue("AJS-TEST".startswith(BR.PRIVATE_PREFIXES))
        self.assertTrue("PENDING-1".startswith(BR.PRIVATE_PREFIXES))

    def test_loose_only_call_is_not_missing_relaxed_when_exact_assembly_pair_exists(self):
        with tempfile.TemporaryDirectory() as td:
            args = self.args(td, include_relaxed_source=True)
            manifest = BR.build(args)
            report = (args.out_root / "AS-TEST_refreshable_bgc_report.md").read_text()
            self.assertNotIn("MISSING_PROFILE_ARCHIVE_NOT_BIOLOGICAL_ABSENCE", manifest["holds"])
            self.assertIn("LOOSE_ONLY_CALL_EXACT_ASSEMBLY_COUNTERPART_PRESENT", report)
            self.assertIn("profile-sensitivity delta, not biological absence", report)

    def test_mixed_antismash_versions_fail_before_report_build(self):
        with tempfile.TemporaryDirectory() as td:
            args = self.args(td, include_relaxed_source=True, mixed_version=True)
            with self.assertRaisesRegex(ValueError, "Mixed antiSMASH versions"):
                BR.build(args)

    def test_fixed_timestamp_double_build_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as td:
            args1 = self.args(td)
            args2 = argparse.Namespace(**vars(args1))
            args2.out_root = Path(td) / "out_second"
            BR.build(args1)
            BR.build(args2)
            first = {path.name: path.read_bytes() for path in args1.out_root.iterdir()}
            second = {path.name: path.read_bytes() for path in args2.out_root.iterdir()}
            self.assertEqual(first, second)

    def test_blastp_outside_exact_locus_is_quarantined(self):
        genes = [{"locus_tag": "gene1", "protein_sha256": "prot", "aa_length": 100}]
        rows = [
            {"strain": "AS-TEST", "exact_node_id": "NODE_X", "gene_id": "gene1", "current_protein_sha256": "prot", "current_aa_length": "100"},
            {"strain": "AS-TEST", "exact_node_id": "NODE_X", "gene_id": "outer", "current_protein_sha256": "", "current_aa_length": ""},
        ]
        admitted, rejected = BR._blastp_rows(rows, "AS-TEST", "NODE_X", genes)
        self.assertEqual([row["gene_id"] for row in admitted], ["gene1"])
        self.assertEqual(rejected[0]["rejection_reason"], "OUTSIDE_EXACT_REGION_LOCUS_SET")

    def test_blastp_inside_locus_hash_mismatch_hard_fails(self):
        genes = [{"locus_tag": "gene1", "protein_sha256": "prot", "aa_length": 100}]
        rows = [{"strain": "AS-TEST", "exact_node_id": "NODE_X", "gene_id": "gene1", "current_protein_sha256": "wrong", "current_aa_length": "100"}]
        with self.assertRaisesRegex(ValueError, "protein hash mismatch"):
            BR._blastp_rows(rows, "AS-TEST", "NODE_X", genes)

    def test_expected_missing_channel_is_visible_not_a_biological_negative(self):
        summaries = BR._channel_summary([], "REGION_X", "NODE_X", 9, ["ebi_uniprot"])
        self.assertEqual(summaries[0]["expected_query_count"], 9)
        self.assertEqual(summaries[0]["missing_query_count"], 9)
        self.assertEqual(summaries[0]["channel_state"], "CHANNEL_NOT_CONSUMED")

    def test_complete_label_length_denominator_stays_held_when_query_sequences_unbound(self):
        rows = [{
            "gene_id": "gene1",
            "gate_state": "PASS_LABEL_LENGTH_SEQUENCE_UNBOUND",
            "sequence_binding_state": "UNBOUND_QUERY_SEQUENCE_NOT_PRESENT_IN_RESULT_CSV",
        }]
        summary = BR._channel_summary(rows, "REGION_X", "NODE_X", 1, ["nr_alternate"])[0]
        self.assertEqual(summary["missing_query_count"], 0)
        self.assertEqual(summary["pass_row_count"], 1)
        self.assertEqual(summary["channel_state"], "CURRENT_SNAPSHOT_COMPLETE_DENOMINATOR_WITH_HOLDS")

    def test_missing_channel_source_is_not_described_as_complete_denominator(self):
        rows = [{
            "gene_id": "gene1",
            "gate_state": "HOLD_CURRENT_GENE_MISSING_FROM_CHANNEL",
            "sequence_binding_state": "UNBOUND_QUERY_SEQUENCE_NO_IMMUTABLE_SUBMISSION_RECEIPT",
            "channel_source_state": "MISSING_CHANNEL_SOURCE",
        }]
        summary = BR._channel_summary(rows, "REGION_X", "NODE_X", 1, ["clusterednr"])[0]
        self.assertEqual(summary["represented_query_count"], 1)
        self.assertEqual(summary["channel_source_state"], "MISSING_CHANNEL_SOURCE")
        self.assertEqual(summary["channel_state"], "CHANNEL_SOURCE_MISSING_HOLD")

    def test_mixed_channel_source_states_hard_fail(self):
        rows = [
            {"gene_id": "gene1", "gate_state": "PASS_LABEL_LENGTH_SEQUENCE_UNBOUND", "sequence_binding_state": "UNBOUND", "channel_source_state": "PRESENT_HASH_VERIFIED"},
            {"gene_id": "gene2", "gate_state": "HOLD_CURRENT_GENE_MISSING_FROM_CHANNEL", "sequence_binding_state": "UNBOUND", "channel_source_state": "MISSING_CHANNEL_SOURCE"},
        ]
        with self.assertRaisesRegex(ValueError, "Mixed BLASTP channel source states"):
            BR._channel_summary(rows, "REGION_X", "NODE_X", 2, ["nr_primary"])


if __name__ == "__main__":
    unittest.main()
