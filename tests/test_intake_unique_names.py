import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from intake_harness import assign_unique_names, clean_name, assembly_tag

def test_colliding_assemblies_disambiguated():
    zips = ["Melissospora_conviva_GCA_048929135_1_ASM4892913v1_genomic.zip",
            "Melissospora_conviv_GCA_049523575_1_ASM4952357v1_genomic.zip",
            "Melissospora_conviva_GCA_049523535_1_ASM4952353v1_genomic.zip"]
    names = assign_unique_names(zips)
    assert len(set(names.values())) == 3, f"expected 3 unique, got {names}"
    assert all("ASM" in n or "GC" in n for n in names.values())

def test_unique_base_kept_clean():
    zips = ["Streptomyces_clavuligerus_ATCC_27064.zip", "Strain705_new_Loose_copy.zip"]
    names = assign_unique_names(zips)
    assert names["Streptomyces_clavuligerus_ATCC_27064.zip"] == "Streptomyces_clavuligerus_ATCC_27064"
    assert "Strain705" in names["Strain705_new_Loose_copy.zip"]

def test_assembly_tag_extraction():
    assert assembly_tag("x_GCA_049523575_1_ASM4952357v1_genomic.zip") in ("GCA_049523575","ASM4952357v1")
