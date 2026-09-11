"""clade_decontam must FAIL CLOSED when makeblastdb fails, and must never put a user filename in a BLAST path.

Measured 2026-09-08 with BLAST+ 2.16.0: a reference named "AS78 assembly.fasta" makes makeblastdb
exit 1 writing nothing, and blastn then exits 3 with EMPTY stdout. In sealed v9.7.413 both calls
ignored their returncodes, so the empty output parsed as "no hits", `target_bits`/`contam_bits` were
{}, `assign_contig` fell through to the GC rule and KEPT every contig — the tool certified an
assembly clean without having done the comparison. The .415 draft added `check=True` (a crash is
better than a wrong "ok") but kept `os.path.basename(ref_fa)` in the db path, so the same input still
fails — loudly now, but caused by the tool itself.

The first version of this test looked for the TOKEN "returncode" near the call. That is a test of
spelling: `check=True` checks the returncode without ever writing the word, so the test failed on a
correct implementation. Both tests below are behavioural.

Hermetic: `subprocess.run` is replaced INSIDE the loaded module; no BLAST binary runs.
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent / "deliverable_tools" / "clade_decontam.py"


def _load():
    if not TOOL.exists():                       # pragma: no cover - environment guard
        pytest.skip(f"tool not present at {TOOL}")
    spec = importlib.util.spec_from_file_location("_clade_decontam_under_test", TOOL)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


class _Proc:
    def __init__(self, rc, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


def test_makeblastdb_failure_raises_instead_of_returning_no_hits(tmp_path, monkeypatch):
    """rc=1 from makeblastdb must surface as an exception — any exception — never as {} 'no hits'."""
    m = _load()
    calls = []

    def fake_run(argv, **kw):
        calls.append(argv)
        if "makeblastdb" in str(argv[0]):
            if kw.get("check"):
                raise m.subprocess.CalledProcessError(1, argv)
            return _Proc(1, "", "BLAST Database creation error: No such file")
        return _Proc(3, "", "")                 # blastn with no db: rc 3, empty stdout

    monkeypatch.setattr(m.subprocess, "run", fake_run)
    with pytest.raises(Exception):
        m.summed_bitscores_vs_ref(str(tmp_path / "asm.fa"), str(tmp_path / "ref.fa"),
                                  "blastn", "makeblastdb", str(tmp_path))
    assert calls and "makeblastdb" in str(calls[0][0])


def test_db_path_never_carries_the_user_reference_filename(tmp_path, monkeypatch):
    """The `-out` argument to makeblastdb must not contain the reference basename (spaces travel)."""
    m = _load()
    seen = {}

    def fake_run(argv, **kw):
        if "makeblastdb" in str(argv[0]):
            seen["out"] = argv[argv.index("-out") + 1]
            return _Proc(0)
        return _Proc(0, "")

    monkeypatch.setattr(m.subprocess, "run", fake_run)
    ref = str(tmp_path / "AS78 assembly.fasta")
    m.summed_bitscores_vs_ref(str(tmp_path / "asm.fa"), ref, "blastn", "makeblastdb", str(tmp_path))
    assert "out" in seen
    assert "AS78 assembly" not in seen["out"] and " " not in seen["out"], (
        f"db path {seen['out']!r} carries the user's filename; a space in it defeats BLAST silently "
        f"(sealed) or crashes the run (.415 draft)")
