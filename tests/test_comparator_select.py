"""Tests for tools/comparator_select.py — the pure (blast-free) logic:
organism parsing (named vs unnamed), reverse-complement, and genome resolution from an inventory.
Uses only generic placeholder taxa/ids (the engine ships no project/organism specifics)."""
import importlib.util, pathlib

_TOOL = pathlib.Path(__file__).resolve().parents[1] / "tools" / "comparator_select.py"
_spec = importlib.util.spec_from_file_location("comparator_select", _TOOL)
cs = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(cs)


# --- parse_org: a real species is named; sp./environmental is not ---
def test_named_species():
    g, s, named = cs.parse_org("Genusa speciesa strain XYZ 1234 16S ribosomal RNA, partial")
    assert (g, s, named) == ("Genusa", "speciesa", True)

def test_unnamed_sp_is_not_named():
    g, s, named = cs.parse_org("Genusa sp. STRAINQ 16S ribosomal RNA, partial sequence")
    assert g == "Genusa" and named is False

def test_uncultured_is_not_named():
    _, _, named = cs.parse_org("uncultured bacterium clone 16S ribosomal RNA")
    assert named is False

def test_garbage_title_is_safe():
    assert cs.parse_org("x") == ("", "", False)


# --- revcomp ---
def test_revcomp():
    assert cs._revcomp("ACGTN") == "NACGT"


# --- find_genomes: match by genus AND species-in-path, size-flag out-of-window ---
def _inv():
    return [
        {"canonical_path": "reference_genomes/x/Genusa_speciesa_TYPE.fna",
         "genus": "Genusa", "bp": "8000000", "accession": "GCF_1"},
        {"canonical_path": "somewhere/Genusa_speciesb_STR.fna",
         "genus": "Genusa", "bp": "8600000", "accession": "GCF_2"},
        {"canonical_path": "frag/Genusa_speciesa_partial.fna",
         "genus": "Genusa", "bp": "1200000", "accession": ""},   # too small -> SIZE?
    ]

def test_find_genomes_matches_species_in_path():
    hits = cs.find_genomes(_inv(), "Genusa", "speciesa")
    paths = [h[0] for h in hits]
    assert any("speciesa_TYPE" in p for p in paths)
    assert all("speciesb" not in p for p in paths)  # wrong species excluded

def test_find_genomes_size_flag():
    hits = cs.find_genomes(_inv(), "Genusa", "speciesa")
    # the 8Mb genome sorts first (no flag); the 1.2Mb one is flagged
    assert hits[0][3] == "" and hits[0][1] == 8000000
    assert any("SIZE?" in h[3] for h in hits)

def test_find_genomes_none_for_absent_species():
    assert cs.find_genomes(_inv(), "Genusa", "speciesz") == []
