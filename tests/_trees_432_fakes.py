"""Shared fakes for the TREES_432 launcher tests. Never runs GToTree or IQ-TREE.

``install_fake_bins(tmp_path, monkeypatch, ...)`` drops executable ``gtotree`` and ``iqtree``
Python scripts on PATH. They mimic the GToTree v2.0.0 / IQ-TREE 3 surface the launcher relies on:
``-v`` output, output-directory layout (``aligned-SCGs.faa``, ``run-files/removed-genomes.tsv``,
``genomes-summary-info.tsv``, ``SCG-hit-counts.tsv``, ``gtotree-runlog.txt``), and the IQ-TREE
prefix files (``.treefile`` / ``.contree`` / ``.log``). Behaviour is steered by environment
variables so one fake serves every card.
"""
import importlib.util
import json
import os
import stat
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNNER = os.path.join(ROOT, "tools", "run_planned_tree.py")
GATE = os.path.join(ROOT, "tools", "gtotree_execution_gate.py")

# Tip set that passes the runner's hard QC (same shape as tests/test_409_phylo_run_qc.py GOOD).
TIPS = ["OUTGROUP_Nocardiopsis_dassonvillei_DSM43111", "Streptomyces_griseus_DSM40236",
        "Streptomyces_coelicolor_A32", "Streptomyces_avermitilis_MA4680"]
OUTGROUP = "Nocardiopsis"
GOOD_TREE = ("(OUTGROUP_Nocardiopsis_dassonvillei_DSM43111:0.12,"
             "(Streptomyces_griseus_DSM40236:0.02,"
             "(Streptomyces_coelicolor_A32:0.02,Streptomyces_avermitilis_MA4680:0.02)98/100:0.01)"
             "95/99:0.02);")
NO_SUPPORT_TREE = ("(OUTGROUP_Nocardiopsis_dassonvillei_DSM43111:0.12,"
                   "(Streptomyces_griseus_DSM40236:0.02,"
                   "(Streptomyces_coelicolor_A32:0.02,Streptomyces_avermitilis_MA4680:0.02):0.01):0.02);")

FAKE_GTOTREE = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
if args == ["-v"]:
    print(os.environ.get("FAKE_GTOTREE_VERSION", "GToTree v2.0.0")); sys.exit(0)
rec = os.environ.get("FAKE_RECORD")
if rec:
    with open(rec, "a") as fh: fh.write(json.dumps({"tool": "gtotree", "argv": args,
        "GToTree_HMM_dir": os.environ.get("GToTree_HMM_dir")}) + "\n")
mode = os.environ.get("FAKE_GTOTREE_MODE", "ok")
if mode == "fail_hmm":
    print("  The environment variable 'GToTree_HMM_dir' does not seem to be set :(")
    print("  This shouldn't happen, check on things with `gtt data locations check`.")
    sys.exit(1)
if "-n" in args and os.environ.get("FAKE_GTOTREE_VERSION", "GToTree v2.0.0").startswith("GToTree v2"):
    print("GToTree: error: unrecognized arguments: -n " + args[args.index("-n") + 1]); sys.exit(2)
def opt(flag):
    return args[args.index(flag) + 1] if flag in args else None
glist, out, hmm = opt("-f"), opt("-o"), opt("-H")
if os.environ.get("FAKE_GTOTREE_VERSION", "GToTree v2.0.0").startswith("GToTree v2") and not os.path.isfile(hmm or ""):
    print("  The environment variable 'GToTree_HMM_dir' does not seem to be set :("); sys.exit(1)
entries = [l.strip() for l in open(glist) if l.strip()]
if any(" " in e for e in entries):
    print('  The specified input file "%s" contains spaces in one or more entries ... Exiting for now :(' % glist); sys.exit(1)
tips = [os.path.basename(e).rsplit(".", 1)[0] for e in entries]
drop = [t for t in os.environ.get("FAKE_DROP_TIPS", "").split(",") if t]
os.makedirs(os.path.join(out, "run-files"), exist_ok=True)
markers = ["ADK", "ATP-synt", "CoaE", "DapB_C"]
with open(os.path.join(out, "SCG-hit-counts.tsv"), "w") as fh:
    fh.write("genome_id\t" + "\t".join(markers) + "\n")
    for t in tips:
        fh.write(t + "\t" + "\t".join(("3\t2\t0\t2" if t in drop else "1\t1\t1\t1").split("\t")) + "\n")
with open(os.path.join(out, "genomes-summary-info.tsv"), "w") as fh:
    fh.write("genome_id\tinput\tsource\tlabel\ttaxid\tnum_SCG_hits\tnum_uniq_SCG_hits\tnum_SCG_hits_after_filtering\tnum_total_genes\tin_final_tree\treason_removed\n")
    for t, e in zip(tips, entries):
        fh.write("\t".join([t, e, "nucleotide-fasta", t, "NA", "138", "39" if t in drop else "130", "37" if t in drop else "128",
                            "14784" if t in drop else "9000", "No" if t in drop else "Yes", "too few unique SCG hits" if t in drop else "NA"]) + "\n")
with open(os.path.join(out, "run-files", "removed-genomes.tsv"), "w") as fh:
    fh.write("genome_id\tinput\tsource\tstage_removed\treason_removed\n")
    for t, e in zip(tips, entries):
        if t in drop: fh.write("\t".join([t, e, "nucleotide-fasta", "scg-hit-filter", "too few unique SCG hits"]) + "\n")
