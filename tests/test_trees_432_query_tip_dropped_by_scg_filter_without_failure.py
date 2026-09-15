"""TREES_432_query_tip_dropped_by_scg_filter_without_failure — after GToTree, the retained tips are
diffed against the genome list; a dropped QUERY is a hard failure that names the genome and quotes its
SCG-hit counts, drops are recorded in DROPPED_BY_QC.tsv, and gtotree exit 0 does not hide any of it."""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _trees_432_fakes as F  # noqa: E402


def _v2_out(tmp_path, tips, dropped):
    """Mimic the evidence layout (gtotree_v2_out/) including the AS-810 removed-genomes row."""
    out = tmp_path / "gtotree_v2_out"
    (out / "run-files").mkdir(parents=True)
    (out / "aligned-SCGs.faa").write_text("".join(f">{t}\nMKV\n" for t in tips if t not in dropped))
    (out / "run-files" / "removed-genomes.tsv").write_text(
        "genome_id\tinput\tsource\tstage_removed\treason_removed\n" +
        "".join(f"{t}\tgenomes/{t}.fna\tnucleotide-fasta\tscg-hit-filter\ttoo few unique SCG hits\n" for t in dropped))
    (out / "SCG-hit-counts.tsv").write_text(
        "genome_id\tADK\tATP-synt\tCoaE\tDapB_C\n" +
        "".join(f"{t}\t" + ("3\t3\t2\t0" if t in dropped else "1\t1\t1\t1") + "\n" for t in tips))
    (out / "gtotree-runlog.txt").write_text(
        "      1 genome(s) removed due to having too few unique SCG hits, reported in:\n" if dropped
        else "             No genomes were removed due to having too few SCG hits!\n")
    return out


def test_query_drop_is_typed_with_scg_line(tmp_path):
    gate = F.load_gate()
    tips = ["AS-365", "AS-810", "Actinomadura_rifamycini_DSM_43936", "GCF_003751225.1_genomic_OUTGROUP"]
    out = _v2_out(tmp_path, tips, ["AS-810"])
    res = gate.tip_retention(tips, gate.gtotree_retained_tips(out), {"AS-365", "AS-810"}, out)
    assert res["status"] == "QUERY_TIP_DROPPED"
    d = res["dropped"][0]
    assert d["tip"] == "AS-810" and d["role"] == "query"
    assert "too few unique SCG hits" in d["reason"] and "scg-hit-filter" in d["reason"]
    assert d["scg_hits"] == {"markers": 4, "total": 8, "unique": 0, "multi_copy": 3, "absent": 1,
                             "raw": "AS-810\t3\t3\t2\t0"}
    assert res["runlog_claim"] == "removed"
    line = gate.format_dropped(res)[0]
    assert "QUERY DROPPED: AS-810" in line and "3 multi-copy" in line


def test_reference_drop_hard_unless_allowed(tmp_path):
    gate = F.load_gate()
    tips = ["AS-365", "Ref_A", "Ref_B_OUTGROUP"]
    out = _v2_out(tmp_path, tips, ["Ref_A"])
    res = gate.tip_retention(tips, gate.gtotree_retained_tips(out), {"AS-365"}, out)
    assert res["status"] == "REFERENCE_TIP_DROPPED"
    res = gate.tip_retention(tips, gate.gtotree_retained_tips(out), {"AS-365"}, out, allow_reference_drop=True)
    assert res["status"] == "REFERENCE_TIP_DROPPED_ALLOWED" and res["dropped"][0]["role"] == "reference"


def test_nothing_dropped(tmp_path):
    gate = F.load_gate()
    tips = ["AS-365", "Ref_A"]
    out = _v2_out(tmp_path, tips, [])
    res = gate.tip_retention(tips, gate.gtotree_retained_tips(out), set(tips), out)
    assert res["status"] == "TIPS_RETAINED" and res["dropped"] == [] and res["runlog_claim"] == "none"
    assert gate.tip_retention(tips, None, set(tips), out)["status"] == "ALIGNMENT_MISSING"


