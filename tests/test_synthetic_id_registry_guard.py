"""Portable fake registry exercises the same standalone owner as local audit.

No registry or research input is discovered implicitly. No reviewed bundle module
is imported; children execute only the new standard-library guard.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOL = Path(__file__).resolve().parents[1] / "tools/synthetic_id_registry_guard.py"


class SyntheticRegistryGuardTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.root = Path(self.workspace.name)
        self.allowlist = self.root / "synthetic.txt"
        self.registry = self.root / "registry.tsv"
        # Deliberately invented portable rows, independent of any actual registry.
        self.token = "AS" + "-" + str(120)
        self.allowlist.write_text(self.token + "\n")
        self.registry.write_text("strain_id\n" + "AS" + "-" + str(121) + "\n")

    def tearDown(self):
        self.workspace.cleanup()

    def call(self, *extra, bind=True):
        command = [sys.executable, "-B", str(TOOL), "--allowlist", str(self.allowlist)]
        if bind:
            command += ["--registry", str(self.registry)]
        process = subprocess.run(command + list(extra), capture_output=True, text=True,
                                 timeout=10, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertNotIn("Traceback", process.stderr)
        self.assertEqual(process.stdout, "")
        return process, json.loads(process.stderr) if process.stderr.startswith("{") else None

    def test_clean_bound_snapshot_is_limited_pass(self):
        process, result = self.call()
        self.assertEqual(process.returncode, 0)
        self.assertEqual(result["state"], "PASS_BOUND_SNAPSHOT")
        self.assertTrue(process.stderr.startswith("{"))
        self.assertIn("no disclosure permission", result["certification_scope"])

    def test_real_overlap_fails_and_default_output_is_redacted(self):
        self.registry.write_text("strain_id\n" + self.token + "\n")
        process, result = self.call()
        self.assertEqual(process.returncode, 1)
        self.assertEqual(result["collision_count"], 1)
        self.assertNotIn("collisions", result)
        self.assertNotIn(self.token, process.stdout + process.stderr)
        self.assertNotIn(str(self.registry), process.stdout + process.stderr)

    def test_dashless_case_and_zero_padding_cannot_bypass_registry(self):
        self.registry.write_text("basename\tpath\n" + "as" + "00120.fna\t" + "relative/example.fna\n")
        process, result = self.call()
        self.assertEqual(process.returncode, 1)
        self.assertEqual(result["collision_count"], 1)

    def test_public_location_name_does_not_authorize_synthetic_identity(self):
        self.registry.write_text("basename\tpath\n" + "reference.fna\tType_Strains/" + self.token + ".fna\n")
        process, result = self.call()
        self.assertEqual(process.returncode, 1)
        self.assertEqual(result["collision_count"], 1)

    def test_pending_registry_separator_and_case_aliases_cannot_false_pass(self):
        payload = "PORTABLECASE"
        self.allowlist.write_text("PENDING" + "-" + payload + "\n")
        for separator in ("", " ", "_", "-"):
            with self.subTest(separator=separator):
                self.registry.write_text("strain_id\npending" + separator + payload.lower() + "\n")
                process, result = self.call()
                self.assertEqual(process.returncode, 1)
                self.assertEqual(result["collision_count"], 1)

    def test_absent_binding_is_hold_not_certification(self):
        process, result = self.call(bind=False)
        self.assertEqual(process.returncode, 2)
        self.assertEqual(result["state"], "HOLD")
        self.assertIn("REGISTRY_UNBOUND", result["issues"])

    def test_missing_registry_is_hold(self):
        self.registry.unlink()
        process, result = self.call()
        self.assertEqual(process.returncode, 2)
        self.assertEqual(result["state"], "HOLD")

    def test_empty_registry_cannot_pass(self):
        self.registry.write_text("strain_id\n")
        process, result = self.call()
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result["state"], "HOLD")

    def test_bad_registry_schema_cannot_pass(self):
        self.registry.write_text("unrelated_column\nanything\n")
        process, result = self.call()
        self.assertEqual(process.returncode, 2)

    def test_public_reference_is_separate_from_synthetic_strains(self):
        self.allowlist.write_text("AS" + "-" + str(48) + "\n")
        process, result = self.call()
        self.assertEqual(process.returncode, 1)
        self.assertIn("PUBLIC_REFERENCE_IS_NOT_A_SYNTHETIC_STRAIN", result["issues"])

    def test_malformed_and_duplicate_allowlist_fail(self):
        for text in (self.token + "\n" + self.token + "\n", self.token.lower() + "\n"):
            with self.subTest(text_kind="duplicate" if text.count("\n") == 2 else "case"):
                self.allowlist.write_text(text)
                process, _ = self.call()
                self.assertNotEqual(process.returncode, 0)

    def test_zero_padded_aliases_are_not_independent_synthetic_declarations(self):
        self.allowlist.write_text(self.token + "\n" + "AS" + "-0" + str(120) + "\n")
        process, result = self.call()
        self.assertEqual(process.returncode, 1)
        self.assertIn("ALLOWLIST_NORMALIZED_ALIAS_DUPLICATE", result["issues"])

    def test_private_detail_export_option_is_not_available(self):
        output = self.root / "private-detail.json"
        process, _ = self.call("--private-detail-report", str(output))
        self.assertEqual(process.returncode, 2)
        self.assertFalse(output.exists())

    def test_very_long_numeric_identity_is_typed_without_integer_conversion(self):
        token = "AS" + "-" + "9" * 5000
        self.allowlist.write_text(token + "\n")
        self.registry.write_text("strain_id\n" + token + "\n")
        process, result = self.call()
        self.assertEqual(process.returncode, 1)
        self.assertEqual(result["collision_count"], 1)
        self.assertNotIn(token, process.stderr)

    @unittest.skipUnless(os.environ.get("SAPOTE_SYNTHETIC_ID_REGISTRY"),
                         "Actual registry unbound; portable fixture is not cohort certification")
    def test_optional_explicit_actual_registry_snapshot(self):
        command = [sys.executable, "-B", str(TOOL), "--allowlist",
                   str(TOOL.parent / "test_synthetic_ids.txt"), "--registry",
                   os.environ["SAPOTE_SYNTHETIC_ID_REGISTRY"]]
        process = subprocess.run(command, capture_output=True, text=True, timeout=15,
                                 env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)


if __name__ == "__main__":
    unittest.main()
