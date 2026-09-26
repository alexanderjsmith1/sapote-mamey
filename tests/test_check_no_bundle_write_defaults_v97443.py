"""v9.7.443: tools/check_no_bundle_write_defaults.py, the gate for writes that default into the bundle.

The fixture cases pin what the gate must tell apart:
  - a write under a cwd-fallback root (os.getcwd() / workspace_root()) is flagged;
  - a root anchored to __file__ (a tool regenerating its own shipped data) is not;
  - a write in a function that calls assert_output_outside_bundle, directly or through a
    same-module wrapper, is not;
  - a same-named local in another function does not leak (scope isolation);
  - one alias hop (CACHE = env.get("X", f"{ROOT}/...")) is followed;
  - scanning nothing is a refusal, not a pass.
The last test is the ratchet on the shipped tree: the count may fall, never rise.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "check_no_bundle_write_defaults.py"

# Unguarded sites measured on the sealed v9.7.442a tree. Lower it when a site adopts the guard;
# never raise it to admit a new one.
CEILING = 21


def _run(root, *extra):
    r = subprocess.run([sys.executable, str(GATE), str(root), *extra], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


@pytest.fixture
def tree(tmp_path):
    for d in ("tools", "mamey", "deliverable_tools"):
        (tmp_path / d).mkdir()
    return tmp_path


def test_flags_a_write_under_a_cwd_fallback_root(tree):
    (tree / "deliverable_tools" / "bad.py").write_text(
        "import os\n"
        'ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())\n'
        'open(f"{ROOT}/sapote_deliverables/x.md", "w").write("h")\n')
    code, out = _run(tree)
    assert code == 1 and "deliverable_tools/bad.py" in out


def test_passes_a_file_anchored_regenerator(tree):
    (tree / "tools" / "regen.py").write_text(
        "import os\n"
        "HERE = os.path.dirname(os.path.abspath(__file__))\n"
        "ROOT = os.path.dirname(HERE)\n"
        'open(f"{ROOT}/mamey/data/x.json", "w").write("{}")\n')
    code, out = _run(tree)
    assert code == 0, out


def test_passes_a_guarded_write(tree):
    (tree / "tools" / "guarded.py").write_text(
        "import os\n"
        "from mamey.path_safety import assert_output_outside_bundle\n"
        'ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())\n'
        "def main():\n"
        '    od = f"{ROOT}/strain_data/out"\n'
        "    assert_output_outside_bundle(od, __file__)\n"
        "    os.makedirs(od)\n")
    code, out = _run(tree)
    assert code == 0, out


def test_passes_a_write_guarded_through_a_wrapper(tree):
    (tree / "tools" / "wrapped.py").write_text(
        "import os, sys\n"
        'ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())\n'
        'OUT = os.path.join(ROOT, "plots")\n'
        "def _refuse(path):\n"
        "    from mamey.path_safety import assert_output_outside_bundle\n"
        "    assert_output_outside_bundle(path, __file__)\n"
        "def main():\n"
        "    _refuse(OUT)\n"
        "    os.makedirs(OUT)\n")
    code, out = _run(tree)
    assert code == 0, out


def test_same_name_in_another_function_does_not_leak(tree):
    (tree / "mamey" / "two.py").write_text(
        "import os\n"
        "def a(pkg):\n"
        "    outdir = os.path.join(str(pkg), 'panel')\n"
        "    os.makedirs(outdir)\n"
        "def b(args):\n"
        "    outdir = getattr(args, 'outdir', None) or os.getcwd()\n"
        "    os.makedirs(outdir)\n")
    code, out = _run(tree)
    assert code == 1 and "in b()" in out and "in a()" not in out


def test_follows_one_alias_hop(tree):
    (tree / "tools" / "alias.py").write_text(
        "import os\n"
        'ROOT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd())\n'
        'CACHE = os.environ.get("C", f"{ROOT}/OFFICIAL_DATA/cache")\n'
        "def get():\n"
        '    os.makedirs(os.path.join(CACHE, "16S"))\n')
    code, out = _run(tree)
    assert code == 1 and "tools/alias.py" in out


def test_max_is_a_ratchet_ceiling(tree):
    (tree / "tools" / "one.py").write_text(
        "import os\n"
        "ROOT = os.getcwd()\n"
        'os.makedirs(f"{ROOT}/x")\n')
    assert _run(tree)[0] == 1
    assert _run(tree, "--max", "1")[0] == 0


def test_scanning_nothing_is_a_refusal(tmp_path):
    assert _run(tmp_path)[0] == 2


def test_shipped_tree_does_not_grow_past_the_ceiling():
    code, out = _run(ROOT, "--max", str(CEILING))
    assert code == 0, out
