"""v9.7.229: strain-ID auto-derivation — Genus_species_Designation from the organism record, never an
LLM abbreviation; canonical AS-cohort IDs are never rewritten."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mamey.cohort_resolver import derive_strain_id as d

def test_derives_from_organism_record():
    assert d("NZ_ARHC00000000_1", "Salinispora arenicola CNX814", "NZ_ARHC00000000_1.zip")[0] == "Salinispora_arenicola_CNX814"
    assert d("SMALAY", "Streptomyces malaysiensis SID8382")[0] == "Streptomyces_malaysiensis_SID8382"
    assert d("SSPORANG", "Streptosporangium sp. NPDC006013")[0] == "Streptosporangium_sp_NPDC006013"

def test_filename_fallback_when_record_empty():
    assert d("SID4912", "", "Streptomyces_sp__SID4912_x.zip")[0] == "Streptomyces_sp_SID4912"

def test_never_rewrites_canonical_as_id():
    assert d("AS-441", "Streptomyces sp.")[0] == "AS-441"
    assert d("Streptomyces_malaysiensis_SID8382", "Streptomyces malaysiensis SID8382")[0] == "Streptomyces_malaysiensis_SID8382"

def test_no_genus_keeps_label_with_note():
    out, note = d("XYZ", "", "")
    assert out == "XYZ" and "supply --strain" in note
