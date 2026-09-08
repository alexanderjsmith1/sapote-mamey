"""test_bigscape_chunk_cli.py — caller/callee CLI interface test for the memory-safe
BiG-SCAPE chunk path (AMBER_TH3, .353 candidate).

The defect: ``tools/bigscape_pipeline.py`` (the caller) invoked
``tools/bigscape_mibig_batches.py`` (the callee) with ``--mibig-dir`` and without
``--index-dir`` — flags the callee does not accept — so the whole ``--chunk-mibig`` path died
at argparse (exit 2) before clustering. The fix corrects the caller to pass the callee's real
contract: ``--mibig-gbk-dir``, ``--index-dir``, ``--out``, ``--batch-size``.

This test proves the two sides now agree:

  (1) CALLER side — the FIXED bigscape_pipeline.py source passes the four correct flags to the
      batcher (and no longer the bare ``--mibig-dir`` in that call).
  (2) CALLEE side — bigscape_mibig_batches.py PARSES/ACCEPTS that exact argument list against a
      tiny fixture (one .gbk + a minimal bacterial index JSON) with NO argparse error (exit != 2).
  (3) REGRESSION — the OLD flag ``--mibig-dir`` is REJECTED by the callee (exit == 2), so the
      pre-fix invocation is provably broken.

Fail-closed: on the pre-fix caller, assertion (1) fails (the call still uses ``--mibig-dir``).
stdlib + pytest only; runs the callee as a subprocess (no BiG-SCAPE binary needed).
"""
import json
import os
import re
import subprocess
import sys

import pytest


def _find_tool(name):
    env = os.environ.get("MAMEY_TOOLS_DIR")
    if env and os.path.isfile(os.path.join(env, name)):
        return os.path.join(env, name)
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        cand = os.path.join(here, "tools", name)
        if os.path.isfile(cand):
            return cand
        here = os.path.dirname(here)
    return None


_BATCHER = _find_tool("bigscape_mibig_batches.py")
_PIPELINE = _find_tool("bigscape_pipeline.py")
pytestmark = pytest.mark.skipif(
    _BATCHER is None or _PIPELINE is None,
    reason="bigscape tools not locatable",
)


def _make_fixture(tmp_path):
    gbk_dir = tmp_path / "mibig_gbks"
    gbk_dir.mkdir()
    # name the GBK to match the one accession in the fake index so a batch is actually kept
    (gbk_dir / "BGC0000001.gbk").write_text("LOCUS       BGC0000001\n//\n", encoding="utf-8")
    index_dir = tmp_path / "mibig_index"
    index_dir.mkdir()
    (index_dir / "mibig_reference_index.bacterial.json").write_text(
        json.dumps({"entries": [{"accession": "BGC0000001", "domain_of_life": "Bacteria"}]}),
        encoding="utf-8",
    )
    out_dir = tmp_path / "mibig_batches"
    return str(gbk_dir), str(index_dir), str(out_dir)


# ── (1) CALLER: the fixed pipeline passes the callee's real contract ───────────────────
def test_caller_passes_correct_flags_to_batcher():
    src = open(_PIPELINE, encoding="utf-8").read()
    # isolate the actual run([...]) invocation of the batcher (anchor on the tool() call,
    # not the docstring mention) and read to the end of the argument list.
    m = re.search(r'tool\(\s*"bigscape_mibig_batches\.py"\s*\).*?\]\)', src, re.S)
    assert m, "could not find the bigscape_mibig_batches.py invocation in the pipeline"
    call = m.group(0)
    assert "--mibig-gbk-dir" in call, "caller does not pass --mibig-gbk-dir (still broken)"
    assert "--index-dir" in call, "caller does not pass --index-dir (still broken)"
    assert "--out" in call and "--batch-size" in call
    # the pre-fix bug: the batcher call used the bare '--mibig-dir'
    assert '"--mibig-dir"' not in call, "caller still passes the rejected --mibig-dir to the batcher"


# ── (2) CALLEE: accepts the fixed argument list (no argparse error) ───────────────────
def test_callee_accepts_fixed_arg_list(tmp_path):
    gbk_dir, index_dir, out_dir = _make_fixture(tmp_path)
    # the EXACT flag set the fixed pipeline passes to the batcher
    argv = [sys.executable, _BATCHER,
            "--mibig-gbk-dir", gbk_dir,
            "--index-dir", index_dir,
            "--out", out_dir,
            "--batch-size", "50"]
    proc = subprocess.run(argv, capture_output=True, text=True)
    # exit 2 == argparse error; anything else means the args parsed/were accepted
    assert proc.returncode != 2, f"batcher rejected the fixed args:\n{proc.stderr}"
    # the fixture has one matching accession -> a batch is kept -> clean exit 0
    assert proc.returncode == 0, f"batcher did not run cleanly (rc={proc.returncode}):\n{proc.stderr}"
    assert os.path.isdir(os.path.join(out_dir, "batch_01")), "no batch dir produced"


# ── (3) REGRESSION: the old flag is rejected ──────────────────────────────────────────
def test_callee_rejects_old_mibig_dir_flag(tmp_path):
    gbk_dir, index_dir, out_dir = _make_fixture(tmp_path)
    argv = [sys.executable, _BATCHER,
            "--mibig-dir", gbk_dir,           # the OLD/broken flag
            "--out", out_dir,
            "--batch-size", "50"]
    proc = subprocess.run(argv, capture_output=True, text=True)
    assert proc.returncode == 2, \
        f"old --mibig-dir flag was NOT rejected (rc={proc.returncode}); interface not tightened"
    assert "--mibig-dir" in proc.stderr or "required" in proc.stderr
