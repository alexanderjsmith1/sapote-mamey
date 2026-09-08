from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from mamey.source_availability import (
    build_source_availability,
    sha256_file,
    write_source_availability,
)


ASSEMBLY = "a" * 64
NODE = "NODE_1_length_1000_cov_20.5"
REGION_KEY = "REGION_0123456789abcdef"


class SourceAvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "evidence"
        self.root.mkdir()
        self.registry = Path(__file__).parents[1] / "mamey" / "data" / "source_collection_registry.json"
        self.catalog_path = self.base / "catalog.json"
        self.decisions_path = self.base / "decisions.tsv"
        self.binding_path = self.base / "bindings.tsv"
        self.collections = [
            ("COLL_ANTISMASH", "ANTISMASH_ARCHIVE", "antismash"),
            ("COLL_MAP", "LOCUS_WIDGETS", "maps"),
            ("COLL_MODEB", "MODE_B_CARDS", "mode_b"),
            ("COLL_BLASTP", "BLASTP_BY_BGC", "blastp_by_bgc"),
        ]
        self.files = {
            "antismash/STRAIN-001__NODE_1_length_1000_cov_20.5__region001.zip": "zip bytes\n",
            "maps/STRAIN-001__NODE_1_length_1000_cov_20.5__region001_locus_map.html": "<html/>\n",
            "mode_b/STRAIN-001__NODE_1_length_1000_cov_20.5__region001_ModeB.md": "# Mode B\n",
            "blastp_by_bgc/STRAIN-001__NODE_1_length_1000_cov_20.5__region001_blastp_per_gene.tsv": "gene\thit\n",
        }
        for relative, text in self.files.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        self.catalog_path.write_text(
            json.dumps({
                "schema_version": "sapote-source-discovery-catalog-v1",
                "status": "PASS_COMPLETE",
                "root_id": "TEST_ROOT",
                "collections": [
                    {
                        "collection_id": cid,
                        "collection_type": ctype,
                        "relative_path": relative,
                    }
                    for cid, ctype, relative in self.collections
                ],
            }, indent=2) + "\n",
            encoding="utf-8",
        )
        with self.decisions_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(["collection_id", "decision", "reason", "evidence_receipt"])
            for cid, _ctype, _relative in self.collections:
                writer.writerow([cid, "CONSUME", "", ""])
        roles = {
            relative: role for relative, role in (
                (next(key for key in self.files if key.startswith("antismash/")), "ANTISMASH_REGION"),
                (next(key for key in self.files if key.startswith("maps/")), "LOCUS_MAP"),
                (next(key for key in self.files if key.startswith("mode_b/")), "MODE_B_CARD"),
                (next(key for key in self.files if key.startswith("blastp_by_bgc/")), "BLASTP_RECONCILIATION"),
            )
        }
        with self.binding_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "root_id", "relative_path", "strain", "assembly_sha256", "node_id",
                    "region", "region_key", "source_role", "source_scoped_alias",
                ],
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            for relative, role in roles.items():
                writer.writerow({
                    "root_id": "TEST_ROOT",
                    "relative_path": relative,
                    "strain": "STRAIN-001",
                    "assembly_sha256": ASSEMBLY,
                    "node_id": NODE,
                    "region": "region001",
                    "region_key": REGION_KEY,
                    "source_role": role,
                    "source_scoped_alias": "BGC001",
                })

    def tearDown(self):
        self.temp.cleanup()

    def target(self):
        return [{
            "strain": "STRAIN-001",
            "assembly_sha256": ASSEMBLY,
            "node_id": NODE,
            "region": "region001",
            "region_key": REGION_KEY,
            "source_scoped_alias": "BGC001",
        }]

    def build(self, binding_tables=None, expected_registry_sha=None):
        return build_source_availability(
            source_root=self.root,
            source_root_id="TEST_ROOT",
            source_catalog_path=self.catalog_path,
            expected_source_catalog_sha256=sha256_file(self.catalog_path),
            source_decisions_path=self.decisions_path,
            expected_source_decisions_sha256=sha256_file(self.decisions_path),
            collection_registry_path=self.registry,
            expected_collection_registry_sha256=(
                expected_registry_sha or sha256_file(self.registry)
            ),
            target_loci=self.target(),
            binding_tables=[self.binding_path] if binding_tables is None else binding_tables,
        )

    def test_writes_four_logical_path_tables_and_routes_exact_locus(self):
        result = self.build()
        out = self.base / "out"
        receipt = write_source_availability(result, out)

        for name in (
            "SOURCE_FILE_CATALOG.tsv",
            "STRAIN_AVAILABILITY.tsv",
            "LOCUS_AVAILABILITY.tsv",
            "WORK_ROUTING.tsv",
        ):
            self.assertTrue((out / name).is_file())
        catalog_text = (out / "SOURCE_FILE_CATALOG.tsv").read_text(encoding="utf-8")
        self.assertIn("evidence://TEST_ROOT/", catalog_text)
        self.assertNotIn(str(self.root), catalog_text)
        with (out / "WORK_ROUTING.tsv").open(encoding="utf-8") as handle:
            routing = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(routing[0]["work_route"], "READY_COMBINED_DRAFT_SOURCE_BOUND")
        self.assertEqual(receipt["source_files_copied"], 0)

    def test_path_locator_match_never_promotes_assembly_binding(self):
        result = self.build(binding_tables=[])
        states = {row["availability_state"] for row in result["locus_rows"]}
        self.assertIn("PRESENT_NODE_REGION_PATH_ASSEMBLY_UNBOUND_HOLD", states)
        self.assertEqual(result["routing_rows"][0]["work_route"], "SKELETON_ONLY_SOURCE_BINDINGS_REQUIRED")

    def test_registry_hash_mismatch_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "collection registry SHA-256 mismatch"):
            self.build(expected_registry_sha="0" * 64)

    def test_source_drift_before_write_fails_closed(self):
        result = self.build()
        path = self.root / next(iter(self.files))
        path.write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SOURCE_DRIFT_BEFORE_AVAILABILITY_PUBLICATION"):
            write_source_availability(result, self.base / "out")

    def test_binding_to_unrequested_locus_fails_closed(self):
        text = self.binding_path.read_text(encoding="utf-8").replace(REGION_KEY, "REGION_other")
        self.binding_path.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unrequested exact locus"):
            self.build()


if __name__ == "__main__":
    unittest.main()
