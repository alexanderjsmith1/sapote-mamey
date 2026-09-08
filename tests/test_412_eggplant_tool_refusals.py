"""v9.7.412 — hostile audit of the sealed .411 placement tools: typed refusals.

Fail-before (measured on sealed .411): `placement_figure.py --graft <non-Newick text>` exited 0 and wrote
a figure; `build_placement_ggtree_inputs.py` did the same and wrote a 1-tip "pruned" tree; a missing
input raised FileNotFoundError and an unwritable output PermissionError as raw tracebacks. Synthetic only.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def _run(tool, *args):
    return subprocess.run([sys.executable, str(TOOLS / tool), *map(str, args)], capture_output=True, text=True,
                          env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin", "MPLBACKEND": "Agg"})


@pytest.fixture
def garbage(tmp_path):
    p = tmp_path / "garbage.txt"; p.write_text("not a tree at all\n", encoding="utf-8"); return p


@pytest.fixture
def small_tree(tmp_path):
    p = tmp_path / "ok.nwk"; p.write_text("((A_ref:0.1,B_ref:0.2):0.3,outgroup_X:0.4);\n", encoding="utf-8"); return p


@pytest.mark.parametrize("tool,extra", [("placement_figure.py", ["--out", "OUT.png"]), ("build_placement_ggtree_inputs.py", ["--out-prefix", "OUT"])])
def test_garbage_graft_is_refused_not_rendered(tool, extra, garbage, tmp_path):
    extra = [str(tmp_path / e) if e.startswith("OUT") else e for e in extra]
    r = _run(tool, "--graft", garbage, *extra)
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    assert "INPUT_NOT_A_TREE" in r.stderr
    assert "Traceback" not in r.stderr
    assert not list(tmp_path.glob("OUT*")), "no output may be written from a non-tree"


@pytest.mark.parametrize("tool,extra", [("placement_figure.py", ["--out", "OUT.png"]), ("build_placement_ggtree_inputs.py", ["--out-prefix", "OUT"])])
def test_missing_graft_is_a_typed_refusal(tool, extra, tmp_path):
    extra = [str(tmp_path / e) if e.startswith("OUT") else e for e in extra]
    r = _run(tool, "--graft", tmp_path / "nope.nwk", *extra)
    assert r.returncode == 2 and "INPUT_NOT_FOUND" in r.stderr and "Traceback" not in r.stderr


def test_unwritable_output_is_a_typed_refusal(small_tree, tmp_path):
    blocker = tmp_path / "file.txt"; blocker.write_text("x", encoding="utf-8")
    r = _run("placement_figure.py", "--graft", small_tree, "--out", blocker / "sub" / "fig.png")
    assert r.returncode == 2 and "OUTPUT_NOT_WRITABLE" in r.stderr and "Traceback" not in r.stderr


def test_postflight_missing_treefile_is_a_typed_refusal(tmp_path):
    r = _run("phylo_postflight.py", tmp_path / "nope.treefile")
    assert r.returncode == 2 and "INPUT_NOT_FOUND" in r.stderr and "Traceback" not in r.stderr


def test_harvest_unwritable_out_dir_is_a_typed_refusal(tmp_path):
    blocker = tmp_path / "file.txt"; blocker.write_text("x", encoding="utf-8")
    r = _run("harvest_16s.py", "--genus", "Streptomyces", "--out-dir", blocker / "sub")
    assert r.returncode == 2 and "OUTPUT_NOT_WRITABLE" in r.stderr and "Traceback" not in r.stderr


@pytest.mark.parametrize("tool,args", [
    ("placement_figure.py", ["--graft", "x", "--out", "y", "--neighbors-per", "2"]),
    ("build_placement_ggtree_inputs.py", ["--graft", "x", "--out-prefix", "y", "--neigh", "2"]),
    ("harvest_16s.py", ["--genus", "X", "--out-dir", "y", "--strain", "AS-1"]),
    ("phylo_postflight.py", ["t", "--outg", "OG"]),
])
def test_option_prefixes_are_not_silently_expanded(tool, args):
    """The .409 audit's `--display`-abbreviation hazard: a prefix silently binds to whichever option it
    matches today and changes meaning when a sibling option is added. New tools refuse prefixes."""
    r = _run(tool, *args)
    assert r.returncode == 2 and "unrecognized arguments" in r.stderr


def test_phylo_place_subcommand_prefixes_are_not_silently_expanded():
    r = _run("phylo_place.py", "all", "ref.fa", "--group", "X", "--query", "q.fa", "--outd", "/tmp/x")
    assert r.returncode == 2 and "unrecognized arguments" in r.stderr
