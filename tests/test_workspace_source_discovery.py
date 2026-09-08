from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from mamey.workspace_source_discovery import (
    ScanLimits,
    build_source_catalog,
    sha256_file,
    validate_report_source_preflight,
    write_catalog,
)


class WorkspaceSourceDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "evidence"
        self.root.mkdir()
        self.registry = self.base / "collections.json"
        self.registry.write_text(
            json.dumps(
                {
                    "schema_version": "sapote-source-collection-registry-v1",
                    "default_strain_regex": (
                        r"(?<![A-Za-z0-9])(?:(?:STRAIN|SAMPLE|ISOLATE)[-_]?\d{1,6}"
                        r"|(?-i:[A-Z]{2})[-_]\d{2,6})"
                        r"(?![A-Za-z0-9])"
                    ),
                    "unclassified_max_depth": 2,
                    "rules": [
                        {
                            "collection_type": "MODE_B_COMPILATION",
                            "directory_regex": r"modeb_compilation_",
                            "material_file_regex": r"ModeB_compilation\.md$",
                        },
                        {
                            "collection_type": "NR_MIBIG_READOUT",
                            "directory_regex": r"nr_vs_MIBiG_readout_",
                            "material_file_regex": r"nr_vs_MIBiG.*\.csv$",
                            "coverage_parser": "DELIMITED_COLUMN",
                            "coverage_column": "strain",
                        },
                        {
                            "collection_type": "BLASTP_AUDIT_MODULE",
                            "directory_regex": r"(?:^|/)_?blastp[_-]?audit(?:/|$)",
                            "root_segment_regex": r"_?blastp[_-]?audit",
                            "material_file_regex": r".*\.(?:tsv|md|svg|png)$",
                        },
                        {
                            "collection_type": "ASSEMBLY_LINE_MODULE",
                            "directory_regex": r"(?:^|/)_?assembly[_-]?line[_-]?module(?:/|$)",
                            "root_segment_regex": r"_?assembly[_-]?line[_-]?module",
                            "material_file_regex": r".*\.(?:py|md|html)$",
                        },
                        {
                            "collection_type": "BIGSCAPE_MODULE",
                            "directory_regex": r"(?:^|/)_?bigscape[_-]?module(?:/|$)",
                            "root_segment_regex": r"_?bigscape[_-]?module",
                            "material_file_regex": r".*\.(?:py|md|gbk|html)$",
                        },
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        self.registry_sha = sha256_file(self.registry)

    def tearDown(self):
        self.temp.cleanup()

    def add_modeb(self, date: str = "2026-08-06") -> Path:
        directory = self.root / f"modeb_compilation_{date}"
        directory.mkdir()
        (directory / "STRAIN-001_ModeB_compilation.md").write_text("# report\n", encoding="utf-8")
        (directory / "STRAIN-002_ModeB_compilation.md").write_text("# report\n", encoding="utf-8")
        return directory

    def add_readout(self) -> Path:
        directory = self.root / "nr_vs_MIBiG_readout_2026-08-07"
        directory.mkdir()
        (directory / "nr_vs_MIBiG_per_bgc_2026-08-07.csv").write_text(
            "strain,bgc\nSTRAIN-001,BGC001\nSTRAIN-003,BGC001\n", encoding="utf-8"
        )
        return directory

    def catalog(self, limits: ScanLimits = ScanLimits(max_depth=4)) -> dict:
        return build_source_catalog(
            root=self.root,
            root_id="TEST_ROOT",
            collection_registry_path=self.registry,
            expected_collection_registry_sha256=self.registry_sha,
            limits=limits,
        )

    def write_catalog_and_decisions(self, catalog: dict, decision_by_id: dict[str, tuple[str, str, str]]):
        catalog_path = self.base / "catalog.json"
        catalog_tsv = self.base / "catalog.tsv"
        write_catalog(catalog, catalog_path, catalog_tsv)
        decisions = self.base / "decisions.tsv"
        with decisions.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(["collection_id", "decision", "reason", "evidence_receipt"])
            for cid, values in decision_by_id.items():
                writer.writerow([cid, *values])
        return catalog_path, decisions

    def test_finds_modeb_compilation_without_package_manifest(self):
        self.add_modeb()
        catalog = self.catalog()
        rows = [row for row in catalog["collections"] if row["collection_type"] == "MODE_B_COMPILATION"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["strain_keys_observed"], ["STRAIN-001", "STRAIN-002"])
        self.assertEqual(rows[0]["authority_state"], "DISCOVERED_NOT_ADMITTED")

    def test_finds_generic_prefixed_strain_keys_without_private_prefix_hardcoding(self):
        directory = self.root / "modeb_compilation_2026-08-08"
        directory.mkdir()
        (directory / "ZX-705_ModeB_compilation.md").write_text("# report\n", encoding="utf-8")
        (directory / "QY_421_ModeB_compilation.md").write_text("# report\n", encoding="utf-8")

        row = next(
            row for row in self.catalog()["collections"]
            if row["collection_type"] == "MODE_B_COMPILATION"
        )

        self.assertEqual(row["strain_keys_observed"], ["QY-421", "ZX-705"])

    def test_finds_nr_mibig_and_reports_coverage(self):
        self.add_readout()
        catalog = self.catalog()
        row = next(row for row in catalog["collections"] if row["collection_type"] == "NR_MIBIG_READOUT")
        self.assertEqual(row["strain_keys_observed"], ["STRAIN-001", "STRAIN-003"])
        self.assertEqual(row["coverage_extraction_state"], "PARSED_REGISTERED_CONTENT")

    def test_registered_content_parser_fails_closed_when_column_missing(self):
        directory = self.root / "nr_vs_MIBiG_readout_2026-08-07"
        directory.mkdir()
        (directory / "nr_vs_MIBiG_per_bgc_2026-08-07.csv").write_text(
            "sample,bgc\nSTRAIN-001,BGC001\n", encoding="utf-8"
        )
        row = next(
            row for row in self.catalog()["collections"]
            if row["collection_type"] == "NR_MIBIG_READOUT"
        )
        self.assertEqual(row["coverage_extraction_state"], "HOLD_COVERAGE_COLUMN_MISSING")

    def test_unclassified_material_is_surfaced(self):
        directory = self.root / "important_new_analysis"
        directory.mkdir()
        (directory / "results.tsv").write_text("a\tb\n", encoding="utf-8")
        catalog = self.catalog()
        self.assertTrue(any(row["collection_type"] == "UNCLASSIFIED_MATERIAL" for row in catalog["collections"]))

    def test_floating_analysis_modules_are_first_class_collections(self):
        blastp = self.root / "_BLASTP_AUDIT"
        blastp.mkdir()
        (blastp / "coverage.tsv").write_text("strain\tcoverage\nSTRAIN-001\t90\n", encoding="utf-8")
        (blastp / "coverage.svg").write_text("<svg/>", encoding="utf-8")

        assembly = self.root / "_ASSEMBLY_LINE_MODULE"
        widgets = assembly / "widgets"
        widgets.mkdir(parents=True)
        (assembly / "README.md").write_text("# Assembly line\n", encoding="utf-8")
        (widgets / "STRAIN-001_assembly_line.html").write_text("<html/>", encoding="utf-8")

        bigscape = self.root / "_BIGSCAPE_MODULE"
        alignments = bigscape / "alignments"
        alignments.mkdir(parents=True)
        (bigscape / "README.md").write_text("# BiG-SCAPE\n", encoding="utf-8")
        (alignments / "GCF_1_clinker.html").write_text("<html/>", encoding="utf-8")

        catalog = self.catalog()
        rows = {row["collection_type"]: row for row in catalog["collections"]}
        self.assertEqual(rows["BLASTP_AUDIT_MODULE"]["relative_path"], "_BLASTP_AUDIT")
        self.assertEqual(rows["ASSEMBLY_LINE_MODULE"]["relative_path"], "_ASSEMBLY_LINE_MODULE")
        self.assertEqual(rows["BIGSCAPE_MODULE"]["relative_path"], "_BIGSCAPE_MODULE")
        self.assertEqual(rows["ASSEMBLY_LINE_MODULE"]["file_count_at_directory"], 2)
        self.assertEqual(rows["BIGSCAPE_MODULE"]["file_count_at_directory"], 2)
        self.assertTrue(all(rows[name]["classification_state"] == "REGISTERED_SIGNATURE" for name in (
            "BLASTP_AUDIT_MODULE", "ASSEMBLY_LINE_MODULE", "BIGSCAPE_MODULE"
        )))
        self.assertTrue(all(rows[name]["authority_state"] == "DISCOVERED_NOT_ADMITTED" for name in (
            "BLASTP_AUDIT_MODULE", "ASSEMBLY_LINE_MODULE", "BIGSCAPE_MODULE"
        )))

    def test_depth_truncation_cannot_pass(self):
        deep = self.root / "a" / "b" / "c"
        deep.mkdir(parents=True)
        (deep / "result.tsv").write_text("x\n", encoding="utf-8")
        catalog = self.catalog(ScanLimits(max_depth=1))
        self.assertEqual(catalog["status"], "TRUNCATED_DEPTH_LIMIT")

    def test_file_limit_truncation_cannot_pass(self):
        self.add_modeb()
        catalog = self.catalog(ScanLimits(max_depth=4, max_files=1))
        self.assertEqual(catalog["status"], "TRUNCATED_FILE_LIMIT")

    def test_stale_catalog_hash_fails(self):
        self.add_modeb()
        catalog = self.catalog()
        cid = catalog["collections"][0]["collection_id"]
        catalog_path, decisions = self.write_catalog_and_decisions(catalog, {cid: ("CONSUME", "", "")})
        result = validate_report_source_preflight(
            catalog_path=catalog_path,
            expected_catalog_sha256="0" * 64,
            decisions_path=decisions,
            expected_decisions_sha256=sha256_file(decisions),
            strain_key="STRAIN-001",
            required_collection_types={"MODE_B_COMPILATION"},
        )
        self.assertEqual(result["reason_code"], "STALE_OR_UNBOUND_CATALOG")

    def test_missing_collection_decision_fails(self):
        self.add_modeb()
        directory = self.root / "new_material"
        directory.mkdir()
        (directory / "result.csv").write_text("x\n", encoding="utf-8")
        catalog = self.catalog()
        modeb = next(row for row in catalog["collections"] if row["collection_type"] == "MODE_B_COMPILATION")
        catalog_path, decisions = self.write_catalog_and_decisions(catalog, {modeb["collection_id"]: ("CONSUME", "", "")})
        result = validate_report_source_preflight(
            catalog_path=catalog_path,
            expected_catalog_sha256=sha256_file(catalog_path),
            decisions_path=decisions,
            expected_decisions_sha256=sha256_file(decisions),
            strain_key="STRAIN-001",
            required_collection_types={"MODE_B_COMPILATION"},
        )
        self.assertEqual(result["reason_code"], "MATERIAL_COLLECTION_DECISION_MISSING")

    def test_required_collection_must_be_consumed(self):
        self.add_modeb()
        catalog = self.catalog()
        cid = catalog["collections"][0]["collection_id"]
        catalog_path, decisions = self.write_catalog_and_decisions(catalog, {cid: ("REJECT_WITH_REASON", "stale", "")})
        result = validate_report_source_preflight(
            catalog_path=catalog_path,
            expected_catalog_sha256=sha256_file(catalog_path),
            decisions_path=decisions,
            expected_decisions_sha256=sha256_file(decisions),
            strain_key="STRAIN-001",
            required_collection_types={"MODE_B_COMPILATION"},
        )
        self.assertEqual(result["reason_code"], "REQUIRED_COLLECTION_TYPE_NOT_CONSUMED")

    def test_parallel_generations_require_explicit_supersession(self):
        self.add_modeb("2026-08-05")
        self.add_modeb("2026-08-06")
        catalog = self.catalog()
        rows = [row for row in catalog["collections"] if row["collection_type"] == "MODE_B_COMPILATION"]
        decisions_map = {
            rows[0]["collection_id"]: ("CONSUME", "", ""),
            rows[1]["collection_id"]: ("REJECT_WITH_REASON", "older", ""),
        }
        catalog_path, decisions = self.write_catalog_and_decisions(catalog, decisions_map)
        result = validate_report_source_preflight(
            catalog_path=catalog_path,
            expected_catalog_sha256=sha256_file(catalog_path),
            decisions_path=decisions,
            expected_decisions_sha256=sha256_file(decisions),
            strain_key="STRAIN-001",
            required_collection_types={"MODE_B_COMPILATION"},
        )
        self.assertEqual(result["reason_code"], "PARALLEL_GENERATION_UNRESOLVED")

    def test_parallel_generations_pass_with_receipted_supersession(self):
        self.add_modeb("2026-08-05")
        self.add_modeb("2026-08-06")
        catalog = self.catalog()
        rows = [row for row in catalog["collections"] if row["collection_type"] == "MODE_B_COMPILATION"]
        decisions_map = {
            rows[0]["collection_id"]: ("CONSUME", "", ""),
            rows[1]["collection_id"]: ("SUPERSEDED_WITH_RECEIPT", "explicit generation selection", "receipt://generation"),
        }
        catalog_path, decisions = self.write_catalog_and_decisions(catalog, decisions_map)
        result = validate_report_source_preflight(
            catalog_path=catalog_path,
            expected_catalog_sha256=sha256_file(catalog_path),
            decisions_path=decisions,
            expected_decisions_sha256=sha256_file(decisions),
            strain_key="STRAIN-001",
            required_collection_types={"MODE_B_COMPILATION"},
        )
        self.assertTrue(result["status"].startswith("PASS"))

    def test_catalog_uses_logical_root_not_absolute_path(self):
        self.add_modeb()
        text = json.dumps(self.catalog(), sort_keys=True)
        self.assertIn("evidence://TEST_ROOT", text)
        self.assertNotIn(str(self.root), text)


if __name__ == "__main__":
    unittest.main()
