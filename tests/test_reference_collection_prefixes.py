"""Declared collection prefixes must not erase genuinely conflicting accessions."""
import importlib.util
from pathlib import Path
import pytest


def tool():
    path = Path(__file__).resolve().parents[1] / "tools/build_placement_ggtree_inputs.py"
    spec = importlib.util.spec_from_file_location("reference_collection_subject", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("prefix", ["SYSU", "LL", "NRRL", "YIM", "CCTCC"])
def test_explicit_supported_collection_prefix_resolves_and_keeps_strain_label(prefix):
    module = tool()
    label = f"Genus_species_strain_{prefix}_K12345_NR_123456.1"
    assert module._ref_accession(label) == "NR_123456.1"
    assert "K12345" in module._ref_label(label, "Genus")


@pytest.mark.parametrize("label", [
    "NR_123456.1 OR MW444715.1",
    "NR_123456.1 strain accession MW444715.1",
    "NR_123456.1 strain OR MW444715.1",
    "NR_123456.1 MW444715.1",
    "NR_123456.1 strain NR_234567.1",
    "NR_123456.1 strain SYSU NR_234567.1",
    "Genus_species_SYSU_K12345_NR_123456.1",
])
def test_unresolved_second_accession_refuses(label):
    with pytest.raises(ValueError, match="REFERENCE_ACCESSION_CONFLICT"):
        tool()._ref_accession(label)
