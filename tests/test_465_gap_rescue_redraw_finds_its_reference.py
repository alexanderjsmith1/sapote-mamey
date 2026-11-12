"""9.7.465: --redraw finds the reference the run used, not only one in --mibig-dir.

Fail-before on sealed 9.7.464: redraw() opened `--mibig-dir/<receipt reference>` and crashed with FileNotFoundError when
the run had used a GenBank kept elsewhere (a non-MIBiG accession in a references/ folder). Pass-after: the reference is
looked for in --reference, the receipt's recorded path, --mibig-dir and references/ beside the run, in that order; a file
whose checksum differs from the run's recorded one is skipped; nothing found is a REFERENCE_NOT_FOUND refusal that lists
where it looked. record_inputs records the path.
"""
import hashlib
import inspect
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
if "mamey" not in sys.modules:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

D = pytest.importorskip("gap_directed_rescue")


def _setup(tmp, sha=None, path=None):
    run = tmp / "batch" / "run1"
    run.mkdir(parents=True)
    inputs = {k: v for k, v in (("reference_sha256", sha), ("reference_path", path)) if v}
    receipt = {"core": "S / NODE_1_length_9000_cov_10.0 / region001 / BGC001", "reference": "XY000001.1.gbk",
               **({"inputs": inputs} if inputs else {})}
    return run, receipt


def test_references_folder_beside_the_run_is_found(tmp_path):
    run, receipt = _setup(tmp_path)
    (tmp_path / "batch" / "references").mkdir()
    ref = tmp_path / "batch" / "references" / "XY000001.1.gbk"
    ref.write_text("LOCUS ref\n")
    assert D.resolve_reference(run, receipt, tmp_path / "mibig") == ref


def test_order_and_checksum(tmp_path):
    good = b"the run's reference"
    run, receipt = _setup(tmp_path, sha=hashlib.sha256(good).hexdigest())
    mibig = tmp_path / "mibig"
    mibig.mkdir()
    (mibig / "XY000001.1.gbk").write_bytes(b"another record of the same name")
    given = tmp_path / "given.gbk"
    given.write_bytes(good)
    assert D.resolve_reference(run, receipt, mibig, given) == given          # --reference first, checksum agrees
    with pytest.raises(SystemExit, match="REFERENCE_NOT_FOUND") as e:
        D.resolve_reference(run, receipt, mibig)                             # same name, wrong bytes: never taken
    assert "different checksum" in str(e.value) and "references" in str(e.value)


def test_the_receipt_path_is_used_and_recorded(tmp_path):
    ref = tmp_path / "elsewhere" / "XY000001.1.gbk"
    ref.parent.mkdir()
    ref.write_text("LOCUS ref\n")
    run, receipt = _setup(tmp_path, path=str(ref))
    assert D.resolve_reference(run, receipt, None) == ref
    zip_path = tmp_path / "S.zip"
    zip_path.write_bytes(b"zip")
    rec = D.record_inputs(run, {"core": receipt["core"]}, zip_path, ref)
    assert rec["inputs"]["reference_path"] == str(ref.resolve())
    assert json.loads((run / "gap_rescue_receipt.json").read_text())["inputs"]["reference_path"] == str(ref.resolve())


def test_redraw_passes_reference_through():
    assert "reference=a.reference" in inspect.getsource(D.main)
    assert "resolve_reference(folder, receipt, mibig_dir, reference)" in inspect.getsource(D.redraw)


def test_a_given_reference_is_used_or_refused_never_passed_over(tmp_path):
    good = b"the run's reference"
    run, receipt = _setup(tmp_path, sha=hashlib.sha256(good).hexdigest())
    (tmp_path / "batch" / "references").mkdir()
    (tmp_path / "batch" / "references" / "XY000001.1.gbk").write_bytes(good)   # a right file exists elsewhere
    wrong = tmp_path / "wrong.gbk"
    wrong.write_bytes(b"another record")
    with pytest.raises(SystemExit, match="REFERENCE_NOT_FOUND: --reference .*different checksum"):
        D.resolve_reference(run, receipt, None, wrong)
    with pytest.raises(SystemExit, match="REFERENCE_NOT_FOUND: --reference .*not a file"):
        D.resolve_reference(run, receipt, None, tmp_path / "missing.gbk")


def test_old_receipt_without_checksum_refuses_differing_same_named_files(tmp_path):
    run, receipt = _setup(tmp_path)                       # no inputs: a receipt written before receipts recorded their inputs
    mibig = tmp_path / "mibig"
    mibig.mkdir()
    (mibig / "XY000001.1.gbk").write_bytes(b"one record")
    (tmp_path / "batch" / "references").mkdir()
    beside = tmp_path / "batch" / "references" / "XY000001.1.gbk"
    beside.write_bytes(b"one record")
    assert D.resolve_reference(run, receipt, mibig) == mibig / "XY000001.1.gbk"   # same bytes: taken
    beside.write_bytes(b"another record")
    with pytest.raises(SystemExit, match="REFERENCE_AMBIGUOUS"):
        D.resolve_reference(run, receipt, mibig)
