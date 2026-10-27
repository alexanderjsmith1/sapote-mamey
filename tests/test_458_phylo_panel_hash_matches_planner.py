"""The panel selector and the GToTree planner give one content hash for the same assembly.

The planner turns U into T before hashing; the selector kept U, so a staged panel built from a
FASTA with U failed the planner's revalidation with a content-hash mismatch.
"""
import importlib.util
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def _load(name):
    spec = importlib.util.spec_from_file_location(f"{name}_458u", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod   # dataclasses resolve their module by name
    spec.loader.exec_module(mod)
    return mod


panel, plan = _load("build_phylo_panel"), _load("plan_gtotree_iqtree")


@pytest.mark.parametrize("fasta", [b">c1\nACGUACGU\n>c2\nGGCC\n", b">c1\nacgt-acgt\n>c2\nGG.CC\n"])
def test_selector_and_planner_agree(fasta):
    seqs = panel.parse_sequence_bytes(fasta, ".fna")
    assert panel.assembly_content_sha256(seqs) == plan.normalized_assembly_sha256(fasta)
