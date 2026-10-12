"""Shared fakes for the TREES_432 launcher tests. Never runs GToTree or IQ-TREE.

``install_fake_bins(tmp_path, monkeypatch, ...)`` drops executable ``gtotree`` and ``iqtree``
Python scripts on PATH. They mimic the GToTree v2.0.0 / IQ-TREE 3 surface the launcher relies on:
``-v`` output, output-directory layout (``aligned-SCGs.faa``, ``run-files/removed-genomes.tsv``,
``genomes-summary-info.tsv``, ``SCG-hit-counts.tsv``, ``gtotree-runlog.txt``), and the IQ-TREE
prefix files (``.treefile`` / ``.contree`` / ``.log``). Behaviour is steered by environment
variables so one fake serves every card.
"""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

import pytest
from tests._python_fixture_launcher import write_python_fixture

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
    print(os.environ.get("FAKE_GTOTREE_VERSION", "GToTree v2.0.0"))
    sys.exit(int(os.environ.get("FAKE_GTOTREE_VERSION_RC", "0")))
if args in (["-h"], ["-s"]):
    # Independent native-style declaration roster. v2 condensed -h omits the
    # detailed mapping/alignment-only flags; the shared probe must request -s.
    version = os.environ.get("FAKE_GTOTREE_VERSION", "GToTree v2.0.0")
    v2 = version.startswith("GToTree v2")
    flags = ["-f <file>", "-H <file>", "-j <int>", "-o <dir>"]
    if not v2 or args == ["-s"]:
        flags += ["-m <file>", "-M <int>", "-N", "-k"]
    if not v2:
        flags += ["-n <int>"]
    missing = os.environ.get("FAKE_GTOTREE_HELP_MISSING", "")
    flags = [line for line in flags if line.split()[0] != missing]
    print("\n".join(flags))
    sys.exit(int(os.environ.get("FAKE_GTOTREE_HELP_RC", "0")))
rec = os.environ.get("FAKE_RECORD")
if rec:
    with open(rec, "a") as fh: fh.write(json.dumps({"tool": "gtotree", "argv": args,
        "python": sys.executable, "prefix": sys.prefix,
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
    with open(rec, "a") as fh: fh.write(json.dumps({"tool": "iqtree", "argv": args,
        "python": sys.executable, "prefix": sys.prefix}) + "\n")
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


@pytest.fixture(name="tmp_path")
def native_tree_tmp_path(tmp_path_factory):
    """Scoped to four importing test modules; production requires space-free paths.

    Keep a lifecycle/hash inventory under pytest's own basetemp, and remove only
    the owned external synthetic tree before teardown completes.
    """
    receipt_dir = tmp_path_factory.mktemp("trees432_native_scope")
    receipt_path = receipt_dir / "external_temp_receipt.json"
    receipt = {"schema": "sapote-mamey.test-native-tree-temp.v1", "status": "ACTIVE",
               "scope": "synthetic tree432 test fixture only", "external_temp_root": None,
               "cleanup_complete": False}
    with tempfile.TemporaryDirectory(prefix="sapote-trees432-", dir="/tmp") as temporary:
        root = Path(temporary).resolve()
        assert " " not in str(root), "native runner fixture needs a space-free physical path"
        receipt["external_temp_root"] = str(root)
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
        try:
            yield root
        finally:
            files = []
            for path in sorted(root.rglob("*")):
                if path.is_symlink():
                    files.append({"path": path.relative_to(root).as_posix(), "kind": "symlink",
                                  "target": os.readlink(path)})
                elif path.is_file():
                    data = path.read_bytes()
                    files.append({"path": path.relative_to(root).as_posix(), "kind": "file",
                                  "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
            receipt.update(files_before_cleanup=files, file_count=len(files),
                           file_bytes=sum(row.get("bytes", 0) for row in files))
    receipt.update(status="CLEANED", cleanup_complete=not root.exists())
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")


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
    write_python_fixture(path, body, mode=None)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def install_fake_bins(tmp_path, monkeypatch, version="GToTree v2.0.0", gtotree_name="gtotree",
                      with_hmm=True, admit_synthetic_resource_profile=True):
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
    if admit_synthetic_resource_profile:
        # This child implements no native HMM search. Its exact source is bound
        # here solely to retain downstream launcher/gate test coverage while
        # the default native v2 resource profile remains held in production.
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import _gtotree_versions as policy
        original_contract = policy.resource_contract
        fake_path = binp / gtotree_name
        fake_payload = fake_path.with_name(fake_path.name + ".fixture.py")
        fake_sha = hashlib.sha256(fake_path.read_bytes()).hexdigest()
        payload_sha = hashlib.sha256(fake_payload.read_bytes()).hexdigest()
        def synthetic_resource_contract(version_text, threads, jobs):
            result = original_contract(version_text, threads, jobs)
            if result["profile"] == "2.0.x":
                assert hashlib.sha256(fake_path.read_bytes()).hexdigest() == fake_sha
                assert hashlib.sha256(fake_payload.read_bytes()).hexdigest() == payload_sha
                assert version_text.strip() == version.strip()
                result.update(status="PASS_EXPLICIT_CLI_RESOURCE_BOUND", hmm_threads=0,
                    maximum_parallel_search_threads=0, hmm_control="NO_HMM_STAGE_IN_SYNTHETIC_CHILD",
                    source_profile="TEST_ONLY_BOUND_SYNTHETIC_CHILD",
                    synthetic_child={"path": str(fake_path), "sha256": fake_sha,
                                     "payload_path": str(fake_payload), "payload_sha256": payload_sha,
                                     "native_execution": False})
            return result
        monkeypatch.setattr(policy, "resource_contract", synthetic_resource_contract)
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
                "FAKE_IQTREE_RC", "FAKE_ALN_NAME", "FAKE_GTOTREE_VERSION_RC",
                "FAKE_GTOTREE_HELP_RC", "FAKE_GTOTREE_HELP_MISSING"):
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
