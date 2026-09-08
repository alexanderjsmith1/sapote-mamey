from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("patch_packet_preflight", ROOT / "tools" / "patch_packet_preflight.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
inspect_packet = MODULE.inspect_packet


class PatchPacketPreflightTests(unittest.TestCase):
    def packet(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name) / "P000-example"
        (root / "candidate_files").mkdir(parents=True)
        (root / "PATCH_CARD.md").write_text("# card\n", encoding="utf-8")
        (root / "candidate_files" / "feature.py").write_text("VALUE = 1\n", encoding="utf-8")
        return temp, root

    def test_minimal_candidate_passes(self):
        temp, root = self.packet(); self.addCleanup(temp.cleanup)
        self.assertEqual("PASS", inspect_packet(root, 100_000, 50_000)["status"])

    def test_environment_directory_fails(self):
        temp, root = self.packet(); self.addCleanup(temp.cleanup)
        (root / "working" / "tooling" / "envs").mkdir(parents=True)
        (root / "working" / "tooling" / "envs" / "binary").write_bytes(b"x")
        codes = {row["code"] for row in inspect_packet(root, 100_000, 50_000)["findings"]}
        self.assertIn("FORBIDDEN_DIRECTORY_CLASS", codes)

    def test_oversized_file_and_packet_fail(self):
        temp, root = self.packet(); self.addCleanup(temp.cleanup)
        (root / "candidate_files" / "payload.bin").write_bytes(b"x" * 120)
        codes = {row["code"] for row in inspect_packet(root, 100, 100)["findings"]}
        self.assertEqual({"FILE_TOO_LARGE", "PACKET_TOO_LARGE"}, codes)

    def test_copied_release_baseline_fails(self):
        temp, root = self.packet(); self.addCleanup(temp.cleanup)
        baseline = root / "working" / "base"; baseline.mkdir(parents=True)
        (baseline / "SOURCE_CHECKSUMS_SHA256.txt").write_text("x\n", encoding="utf-8")
        (baseline / "TIER_MANIFEST.json").write_text("{}\n", encoding="utf-8")
        codes = {row["code"] for row in inspect_packet(root, 100_000, 50_000)["findings"]}
        self.assertIn("COPIED_RELEASE_BASELINE", codes)

    def test_missing_delta_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "P000-empty"; root.mkdir()
            (root / "PATCH_CARD.md").write_text("# card\n", encoding="utf-8")
            codes = {row["code"] for row in inspect_packet(root, 100_000, 50_000)["findings"]}
            self.assertIn("IMPLEMENTATION_DELTA_MISSING", codes)

    def test_receipt_never_exposes_absolute_packet_path(self):
        temp, root = self.packet(); self.addCleanup(temp.cleanup)
        result = inspect_packet(root, 100_000, 50_000)
        self.assertNotIn(str(root.parent), str(result))
        self.assertEqual("RELATIVE_ONLY", result["path_disclosure"])

    def test_ordinary_unified_diff_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "P000-diff"; root.mkdir()
            (root / "PATCH_CARD.md").write_text("# card\n", encoding="utf-8")
            (root / "feature.patch").write_text(
                "--- a/mamey/feature.py\n+++ b/mamey/feature.py\n@@ -1 +1 @@\n-old\n+new\n",
                encoding="utf-8",
            )
            self.assertEqual("PASS", inspect_packet(root, 100_000, 50_000)["status"])

    def test_forbidden_cache_path_inside_diff_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "P000-diff"; root.mkdir()
            (root / "PATCH_CARD.md").write_text("# card\n", encoding="utf-8")
            (root / "feature.patch").write_text(
                "--- a/mamey/__pycache__/feature.cpython-312.pyc\n"
                "+++ b/mamey/__pycache__/feature.cpython-312.pyc\n",
                encoding="utf-8",
            )
            codes = {row["code"] for row in inspect_packet(root, 100_000, 50_000)["findings"]}
            self.assertIn("FORBIDDEN_PATCH_PAYLOAD_PATH", codes)

    def test_unappliable_binary_diff_marker_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "P000-diff"; root.mkdir()
            (root / "PATCH_CARD.md").write_text("# card\n", encoding="utf-8")
            (root / "feature.patch").write_text(
                "Binary files a/assets/panel.bin and b/assets/panel.bin differ\n",
                encoding="utf-8",
            )
            codes = {row["code"] for row in inspect_packet(root, 100_000, 50_000)["findings"]}
            self.assertIn("UNAPPLICABLE_BINARY_DIFF_MARKER", codes)


if __name__ == "__main__":
    unittest.main()
