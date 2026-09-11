"""A failed BLAST is not the finding "there are no 16S references here".

DEFECT, measured 2026-09-08 by AST over the seven loose 16S tools: **6 of 8 `subprocess.run` call
sites never inspected a returncode.** One of the six could not — `Tools/audit_16s_merges.py:48`
took `.stdout` off the end of the `subprocess.run(...)` expression, so the returncode was
unreachable by construction.

WHY THIS IS NOT A STYLE POINT. NCBI BLAST+ re-parses its own `-db`, `-in` and `-query` strings and
cannot open a path containing a SPACE. Reproduced with this project's own binaries:

    makeblastdb -out "<...>/space test/blastdb/tag"   rc=1, wrote nothing
    blastn      -db  "<...>/space test/blastdb/tag"   rc=3, 0 bytes on stdout

Nearly every folder in the workspace these tools were written in has a space in it — `16S
Database/`, `AS Strain Master/`, `September 6 2026/`, `September 7 2026/EXTERNAL_16S_2026-09/` —
so the failure is the ORDINARY case. Unchecked, each one renders as a result:

  * `phylo_16s_panel.rank_references` returns `[]`, and the panel is written with its queries and
    no references at all, printed as `type requested 300 taken 0 (pool 0)`.
  * `phylo_16s_from_genome.extract` returns `[]`, and every genome is reported as
    `NO 16S >= 1200 nt` — a tool failure written out as "these assemblies carry no 16S gene".

Two defences are asserted here, in order: the spaced path is STAGED so BLAST never sees it, and
any nonzero exit becomes a typed refusal. Either is acceptable; silently yielding zero hits is not.

Hermetic: `subprocess.run` is replaced, so no BLAST binary runs and nothing touches the network or
the real 279 MiB store. Every path is under tmp_path.
"""
from __future__ import annotations

