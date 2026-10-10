"""`python mamey_run.py gap-rescue`: the gap-rescue screen as one optional step after the run (made-up paths only).

2026-10-06, the owner: "make it one documented step after the run". The step wraps tools/gap_rescue_all_regions.py,
finds its inputs in a fixed order, refuses up front when DIAMOND, a MIBiG input or (unless --no-pfam) Pfam/pyhmmer is
missing, never writes inside the bundle, and records itself in run_receipt.json as a screen, not adjudicated.
"""
import argparse
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from mamey import cli  # noqa: E402

ENV = ("SAPOTE_MIBIG_GBK_DIR", "SAPOTE_MIBIG_DMND", "SAPOTE_MIBIG_NAMES", "SAPOTE_PFAM_HMM", "RGGMCI_MIBIG_DB",
       "RGGMCI_PFAM_HMM")


def _args(tmp, **kw):
    base = dict(strain="TST-1", input_zip=str(tmp / "TST-1.zip"), out=str(tmp / "out"), edge_only=False, threads=4,
                no_figure=True, no_pfam=False, mibig_dir=None, mibig_db=None, mibig_names=None, pfam=None)
    base.update(kw)
    return argparse.Namespace(**base)


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """A made-up workspace: a registry naming a MIBiG GenBank folder, a protein database folder, a name index and Pfam."""
    for k in ENV:
        monkeypatch.delenv(k, raising=False)
    (tmp_path / "mibig_gbk").mkdir()
    db = tmp_path / "mibig_db"
    db.mkdir()
    for n in ("mibig_proteins.faa", "mibig_proteins.dmnd", "mibig_proteins.tsv"):
        (db / n).write_text("x")
    (tmp_path / "names.json").write_text('{"entries": []}')
    (tmp_path / "Pfam-A.hmm").write_text("x")
    (tmp_path / "TST-1.zip").write_text("x")
    reg = tmp_path / "OFFICIAL_DATA"
    reg.mkdir()
    (reg / "ASSET_REGISTRY.tsv").write_text("\n".join([
        "# made-up registry", "mibig_local2088_gbk\tgbk_tree\tmibig_gbk", "mibig_local2088_proteins\tprotein_db\tmibig_db",
        "mibig_reference_index_bacterial\tdata-index\tnames.json", "pfam_a_hmm\thmm_db\tPfam-A.hmm"]) + "\n")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_inputs_come_from_the_registry_and_the_database_folder_gives_its_diamond_file(workspace):
    got = cli._gap_rescue_inputs(_args(workspace), workspace)
    assert got["mibig_dir"] == {"path": str(workspace / "mibig_gbk"), "how": "registry mibig_local2088_gbk"}
    assert got["mibig_db"]["path"] == str(workspace / "mibig_db" / "mibig_proteins.dmnd")
    assert got["mibig_db"]["how"] == "registry mibig_local2088_proteins"
    assert got["pfam"]["how"] == "registry pfam_a_hmm" and got["mibig_names"]["how"] == "registry mibig_reference_index_bacterial"


def test_order_is_flag_then_sapote_then_rggmci_then_registry(workspace, monkeypatch):
    other = workspace / "other_db"
    other.mkdir()
    (other / "mibig_proteins.faa").write_text("x")
    monkeypatch.setenv("RGGMCI_MIBIG_DB", str(other))
    assert cli._gap_rescue_inputs(_args(workspace), workspace)["mibig_db"] == {
        "path": str(other / "mibig_proteins.dmnd"), "how": "env RGGMCI_MIBIG_DB"}
    monkeypatch.setenv("SAPOTE_MIBIG_DMND", "/made/up/sapote.dmnd")
    assert cli._gap_rescue_inputs(_args(workspace), workspace)["mibig_db"]["how"] == "env SAPOTE_MIBIG_DMND"
    got = cli._gap_rescue_inputs(_args(workspace, mibig_db=str(workspace / "mibig_db")), workspace)["mibig_db"]
    assert got == {"path": str(workspace / "mibig_db" / "mibig_proteins.dmnd"), "how": "flag"}


