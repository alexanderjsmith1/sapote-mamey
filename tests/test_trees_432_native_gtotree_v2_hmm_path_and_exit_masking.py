"""TREES_432_native_gtotree_v2_hmm_path_and_exit_masking — an invalid ``-H`` is refused BEFORE launch
(typed HMM_PATH_MISSING, sha256 recorded/checked, GToTree_HMM_dir exported to the file's directory) and
GToTree's real exit code is surfaced (GTOTREE_EXIT rc=1 -> runner rc 4, run_status.json), never masked."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _trees_432_fakes as F  # noqa: E402


def test_resolve_hmm_name_and_path(tmp_path, monkeypatch):
    mod = F.load_runner()
    fake = F.install_fake_bins(tmp_path, monkeypatch)
    f, d, sha = mod.resolve_hmm("Actinobacteria", fake["hmm_dir"])
    assert f == fake["hmm"] and d == fake["hmm_dir"] and len(sha) == 64
    f2, d2, _ = mod.resolve_hmm(fake["hmm"], None)
    assert (f2, d2) == (fake["hmm"], fake["hmm_dir"])
    # sha prefix accepted, mismatch typed
    assert mod.resolve_hmm("Actinobacteria", fake["hmm_dir"], sha[:16])[2] == sha
    with pytest.raises(ValueError, match="HMM_IDENTITY"):
        mod.resolve_hmm("Actinobacteria", fake["hmm_dir"], "0" * 64)


def test_stale_hmm_path_refused_before_launch(tmp_path, monkeypatch):
    """The 2026-09-14 Saccharopolyspora failure: -H pointed at old/gtotree_hmm_sets/Actinobacteria.hmm."""
    mod = F.load_runner()
    fake = F.install_fake_bins(tmp_path, monkeypatch)
    stale = str(tmp_path / "old" / "gtotree_hmm_sets" / "Actinobacteria.hmm")
    with pytest.raises(FileNotFoundError, match="HMM_PATH_MISSING"):
        mod.resolve_hmm(stale, None)
    gl = F.stage_genomes(tmp_path)
    monkeypatch.setenv("GToTree_HMM_dir", str(tmp_path / "old" / "gtotree_hmm_sets"))
    rc = mod.main(F.base_args(gl, tmp_path / "wd", hmm=stale))
    assert rc == 3
    assert F.records(fake["record"]) == [], "gtotree must not run with a missing HMM file"


def test_missing_hmm_set_in_env_refused(tmp_path, monkeypatch):
    mod = F.load_runner()
    fake = F.install_fake_bins(tmp_path, monkeypatch, with_hmm=False)
    gl = F.stage_genomes(tmp_path)
    assert mod.main(F.base_args(gl, tmp_path / "wd")) == 3
    assert F.records(fake["record"]) == []


def test_gtotree_exit_code_surfaced_not_masked(tmp_path, monkeypatch, capsys):
    """gtotree exits 1 after the HMM_dir message: runner returns 4, prints GTOTREE_EXIT rc=1 with the
    log tail, and run_status.json records GTOTREE_FAILED / gtotree_rc=1."""
    mod = F.load_runner()
    F.install_fake_bins(tmp_path, monkeypatch)
    monkeypatch.setenv("FAKE_GTOTREE_MODE", "fail_hmm")
    gl = F.stage_genomes(tmp_path)
    wd = tmp_path / "wd"
    rc = mod.main(F.base_args(gl, wd))
    err = capsys.readouterr().err
    assert rc == 4
    assert "GTOTREE_EXIT rc=1" in err and "GToTree_HMM_dir" in err
    st = F.read_status(wd)
    assert st["status"] == "GTOTREE_FAILED" and st["gtotree_rc"] == 1
    assert "GTOTREE_EXIT rc=1" in open(wd / "run_planned_tree.log").read()
    assert not (wd / "iqtree.treefile").exists()


def test_nonzero_rc_with_alignment_present_still_fails(tmp_path, monkeypatch):
    """A wrapper that checked only for output would call this run done; the runner must not."""
    mod = F.load_runner()
    F.install_fake_bins(tmp_path, monkeypatch)
    monkeypatch.setenv("FAKE_GTOTREE_RC", "1")
    gl = F.stage_genomes(tmp_path)
    wd = tmp_path / "wd"
    assert mod.main(F.base_args(gl, wd)) == 4
    assert F.read_status(wd)["status"] == "GTOTREE_FAILED"


def test_hmm_sha_recorded_and_mismatch_refused(tmp_path, monkeypatch):
    mod = F.load_runner()
    fake = F.install_fake_bins(tmp_path, monkeypatch)
    gl = F.stage_genomes(tmp_path)
    wd = tmp_path / "wd"
    assert mod.main(F.base_args(gl, wd, hmm_sha256="deadbeef")) == 3
    assert mod.main(F.base_args(gl, wd)) == 0
    st = F.read_status(wd)
    assert st["hmm_file"] == fake["hmm"] and len(st["hmm_sha256"]) == 64


def test_gate_accepts_v2_packet_version():
    gate = F.load_gate()
    assert gate._ACCEPTED_GTOTREE_VERSIONS.search("GToTree v2.0.0")
    assert gate._ACCEPTED_GTOTREE_VERSIONS.search("1.8.19")
    assert not gate._ACCEPTED_GTOTREE_VERSIONS.search("GToTree v1.8.16")
