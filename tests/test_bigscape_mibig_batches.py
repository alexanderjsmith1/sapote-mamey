"""Fixture test for bigscape_mibig_batches.py — no real BiG-SCAPE run.

Asserts the tool (a) keeps only accessions in the bacterial index by default, (b) adds fungal
with --include-fungi, (c) splits into the right number of batch dirs, and (d) emits RUN_ORDER.md
carrying the required `--include-gbk '*'` flag (the non-obvious bit that makes MIBiG load at all).
"""
import json
import os
import subprocess
import sys
import tempfile
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
TOOL = HERE.parent / "tools" / "bigscape_mibig_batches.py"


def _setup(tmp):
    # 5 fake MIBiG GBKs: 3 bacterial (0001-0003), 1 fungal (0004), 1 unlisted (0005)
    gbk = os.path.join(tmp, "gbk"); os.makedirs(gbk)
    for acc in ("BGC0000001", "BGC0000002", "BGC0000003", "BGC0000004", "BGC0000005"):
        open(os.path.join(gbk, f"{acc}.gbk"), "w").write(f"LOCUS {acc}\n//\n")
    idx = os.path.join(tmp, "idx"); os.makedirs(idx)
    json.dump({"entries": [{"accession": a} for a in ("BGC0000001", "BGC0000002", "BGC0000003")]},
              open(os.path.join(idx, "mibig_reference_index.bacterial.json"), "w"))
    json.dump({"entries": [{"accession": "BGC0000004"}]},
              open(os.path.join(idx, "mibig_reference_index.fungal.json"), "w"))
    return gbk, idx


def _run(gbk, idx, out, *extra):
    return subprocess.run(
        [sys.executable, str(TOOL), "--mibig-gbk-dir", gbk, "--index-dir", idx,
         "--out", out, "--batch-size", "2", *extra],
        capture_output=True, text=True, check=True)


def test_prokaryote_only_default():
    with tempfile.TemporaryDirectory() as tmp:
        gbk, idx = _setup(tmp); out = os.path.join(tmp, "batches")
        _run(gbk, idx, out)
        kept = []
        for d in sorted(pathlib.Path(out).glob("batch_*")):
            kept += [p.stem for p in d.glob("*.gbk")]
        assert set(kept) == {"BGC0000001", "BGC0000002", "BGC0000003"}  # fungal + unlisted excluded
        # 3 kept, batch-size 2 -> 2 batch dirs
        assert len(list(pathlib.Path(out).glob("batch_*"))) == 2


def test_include_fungi():
    with tempfile.TemporaryDirectory() as tmp:
        gbk, idx = _setup(tmp); out = os.path.join(tmp, "batches")
        _run(gbk, idx, out, "--include-fungi")
        kept = [p.stem for d in pathlib.Path(out).glob("batch_*") for p in d.glob("*.gbk")]
        assert "BGC0000004" in kept  # fungal now included
        assert "BGC0000005" not in kept  # still excluded (in neither index)


def test_run_order_carries_include_gbk_flag():
    with tempfile.TemporaryDirectory() as tmp:
        gbk, idx = _setup(tmp); out = os.path.join(tmp, "batches")
        _run(gbk, idx, out)
        ro = (pathlib.Path(out) / "RUN_ORDER.md").read_text()
        assert "--include-gbk '*'" in ro   # the required, non-obvious flag
        assert "-r mibig_batches/" in ro    # loaded as references
