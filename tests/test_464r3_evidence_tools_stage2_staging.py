"""The Stage 2 overlay never removes a staging folder it did not create, and never writes inside its inputs."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from mamey.stage2_overlay import build, sha256_file
from tests.test_stage2_overlay import POLICY, Stage2OverlayTests


class Stage2StagingTests(unittest.TestCase):
    def _kwargs(self, f, out):
        return dict(base_report_root=f["base"], target_ledger=f["target"],
                    expected_target_sha256=sha256_file(f["target"]), review_root=f["review"],
                    source_manifest=f["manifest"], expected_manifest_sha256=sha256_file(f["manifest"]),
                    analysis_paths=[f["analysis"]], disposition_paths=[f["disposition"]], out_root=out,
                    **POLICY, **f["source_preflight"])

    def test_existing_staging_folder_is_refused_and_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Stage2OverlayTests.fixture(None, Path(tmp)); out = Path(tmp) / "out"
            staging = out.with_name(f".{out.name}.staging-{os.getpid()}")
            staging.mkdir()
            keep = staging / "someone_elses_file.txt"; keep.write_text("keep me\n")
            with self.assertRaisesRegex(FileExistsError, "Staging path already exists"):
                build(**self._kwargs(f, out))
            self.assertEqual(keep.read_text(), "keep me\n")
            self.assertFalse(out.exists())

    def test_output_nested_under_base_report_root_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Stage2OverlayTests.fixture(None, Path(tmp)); out = f["base"] / "overlay"
            with self.assertRaisesRegex(ValueError, "outside the protected input root"):
                build(**self._kwargs(f, out))
            self.assertFalse(out.exists())

    def test_output_nested_under_review_root_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Stage2OverlayTests.fixture(None, Path(tmp)); out = f["review"] / "overlay"
            with self.assertRaisesRegex(ValueError, "outside the protected input root"):
                build(**self._kwargs(f, out))
