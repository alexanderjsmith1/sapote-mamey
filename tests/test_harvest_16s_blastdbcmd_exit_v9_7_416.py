"""A failed blastdbcmd is not the finding "this genus has no 16S references".

Defect (sealed v9.7.414, tools/harvest_16s.py:105-107): only the blastdbcmd BINARY's existence was
checked (`if os.path.exists(bdc)`), never the DATABASE. The returncode was discarded, so a missing,
corrupt or space-pathed BLAST DB — blastdbcmd exits nonzero with empty stdout — fell straight into
the parsing loop.

Concrete wrong output: an EMPTY `<genus>_reference.fasta` is written, `harvest_receipt.txt` records
`reference_records=0`, the console prints `reference 0`, and the tool exits 0. The next step
(phylo_place build-ref) then builds a placement with no reference panel at all, and the receipt
that documents it says zero references were available — a tool failure recorded as a measurement.
The sibling `tools/outgroup_registry.py:135-139` (`_title_index`) does this correctly.

Hermetic: `subprocess` and the optional outgroup_registry import are replaced with stubs; no BLAST
DB, no binary execution, no network. Everything is written under tmp_path.
"""
import importlib.util
import os
import sys
import types

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, "..", "tools")


def _load():
    path = os.path.join(TOOLS, "harvest_16s.py")
    spec = importlib.util.spec_from_file_location("harvest_16s_v415", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class _Proc:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


class _StubOutgroupRegistry:
    @staticmethod
    def get_16s(*a, **k):
        raise SystemExit("no registry row (stub)")


def _harness(monkeypatch, tmp_path, proc, bdc_exists=True):
    """Wire a fully local harvest_16s run whose blastdbcmd behaviour is `proc`."""
    mod = _load()
    auth = tmp_path / "auth.fasta"
    auth.write_text(">AS-001\nACGTACGTACGT\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    bdc = tmp_path / "blastdbcmd"
    if bdc_exists:
        bdc.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    monkeypatch.setitem(sys.modules, "outgroup_registry", _StubOutgroupRegistry)
    monkeypatch.setattr(mod, "subprocess", types.SimpleNamespace(run=lambda *a, **k: proc))
    monkeypatch.setattr(sys, "argv", [
        "harvest_16s.py", "--genus", "Streptomyces", "--strains", "AS-001",
        "--out-dir", str(out_dir), "--authoritative", str(auth),
        "--refseq-db", str(tmp_path / "nonexistent_db"), "--blastdbcmd", str(bdc),
    ])
    return mod, out_dir


def test_blastdbcmd_failure_is_not_reported_as_zero_references(monkeypatch, tmp_path):
    mod, out_dir = _harness(
        monkeypatch, tmp_path,
        _Proc(1, "", "BLAST Database error: No alias or index file found"))
    rc = mod.main()
    receipt = (out_dir / "harvest_receipt.txt").read_text(encoding="utf-8")
    assert rc == 3, (
        f"exit {rc!r}: a failed blastdbcmd must make the run nonzero, not exit 0 with a receipt")
    assert "reference_records=0" not in receipt, (
        "'reference_records=0' claims the genus has no 16S references; the database was never "
        "read at all")
    assert "reference_status=ERROR" in receipt, receipt
    assert not (out_dir / "Streptomyces_reference.fasta").exists(), (
        "an empty reference FASTA must not be written from a failed database read")


def test_missing_blastdbcmd_binary_is_also_recorded_and_nonzero(monkeypatch, tmp_path):
    mod, out_dir = _harness(monkeypatch, tmp_path, _Proc(0, ""), bdc_exists=False)
    rc = mod.main()
    receipt = (out_dir / "harvest_receipt.txt").read_text(encoding="utf-8")
    assert rc == 3
    assert "reference_records=0" not in receipt
    assert "reference_status=ERROR" in receipt, receipt


def test_successful_blastdbcmd_still_builds_and_counts_the_panel(monkeypatch, tmp_path):
    """Regression guard: the healthy path is unchanged and still exits 0."""
    stdout = (">NR_000001.1 Streptomyces coelicolor strain A3(2) 16S ribosomal RNA\nACGT\n"
              ">NR_000002.1 Nocardia farcinica strain X 16S ribosomal RNA\nTTTT\n")
    mod, out_dir = _harness(monkeypatch, tmp_path, _Proc(0, stdout))
    rc = mod.main()
    receipt = (out_dir / "harvest_receipt.txt").read_text(encoding="utf-8")
    assert rc == 0
    assert "reference_records=1" in receipt, receipt
    assert "reference_status=ok" in receipt
    panel = (out_dir / "Streptomyces_reference.fasta").read_text(encoding="utf-8")
    assert "Streptomyces coelicolor" in panel and "Nocardia" not in panel