def test_declared_query_roles():
    gate = F.load_gate()
    tips = ["AS-1", "AS-2", "Ref"]
    assert gate.declared_query_tips(tips, None, None) == set(tips)            # nothing declared -> all
    assert gate.declared_query_tips(tips, {"queries": ["genomes/AS-1.fna"]}, None) == {"AS-1"}
    assert gate.declared_query_tips(tips, {"queries": ["AS-1"]}, ["AS-2"]) == {"AS-2"}
    assert gate.tip_from_genome_path("genomes/AS-810.fna.gz") == "AS-810"


def test_dropped_by_qc_tsv_and_cli(tmp_path):
    gate = F.load_gate()
    tips = ["AS-365", "AS-810", "Ref"]
    out = _v2_out(tmp_path, tips, ["AS-810"])
    gl = tmp_path / "genome_list.txt"
    gl.write_text("".join(f"genomes/{t}.fna\n" for t in tips))
    spec = tmp_path / "TREE_SPEC.json"
    spec.write_text(json.dumps({"queries": ["AS-365", "AS-810"]}))
    tsv = tmp_path / "DROPPED_BY_QC.tsv"
    proc = subprocess.run([sys.executable, F.GATE, "--check-tips", str(out), "--genome-list", str(gl),
                           "--tree-spec", str(spec), "--dropped-tsv", str(tsv)], capture_output=True, text=True)
    assert proc.returncode == 1 and '"QUERY_TIP_DROPPED"' in proc.stdout
    rows = tsv.read_text().splitlines()
    assert rows[0].startswith("tip\trole\treason") and rows[1].startswith("AS-810\tquery\ttoo few unique SCG hits")
    # a reference-only drop with --allow-reference-drop exits 0
    proc = subprocess.run([sys.executable, F.GATE, "--check-tips", str(out), "--genome-list", str(gl),
                           "--query-tips", "AS-365", "--allow-reference-drop"], capture_output=True, text=True)
    assert proc.returncode == 0 and '"REFERENCE_TIP_DROPPED_ALLOWED"' in proc.stdout


def test_runner_fails_loudly_when_query_dropped(tmp_path, monkeypatch, capsys):
    """gtotree exits 0 with 3 of 4 tips; the runner must return 7, name the genome, and not run IQ-TREE."""
    mod = F.load_runner()
    fake = F.install_fake_bins(tmp_path, monkeypatch)
    monkeypatch.setenv("FAKE_DROP_TIPS", "Streptomyces_coelicolor_A32")
    gl = F.stage_genomes(tmp_path)
    wd = tmp_path / "wd"
    rc = mod.main(F.base_args(gl, wd))
    err = capsys.readouterr().err
    assert rc == 7
    assert "QUERY_TIP_DROPPED" in err and "QUERY DROPPED: Streptomyces_coelicolor_A32" in err
    assert "too few unique SCG hits" in err and "multi-copy" in err
    assert [r["tool"] for r in F.records(fake["record"])] == ["gtotree"], "IQ-TREE must not run"
    st = F.read_status(wd)
    assert st["status"] == "QUERY_TIP_DROPPED" and st["dropped"][0]["tip"] == "Streptomyces_coelicolor_A32"
    assert (wd / "DROPPED_BY_QC.tsv").read_text().splitlines()[1].startswith("Streptomyces_coelicolor_A32\tquery")


def test_runner_allows_declared_reference_drop(tmp_path, monkeypatch):
    mod = F.load_runner()
    F.install_fake_bins(tmp_path, monkeypatch)
    monkeypatch.setenv("FAKE_DROP_TIPS", "Streptomyces_griseus_DSM40236")
    gl = F.stage_genomes(tmp_path)
    wd = tmp_path / "wd"
    # declared queries exclude the dropped one; without --allow-reference-drop it is still hard
    assert mod.main(F.base_args(gl, wd, query_tips="Streptomyces_coelicolor_A32")) == 7
    assert F.read_status(wd)["status"] == "REFERENCE_TIP_DROPPED"
    rc = mod.main(F.base_args(gl, wd, query_tips="Streptomyces_coelicolor_A32", allow_reference_drop=True))
    assert rc == 0
    st = F.read_status(wd)
    assert st["status"] == "DONE" and st["tip_retention"] == "REFERENCE_TIP_DROPPED_ALLOWED"
    assert (wd / "DROPPED_BY_QC.tsv").exists()
