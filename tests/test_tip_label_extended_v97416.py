import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import tip_label as tl

def test_refseq_complete_namespace():
    assert tl.species_from_tip("NZ_CP108647.1_Streptomyces_griseus") == ("Streptomyces griseus", "NZ_CP108647.1")
    assert tl.accession("GCF_000123456.123") == "GCF_000123456.123"

def test_no_prefix_salvage_or_ambiguity():
    assert tl.accession("IFO_14684") == ""
    assert tl.accession("NR_151944.1 NR_151945.2") == ""

def test_host_and_accession_survive_narrow_display():
    lab=tl.ref_label("Streptomyces longissimus", acc="NR_151944.123", source="root nodule of a plant", width=12)
    assert "[root nodule of a plant]" in lab and lab.endswith("(NR_151944.123)")
    assert lab.count("[") == lab.count("]")

def test_outgroup_normal_grammar():
    assert tl.outgroup_label("Example bacterium", "NR_151944.1") == "Example bacterium (NR_151944.1)"
