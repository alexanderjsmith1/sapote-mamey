"""P357-021: release identity and final-evidence ordering must fail closed."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load_tool(name: str):
    path = ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReleaseCutIntegrityTests(unittest.TestCase):
    def test_atomic_identity_rewrite_changes_only_cut_owned_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text(
                '[project]\nversion = "1.9.119"\n\n[tool.sapote]\nbundle_version = "9.7.356"\n',
                encoding="utf-8",
            )
            (root / "BUILD_STAMP.txt").write_text(
                "version=9.7.356\nbuild=20260807v97356a\nengine=1.9.119\ntier=code\n",
                encoding="utf-8",
            )
            (root / "TIER_MANIFEST.txt").write_text(
                "# TIER_MANIFEST tier=code version=9.7.356 stamp=20260807v97356a\n./README.md\n",
                encoding="utf-8",
            )
            tool = ROOT / "tools" / "rewrite_release_identity.py"
            run = subprocess.run(
                [sys.executable, str(tool), "9.7.357", "20260809v97357a", "--root", str(root)],
                text=True,
                capture_output=True,
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertIn('version = "1.9.119"', (root / "pyproject.toml").read_text())
            self.assertIn('bundle_version = "9.7.357"', (root / "pyproject.toml").read_text())
            self.assertIn("version=9.7.357", (root / "BUILD_STAMP.txt").read_text())
            self.assertIn("build=20260809v97357a", (root / "BUILD_STAMP.txt").read_text())
            self.assertIn("version=9.7.357 stamp=20260809v97357a", (root / "TIER_MANIFEST.txt").read_text())
            debris = [
                p.name
                for p in root.rglob("*")
                if p.is_file() and p.name.endswith(("-E", ".orig", ".rej", ".bak", "~"))
            ]
            self.assertEqual(debris, [])
            check = subprocess.run(
                [sys.executable, str(tool), "9.7.357", "20260809v97357a", "--root", str(root), "--check"],
                text=True,
                capture_output=True,
            )
            self.assertEqual(check.returncode, 0, check.stderr)

    def test_atomic_identity_rewrite_rejects_bad_stamp(self):
        tool = ROOT / "tools" / "rewrite_release_identity.py"
        run = subprocess.run(
            [sys.executable, str(tool), "9.7.357", "not-a-stamp", "--root", "."],
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(run.returncode, 0)

    def test_release_cut_uses_atomic_rewrite_and_binds_final_green_log(self):
        text = (ROOT / "tools" / "release_cut.sh").read_text(encoding="utf-8")
        self.assertNotIn("sed -i", text)
        self.assertIn("rewrite_release_identity.py", text)
        self.assertLess(
            text.index("python3 -m pytest -q"),
            text.index("gen_release_manifest.py --apply --pytest-log"),
        )
        self.assertNotIn("--skip-tests requires PYTEST_LOG=", text)
        self.assertIn("--skip-tests requires PYTEST_RECEIPT=", text)
        self.assertIn("PYTEST_RECEIPT_SHA256", text)
        self.assertIn("verify_external_validation_receipt.py", text)
        self.assertLess(
            text.index("verify_external_validation_receipt.py"),
            text.index('export BUILD_STAMP="$STAMP" SKIP_INTIER_PYTEST=1'),
        )
        self.assertIn("assert_no_backup_debris", text)
        self.assertIn("-name '*-E'", text)

    def test_tier_builder_fails_closed_on_backup_debris_and_excludes_dash_e(self):
        text = (ROOT / "tools" / "make_public_tier.sh").read_text(encoding="utf-8")
        self.assertIn("fail_on_backup_debris", text)
        self.assertIn("will not silently delete evidence", text)
        self.assertIn("-x '*-E'", text)
        for line in text.splitlines():
            if "-delete" in line:
                self.assertNotIn("-name '*-E'", line)

    def test_release_manifest_derives_both_dates_from_build_stamp(self):
        module = _load_tool("gen_release_manifest")
        self.assertEqual(module.date_from_stamp("20260809v97357a"), "2026-08-09")
        labels = [
            label
            for label, _, _ in module.build_rules(
                "1.9.119", "9.7.357", "20260809v97357a", 1, 0
            )
        ]
        self.assertIn("cut/build date", labels)
        self.assertIn("generated date", labels)
        self.assertIn("shared tier-count/build-stamp line", labels)

        shared_pattern, shared_replacement = next(
            (pattern, replacement)
            for label, pattern, replacement in module.build_rules(
                "1.9.119", "9.7.357", "20260809v97357a", 1, 0
            )
            if label == "shared tier-count/build-stamp line"
        )
        rewritten, count = shared_pattern.subn(
            shared_replacement, "All four tiers share build stamp `20260807v97356a`."
        )
        self.assertEqual(count, 1)
        self.assertEqual(
            rewritten, "All four tiers share build stamp `20260809v97357a`."
        )

    def test_release_manifest_inserts_and_updates_final_suite_evidence(self):
        module = _load_tool("gen_release_manifest")
        source = "## Validation status\n\n| Gate | Status |\n|---|---|\n| sync | PASS |\n"
        inserted, row = module.ensure_test_evidence_row(source, 1512, 88)
        self.assertIn(row, inserted)
        self.assertEqual(inserted.count("| Full pytest suite |"), 1)

        updated, new_row = module.ensure_test_evidence_row(inserted, 1513, 87)
        self.assertIn(new_row, updated)
        self.assertNotIn("1512 passed", updated)
        self.assertEqual(updated.count("| Full pytest suite |"), 1)

    def test_release_manifest_accepts_aligned_validation_separator(self):
        module = _load_tool("gen_release_manifest")
        source = "## Validation status\n\n| Gate | Status |\n| :--- | ---: |\n"
        updated, row = module.ensure_test_evidence_row(source, 8, 2)
        self.assertIn(row, updated)
        self.assertEqual(updated.count("| Full pytest suite |"), 1)

    def test_release_manifest_targets_validation_section_among_multiple_tables(self):
        module = _load_tool("gen_release_manifest")
        source = (
            "## Other gates\n\n| Gate | Status |\n|---|---|\n| other | PASS |\n\n"
            "## Validation status\n\n| Gate | Status |\n|---|---|\n| sync | PASS |\n"
        )
        updated, row = module.ensure_test_evidence_row(source, 8, 2)
        self.assertEqual(updated.count(row), 1)
        self.assertLess(updated.index("## Validation status"), updated.index(row))
        self.assertLess(updated.index(row), updated.index("| sync | PASS |"))

    def test_release_manifest_rejects_missing_validation_anchor(self):
        module = _load_tool("gen_release_manifest")
        with self.assertRaises(ValueError):
            module.ensure_test_evidence_row("# no validation table\n", 1, 0)

    def test_check_mode_does_not_require_cut_only_test_counts(self):
        module = _load_tool("gen_release_manifest")
        source = inspect.getsource(module.main)
        self.assertIn("if args.check and passed is None", source)
        self.assertIn("test_bound_text, canonical_test_row = text", source)

    def test_cut_protocol_assigns_tag_build_to_sync_version(self):
        text = (ROOT / "CUT_PROTOCOL.md").read_text(encoding="utf-8")
        self.assertIn("sync_version.py` owns all three `TAG` identity lines", text)
        self.assertNotIn("One field none of the above tools touch", text)


if __name__ == "__main__":
    unittest.main()