import importlib.util
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def _load(name: str):
    path = TOOLS / name
    if not path.is_file():
        pytest.fail(f"{name} is not in tools/ — the 16S workflow was not landed in the bundle")
    spec = importlib.util.spec_from_file_location(f"_v415blast_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def blast_bin(tmp_path, monkeypatch):
    """A directory of stand-in BLAST binaries. They are never executed — `subprocess.run` is
    replaced — but they must EXIST so the resolver returns a path instead of refusing."""
    d = tmp_path / "blastbin"
    d.mkdir()
    for exe in ("blastn", "makeblastdb", "blastdbcmd"):
        p = d / exe
        p.write_text("#!/bin/sh\nexit 0\n")
        p.chmod(0o755)
    monkeypatch.setenv("BLAST_BIN", str(d))
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    return d


# The BLAST flags whose VALUE is a path. `-outfmt "6 qseqid sseqid pident length"` legitimately
# contains spaces and is not a path, so a blanket sweep for spaces would flag it; only the
# path-bearing arguments matter, because those are the ones BLAST+ re-parses and cannot open.
PATH_FLAGS = ("-db", "-in", "-out", "-query", "-subject")


def spaced_path_args(cmd):
    return [v for f, v in zip(cmd, cmd[1:]) if f in PATH_FLAGS and " " in v]


def _recorder(*procs):
    """Return (fake_run, calls). Successive calls get successive `procs`; the last repeats."""
    calls = []

    def fake_run(cmd, *a, **kw):
        calls.append([str(x) for x in cmd])
        return procs[min(len(calls) - 1, len(procs) - 1)]
    return fake_run, calls


# --------------------------------------------------------------- the panel writer

def _panel_db(tmp_path):
    con = sqlite3.connect(tmp_path / "panel.sqlite")
    con.execute("CREATE TABLE record (acc_base TEXT, acc_version TEXT, definition TEXT, seq TEXT, "
                "binomial TEXT, genus TEXT, source TEXT, uncultured INT, designation TEXT)")
    con.execute("CREATE TABLE record_strain (acc_base TEXT, strain_uid TEXT)")
    con.executemany("INSERT INTO record VALUES (?,?,?,?,?,?,?,0,?)", [
        ("NR_000001", "NR_000001.1", "Streptomyces coelicolor strain A3(2) 16S ribosomal RNA",
         "ACGT" * 400, "Streptomyces coelicolor", "Streptomyces", "refseq_type", ""),
        ("NR_000002", "NR_000002.1", "Streptomyces griseus strain DSM 40236 16S ribosomal RNA",
         "ACGT" * 400, "Streptomyces griseus", "Streptomyces", "refseq_type", ""),
    ])
    con.commit()
    return con


QUERIES = [("PX000001", "Streptomyces sp. AS-001 16S ribosomal RNA", "ACGT" * 400, "AS-001")]


def test_a_failed_makeblastdb_is_a_refusal_not_an_empty_reference_pool(
        monkeypatch, tmp_path, blast_bin):
    """rc=1 writing nothing is what a spaced -out does. Unchecked it becomes `pool 0`."""
    mod = _load("phylo_16s_panel.py")
    fake, _ = _recorder(_Proc(1, "", "BLAST options error: File ... does not exist"))
    monkeypatch.setattr(subprocess, "run", fake)
    con = _panel_db(tmp_path)
    with pytest.raises(SystemExit) as e:
        mod.rank_references(con, QUERIES, ("refseq_type",), set(), None)
    msg = str(e.value)
    assert "makeblastdb" in msg and "exit 1" in msg, msg
    assert "not a result" in msg or "no hits" in msg, (
        f"the refusal must say the empty output is not a finding; got: {msg[:200]}")


def test_a_failed_blastn_is_a_refusal_not_zero_references(monkeypatch, tmp_path, blast_bin):
    """rc=3 with EMPTY stdout is what a spaced -db does. Unchecked, `best` stays empty and
    rank_references returns [] — indistinguishable from a database with no comparators."""
    mod = _load("phylo_16s_panel.py")
    fake, _ = _recorder(_Proc(0, ""), _Proc(3, "", "BLAST Database error: Database memory map "
                                                   "file error"))
    monkeypatch.setattr(subprocess, "run", fake)
    con = _panel_db(tmp_path)
    with pytest.raises(SystemExit) as e:
        mod.rank_references(con, QUERIES, ("refseq_type",), set(), None)
    msg = str(e.value)
    assert "blastn" in msg and "exit 3" in msg, msg
    assert "Database memory map file error" in msg, (
        "the refusal must carry the tool's own stderr; that text is the only clue BLAST gives, "
        "and it does not mention paths at all")


def test_a_spaced_TMPDIR_is_refused_rather_than_silently_defeating_the_staging(
        monkeypatch, tmp_path, blast_bin):
    """The staging strategy has one hole and it must not be a quiet one.

    `tempfile` honours `$TMPDIR`, so a `$TMPDIR` that itself contains a space puts the panel's
    reference FASTA and its temporary BLAST database behind a spaced path again — and BLAST fails
    exactly as it would have unstaged, with rc=1/rc=3 and empty output. The panel then reports
    `pool 0`. This asserts the workdir is CHECKED, not assumed.
    """
    import tempfile as _tempfile
    spaced = tmp_path / "tmp dir"
    spaced.mkdir()
    monkeypatch.setenv("TMPDIR", str(spaced))
    monkeypatch.setattr(_tempfile, "tempdir", str(spaced))   # gettempdir() caches at first use
    mod = _load("phylo_16s_panel.py")
    fake, calls = _recorder(_Proc(0, ""), _Proc(0, ""))
    monkeypatch.setattr(subprocess, "run", fake)
    con = _panel_db(tmp_path)
    with pytest.raises(SystemExit) as e:
        mod.rank_references(con, QUERIES, ("refseq_type",), set(), None)
    msg = str(e.value)
    assert "TMPDIR" in msg or "space" in msg.lower(), msg
    assert not [a for c in calls for a in spaced_path_args(c)], (
        "the refusal must come BEFORE handing BLAST a spaced path, not after it fails")


def test_a_healthy_panel_blast_still_ranks_its_references(monkeypatch, tmp_path, blast_bin):
    """REGRESSION GUARD (passes on both trees): the fix must not change the working path."""
    mod = _load("phylo_16s_panel.py")
    fake, _ = _recorder(_Proc(0, ""),
                        _Proc(0, "PX000001\tNR_000001\t99.1\t1500\n"
                                 "PX000001\tNR_000002\t97.4\t1490\n"))
    monkeypatch.setattr(subprocess, "run", fake)
    con = _panel_db(tmp_path)
    out = mod.rank_references(con, QUERIES, ("refseq_type",), set(), None)
    assert [r[0] for r in out] == ["NR_000001", "NR_000002"], out
    assert out[0][5] == 99.1 and out[0][6] == 1500


# --------------------------------------------------------------- 16S out of a genome

def _spaced_genome(tmp_path):
    """A genome in a folder with a space, which is how they actually sit in this workspace
    (`September 7 2026/EXTERNAL_16S_2026-09/`)."""
    d = tmp_path / "September 7 2026" / "EXTERNAL_16S"
    d.mkdir(parents=True)
    g = d / "AmelKG_E11A.fna"
    g.write_text(">contig_1\n" + "ACGT" * 500 + "\n")
    return g


def _spaced_blastdb(tmp_path):
    d = tmp_path / "16S Database"
    d.mkdir(parents=True, exist_ok=True)
    prefix = d / "16S_ribosomal_RNA"
    for ext in (".nin", ".nsq", ".nhr"):
        (d / (prefix.name + ext)).write_bytes(b"\x00")
    return str(prefix)


def test_a_spaced_genome_and_database_never_reach_blast(monkeypatch, tmp_path, blast_bin):
    """The direct proof. BLAST+ exits 3 on a spaced path with empty stdout, which `extract`
    reports as `NO 16S >= 1200 nt` for every genome in the run."""
    mod = _load("phylo_16s_from_genome.py")
    monkeypatch.setattr(mod, "DB", _spaced_blastdb(tmp_path))
    fake, calls = _recorder(_Proc(0, ""))
    monkeypatch.setattr(subprocess, "run", fake)
    mod.extract(str(_spaced_genome(tmp_path)), 1200, False, 1)
    assert calls, "blastn was never invoked"
    spaced = spaced_path_args(calls[0])
    assert not spaced, (
        f"these arguments still carry a space and NCBI BLAST+ cannot open them: {spaced}. "
        f"Stage them behind a space-free path, or the run reports every genome as carrying no 16S.")


def test_a_failed_extraction_blast_is_a_refusal_not_a_genome_without_16s(
        monkeypatch, tmp_path, blast_bin):
    mod = _load("phylo_16s_from_genome.py")
    monkeypatch.setattr(mod, "DB", _spaced_blastdb(tmp_path))
    fake, _ = _recorder(_Proc(3, "", "BLAST Database error: Database memory map file error"))
    monkeypatch.setattr(subprocess, "run", fake)
    with pytest.raises(SystemExit) as e:
        mod.extract(str(_spaced_genome(tmp_path)), 1200, False, 1)
    assert "exit 3" in str(e.value), str(e.value)


def test_a_healthy_extraction_still_returns_the_span(monkeypatch, tmp_path, blast_bin):
    """REGRESSION GUARD (passes on both trees)."""
    mod = _load("phylo_16s_from_genome.py")
    monkeypatch.setattr(mod, "DB", _spaced_blastdb(tmp_path))
    hit = "contig_1\t101\t1600\t1\t1500\t98.7\t1500\tNR_000001.1\n"
    fake, _ = _recorder(_Proc(0, hit))
    monkeypatch.setattr(subprocess, "run", fake)
    out = mod.extract(str(_spaced_genome(tmp_path)), 1200, False, 1)
    assert len(out) == 1 and out[0][3] >= 1200, out


# --------------------------------------------------------------- the merge audit

def test_a_failed_mafft_is_not_the_verdict_THIN(monkeypatch, tmp_path):
    """`Tools/audit_16s_merges.py:48` chained `.stdout` onto `subprocess.run(...)`, so the
    returncode was unreachable. An empty alignment gives ident() zero shared columns, and the pair
    is written back to `merge_audit.note` as THIN — "these two records barely overlap". That is a
    statement about the sequences; it was a statement about MAFFT."""
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("MAFFT_BIN", str(tmp_path))
    mafft = tmp_path / "mafft"
    mafft.write_text("#!/bin/sh\nexit 1\n")
    mafft.chmod(0o755)
    mod = _load("phylo_16s_audit_merges.py")
    fake, _ = _recorder(_Proc(1, "", "mafft: cannot open input"))
    monkeypatch.setattr(subprocess, "run", fake)
    with pytest.raises(SystemExit) as e:
        mod.align("ACGT" * 200, "ACGT" * 300)
    assert "mafft" in str(e.value).lower() and "exit 1" in str(e.value), str(e.value)
