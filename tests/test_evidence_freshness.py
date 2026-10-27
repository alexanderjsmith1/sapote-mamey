"""Behavioral fixtures: stale upstream bytes must invalidate unchanged outputs."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

PATH = Path(__file__).resolve().parents[1] / "tools" / "evidence_freshness.py"
SPEC = importlib.util.spec_from_file_location("freshness_candidate", PATH)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.nodes = []
        for key, deps in (("source", []), ("table", ["source"]), ("report", ["table"])):
            path = self.root / key
            path.write_text(key)
            self.nodes.append({"id": key, "path": key, "sha256": M.digest(path),
                               "unit": "artifact", "source_revision": "fixture-v1", "depends_on": deps})

    def run_audit(self, **kwargs):
        return M.audit({"schema": M.SCHEMA, "artifacts": self.nodes}, self.root, **kwargs)

    def test_changed_source_invalidates_two_generations_without_rewriting_pins(self):
        old = self.nodes[0]["sha256"]
        (self.root / "source").write_text("changed upstream")
        rows = {r["id"]: r for r in self.run_audit()["artifacts"]}
        self.assertEqual(rows["source"]["direct_state"], "CHANGED")
        self.assertEqual(rows["report"]["direct_state"], "HASH_MATCH")
        self.assertEqual(rows["report"]["state"], "INVALIDATED_DEPENDENCY")
        self.assertEqual(rows["report"]["blocking_ancestors"], ["source", "table"])
        self.assertEqual(self.nodes[0]["sha256"], old)

    def test_timestamp_only_change_does_not_invalidate_matching_bytes(self):
        import os
        os.utime(self.root / "source", (100, 100))
        self.assertEqual(self.run_audit()["status"], "PASS_BYTES_AND_DECLARED_DEPENDENCIES")

    def test_missing_is_distinct_from_unpinned(self):
        (self.root / "source").unlink()
        self.nodes[1]["sha256"] = ""
        rows = self.run_audit()["artifacts"]
        self.assertEqual(rows[0]["direct_state"], "MISSING_FILE")
        self.assertEqual(rows[1]["direct_state"], "UNVERIFIED_BASELINE")

    def test_cycles_unknown_dependencies_and_duplicates_refuse(self):
        for change in ("cycle", "unknown", "duplicate"):
            with self.subTest(change=change):
                saved = [dict(n) for n in self.nodes]
                if change == "cycle": self.nodes[0]["depends_on"] = ["report"]
                if change == "unknown": self.nodes[0]["depends_on"] = ["absent"]
                if change == "duplicate": self.nodes.append(dict(self.nodes[0]))
                with self.assertRaises(ValueError): self.run_audit()
                self.nodes = saved

    def test_budgets_hold_without_huge_read(self):
        rows = self.run_audit(max_file_bytes=2)["artifacts"]
        self.assertTrue(all(r["direct_state"] == "UNVERIFIED_FILE_BUDGET" for r in rows))
        rows = self.run_audit(max_total_bytes=7)["artifacts"]
        self.assertEqual(rows[1]["direct_state"], "UNVERIFIED_TOTAL_BUDGET")

    def test_locus_metadata_needs_native_owner(self):
        self.nodes[0]["unit"] = "locus"
        rows = self.run_audit()["artifacts"]
        self.assertEqual(rows[0]["identity_state"], "UNVERIFIED_OWNER_NOT_SELECTED")
        self.assertEqual(rows[2]["state"], "INVALIDATED_DEPENDENCY")

    def test_missing_revision_holds_even_matching_bytes(self):
        self.nodes[0]["source_revision"] = ""
        self.assertEqual(self.run_audit()["artifacts"][0]["state"], "HOLD_METADATA")

    def test_owner_read_does_not_write_cache_when_caller_allows_bytecode(self):
        import sys
        owner_dir = self.root / "mamey"
        owner_dir.mkdir()
        (owner_dir / "exact_identity.py").write_text("def marker(): return 1\n")
        old = sys.dont_write_bytecode
        try:
            sys.dont_write_bytecode = False
            owner, binding = M.identity_owner(self.root)
        finally:
            sys.dont_write_bytecode = old
        self.assertEqual(owner.marker(), 1)
        self.assertFalse((owner_dir / "__pycache__").exists())

    def test_invalid_hash_and_missing_unit_refuse(self):
        self.nodes[0]["sha256"] = "not-a-sha"
        with self.assertRaises(ValueError): self.run_audit()
        self.nodes[0]["sha256"] = ""
        self.nodes[0].pop("unit")
        with self.assertRaises(ValueError): self.run_audit()


if __name__ == "__main__":
    unittest.main()
