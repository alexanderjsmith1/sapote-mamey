from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from mamey.bgc_report_builder import (
    _input_paths,
    _source_availability_configuration,
)


class ReportBuilderSourceAvailabilityTests(unittest.TestCase):
    def test_no_availability_options_preserves_existing_builder_path(self):
        self.assertIsNone(_source_availability_configuration(argparse.Namespace()))

    def test_partial_availability_options_fail_closed(self):
        args = argparse.Namespace(source_availability_root=Path("evidence"))
        with self.assertRaisesRegex(ValueError, "Incomplete source availability configuration"):
            _source_availability_configuration(args)

    def test_registry_and_binding_tables_join_input_hash_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            paths = {
                name: base / name for name in (
                    "identity.db", "catalog.json", "decisions.tsv", "collections.json", "bindings.tsv"
                )
            }
            for path in paths.values():
                path.write_text("x", encoding="utf-8")
            args = argparse.Namespace(
                identity_db=paths["identity.db"],
                source_discovery_catalog=paths["catalog.json"],
                source_discovery_decisions=paths["decisions.tsv"],
                blastp_reconciliation=None,
                modeb_ledger=None,
                literature_json=None,
                locus_project=[],
                source_collection_registry=paths["collections.json"],
                source_availability_binding_table=[paths["bindings.tsv"]],
            )
            resolved = {path.resolve() for path in _input_paths(args)}
            self.assertEqual(resolved, {path.resolve() for path in paths.values()})


if __name__ == "__main__":
    unittest.main()
