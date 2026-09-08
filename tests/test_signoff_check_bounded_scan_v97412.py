"""v9.7.412 (Razzle Dazzle Rose): signoff_check's scan mode must be a BOUNDED walk — it must find a
recent tree under a normal folder and must NOT descend into the huge subtrees that can never hold
tree artefacts (conda envs, genome pools, wheelhouses). The unbounded recursive glob it replaces
crawled a whole 18 GB workspace on every chat turn-end and thrashed the machine."""
from __future__ import annotations
import importlib.util, os, time
_TOOL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "signoff_check.py")
spec = importlib.util.spec_from_file_location("_sc", _TOOL); sc = importlib.util.module_from_spec(spec); spec.loader.exec_module(sc)

def _mk(tmp, rel, age_s=0):
    p = tmp / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text("(a:1,b:2);", encoding="utf-8")
    if age_s: t = time.time() - age_s; os.utime(p, (t, t))
    return p

def test_finds_recent_tree_and_prunes_heavy_dirs(tmp_path):
    keep = _mk(tmp_path, "runs/tree01/iqtree.treefile")
    _mk(tmp_path, "miniconda3/envs/phylo/share/demo.treefile")        # pruned: conda env
    _mk(tmp_path, "Tools/reference_genomes/x/y.treefile")             # pruned: genome pool
    _mk(tmp_path, ".git/objects/z.treefile")                          # pruned: dot-dir
    got = sc.find_recent_trees(str(tmp_path), minutes=90)
    assert got == [os.path.abspath(str(keep))]

def test_old_trees_excluded_by_minutes(tmp_path):
    _mk(tmp_path, "runs/old.treefile", age_s=3 * 3600)               # 3 h old, window 90 min
    new = _mk(tmp_path, "runs/new.treefile")
    got = sc.find_recent_trees(str(tmp_path), minutes=90)
    assert got == [os.path.abspath(str(new))]

def test_env_extends_prune(tmp_path, monkeypatch):
    _mk(tmp_path, "scratch_big/deep/t.treefile")
    keep = _mk(tmp_path, "runs/t.treefile")
    got = sc.find_recent_trees(str(tmp_path), minutes=90, prune=sc.PRUNE_DIRS | {"scratch_big"})
    assert got == [os.path.abspath(str(keep))]
