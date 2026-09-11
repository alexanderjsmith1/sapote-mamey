"""Tier-2 reference dedup must fail closed, and must never be reported as if it had run.

Defect (sealed v9.7.414, tools/phylo_refset.py:150-153): neither the makeblastdb nor the blastn
returncode inside `dedup()`'s Tier-2 block was read, while the SAME FILE's `marker_blast()`
(lines 224-226) does check `res.returncode` — an internal inconsistency, not an oversight of
style.

Concrete wrong output: a failed BLAST returns empty stdout, the union-find sees zero pairs, every
record becomes its own cluster and Tier 2 collapses NOTHING — yet line ~206 still prints
`[dedup] 34 -> 25 references (9 duplicates collapsed)` from Tier 1 alone. A reference set that was
never screened for sequence-level duplicates (the same physical type strain deposited under two
culture-collection IDs — sampsonii ATCC 25495 vs NRRL B-12325) goes into a tree as if it had been,
and the operator's receipt says so.

Hermetic: `subprocess` and `_bin` are replaced inside the module object; no BLAST binary is
resolved or run, no database is built, no network, no workspace fixture.
"""
import importlib.util
import os
import sys
import types

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, "..", "tools")

# Two records that SURVIVE Tier 1 (same species, different strain tokens) so Tier 2 is reached.
RECS = [
    ("Streptomyces_sampsonii_strain_ATCC_25495_NR_041066", "ACGT" * 350),
    ("Streptomyces_sampsonii_strain_NRRL_B_12325_NR_112345", "ACGT" * 350),
]


def _load():
    path = os.path.join(TOOLS, "phylo_refset.py")
    spec = importlib.util.spec_from_file_location("phylo_refset_v415", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class _Proc:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def _fake_blast(monkeypatch, mod, makeblastdb_rc=0, blastn_rc=0):
    monkeypatch.setattr(mod, "_bin", lambda name: f"/fake/bin/{name}")

    def run(cmd, *a, **k):
        rc = makeblastdb_rc if "makeblastdb" in str(cmd[0]) else blastn_rc
        return _Proc(rc, "", "BLAST Database error: Database memory map file error")

    monkeypatch.setattr(mod, "subprocess", types.SimpleNamespace(run=run))


def test_failed_makeblastdb_refuses_instead_of_collapsing_nothing(monkeypatch):
    mod = _load()
    _fake_blast(monkeypatch, mod, makeblastdb_rc=1)
    with pytest.raises(SystemExit) as exc:
        mod.dedup(RECS, report=None, verbose=False)
    assert "makeblastdb" in str(exc.value)


def test_failed_blastn_refuses_instead_of_collapsing_nothing(monkeypatch):
    mod = _load()
    _fake_blast(monkeypatch, mod, makeblastdb_rc=0, blastn_rc=3)
    with pytest.raises(SystemExit) as exc:
        mod.dedup(RECS, report=None, verbose=False)
    assert "blastn" in str(exc.value)


def test_summary_line_declares_which_tiers_actually_ran(monkeypatch, capsys):
    """The blast env being absent is a legitimate skip — but the receipt must SAY so."""
    mod = _load()
    monkeypatch.setattr(mod, "_bin", lambda name: "")     # blast env not found -> Tier 2 skipped
    mod.dedup(RECS, report=None, verbose=True)
    lines = [ln for ln in capsys.readouterr().out.splitlines()
             if ln.startswith("[dedup]") and "duplicates collapsed" in ln]
    assert lines, "the dedup summary line must still be printed"
    assert "TIER 1 ONLY" in lines[0].upper(), (
        f"summary line {lines[0]!r} reports a collapse count without saying that the "
        "sequence-level tier never ran — indistinguishable from a completed two-tier dedup")


def test_successful_blast_still_dedups(monkeypatch):
    """Regression guard: a healthy Tier 2 still collapses the con-specific pair."""
    mod = _load()
    monkeypatch.setattr(mod, "_bin", lambda name: f"/fake/bin/{name}")
    hits = "s0\ts1\t99.9\t1400\t1400\t1400\ns1\ts0\t99.9\t1400\t1400\t1400\n"

    def run(cmd, *a, **k):
        return _Proc(0, hits if "blastn" in str(cmd[0]) else "", "")

    monkeypatch.setattr(mod, "subprocess", types.SimpleNamespace(run=run))
    kept, collapses = mod.dedup(RECS, report=None, verbose=False)
    assert len(kept) == 1 and any(c["tier"] == 2 for c in collapses)
