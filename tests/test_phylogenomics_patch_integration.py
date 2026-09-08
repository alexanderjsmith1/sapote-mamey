"""Cross-family guards for the reconciled optional phylogenomics patch."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def load_tool(name: str):
    path = ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"integration_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_panel_builder_and_run_planner_share_exact_content_hash_contract():
    builder = load_tool("build_phylo_panel")
    planner = load_tool("plan_gtotree_iqtree")
    records = ["AAAACCCC", "GGGGTTTT"]
    fasta = b">second\nGGGGTTTT\n>first\nAAAACCCC\n"
    assert builder.assembly_content_sha256(records) == planner.normalized_assembly_sha256(fasta)


def test_canonical_docs_route_one_panel_authority_and_separate_16s():
    phylo = (ROOT / "docs" / "phylogenomics.md").read_text(encoding="utf-8")
    preflight = (ROOT / "docs" / "GTOTREE_IQTREE_PREFLIGHT.md").read_text(encoding="utf-8")
    assert "build_phylo_panel.py (membership, one outgroup" in phylo
    assert "plan_gtotree_iqtree.py --prepared-panel" in phylo
    assert "16S must not be disguised as a GToTree protein HMM" in phylo
    assert "The panel selector is authoritative for membership" in preflight


def test_nonrunning_preparers_do_not_import_subprocess_or_network_clients():
    for name in (
        "build_phylo_panel.py",
        "rank_clusterblast_phylo_candidates.py",
        "prepare_biosynthetic_tree_inputs.py",
    ):
        text = (ROOT / "tools" / name).read_text(encoding="utf-8")
        assert "import subprocess" not in text
        assert "import requests" not in text
        assert "import urllib" not in text


def test_expected_patch_surface_is_complete():
    required = {
        "tools/plan_gtotree_iqtree.py",
        "tools/build_phylo_panel.py",
        "tools/rank_clusterblast_phylo_candidates.py",
        "tools/prepare_biosynthetic_tree_inputs.py",
        "docs/phylogenomics.md",
        "docs/GTOTREE_IQTREE_PREFLIGHT.md",
        "docs/GTOTREE_PANEL_SELECTION.md",
        "docs/CLUSTERBLAST_PHYLO_CANDIDATES.md",
        "docs/PKS_KS_TREE_OPTIONS.md",
        "docs/RIPP_TREE_OPTIONS.md",
        "docs/SPECIES_VS_BGC_TREE_COMPARISON.md",
    }
    assert all((ROOT / relative).is_file() for relative in required)
