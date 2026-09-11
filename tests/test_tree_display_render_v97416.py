"""Exercise the real R graphics boundary using generic frozen display receipts."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest
from tests.test_tree_display_contract_v97416 import make_display, display_paths

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def rscript():
    executable = shutil.which("Rscript")
    if not executable:
        pytest.skip("R graphics stack not installed")
    cp = subprocess.run([executable, "-e", 'quit(status=if(all(sapply(c("ape","ggtree","ggplot2","aplot","treeio","patchwork"),requireNamespace,quietly=TRUE))) 0 else 1)'], capture_output=True, timeout=60)
    if cp.returncode:
        pytest.skip("R graphics packages unavailable")
    return executable


def render(rscript, tmp_path, case, **override):
    _, parent, _, receipt, sha = case
    paths = display_paths(receipt)
    env = dict(os.environ)
    for key in ("GG_SKIP_GUARD", "GG_GATE_EXEMPTION", "GG_GATE_TREE", "GG_DISPLAY_RECEIPT", "GG_DISPLAY_RECEIPT_SHA256"):
        env.pop(key, None)
    env.update(SAPOTE_PYTHON=sys.executable, GG_DISPLAY_RECEIPT=str(receipt),
               GG_DISPLAY_RECEIPT_SHA256=sha, GG_GATE_TREE=str(parent),
               GG_FIGID="Figure generic display", GG_METHODS="Generic test tree with fixed branch lengths.",
               GG_STRIP1_TITLE="Recorded category", GG_STRIP2_TITLE="Recorded source")
    env.update(override)
    prefix = tmp_path / "figure with spaces"
    cp = subprocess.run([rscript, str(ROOT / "tools/ggtree_rect_heatmap.R"), str(paths["tree"]),
                         str(paths["metadata"]), str(prefix), "QUERY_A"], env=env,
                        capture_output=True, text=True, timeout=120)
    return cp, prefix


@pytest.mark.parametrize("strips,prune", [("0", False), ("2", True)])
def test_receipted_display_renders_named_figures_and_binds_outputs(rscript, tmp_path, strips, prune):
    case = make_display(tmp_path, prune_outgroup=prune)
    cp, prefix = render(rscript, tmp_path, case, GG_STRIPS=strips)
    assert cp.returncode == 0, cp.stdout + cp.stderr
    receipt = json.loads(Path(str(prefix) + ".render_receipt.json").read_text())
    import hashlib
    for suffix in (".pdf", ".png", ".session.txt"):
        path = Path(str(prefix) + suffix)
        assert path.stat().st_size > 100
        assert receipt["outputs"][suffix]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert "DISPLAY_ONLY" not in receipt["authority"]  # Render receipt has its own scope.
    assert receipt["authority"] == "RENDER_ONLY_NOT_SCIENTIFIC_ACCEPTANCE"
    # A second run refuses the old named outputs before drawing over them.
    before = Path(str(prefix) + ".pdf").read_bytes()
    second, _ = render(rscript, tmp_path, case, GG_STRIPS=strips)
    assert second.returncode != 0 and "already exist" in second.stderr
    assert Path(str(prefix) + ".pdf").read_bytes() == before


@pytest.mark.parametrize("mutation,expected", [("parent", "BOUND_FILE_CHANGED"),
    ("metadata", "BOUND_FILE_CHANGED"), ("receipt", "HASH_MISMATCH"),
    ("display", "BOUND_FILE_CHANGED"), ("skip", "overrides are not supported"),
    ("exemption", "overrides are not supported"), ("unbound", "hash-bound display receipt")])
def test_receipt_or_guard_changes_refuse_before_any_graphics(rscript, tmp_path, mutation, expected):
    case = make_display(tmp_path, prune_outgroup=True)
    _, parent, _, receipt, _ = case
    paths = display_paths(receipt)
    override = {}
    if mutation == "parent": parent.write_text(parent.read_text() + "\n")
    elif mutation == "metadata": paths["metadata"].write_text(paths["metadata"].read_text() + "\n")
    elif mutation == "receipt": receipt.write_text(receipt.read_text() + "\n")
    elif mutation == "display": paths["tree"].write_text(paths["tree"].read_text() + "\n")
    elif mutation == "skip": override["GG_SKIP_GUARD"] = "1"
    elif mutation == "exemption": override["GG_GATE_EXEMPTION"] = "arbitrary reason"
    elif mutation == "unbound": override.update(GG_DISPLAY_RECEIPT="", GG_DISPLAY_RECEIPT_SHA256="")
    cp, prefix = render(rscript, tmp_path, case, **override)
    assert cp.returncode != 0 and expected in cp.stdout + cp.stderr, cp.stdout + cp.stderr
    assert not Path(str(prefix) + ".pdf").exists()
    assert not Path(str(prefix) + ".render_receipt.json").exists()
