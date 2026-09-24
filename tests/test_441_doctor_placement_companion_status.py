"""v9.7.441 card 283f1f96: doctor's placement/R companion probe finds binaries in the workspace conda
envs (via SAPOTE_WORKSPACE_ROOT), honours $BLAST_BIN, and reports the rest as missing (NOT MEASURED)."""
from mamey.cli import _placement_and_r_companion_status


def test_workspace_env_and_blast_bin(tmp_path):
    (tmp_path / "miniconda3/envs/placement/bin").mkdir(parents=True)
    for b in ("mafft", "raxml-ng", "epa-ng"):
        (tmp_path / "miniconda3/envs/placement/bin" / b).write_text("")
    bb = tmp_path / "custom_blast"; bb.mkdir(); (bb / "blastdbcmd").write_text("")
    env = {"SAPOTE_WORKSPACE_ROOT": str(tmp_path), "BLAST_BIN": str(bb), "PATH": str(tmp_path / "nothing")}
    found, missing = _placement_and_r_companion_status(env)
    assert set(found) == {"mafft", "raxml-ng", "epa-ng", "blastdbcmd"}
    assert set(missing) == {"gappa", "Rscript"}


def test_nothing_found_reports_all_missing(tmp_path):
    env = {"SAPOTE_WORKSPACE_ROOT": str(tmp_path), "PATH": str(tmp_path / "nothing")}
    found, missing = _placement_and_r_companion_status(env)
    assert found == [] and len(missing) == 6