with open(os.path.join(out, "gtotree-runlog.txt"), "w") as fh:
    fh.write("GToTree v2.0.0\n#### FILTERING GENOMES WITH TOO FEW HITS ####\n")
    fh.write(("      %d genome(s) removed due to having too few unique SCG hits, reported in:\n" % len(drop)) if drop
             else "             No genomes were removed due to having too few SCG hits!\n")
aln_name = os.environ.get("FAKE_ALN_NAME", "aligned-SCGs.faa")
if os.environ.get("FAKE_GTOTREE_MODE") != "no_alignment":
    with open(os.path.join(out, aln_name), "w") as fh:
        for t in tips:
            if t not in drop: fh.write(">" + t + "\nMKV\n")
sys.exit(int(os.environ.get("FAKE_GTOTREE_RC", "0")))
'''

FAKE_IQTREE = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
rec = os.environ.get("FAKE_RECORD")
if rec:
    with open(rec, "a") as fh: fh.write(json.dumps({"tool": "iqtree", "argv": args}) + "\n")
prefix = args[args.index("--prefix") + 1] if "--prefix" in args else "iqtree"
mode = os.environ.get("FAKE_IQTREE_MODE", "complete")
good = open(os.environ["FAKE_GOOD_TREE"]).read()
nosup = open(os.environ["FAKE_NOSUPPORT_TREE"]).read()
if mode == "complete":
    open(prefix + ".treefile", "w").write(good + "\n")
    open(prefix + ".contree", "w").write(good + "\n")
    open(prefix + ".log", "w").write("IQ-TREE multicore version 3.0.1\nGenerating 1000 samples for ultrafast bootstrap...\n"
                                     "Total CPU time used: 10.0 sec\nTotal wall-clock time used: 5.0 sec (0h:0m:5s)\nDate and Time: now\n")
elif mode == "interrupted":
    open(prefix + ".treefile", "w").write(nosup + "\n")
    open(prefix + ".log", "w").write("IQ-TREE multicore version 3.0.1\nGenerating 1000 samples for ultrafast bootstrap...\n")
sys.exit(int(os.environ.get("FAKE_IQTREE_RC", "0")))
'''


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_runner():
    return _load(RUNNER, "run_planned_tree_trees432")


def load_gate():
    return _load(GATE, "gtotree_execution_gate_trees432")


def _script(path, body):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body.replace("#!/usr/bin/env python3", "#!" + sys.executable, 1))
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def install_fake_bins(tmp_path, monkeypatch, version="GToTree v2.0.0", gtotree_name="gtotree",
                      with_hmm=True):
    """Fake env: <tmp>/env/bin/{gtotree,iqtree}, <tmp>/env/share/gtotree/hmm_sets/Actinobacteria.hmm.
    Returns dict(bin=..., hmm_dir=..., hmm=..., record=...)."""
    env = tmp_path / "env"
    binp = env / "bin"
    binp.mkdir(parents=True)
    hmm_dir = env / "share" / "gtotree" / "hmm_sets"
    hmm_dir.mkdir(parents=True)
    hmm = hmm_dir / "Actinobacteria.hmm"
    if with_hmm:
        hmm.write_text("HMMER3/f [3.3]\nNAME  fake\n")
    _script(str(binp / gtotree_name), FAKE_GTOTREE)
    _script(str(binp / "iqtree"), FAKE_IQTREE)
    record = tmp_path / "fake_record.jsonl"
    good = tmp_path / "good.tre"; good.write_text(GOOD_TREE)
    nosup = tmp_path / "nosup.tre"; nosup.write_text(NO_SUPPORT_TREE)
    monkeypatch.setenv("PATH", str(binp) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.delenv("GToTree_HMM_dir", raising=False)
    monkeypatch.setenv("FAKE_GTOTREE_VERSION", version)
    monkeypatch.setenv("FAKE_RECORD", str(record))
    monkeypatch.setenv("FAKE_GOOD_TREE", str(good))
    monkeypatch.setenv("FAKE_NOSUPPORT_TREE", str(nosup))
    for var in ("FAKE_GTOTREE_MODE", "FAKE_DROP_TIPS", "FAKE_IQTREE_MODE", "FAKE_GTOTREE_RC",
                "FAKE_IQTREE_RC", "FAKE_ALN_NAME"):
        monkeypatch.delenv(var, raising=False)
    return {"bin": str(binp), "hmm_dir": str(hmm_dir), "hmm": str(hmm), "record": str(record)}


def stage_genomes(tmp_path, tips=TIPS, subdir="genomes"):
    """Empty .fna files + an absolute-path genome_list.txt (no spaces). Returns the list path."""
    gdir = tmp_path / subdir
    gdir.mkdir(exist_ok=True)
    paths = []
    for t in tips:
        p = gdir / (t + ".fna")
        p.write_text(">" + t + "\nACGT\n")
        paths.append(str(p))
    gl = tmp_path / "genome_list.txt"
    gl.write_text("\n".join(paths) + "\n")
    return str(gl)


def records(record_path):
    if not os.path.exists(record_path):
        return []
    return [json.loads(l) for l in open(record_path) if l.strip()]


def read_status(workdir):
    p = os.path.join(str(workdir), "run_status.json")
    return json.load(open(p)) if os.path.exists(p) else None


def base_args(genome_list, workdir, **extra):
    argv = ["--genome-list", genome_list, "--workdir", str(workdir), "--outgroup", OUTGROUP, "--approved"]
    for k, v in extra.items():
        argv += ["--" + k.replace("_", "-")] + ([] if v is True else [str(v)])
    return argv
