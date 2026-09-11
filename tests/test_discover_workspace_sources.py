from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from mamey.cli import main
from mamey.discover import _render, run
from mamey.workspace_source_discovery import ScanLimits, sha256_file


FIXTURES = Path(__file__).parent / "fixtures" / "workspace_discovery_cli"


class DiscoverWorkspaceSourceIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "workspace"
        self.root.mkdir()
        collection = self.root / "modeb_compilation_2026-08-06"
        collection.mkdir()
        (collection / "STRAIN-001_ModeB_compilation.md").write_text("# prior report\n")
        self.registry = Path(self.temp.name) / "registry.json"
        self.registry.write_text(
            json.dumps(
                {
                    "schema_version": "sapote-source-collection-registry-v1",
                    "default_strain_regex": r"STRAIN-\d+",
                    "unclassified_max_depth": 1,
                    "rules": [
                        {
                            "collection_type": "MODE_B_COMPILATION",
                            "directory_regex": r"modeb_compilation_",
                            "root_segment_regex": r"modeb_compilation_.*",
                            "material_file_regex": r"ModeB_compilation\.md$",
                        }
                    ],
                },
                indent=2,
            )
            + "\n"
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_discover_surfaces_nonpackage_evidence_collection(self):
        report = run(
            self.root,
            4,
            source_collection_registry=self.registry,
            expected_source_collection_registry_sha256=sha256_file(self.registry),
            source_root_id="TEST_SOURCE",
            source_scan_limits=ScanLimits(max_depth=4),
        )
        self.assertEqual(report["packages"], [])
        self.assertEqual(report["source_catalog"]["status"], "PASS_COMPLETE")
        self.assertEqual(
            report["source_catalog"]["collections"][0]["collection_type"],
            "MODE_B_COMPILATION",
        )
        rendered = _render(report)
        self.assertIn("Workspace evidence collections", rendered)
        self.assertIn("discovery is not source admission", rendered)

    def test_discover_requires_hash_and_logical_root_id(self):
        with self.assertRaisesRegex(ValueError, "expected registry SHA-256"):
            run(self.root, 4, source_collection_registry=self.registry)

    def test_supported_cli_emits_governed_catalog_for_generic_project(self):
        registry = FIXTURES / "collection_registry.json"
        project = FIXTURES / "project"
        out_json = Path(self.temp.name) / "source_catalog.json"
        out_tsv = Path(self.temp.name) / "source_catalog.tsv"

        with redirect_stdout(StringIO()):
            status = main([
                "discover", str(project),
                "--json",
                "--source-collection-registry", str(registry),
                "--expected-source-collection-registry-sha256", sha256_file(registry),
                "--source-root-id", "GENERIC_PROJECT",
                "--emit-source-catalog-json", str(out_json),
                "--emit-source-catalog-tsv", str(out_tsv),
            ])

        self.assertEqual(status, 0)
        catalog = json.loads(out_json.read_text(encoding="utf-8"))
        self.assertEqual(catalog["status"], "PASS_COMPLETE")
        self.assertEqual(catalog["root_display"], "evidence://GENERIC_PROJECT")
        self.assertEqual(catalog["collections"][0]["collection_type"], "ASSAY_TABLE")
        self.assertEqual(catalog["collections"][0]["authority_state"], "DISCOVERED_NOT_ADMITTED")
        self.assertNotIn(str(project.resolve()), out_json.read_text(encoding="utf-8"))
        self.assertTrue(out_tsv.is_file())


if __name__ == "__main__":
    unittest.main()
