"""Prospective hermetic version gate: synthetic executables, no EPA/MAFFT/inference.

Only the version-banner subprocess is real; accepted placement uses a synthetic
executable which records arguments/environment and emits explicitly fake jplace.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest
from tools import phylo_place as place
from ._python_fixture_launcher import write_python_fixture


def _fixture(tmp_path, monkeypatch, banner="EPA-ng v0.3.8\n", rc=0):
    ref = tmp_path / "refpkg"
    ref.mkdir()
    inputs = {
        "_provenance.json": json.dumps({"group": "streptomyces", "molecule": "nucleotide"}),
        "labelmap.tsv": "safe\toriginal\nREF\tREF\n",
        "ref.aln.fasta": ">REF\nACGT\n",
        "ref.tree": "(REF:0.1);\n",  # no asserted proof of unrooted input
        "MODEL": "GTR+G\n",
    }
    for name, content in inputs.items():
        (ref / name).write_text(content)
    query = tmp_path / "query.fasta"
    query.write_text(">Q\n" + "ACGT" * 350 + "\n")
    log = tmp_path / "synthetic calls.jsonl"
    executable = tmp_path / "synthetic epa-ng"
    body = "import json, os, sys\nfrom pathlib import Path\n"
    body += "with Path(os.environ['SYNTHETIC_LOG']).open('a') as stream:\n"
    body += "    stream.write(json.dumps({'argv': sys.argv[1:], 'environment': {k: os.environ.get(k) for k in ('OMP_NUM_THREADS', 'OMP_THREAD_LIMIT', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')}}) + '\\n')\n"
    body += "if sys.argv[1:] == ['--version']:\n"
    body += "    sys.stdout.write(" + repr(banner) + ")\n    raise SystemExit(" + repr(rc) + ")\n"
    body += "out = Path(sys.argv[sys.argv.index('--outdir') + 1])\n"
    body += "(out / 'epa_result.jplace').write_text('SYNTHETIC ONLY: not scientific placement data')\n"
    body += "if os.environ.get('MUTATE_EXECUTABLE') == '1':\n"
    body += "    Path(os.environ['SELECTED_EPA']).write_text('changed synthetic executable')\n"
    write_python_fixture(executable, body)
    monkeypatch.setenv("SYNTHETIC_LOG", str(log))
    monkeypatch.setenv("SELECTED_EPA", str(executable))
    monkeypatch.setenv("OMP_NUM_THREADS", "48")
    monkeypatch.delenv("MUTATE_EXECUTABLE", raising=False)
    monkeypatch.setattr(place, "_which", lambda name, *bins: str(executable) if name == "epa-ng" else name)
    out = tmp_path / "new placement"
    args = SimpleNamespace(refpkg=str(ref), query=str(query), outdir=str(out), fragmentary=False, threads=2)
    before = {name: (ref / name).read_bytes() for name in inputs}
    return args, ref, out, executable, log, before


def _no_alignment(*args, **kwargs):
    pytest.fail("alignment started before version admission")


@pytest.mark.parametrize("version", ("0.3.0", "0.3.1", "0.3.2", "0.3.3"))
def test_known_affected_releases_refuse_before_output_and_alignment(tmp_path, monkeypatch, version):
    args, ref, out, executable, log, before = _fixture(tmp_path, monkeypatch, f"EPA-ng v{version}\n")
    monkeypatch.setattr(place, "_align_queries", _no_alignment)
    with pytest.raises(SystemExit, match="EPA_VERSION_KNOWN_ROOTED_TREE_BUG"):
        place.cmd_place(args)
    assert not out.exists()
    assert [json.loads(line)["argv"] for line in log.read_text().splitlines()] == [["--version"]]
    assert {name: (ref / name).read_bytes() for name in before} == before


@pytest.mark.parametrize("banner,rc,reason", (
    ("EPA-ng v0.2.0\n", 0, "EPA_VERSION_UNSUPPORTED"),
    ("EPA-ng vUNKNOWN\n", 0, "EPA_VERSION_UNVERIFIED"),
    ("EPA-ng v0.3\n", 0, "EPA_VERSION_UNVERIFIED"),
    ("EPA-ng v0.3.8-dev\n", 0, "EPA_VERSION_UNVERIFIED"),
    ("EPA-ng v0.3.8\nEPA-ng v0.3.3\n", 0, "EPA_VERSION_UNVERIFIED"),
    ("OtherTool 0.3.8\n", 0, "EPA_VERSION_UNVERIFIED"),
    ("", 0, "EPA_VERSION_UNVERIFIED"),
    ("EPA-ng v0.3.8\n", 1, "EPA_VERSION_UNVERIFIED"),
))
def test_unverified_or_unsupported_version_preserves_occupied_destination(tmp_path, monkeypatch, banner, rc, reason):
    args, ref, out, executable, log, before = _fixture(tmp_path, monkeypatch, banner, rc)
    out.mkdir()
    (out / "labelmap.tsv").write_bytes(b"prior exact evidence\x00\n")
    prior = {f.name: f.read_bytes() for f in out.iterdir()}
    monkeypatch.setattr(place, "_align_queries", _no_alignment)
    with pytest.raises(SystemExit, match=reason):
        place.cmd_place(args)
    assert {f.name: f.read_bytes() for f in out.iterdir()} == prior
    assert {name: (ref / name).read_bytes() for name in before} == before


@pytest.mark.parametrize("version", ("0.3.4", "0.3.8"))
def test_actual_place_uses_same_admitted_executable_model_budget_and_stamps_binding(tmp_path, monkeypatch, version):
    args, ref, out, executable, log, before = _fixture(tmp_path, monkeypatch, f"EPA-ng v{version}\n")
    executable_sha = hashlib.sha256(executable.read_bytes()).hexdigest()
    def align(mafft, epa, ref_aln, query, outdir, fragmentary, *, threads):
        assert epa == str(executable) and threads == 2
        aligned = out / "query.aligned.fasta"
        aligned.write_text(">Q\nACGT\n")
        return str(aligned)
    monkeypatch.setattr(place, "_align_queries", align)
    assert place.cmd_place(args) == 0
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert len(calls) == 2 and calls[0]["argv"] == ["--version"]
    assert "--tree" not in calls[0]["argv"]
    argv = calls[1]["argv"]
    assert argv[argv.index("--tree") + 1] == str(ref / "ref.tree")
    assert argv[argv.index("--model") + 1] == "GTR+G"
    assert argv[argv.index("--threads") + 1] == "2" and "--redo" in argv
    for call in calls:
        assert set(call["environment"].values()) == {"2"}
    receipt = json.loads((out / "_provenance.json").read_text())
    admission = receipt["epa_ng_admission"]
    assert admission["version"] == version
    assert admission["state"] == "ADMITTED_KNOWN_BUG_MINIMUM"
    assert admission["executable"]["sha256"] == executable_sha
    assert admission["probe_stdout_sha256"] == hashlib.sha256(f"EPA-ng v{version}\n".encode()).hexdigest()
    assert admission["probe_command"] == [str(executable), "--version"]
    assert {name: (ref / name).read_bytes() for name in before} == before


@pytest.mark.parametrize("failure", ("timeout", "missing", "invalid-encoding"))
def test_probe_transport_failure_refuses_before_alignment_and_output(tmp_path, monkeypatch, failure):
    args, ref, out, executable, log, before = _fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(place, "_align_queries", _no_alignment)
    def probe(cmd, **kwargs):
        assert cmd == [str(executable), "--version"]
        assert kwargs["timeout"] == 10 and kwargs["env"]["OMP_THREAD_LIMIT"] == "2"
        if failure == "timeout":
            raise subprocess.TimeoutExpired(cmd, 10)
        if failure == "missing":
            raise OSError("synthetic unavailable executable")
        return SimpleNamespace(returncode=0, stdout=b"\xff\n", stderr=b"")
    monkeypatch.setattr(place.subprocess, "run", probe)
    with pytest.raises(SystemExit, match="EPA_VERSION_UNVERIFIED"):
        place.cmd_place(args)
    assert not out.exists()


def test_changed_executable_during_probe_cannot_be_admitted(tmp_path, monkeypatch):
    args, ref, out, executable, log, before = _fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(place, "_align_queries", _no_alignment)
    def probe(cmd, **kwargs):
        executable.write_text("changed synthetic executable")
        return SimpleNamespace(returncode=0, stdout=b"EPA-ng v0.3.8\n", stderr=b"")
    monkeypatch.setattr(place.subprocess, "run", probe)
    with pytest.raises(SystemExit, match="EPA_EXECUTABLE_CHANGED"):
        place.cmd_place(args)
    assert not out.exists()


def test_changed_executable_during_alignment_refuses_native_placement(tmp_path, monkeypatch):
    args, ref, out, executable, log, before = _fixture(tmp_path, monkeypatch)
    def align(*args, **kwargs):
        aligned = out / "query.aligned.fasta"
        aligned.write_text(">Q\nACGT\n")
        executable.write_text("changed after version probe")
        return str(aligned)
    monkeypatch.setattr(place, "_align_queries", align)
    with pytest.raises(SystemExit, match="EPA_EXECUTABLE_CHANGED"):
        place.cmd_place(args)
    assert [json.loads(line)["argv"] for line in log.read_text().splitlines()] == [["--version"]]
    assert (out / "query.aligned.fasta").is_file()
    assert not (out / "_provenance.json").exists()


def test_changed_executable_after_placement_retains_outputs_without_success_stamp(tmp_path, monkeypatch):
    args, ref, out, executable, log, before = _fixture(tmp_path, monkeypatch)
    monkeypatch.setenv("MUTATE_EXECUTABLE", "1")
    def align(*args, **kwargs):
        aligned = out / "query.aligned.fasta"
        aligned.write_text(">Q\nACGT\n")
        return str(aligned)
    monkeypatch.setattr(place, "_align_queries", align)
    with pytest.raises(SystemExit, match="EPA_EXECUTABLE_CHANGED"):
        place.cmd_place(args)
    assert (out / "epa_result.jplace").read_text().startswith("SYNTHETIC ONLY")
    assert not (out / "_provenance.json").exists()
    assert len(log.read_text().splitlines()) == 2