def test_no_pfam_is_recorded_not_resolved(workspace):
    assert cli._gap_rescue_inputs(_args(workspace, no_pfam=True), workspace)["pfam"] == {
        "path": None, "how": "opted_out (--no-pfam)"}


def test_refusals_name_what_is_missing(workspace, monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    with pytest.raises(SystemExit, match="no DIAMOND on PATH"):
        cli.gap_rescue_command(_args(workspace))
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/made/up/diamond")
    (workspace / "OFFICIAL_DATA" / "ASSET_REGISTRY.tsv").write_text("# empty\n")
    with pytest.raises(SystemExit, match="pass --mibig-dir"):
        cli.gap_rescue_command(_args(workspace))


def test_a_mistyped_pfam_or_name_index_is_refused_before_any_search(workspace, monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/made/up/diamond")
    with pytest.raises(SystemExit, match="no Pfam-A.hmm found .*pass --pfam"):
        cli.gap_rescue_command(_args(workspace, pfam=str(workspace / "Pfam-A.hmm.typo")))
    monkeypatch.setenv("SAPOTE_MIBIG_NAMES", str(workspace / "names.jsn"))
    with pytest.raises(SystemExit, match="pass --mibig-names"):
        cli.gap_rescue_command(_args(workspace, no_pfam=True))


def test_a_database_folder_without_its_diamond_file_says_how_to_build_it(workspace, monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/made/up/diamond")
    (workspace / "mibig_db" / "mibig_proteins.dmnd").unlink()
    with pytest.raises(SystemExit, match="has no mibig_proteins.dmnd; build it with `diamond makedb"):
        cli.gap_rescue_command(_args(workspace, no_pfam=True))


def test_pyhmmer_missing_refuses_unless_no_pfam(workspace, monkeypatch):
    import importlib.util
    real = importlib.util.find_spec
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/made/up/diamond")
    monkeypatch.setattr(importlib.util, "find_spec", lambda n, *a, **k: None if n == "pyhmmer" else real(n, *a, **k))
    with pytest.raises(SystemExit, match="--no-pfam"):
        cli.gap_rescue_command(_args(workspace))


def test_output_inside_the_bundle_is_refused_from_any_working_directory(workspace, monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/made/up/diamond")
    with pytest.raises(SystemExit, match="OUTPUT_INSIDE_BUNDLE"):   # cwd is the made-up workspace, not the bundle
        cli.gap_rescue_command(_args(workspace, out=str(ROOT / "runs" / "TST-1_gap_rescue")))


def test_the_screen_gets_the_resolved_inputs_and_the_receipt_says_screen_not_adjudicated(workspace, monkeypatch):
    import gap_rescue_all_regions
    seen = {}

    def fake_main(argv):
        seen["argv"] = argv
        out = Path(argv[argv.index("--out") + 1])
        out.mkdir(parents=True, exist_ok=True)
        (out / "run_receipt.json").write_text(json.dumps({"label": "TST-1"}))
        return 0

    monkeypatch.setattr(cli.shutil, "which", lambda name: "/made/up/diamond")
    monkeypatch.setattr(gap_rescue_all_regions, "main", fake_main)
    assert cli.gap_rescue_command(_args(workspace, no_pfam=True, edge_only=True)) == 0
    argv = seen["argv"]
    assert argv[argv.index("--label") + 1] == "TST-1" and "--sensitivity" not in argv and "--pfam" not in argv
    assert argv[argv.index("--mibig-db") + 1].endswith("mibig_proteins.dmnd") and "--edge-only" in argv
    cmd = json.loads((workspace / "out" / "run_receipt.json").read_text())["command"]
    assert cmd["scope"] == "screen, not adjudicated" and cmd["sensitivity"] == "ultra-sensitive"
    assert cmd["inputs"]["pfam"]["how"] == "opted_out (--no-pfam)"


def test_the_subcommand_is_registered():
    with pytest.raises(SystemExit):
        cli.main(["gap-rescue", "--help"])
