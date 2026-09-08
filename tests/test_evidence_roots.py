from __future__ import annotations

import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE = Path(__file__).parents[1] / "mamey" / "evidence_roots.py"
SPEC = importlib.util.spec_from_file_location("candidate_evidence_roots", MODULE)
assert SPEC and SPEC.loader
ER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ER
SPEC.loader.exec_module(ER)


class EvidenceRootTests(unittest.TestCase):
    def fixture(self, root: Path):
        evidence = root / "evidence"
        evidence.mkdir()
        source = evidence / "input.tsv"
        source.write_text("a\tb\n1\t2\n", encoding="utf-8")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        config_path = root / "roots.json"
        config = {
            "schema_version": ER.CONFIG_SCHEMA,
            "roots": {"report_inputs": {"path": "evidence"}},
        }
        manifest = {
            "schema_version": ER.MANIFEST_SCHEMA,
            "sources": [{
                "logical_source_id": "fixture.input",
                "role": "BLASTP_RECONCILIATION",
                "root_id": "report_inputs",
                "relative_path": "input.tsv",
                "sha256": digest,
                "bytes": source.stat().st_size,
                "required": True,
                "release_class": "INTERNAL",
            }],
        }
        return config_path, config, manifest, source

    def test_relative_config_root_is_anchored_to_config(self):
        with tempfile.TemporaryDirectory() as td:
            config_path, config, _, source = self.fixture(Path(td))
            roots = ER.resolve_roots(config, config_path, environ={})
            self.assertEqual(roots["report_inputs"], source.parent.resolve())

    def test_hash_bound_source_resolves(self):
        with tempfile.TemporaryDirectory() as td:
            config_path, config, manifest, source = self.fixture(Path(td))
            roots = ER.resolve_roots(config, config_path, environ={})
            resolved, receipt = ER.resolve_sources(manifest, roots, "INTERNAL")
            self.assertEqual(resolved["fixture.input"], source.resolve())
            self.assertEqual(receipt["status"], "PASS_PREFLIGHT")

    def test_parent_traversal_hard_fails(self):
        with tempfile.TemporaryDirectory() as td:
            config_path, config, manifest, _ = self.fixture(Path(td))
            manifest["sources"][0]["relative_path"] = "../input.tsv"
            roots = ER.resolve_roots(config, config_path, environ={})
            with self.assertRaisesRegex(ER.EvidenceRootError, "Unsafe portable"):
                ER.resolve_sources(manifest, roots, "INTERNAL")

    def test_optional_missing_source_becomes_channel_not_consumed(self):
        with tempfile.TemporaryDirectory() as td:
            config_path, config, manifest, _ = self.fixture(Path(td))
            manifest["sources"][0].update({"relative_path": "missing.tsv", "required": False})
            roots = ER.resolve_roots(config, config_path, environ={})
            resolved, receipt = ER.resolve_sources(manifest, roots, "INTERNAL")
            self.assertEqual(resolved, {})
            self.assertEqual(receipt["sources"][0]["state"], "CHANNEL_NOT_CONSUMED")


if __name__ == "__main__":
    unittest.main()
