"""Synthetic lineage invariants; no biological activity or potency inference."""
import csv
from pathlib import Path
import unittest
from mamey import evidence_registry as registry


class LineageTests(unittest.TestCase):
    def setUp(self):
        import os, tempfile
        self.work = tempfile.mkdtemp(prefix="lineage-", dir=os.environ.get("SAPOTE_LINEAGE_TEST_ROOT", tempfile.gettempdir()))

    def material(self, identifier, strain="SYNTHETIC-A", parent="ROOT", level="crude_extract"):
        row = dict.fromkeys(registry.REQUIRED_HEADERS, "synthetic")
        row.update(record_id=identifier, strain_id=strain, material_id=identifier,
                   parent_material_id=parent, evidence_type="material", material_level=level,
                   assay_state="NOT_SCREENED", claim_ceiling="Synthetic lineage only; no activity inference")
        return row

    def validate(self, rows):
        p = Path(self.work) / (self._testMethodName + ".tsv")
        with p.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=registry.REQUIRED_HEADERS, delimiter="\t")
            w.writeheader()
            w.writerows(rows)
        return registry.validate_evidence_registry(p)

    def test_valid_crude_flash_hplc_chain(self):
        result = self.validate([self.material("crude"), self.material("flash", parent="crude", level="flash_fraction"),
                                self.material("hplc", parent="flash", level="hplc_fraction")])
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["material_count"], 3)
        self.assertIn("do not establish activity", result["claim_ceiling"])

    def test_cross_strain_parent_refused(self):
        with self.assertRaisesRegex(registry.EvidenceRegistryError, "parent strain_id"):
            self.validate([self.material("crude"), self.material("flash", strain="SYNTHETIC-B", parent="crude", level="flash_fraction")])

    def test_self_parent_refused(self):
        with self.assertRaisesRegex(registry.EvidenceRegistryError, "cyclic"):
            self.validate([self.material("flash", parent="flash", level="flash_fraction")])

    def test_two_fraction_cycle_refused(self):
        with self.assertRaisesRegex(registry.EvidenceRegistryError, "cyclic"):
            self.validate([self.material("flash", parent="hplc", level="flash_fraction"), self.material("hplc", parent="flash", level="hplc_fraction")])

    def test_multiple_independent_strains_valid(self):
        self.assertEqual(self.validate([self.material("a"), self.material("b", strain="SYNTHETIC-B")])["status"], "PASS")


