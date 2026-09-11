from __future__ import annotations

import csv
import argparse
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from mamey.bgc_l0_program import add_cli_parser, run


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PortableL0ProgramTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "evidence").mkdir()
        (self.root / "outputs").mkdir()
        self.evidence = self.root / "evidence"
        self._inventory()
        self._modeb()
        self._identity_db()
        self._blastp_db()
        self._config_manifest_spec()

    def tearDown(self):
        self.temp.cleanup()

    def _inventory(self):
        fields = ["BGC_ID", "Contig", "antiSMASH_Region", "Length_kb", "Boundary", "Products", "Start", "End"]
        with (self.evidence / "inventory.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerow({
                "BGC_ID": "BGC007", "Contig": "NODE_7_length_9000_cov_40.0",
                "antiSMASH_Region": "region001", "Length_kb": "9.00", "Boundary": "Interior",
                "Products": "NRPS", "Start": "1", "End": "9000",
            })

    def _modeb(self):
        with (self.evidence / "modeb.tsv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["strain", "sha256", "mode_b_card_count"], delimiter="\t")
            writer.writeheader(); writer.writerow({"strain": "STRAIN-A", "sha256": "0" * 64, "mode_b_card_count": "1"})

    def _identity_db(self):
        db = sqlite3.connect(self.evidence / "identity.sqlite")
        db.executescript("""
        CREATE TABLE regions(region_key TEXT PRIMARY KEY,strain TEXT,assembly_sha256 TEXT,node_id TEXT);
        CREATE TABLE sources(source_id TEXT PRIMARY KEY,archive_sha256 TEXT,antismash_version TEXT,embedded_assembly_sha256 TEXT);
        CREATE TABLE region_calls(call_key TEXT,region_key TEXT,source_id TEXT,profile TEXT,region_id TEXT,products_json TEXT,contig_edge TEXT,region_gbk_sha256 TEXT);
        CREATE TABLE genes(gene_key TEXT PRIMARY KEY,locus_tag TEXT,strand INTEGER,protein_sha256 TEXT,aa_length INTEGER,nucleotide_sha256 TEXT,nucleotide_length INTEGER,product TEXT,gene_kind TEXT,gene_functions TEXT);
        CREATE TABLE gene_region_membership(region_key TEXT,gene_key TEXT,start_region_record_relative INTEGER,end_region_record_relative INTEGER);
        CREATE TABLE domains(region_key TEXT,domain_key TEXT,gene_key TEXT,label TEXT);
        INSERT INTO regions VALUES('REGION_X','STRAIN-A','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','NODE_7_length_9000_cov_40.0');
        INSERT INTO sources VALUES('S1','bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb','8.0.4','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa');
        INSERT INTO region_calls VALUES('C1','REGION_X','S1','relaxed','region001','["NRPS"]','False','cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc');
        INSERT INTO genes VALUES('G1','ctg7_1',1,'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd',300,'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',900,'NRPS protein','CDS','NRPS');
        INSERT INTO gene_region_membership VALUES('REGION_X','G1',1,900);
        INSERT INTO domains VALUES('REGION_X','D1','G1','AMP-binding');
        """)
        db.commit(); db.close()

    def _blastp_db(self):
        db = sqlite3.connect(self.evidence / "blastp.sqlite")
        db.execute("""CREATE TABLE hits(
            strain TEXT,bgc_id TEXT,gene TEXT,aa_length INTEGER,role TEXT,domains TEXT,
            hit_rank INTEGER,subject_acc TEXT,subject_organism TEXT,subject_def TEXT,
            pct_identity REAL,query_coverage REAL,evalue REAL,bitscore REAL,
            provenance_suspect INTEGER,channel TEXT)""")
        db.execute("INSERT INTO hits VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            "STRAIN-A", "BGC007", "ctg7_1", 300, "core", "AMP-binding", 1,
            "ACC1", "Reference organism", "NRPS protein", 81.0, 95.0, 1e-50,
            500.0, 0, "ncbi_nr"
        ))
        db.commit(); db.close()

    def _config_manifest_spec(self):
        (self.root / "config.json").write_text(json.dumps({
            "schema_version": "sapote_evidence_root_config_v1",
            "roots": {"evidence": {"path": "evidence"}, "outputs": {"path": "outputs"}},
        }))
        catalog = self.evidence / "source-catalog.json"
        catalog.write_text(json.dumps({
            "schema_version": "sapote-workspace-source-catalog-v1",
            "status": "PASS_COMPLETE",
            "collections": [
                {"collection_id": "COLL_MODEB_CURRENT", "collection_type": "MODE_B_COMPILATION",
                 "strain_keys_observed": ["STRAIN-A"]},
                {"collection_id": "COLL_BLASTP_CURRENT", "collection_type": "BLASTP_RESULTS",
                 "strain_keys_observed": ["STRAIN-A"]},
            ],
        }))
        decisions = self.evidence / "source-decisions.tsv"
        with decisions.open("w", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["collection_id", "decision", "reason", "evidence_receipt"],
                delimiter="\t",
            )
            writer.writeheader()
            writer.writerow({"collection_id": "COLL_MODEB_CURRENT", "decision": "CONSUME",
                             "reason": "", "evidence_receipt": ""})
            writer.writerow({"collection_id": "COLL_BLASTP_CURRENT", "decision": "CONSUME",
                             "reason": "", "evidence_receipt": ""})
        sources = []
        for source_id, name in (
            ("inventory", "inventory.csv"), ("modeb", "modeb.tsv"),
            ("identity", "identity.sqlite"), ("blastp", "blastp.sqlite"),
        ):
            path = self.evidence / name
            sources.append({
                "logical_source_id": source_id, "root_id": "evidence", "relative_path": name,
                "sha256": sha(path), "bytes": path.stat().st_size,
                "release_class": "INTERNAL", "required": True,
            })
        for source_id, name in (
            ("source_catalog", "source-catalog.json"),
            ("source_decisions", "source-decisions.tsv"),
        ):
            path = self.evidence / name
            sources.append({
                "logical_source_id": source_id, "root_id": "evidence", "relative_path": name,
                "sha256": sha(path), "bytes": path.stat().st_size,
                "release_class": "INTERNAL", "required": True,
            })
        (self.root / "manifest.json").write_text(json.dumps({
            "schema_version": "sapote_portable_source_manifest_v1", "sources": sources,
        }))
        (self.root / "spec.json").write_text(json.dumps({
            "schema_version": "sapote_l0_report_program_spec_v2", "release": "INTERNAL",
            "captured_at_utc": "2026-01-01T00:00:00Z",
            "identity_db_source_id": "identity", "blastp_db_source_id": "blastp",
            "modeb_census_source_id": "modeb", "routing_source_ids": [],
            "source_discovery_preflight": {
                "catalog_source_id": "source_catalog",
                "decisions_source_id": "source_decisions",
                "required_collection_types": ["MODE_B_COMPILATION", "BLASTP_RESULTS"],
            },
            "inventories": [{"strain": "STRAIN-A", "source_id": "inventory", "profile": "relaxed", "allocation": 1}],
            "first_batch_per_strain": 1,
            "deepening_per_strain": 1,
            "output": {"root_id": "outputs", "relative_path": "run-1"},
        }))

    def test_parallel_source_generation_fails_before_report_emission(self):
        catalog_path = self.evidence / "source-catalog.json"
        catalog = json.loads(catalog_path.read_text())
        catalog["collections"].append({
            "collection_id": "COLL_MODEB_OLDER", "collection_type": "MODE_B_COMPILATION",
            "strain_keys_observed": ["STRAIN-A"],
        })
        catalog_path.write_text(json.dumps(catalog))
        decisions = self.evidence / "source-decisions.tsv"
        with decisions.open("a", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t")
            writer.writerow(["COLL_MODEB_OLDER", "REJECT_WITH_REASON", "older", ""])
        manifest = json.loads((self.root / "manifest.json").read_text())
        for logical_id, path in (
            ("source_catalog", catalog_path), ("source_decisions", decisions),
        ):
            row = next(item for item in manifest["sources"] if item["logical_source_id"] == logical_id)
            row["sha256"] = sha(path)
            row["bytes"] = path.stat().st_size
        (self.root / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(Exception, "PARALLEL_GENERATION_UNRESOLVED"):
            run(self.root / "config.json", self.root / "manifest.json", self.root / "spec.json", {})
        self.assertFalse((self.root / "outputs" / "run-1").exists())

    def test_portable_program_uses_canonical_channel_codes_and_locator_title(self):
        result = run(self.root / "config.json", self.root / "manifest.json", self.root / "spec.json", {})
        self.assertEqual(result["roster_rows"], 1)
        self.assertEqual(result["report_rows"], 1)
        report = next((self.root / "outputs" / "run-1" / "reports").glob("*.md"))
        text = report.read_text()
        self.assertEqual(text.splitlines()[0], "# STRAIN-A — NODE_7_length_9000_cov_40.0 / region001")
        self.assertIn("| nr | 1 | 1 | 0 |", text)
        self.assertIn("EXACT_ASSEMBLY_NODE_REGION_PROFILE_BOUND", text)
        self.assertIn("Exact gene/domain inventory", text)
        self.assertIn("Observed per-gene/channel BLASTP summary", text)
        tables = list((self.root / "outputs" / "run-1" / "tables").rglob("*.tsv"))
        self.assertEqual(len(tables), 4)
        gene_table = next(path for path in tables if path.name == "exact_gene_domain_inventory.tsv")
        blastp_table = next(path for path in tables if path.name == "observed_per_gene_channel_summary.tsv")
        self.assertIn("protein_sha256", gene_table.read_text().splitlines()[0])
        self.assertIn("ctg7_1", blastp_table.read_text())
        self.assertIn("OBSERVED_ALIAS_SCOPED_QUERY_AND_RUN_RECEIPTS_UNBOUND", blastp_table.read_text())
        queue = self.root / "outputs" / "run-1" / "SELECTIVE_DEEPENING_QUEUE.tsv"
        with queue.open(newline="") as handle:
            queue_rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(queue_rows), 1)
        self.assertEqual(queue_rows[0]["primary_user_locator"], "NODE_7_length_9000_cov_40.0 / region001")
        self.assertEqual(queue_rows[0]["deepening_state"], "READY_FOR_EXACT_LOCUS_OVERLAYS")
        self.assertNotIn(str(self.root), text)
        self.assertNotIn("Claude", text)
        self.assertNotIn("Codex", text)

    def test_atomic_output_refuses_existing_destination(self):
        run(self.root / "config.json", self.root / "manifest.json", self.root / "spec.json", {})
        with self.assertRaises(FileExistsError):
            run(self.root / "config.json", self.root / "manifest.json", self.root / "spec.json", {})

    def test_display_label_is_not_used_as_storage_key(self):
        db = sqlite3.connect(self.evidence / "blastp.sqlite")
        db.execute("UPDATE hits SET channel='nr'")
        db.commit(); db.close()
        # The source hash must be updated before the altered fixture can be consumed.
        manifest = json.loads((self.root / "manifest.json").read_text())
        row = next(item for item in manifest["sources"] if item["logical_source_id"] == "blastp")
        row["sha256"] = sha(self.evidence / "blastp.sqlite"); row["bytes"] = (self.evidence / "blastp.sqlite").stat().st_size
        (self.root / "manifest.json").write_text(json.dumps(manifest))
        spec = json.loads((self.root / "spec.json").read_text()); spec["output"]["relative_path"] = "run-display-code"
        (self.root / "spec.json").write_text(json.dumps(spec))
        run(self.root / "config.json", self.root / "manifest.json", self.root / "spec.json", {})
        report = next((self.root / "outputs" / "run-display-code" / "reports").glob("*.md"))
        self.assertIn("| nr | 0 | 0 | 0 |", report.read_text())

    def test_cli_registration_exposes_portable_command_and_required_inputs(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command", required=True)
        registered = add_cli_parser(subparsers)
        self.assertEqual(registered.prog.split()[-1], "build-bgc-drafts")
        args = parser.parse_args([
            "build-bgc-drafts",
            "--evidence-root-config", "roots.json",
            "--source-manifest", "sources.json",
            "--program-spec", "program.json",
            "--evidence-root", "data=/portable/data",
        ])
        self.assertEqual(args.command, "build-bgc-drafts")
        self.assertEqual(args.evidence_root, ["data=/portable/data"])
        self.assertTrue(callable(args.func))

    def test_hash_bound_precomputed_roster_can_drive_the_program(self):
        roster = self.evidence / "roster.tsv"
        with roster.open("w", newline="") as handle:
            fields = [
                "strain", "strain_queue_rank", "primary_user_locator",
                "source_scoped_bgc_alias", "products", "length_kb", "boundary",
                "selection_lane", "activity_route", "prior_activity_routing_score",
                "prior_route_rank",
            ]
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
            writer.writeheader(); writer.writerow({
                "strain": "STRAIN-A", "strain_queue_rank": "1",
                "primary_user_locator": "NODE_7_length_9000_cov_40.0 / region001",
                "source_scoped_bgc_alias": "BGC007", "products": "NRPS",
                "length_kb": "9.00", "boundary": "Interior",
                "selection_lane": "SIZE_COMPLETION", "activity_route": "NOT_ROUTED",
                "prior_activity_routing_score": "", "prior_route_rank": "",
            })
        manifest = json.loads((self.root / "manifest.json").read_text())
        manifest["sources"].append({
            "logical_source_id": "roster", "root_id": "evidence", "relative_path": "roster.tsv",
            "sha256": sha(roster), "bytes": roster.stat().st_size,
            "release_class": "INTERNAL", "required": True,
        })
        (self.root / "manifest.json").write_text(json.dumps(manifest))
        spec = json.loads((self.root / "spec.json").read_text())
        spec.pop("inventories")
        spec["roster_source_id"] = "roster"
        spec["strain_profiles"] = {"STRAIN-A": "relaxed"}
        spec["output"]["relative_path"] = "roster-run"
        (self.root / "spec.json").write_text(json.dumps(spec))
        result = run(self.root / "config.json", self.root / "manifest.json", self.root / "spec.json", {})
        self.assertEqual(result["roster_rows"], 1)
        report = next((self.root / "outputs" / "roster-run" / "reports").glob("*.md"))
        self.assertIn("Inventory interval: `not carried in roster snapshot`", report.read_text())
        self.assertIn("EXACT_ASSEMBLY_NODE_REGION_PROFILE_BOUND", report.read_text())

    def test_missing_exact_region_is_a_visible_draft_hold(self):
        spec = json.loads((self.root / "spec.json").read_text())
        spec["inventories"][0]["profile"] = "loose"
        spec["output"]["relative_path"] = "identity-hold-run"
        (self.root / "spec.json").write_text(json.dumps(spec))
        result = run(self.root / "config.json", self.root / "manifest.json", self.root / "spec.json", {})
        self.assertEqual(result["identity_state_counts"], {"SOURCE_LOCATOR_BOUND_EXACT_REGION_JOIN_MISSING": 1})
        self.assertEqual(result["draft_state_counts"], {"L0_SOURCE_BOUND_DRAFT_EXACT_IDENTITY_HOLD": 1})
        row = result["reports"][0]
        self.assertEqual(row["draft_state"], "L0_SOURCE_BOUND_DRAFT_EXACT_IDENTITY_HOLD")
        report = self.root / "outputs" / "identity-hold-run" / row["report_path"]
        self.assertIn("State: `L0_SOURCE_BOUND_DRAFT_EXACT_IDENTITY_HOLD`", report.read_text())

    def test_preliminary_v7_and_modeb_modules_attach_without_becoming_current(self):
        v7 = self.evidence / "v7.md"
        v7.write_text(
            "# Atlas\n\n## Rank 007: STRAIN-A BGC007 - named comparator\n\nLegacy literature.\n"
        )
        modeb = self.evidence / "preliminary-modeb.md"
        modeb.write_text(
            "# Mode B\n\n## Mode B — BGC007 (OLD_NODE_7) — STRAIN-A\n\nPreliminary judgment.\n"
        )
        manifest = json.loads((self.root / "manifest.json").read_text())
        for source_id, path in (("v7", v7), ("preliminary_modeb", modeb)):
            manifest["sources"].append({
                "logical_source_id": source_id, "root_id": "evidence",
                "relative_path": path.name, "sha256": sha(path), "bytes": path.stat().st_size,
                "release_class": "INTERNAL", "required": True,
            })
        (self.root / "manifest.json").write_text(json.dumps(manifest))
        spec = json.loads((self.root / "spec.json").read_text())
        spec["evidence_modules"] = [
            {"strain": "STRAIN-A", "source_id": "v7", "module_type": "V7_LITERATURE_ATLAS",
             "format": "V7_RANKED_ATLAS_MARKDOWN",
             "verification_state": "PRELIMINARY_SOURCE_BOUND_NOT_VERIFIED"},
            {"strain": "STRAIN-A", "source_id": "preliminary_modeb",
             "module_type": "PRELIMINARY_MODE_B",
             "format": "PRELIMINARY_MODE_B_COMPILATION_MARKDOWN",
             "verification_state": "PRELIMINARY_SOURCE_BOUND_NOT_VERIFIED"},
        ]
        spec["output"]["relative_path"] = "modular-run"
        (self.root / "spec.json").write_text(json.dumps(spec))
        result = run(self.root / "config.json", self.root / "manifest.json", self.root / "spec.json", {})
        self.assertEqual(result["evidence_module_rows"], 2)
        report = next((self.root / "outputs" / "modular-run" / "reports").glob("*.md"))
        report_text = report.read_text()
        self.assertIn("V7_LITERATURE_ATLAS", report_text)
        self.assertIn("PRELIMINARY_SOURCE_BOUND_NOT_VERIFIED", report_text)
        modules = list((self.root / "outputs" / "modular-run" / "modules").rglob("*.md"))
        self.assertEqual(len(modules), 2)
        self.assertTrue(any("Legacy literature" in path.read_text() for path in modules))
        status = self.root / "outputs" / "modular-run" / "REPORT_MODULE_STATUS.tsv"
        status_text = status.read_text()
        self.assertIn("STAGE_1_PRELIMINARY_ASSEMBLY", status_text)
        self.assertIn("STAGE_2_VERIFICATION_PROMOTION", status_text)
        self.assertIn("PRELIMINARY_MODE_B", status_text)
        module_ledger = (
            self.root / "outputs" / "modular-run" / "EVIDENCE_MODULE_LEDGER.tsv"
        ).read_text()
        self.assertIn("consistency_gate_state", module_ledger)
        self.assertIn("PASS_SINGLE_LOCUS_STRUCTURAL_IDENTITY", module_ledger)
        self.assertIn("MIBIG_KCB_COMPARATOR_CHILDREN", status_text)
        self.assertEqual(result["report_module_status_rows"], 12)
        report_status = list(
            (self.root / "outputs" / "modular-run" / "tables").rglob("report_module_status.tsv")
        )
        self.assertEqual(len(report_status), 1)

    def _configure_modeb_bridge(self, bridge_state, *, assembly_sha=None):
        modeb = self.evidence / "preliminary-modeb-bridge.md"
        modeb.write_text(
            "# Mode B compilation\n\n"
            "## Mode B — BGC007 (NODE_7_length_9000_cov_40) — STRAIN-A\n\n"
            "**Identity:** BGC007 | `NODE_7_length_9000_cov_40` | `region001`\n\n"
            "| gene | node | start | end | strand | aa |\n"
            "|---|---|---:|---:|:---:|---:|\n"
            "| ctg7_1 | NODE_7_length_9000_cov_40.0 | 1 | 900 | + | 300 |\n\n"
            "Historical interpretation only.\n"
        )
        bridge = self.evidence / "modeb-bridge.tsv"
        fields = [
            "strain", "primary_user_locator", "source_scoped_bgc_alias",
            "assembly_sha256", "exact_region_key", "compilation_source_sha256",
            "bridge_state", "historical_gene_rows", "current_gene_rows",
            "shared_locus_tags", "coordinate_mismatches", "strand_mismatches",
            "aa_length_mismatches", "reason_code",
        ]
        with bridge.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
            writer.writeheader(); writer.writerow({
                "strain": "STRAIN-A",
                "primary_user_locator": "NODE_7_length_9000_cov_40.0 / region001",
                "source_scoped_bgc_alias": "BGC007",
                "assembly_sha256": assembly_sha or "a" * 64,
                "exact_region_key": "REGION_X",
                "compilation_source_sha256": sha(modeb),
                "bridge_state": bridge_state,
                "historical_gene_rows": "1",
                "current_gene_rows": (
                    "2" if bridge_state == "HOLD_PARTIAL_GENE_TABLE_BRIDGE" else "1"
                ),
                "shared_locus_tags": "1", "coordinate_mismatches": "0",
                "strand_mismatches": "0", "aa_length_mismatches": "0",
                "reason_code": (
                    "EXACT_IDENTITY_AND_COMPLETE_GENE_TABLE_MATCH"
                    if bridge_state == "PASS_EXACT_BODY_LOCATOR_AND_GENE_TABLE_BRIDGE"
                    else "EXACT_LOCUS_IDENTITY_SUPPORTED_GENE_DENOMINATOR_DIFFERS"
                ),
            })
        manifest = json.loads((self.root / "manifest.json").read_text())
        for source_id, path in (("preliminary_modeb", modeb), ("modeb_bridge", bridge)):
            manifest["sources"].append({
                "logical_source_id": source_id, "root_id": "evidence",
                "relative_path": path.name, "sha256": sha(path), "bytes": path.stat().st_size,
                "release_class": "INTERNAL", "required": True,
            })
        (self.root / "manifest.json").write_text(json.dumps(manifest))
        spec = json.loads((self.root / "spec.json").read_text())
        spec["modeb_exact_locus_bridge_source_id"] = "modeb_bridge"
        spec["evidence_modules"] = [{
            "strain": "STRAIN-A", "source_id": "preliminary_modeb",
            "module_type": "PRELIMINARY_MODE_B",
            "format": "PRELIMINARY_MODE_B_COMPILATION_MARKDOWN",
            "verification_state": "PRELIMINARY_SOURCE_BOUND_NOT_VERIFIED",
        }]
        spec["output"]["relative_path"] = "modeb-bridge-run"
        (self.root / "spec.json").write_text(json.dumps(spec))

    def test_exact_modeb_bridge_is_independent_from_prose_currentness(self):
        self._configure_modeb_bridge("PASS_EXACT_BODY_LOCATOR_AND_GENE_TABLE_BRIDGE")
        result = run(self.root / "config.json", self.root / "manifest.json", self.root / "spec.json", {})
        self.assertEqual(result["evidence_module_exact_locus_bridge_counts"], {
            "PASS_EXACT_BODY_LOCATOR_AND_GENE_TABLE_BRIDGE": 1,
        })
        ledger = self.root / "outputs" / "modeb-bridge-run" / "EVIDENCE_MODULE_LEDGER.tsv"
        with ledger.open(newline="") as handle:
            row = next(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(row["consistency_gate_state"], "PASS_SINGLE_LOCUS_STRUCTURAL_IDENTITY")
        self.assertEqual(row["historical_gene_table_completeness_state"],
                         "COMPLETE_HISTORICAL_CURRENT_GENE_TABLE_MATCH")
        self.assertEqual(row["prose_currentness_state"], "HISTORICAL_SOURCE_ONLY_NOT_CURRENT")
        report = next((self.root / "outputs" / "modeb-bridge-run" / "reports").glob("*.md"))
        self.assertIn("PASS_EXACT_BODY_LOCATOR_AND_GENE_TABLE_BRIDGE", report.read_text())
        self.assertIn("COMPLETE_HISTORICAL_CURRENT_GENE_TABLE_MATCH", report.read_text())
        self.assertIn("HISTORICAL_SOURCE_ONLY_NOT_CURRENT", report.read_text())

    def test_partial_modeb_bridge_never_becomes_current_prose(self):
        self._configure_modeb_bridge("HOLD_PARTIAL_GENE_TABLE_BRIDGE")
        run(self.root / "config.json", self.root / "manifest.json", self.root / "spec.json", {})
        ledger = self.root / "outputs" / "modeb-bridge-run" / "EVIDENCE_MODULE_LEDGER.tsv"
        with ledger.open(newline="") as handle:
            row = next(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(row["historical_gene_table_completeness_state"],
                         "PARTIAL_HISTORICAL_SELECTED_GENE_TABLE")
        self.assertEqual(row["prose_currentness_state"], "HISTORICAL_SOURCE_ONLY_NOT_CURRENT")

    def test_modeb_bridge_identity_mismatch_fails_closed(self):
        self._configure_modeb_bridge(
            "PASS_EXACT_BODY_LOCATOR_AND_GENE_TABLE_BRIDGE", assembly_sha="f" * 64,
        )
        with self.assertRaisesRegex(ValueError, "ASSEMBLY_SHA256"):
            run(self.root / "config.json", self.root / "manifest.json", self.root / "spec.json", {})

    def test_modeb_bridge_state_count_invariants_fail_closed(self):
        cases = [
            ("PASS_EXACT_BODY_LOCATOR_AND_GENE_TABLE_BRIDGE", {
                "historical_gene_rows": "20", "current_gene_rows": "3",
                "shared_locus_tags": "1", "coordinate_mismatches": "7",
            }),
            ("HOLD_PARTIAL_GENE_TABLE_BRIDGE", {"shared_locus_tags": "0"}),
            ("HOLD_CONTRADICTION", {"historical_gene_rows": "1", "current_gene_rows": "1",
                                    "shared_locus_tags": "1", "reason_code": "CONTRADICTION"}),
            ("HOLD_MISSING_REQUIRED_EVIDENCE", {
                "historical_gene_rows": "1", "current_gene_rows": "1",
                "shared_locus_tags": "1", "reason_code": "MISSING",
            }),
        ]
        for index, (state, changes) in enumerate(cases):
            with self.subTest(state=state):
                self._configure_modeb_bridge(state)
                bridge = self.evidence / "modeb-bridge.tsv"
                with bridge.open(newline="") as handle:
                    rows = list(csv.DictReader(handle, delimiter="\t"))
                    fields = list(rows[0])
                rows[0].update(changes)
                rows[0]["bridge_state"] = state
                with bridge.open("w", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
                    writer.writeheader(); writer.writerows(rows)
                manifest = json.loads((self.root / "manifest.json").read_text())
                row = next(item for item in manifest["sources"]
                           if item["logical_source_id"] == "modeb_bridge")
                row["sha256"] = sha(bridge); row["bytes"] = bridge.stat().st_size
                (self.root / "manifest.json").write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError, "state/count invariant"):
                    run(self.root / "config.json", self.root / "manifest.json",
                        self.root / "spec.json", {})
            if index + 1 < len(cases):
                self.tearDown(); self.setUp()

    def test_modeb_bridge_reason_code_uses_controlled_vocabulary(self):
        self._configure_modeb_bridge("PASS_EXACT_BODY_LOCATOR_AND_GENE_TABLE_BRIDGE")
        bridge = self.evidence / "modeb-bridge.tsv"
        with bridge.open(newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t")); fields = list(rows[0])
        rows[0]["reason_code"] = "UNREGISTERED_FREE_TEXT_VALUE"
        with bridge.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
            writer.writeheader(); writer.writerows(rows)
        manifest = json.loads((self.root / "manifest.json").read_text())
        row = next(item for item in manifest["sources"]
                   if item["logical_source_id"] == "modeb_bridge")
        row["sha256"] = sha(bridge); row["bytes"] = bridge.stat().st_size
        (self.root / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "Invalid Mode B bridge reason_code"):
            run(self.root / "config.json", self.root / "manifest.json",
                self.root / "spec.json", {})

    def test_source_local_module_references_are_replaced_by_portable_uri(self):
        self._configure_modeb_bridge("PASS_EXACT_BODY_LOCATOR_AND_GENE_TABLE_BRIDGE")
        modeb = self.evidence / "preliminary-modeb-bridge.md"
        modeb.write_text(modeb.read_text() + "\n- `strain_data/STRAIN-A/widgets/example.html`\n")
        bridge = self.evidence / "modeb-bridge.tsv"
        with bridge.open(newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t")); fields = list(rows[0])
        rows[0]["compilation_source_sha256"] = sha(modeb)
        with bridge.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
            writer.writeheader(); writer.writerows(rows)
        manifest = json.loads((self.root / "manifest.json").read_text())
        for source_id, path in (("preliminary_modeb", modeb), ("modeb_bridge", bridge)):
            row = next(item for item in manifest["sources"] if item["logical_source_id"] == source_id)
            row["sha256"] = sha(path); row["bytes"] = path.stat().st_size
        (self.root / "manifest.json").write_text(json.dumps(manifest))
        result = run(self.root / "config.json", self.root / "manifest.json", self.root / "spec.json", {})
        self.assertEqual(result["evidence_module_portable_content_counts"], {
            "REDACTED_SOURCE_LOCAL_REFERENCES": 1,
        })
        self.assertEqual(result["evidence_module_source_local_reference_redactions"], 1)
        module = next((self.root / "outputs" / "modeb-bridge-run" / "modules").rglob("*.md"))
        text = module.read_text()
        self.assertNotIn("strain_data/", text)
        self.assertIn("evidence://preliminary_modeb#source-local-reference-1", text)

    def test_public_build_rejects_raw_preliminary_modules(self):
        spec = json.loads((self.root / "spec.json").read_text())
        spec["release"] = "PUBLIC"
        spec["evidence_modules"] = [{
            "strain": "STRAIN-A", "source_id": "modeb", "module_type": "PRELIMINARY_MODE_B",
            "format": "PRELIMINARY_MODE_B_COMPILATION_MARKDOWN",
            "verification_state": "PRELIMINARY_SOURCE_BOUND_NOT_VERIFIED",
        }]
        (self.root / "spec.json").write_text(json.dumps(spec))
        with self.assertRaisesRegex(ValueError, "PUBLIC builds cannot consume"):
            run(self.root / "config.json", self.root / "manifest.json", self.root / "spec.json", {})

    def test_preliminary_comparator_children_are_separate_and_query_unbound(self):
        mibig = self.evidence / "mibig_per_gene.csv"
        with mibig.open("w", newline="") as handle:
            fields = [
                "bgc_id", "query_gene", "subject_gene", "mibig_accession",
                "mibig_compound", "reference_type", "pct_identity", "pct_coverage",
                "coverage_qc_flag", "blast_score", "evalue", "reference_rank", "reference",
            ]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader(); writer.writerow({
                "bgc_id": "BGC007", "query_gene": "ctg7_1", "subject_gene": "ref_1",
                "mibig_accession": "BGC0000001", "mibig_compound": "example family",
                "reference_type": "MIBIG", "pct_identity": "81.0", "pct_coverage": "120.6",
                "coverage_qc_flag": "SOURCE_GT100_HOLD", "blast_score": "500",
                "evalue": "1e-50", "reference_rank": "1", "reference": "example",
            })
        cluster = self.evidence / "clusterblast_per_gene.csv"
        with cluster.open("w", newline="") as handle:
            fields = [
                "bgc_id", "query_gene", "subject_gene", "pct_identity", "pct_coverage",
                "blast_score", "evalue", "reference", "reference_source", "reference_rank",
            ]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader(); writer.writerow({
                "bgc_id": "BGC007", "query_gene": "ctg7_1", "subject_gene": "subject_1",
                "pct_identity": "79.0", "pct_coverage": "94.0", "blast_score": "450",
                "evalue": "1e-40", "reference": "neighbor locus", "reference_source": "ClusterBlast",
                "reference_rank": "1",
            })
        manifest = json.loads((self.root / "manifest.json").read_text())
        for source_id, path in (("mibig", mibig), ("clusterblast", cluster)):
            manifest["sources"].append({
                "logical_source_id": source_id, "root_id": "evidence",
                "relative_path": path.name, "sha256": sha(path), "bytes": path.stat().st_size,
                "release_class": "INTERNAL", "required": True,
            })
        (self.root / "manifest.json").write_text(json.dumps(manifest))
        spec = json.loads((self.root / "spec.json").read_text())
        spec["comparator_sources"] = [
            {"strain": "STRAIN-A", "source_id": "mibig", "format": "MIBIG_PER_GENE_CSV"},
            {"strain": "STRAIN-A", "source_id": "clusterblast", "format": "CLUSTERBLAST_PER_GENE_CSV"},
        ]
        spec["output"]["relative_path"] = "comparator-run"
        (self.root / "spec.json").write_text(json.dumps(spec))
        result = run(self.root / "config.json", self.root / "manifest.json", self.root / "spec.json", {})
        self.assertEqual(result["comparator_evidence_rows"], 2)
        self.assertEqual(result["comparator_channel_counts"], {
            "MIBIG_KNOWNCLUSTERBLAST": 1, "CLUSTERBLAST": 1,
        })
        self.assertEqual(
            result["comparator_query_join_state_counts"],
            {"LOCUS_TAG_IN_EXACT_REGION_QUERY_BYTES_UNBOUND": 2},
        )
        run_root = self.root / "outputs" / "comparator-run"
        mibig_child = next(run_root.rglob("mibig_knownclusterblast_children.tsv"))
        with mibig_child.open(newline="") as handle:
            mibig_rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(mibig_rows[0]["usable_pct_coverage"], "")
        self.assertEqual(
            mibig_rows[0]["coverage_state"],
            "SOURCE_GT100_HOLD_DENOMINATOR_OR_HSP_AGGREGATE_UNRESOLVED",
        )
        self.assertEqual(
            mibig_rows[0]["evidence_state"],
            "PRELIMINARY_SOURCE_BOUND_QUERY_AND_RUN_RECEIPTS_UNBOUND",
        )
        report = next((run_root / "reports").glob("*.md")).read_text()
        self.assertIn("MIBIG_KCB_COMPARATOR_CHILDREN", report)
        self.assertIn("CLUSTERBLAST_COMPARATOR_CHILDREN", report)

    def test_public_build_rejects_preliminary_comparator_sources(self):
        spec = json.loads((self.root / "spec.json").read_text())
        spec["release"] = "PUBLIC"
        spec["comparator_sources"] = [{
            "strain": "STRAIN-A", "source_id": "modeb", "format": "MIBIG_PER_GENE_CSV",
        }]
        (self.root / "spec.json").write_text(json.dumps(spec))
        with self.assertRaisesRegex(ValueError, "PUBLIC builds cannot consume preliminary comparator"):
            run(self.root / "config.json", self.root / "manifest.json", self.root / "spec.json", {})


if __name__ == "__main__":
    unittest.main()
