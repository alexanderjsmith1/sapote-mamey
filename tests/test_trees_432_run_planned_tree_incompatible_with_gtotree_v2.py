"""TREES_432_run_planned_tree_incompatible_with_gtotree_v2 — the runner builds a version-correct
GToTree command (no ``-n`` on v2, ``-H`` = HMM file, lowercase ``gtotree`` binary found), accepts the
v2 alignment spelling, preflights the genome list for spaces, and completes end to end on fakes."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _trees_432_fakes as F  # noqa: E402


def test_v2_command_has_no_n_flag_and_v1_keeps_it():
    mod = F.load_runner()
    v2 = mod.gtotree_command("/x/gtotree", 2, "list.txt", "/h/Actinobacteria.hmm", 4, 2, "out")
    assert "-n" not in v2
    assert v2[v2.index("-H") + 1] == "/h/Actinobacteria.hmm"
    assert v2[v2.index("-j") + 1] == "2" and v2[v2.index("-M") + 1] == "4" and "-N" in v2
    v1 = mod.gtotree_command("/x/GToTree", 1, "list.txt", "Actinobacteria", 4, 2, "out")
    assert v1[v1.index("-n") + 1] == "4" and v1[v1.index("-j") + 1] == "2"


def test_version_probe_parses_v2_and_v1(tmp_path, monkeypatch):
    mod = F.load_runner()
    fake = F.install_fake_bins(tmp_path, monkeypatch, version="GToTree v2.0.0")
    major, raw = mod.gtotree_version(os.path.join(fake["bin"], "gtotree"))
    assert major == 2 and "2.0.0" in raw
    monkeypatch.setenv("FAKE_GTOTREE_VERSION", "GToTree v1.8.19")
    assert mod.gtotree_version(os.path.join(fake["bin"], "gtotree"))[0] == 1
    assert mod.gtotree_version("/no/such/gtotree")[0] is None


def test_v2_end_to_end_on_fakes(tmp_path, monkeypatch):
    """Full v2 path: probe -> -n-free command -> aligned-SCGs.faa found -> IQ-TREE -> gates -> DONE."""
    mod = F.load_runner()
    fake = F.install_fake_bins(tmp_path, monkeypatch)
    gl = F.stage_genomes(tmp_path)
    wd = tmp_path / "wd"
    rc = mod.main(F.base_args(gl, wd))
    assert rc == 0, open(wd / "run_planned_tree.log").read()
    recs = F.records(fake["record"])
    gt = [r for r in recs if r["tool"] == "gtotree"][0]
    assert "-n" not in gt["argv"]
    assert gt["argv"][gt["argv"].index("-H") + 1] == fake["hmm"]
    assert gt["GToTree_HMM_dir"].rstrip("/") == fake["hmm_dir"]
    iq = [r for r in recs if r["tool"] == "iqtree"][0]
    assert iq["argv"][iq["argv"].index("-s") + 1].endswith("aligned-SCGs.faa")
    assert "-seed" in iq["argv"] and "MFP" in iq["argv"]
    st = F.read_status(wd)
    assert st["status"] == "DONE" and st["gtotree_major"] == 2 and st["support_nodes"] >= 1


def test_v1_alignment_spelling_still_found(tmp_path, monkeypatch):
    mod = F.load_runner()
    F.install_fake_bins(tmp_path, monkeypatch, version="GToTree v1.8.19", gtotree_name="GToTree")
    monkeypatch.setenv("FAKE_ALN_NAME", "Aligned_SCGs.faa")
    gl = F.stage_genomes(tmp_path)
    wd = tmp_path / "wd"
    assert mod.main(F.base_args(gl, wd)) == 0
    assert F.read_status(wd)["alignment"].endswith("Aligned_SCGs.faa")


def test_spaced_genome_entry_refused_before_launch(tmp_path, monkeypatch):
    """Card addendum: a staged path with a space must fail at preflight, not after gtotree starts."""
    mod = F.load_runner()
    fake = F.install_fake_bins(tmp_path, monkeypatch)
    spaced = tmp_path / "Actinomadura macrotermitis Strain RB68.fna"
    spaced.write_text(">x\nACGT\n")
    gl = tmp_path / "genome_list.txt"
    gl.write_text(str(spaced) + "\n")
    entries, errors = mod.preflight_genome_list(str(gl))
    assert any(e.startswith("GENOME_PATH_HAS_SPACE") for e in errors)
    rc = mod.main(F.base_args(str(gl), tmp_path / "wd"))
    assert rc == 2
    assert F.records(fake["record"]) == [], "gtotree must not have been launched"


def test_missing_genome_file_refused_before_launch(tmp_path, monkeypatch):
    mod = F.load_runner()
    F.install_fake_bins(tmp_path, monkeypatch)
    gl = tmp_path / "genome_list.txt"
    gl.write_text(str(tmp_path / "ghost.fna") + "\n")
    _, errors = mod.preflight_genome_list(str(gl))
    assert any(e.startswith("GENOME_FILE_MISSING") for e in errors)
    assert mod.main(F.base_args(str(gl), tmp_path / "wd")) == 2
