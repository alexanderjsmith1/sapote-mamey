"""TREES_432_build_completion_gate_requires_contree — COMPLETE needs .contree + support labels +
'Total wall-clock time'; a bare .treefile is INTERRUPTED (typed), and the runner refuses DONE on it."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _trees_432_fakes as F  # noqa: E402

COMPLETE_LOG = "IQ-TREE 3.0.1\nGenerating 1000 samples for ultrafast bootstrap...\nTotal wall-clock time used: 1332.0 sec\nDate: x\n"
KILLED_LOG = "IQ-TREE 3.0.1\nGenerating 1000 samples for ultrafast bootstrap (v3)...\n"


def _run(tmp_path, treefile=None, contree=None, log=None, prefix="iqtree"):
    p = tmp_path / prefix
    if treefile is not None:
        (tmp_path / (prefix + ".treefile")).write_text(treefile)
    if contree is not None:
        (tmp_path / (prefix + ".contree")).write_text(contree)
    if log is not None:
        (tmp_path / (prefix + ".log")).write_text(log)
    return str(p)


def test_complete_run(tmp_path):
    gate = F.load_gate()
    res = gate.iqtree_completion(_run(tmp_path, F.GOOD_TREE, F.GOOD_TREE, COMPLETE_LOG))
    assert res["status"] == "COMPLETE" and res["reasons"] == [] and res["support_nodes"] == 2


def test_bare_treefile_is_interrupted(tmp_path):
    """The 2026-09-14 Micromonospora disconnect: treefile without support, no contree, no wall-clock."""
    gate = F.load_gate()
    res = gate.iqtree_completion(_run(tmp_path, F.NO_SUPPORT_TREE, None, KILLED_LOG))
    assert res["status"] == "INTERRUPTED"
    codes = {r.split(":")[0] for r in res["reasons"]}
    assert codes == {"TREEFILE_NO_SUPPORT", "CONTREE_MISSING", "LOG_NO_WALLCLOCK"}
    assert "ultrafast bootstrap" in res["last_log_line"]


def test_each_marker_is_required(tmp_path):
    gate = F.load_gate()
    # supported treefile + wall-clock, but empty contree
    r = gate.iqtree_completion(_run(tmp_path / "a", F.GOOD_TREE, "", COMPLETE_LOG) if (tmp_path / "a").mkdir() is None else None)
    assert r["status"] == "INTERRUPTED" and any(x.startswith("CONTREE_MISSING") for x in r["reasons"])
    (tmp_path / "b").mkdir()
    r = gate.iqtree_completion(_run(tmp_path / "b", F.GOOD_TREE, F.GOOD_TREE, KILLED_LOG))
    assert r["status"] == "INTERRUPTED" and any(x.startswith("LOG_NO_WALLCLOCK") for x in r["reasons"])
    (tmp_path / "c").mkdir()
    r = gate.iqtree_completion(_run(tmp_path / "c", F.NO_SUPPORT_TREE, F.GOOD_TREE, COMPLETE_LOG))
    assert r["status"] == "INTERRUPTED" and any(x.startswith("TREEFILE_NO_SUPPORT") for x in r["reasons"])
    (tmp_path / "d").mkdir()
    r = gate.iqtree_completion(_run(tmp_path / "d", None, None, None))
    assert r["status"] == "MISSING"


def test_accepts_gtotree_v2_output_dir_layout(tmp_path):
    """<out>/run-files/iqtree-out/iqtree.* is where native `gtotree -T IQTREE` writes."""
    gate = F.load_gate()
    out = tmp_path / "gtotree_v2_out"
    iq = out / "run-files" / "iqtree-out"
    iq.mkdir(parents=True)
    _run(iq, F.GOOD_TREE, F.GOOD_TREE, COMPLETE_LOG)
    res = gate.iqtree_completion(str(out))
    assert res["status"] == "COMPLETE" and res["contree"].endswith(os.path.join("iqtree-out", "iqtree.contree"))


def test_cli_check_completion_exit_code(tmp_path):
    gate_path = F.GATE
    prefix = _run(tmp_path, F.NO_SUPPORT_TREE, None, KILLED_LOG)
    proc = subprocess.run([sys.executable, gate_path, "--check-completion", prefix], capture_output=True, text=True)
    assert proc.returncode == 1 and '"INTERRUPTED"' in proc.stdout
    prefix = _run(tmp_path, F.GOOD_TREE, F.GOOD_TREE, COMPLETE_LOG, prefix="ok")
    proc = subprocess.run([sys.executable, gate_path, "--check-completion", prefix], capture_output=True, text=True)
    assert proc.returncode == 0 and '"COMPLETE"' in proc.stdout


def test_runner_refuses_done_on_interrupted_iqtree(tmp_path, monkeypatch, capsys):
    mod = F.load_runner()
    F.install_fake_bins(tmp_path, monkeypatch)
    monkeypatch.setenv("FAKE_IQTREE_MODE", "interrupted")
    gl = F.stage_genomes(tmp_path)
    wd = tmp_path / "wd"
    rc = mod.main(F.base_args(gl, wd))
    err = capsys.readouterr().err
    assert rc == 5
    assert "INTERRUPTED" in err and "CONTREE_MISSING" in err and "Do NOT render" in err
    st = F.read_status(wd)
    assert st["status"] == "IQTREE_INTERRUPTED"
    assert (wd / "iqtree.treefile").exists() and not (wd / "iqtree.contree").exists()
