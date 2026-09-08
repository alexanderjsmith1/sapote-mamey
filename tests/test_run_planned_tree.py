"""Tests for tools/run_planned_tree.py — the approved-tree execution companion.

Fast/hermetic: exercises the approval gate, the no-space guard, --help, and the HMM-dir
resolver. Does NOT invoke GToTree/IQ-TREE (that needs the phylo env + genomes + approval).
"""
import importlib.util
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
# tool lives at ../tools/run_planned_tree.py within the card; in the cut it is tools/run_planned_tree.py
CANDS = [
    os.path.join(HERE, "..", "tools", "run_planned_tree.py"),
    os.path.join(HERE, "..", "..", "..", "tools", "run_planned_tree.py"),
    os.path.join(os.getcwd(), "tools", "run_planned_tree.py"),
]


def _load():
    for p in CANDS:
        if os.path.exists(p):
            spec = importlib.util.spec_from_file_location("run_planned_tree", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise FileNotFoundError("run_planned_tree.py not found in candidate locations")


def test_refuses_without_approval():
    mod = _load()
    rc = mod.main(["--genome-list", "x.txt", "--workdir", "/tmp/nospace_wd", "--outgroup", "Foo"])
    assert rc == 2, "must refuse to run without --approved (tree-approval gate)"


def test_refuses_spaced_workdir():
    mod = _load()
    rc = mod.main(["--genome-list", "x.txt", "--workdir", "/tmp/has space wd",
                   "--outgroup", "Foo", "--approved"])
    assert rc == 2, "must refuse a workdir path containing spaces"


def test_help_parses():
    mod = _load()
    try:
        mod.main(["--help"])
    except SystemExit as e:
        assert e.code == 0


def test_hmm_dir_resolver():
    mod = _load()
    # <env>/bin/GToTree -> <env>/share/gtotree/hmm_sets
    import tempfile
    with tempfile.TemporaryDirectory() as env:
        binp = os.path.join(env, "bin"); os.makedirs(binp)
        hmm = os.path.join(env, "share", "gtotree", "hmm_sets"); os.makedirs(hmm)
        gt = os.path.join(binp, "GToTree"); open(gt, "w").close()
        assert mod._hmm_dir_for(gt) == hmm
    # missing dir -> None
    assert mod._hmm_dir_for("/no/such/bin/GToTree") is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); print("ok", name)
