"""Restaging an input never removes an earlier attempt or other files under _stage/."""
from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("_intake_stage_464r3c", ROOT / "tools" / "intake_harness.py")
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)


def _zip(path: Path) -> Path:
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("one/region001.gbk", "LOCUS x\n  ORGANISM  Synthetic organism\n//\n")
    return path


def test_prior_stage_and_foreign_files_survive_a_retry(tmp_path):
    stage = tmp_path / "_stage"
    prior = stage / "SYNTH"
    prior.mkdir(parents=True)
    (prior / "partial_evidence.log").write_text("first attempt", encoding="utf-8")
    old_zip = stage / "SYNTH.input.zip"
    old_zip.write_bytes(b"earlier staged zip")
    source = _zip(tmp_path / "in.zip")
    kind, staged, cb, org = H.detect_and_stage(str(source), str(stage), "SYNTH")
    assert kind == "ANTISMASH"
    assert (prior / "partial_evidence.log").read_text(encoding="utf-8") == "first attempt"
    assert old_zip.read_bytes() == b"earlier staged zip"
    second = H.detect_and_stage(str(source), str(stage), "SYNTH")[1]
    assert Path(staged).is_file() and Path(second).is_file() and staged != second
