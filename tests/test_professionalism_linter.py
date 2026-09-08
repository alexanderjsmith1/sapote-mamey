"""Tests for tools/professionalism_linter.py — each rule must FIRE on the bad case and STAY SILENT
on the false-positive case (the linter is worthless if it cries wolf).
Uses only generic placeholder taxa/ids (the engine ships no project/organism specifics)."""
import importlib.util, pathlib, sys

_TOOL = pathlib.Path(__file__).resolve().parents[1] / "tools" / "professionalism_linter.py"
_spec = importlib.util.spec_from_file_location("professionalism_linter", _TOOL)
pl = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(pl)
lint = pl.lint_professionalism

def rules(text):
    return {r for _, r, _, _ in lint(text)}

# --- PRO1 certainty ---
def test_pro1_fires_on_unhedged_certainty():
    assert "PRO1" in rules("This is clearly a novel species.")

def test_pro1_silent_on_descriptive_clearly():
    assert "PRO1" not in rules("Every tip is clearly labeled with Genus species strain.")

def test_pro1_silent_on_hedged():
    assert "PRO1" not in rules("This is likely a candidate-novel species, consistent with the ANI.")

# --- PRO2 unverified problem/identity ---
def test_pro2_fires_without_evidence():
    assert "PRO2" in rules("STRAIN-1 is a duplicate and should be removed.")

def test_pro2_silent_with_evidence_hash():
    assert "PRO2" not in rules("query.fna is a duplicate (md5 identical; keep=reference_genomes/x.fna).")

def test_pro2_silent_with_ani_evidence():
    assert "PRO2" not in rules("The two are identical at 100% ANI over the full contig.")

# --- PRO3 metric without denominator ---
def test_pro3_fires_on_bare_percent():
    assert "PRO3" in rules("About 89% of the calls are housekeeping sugar operons.")

def test_pro3_silent_with_denominator():
    assert "PRO3" not in rules("40 of 45 items (89%) are candidate-novel.")

def test_pro3_silent_on_identity_percent():
    # a pairwise %identity / ANI / coverage is intrinsically self-denominated, not a proportion
    assert "PRO3" not in rules("STRAIN-1 nearest named = Genusa speciesa (98.93% id).")
    assert "PRO3" not in rules("STRAIN-2 leans conspecific at 98.72% ANI, 93.5% coverage.")

# --- PRO4 nearest identity without a number ---
def test_pro4_fires_without_number():
    assert "PRO4" in rules("The nearest named type is Genusa speciesa.")

def test_pro4_silent_with_ani():
    assert "PRO4" not in rules("Nearest named type: Genusa speciesa (ANI 81.66%, aln 50.6%).")

# --- structure / smoke ---
def test_clean_text_has_no_findings():
    txt = ("STRAIN-2 leans conspecific with Genusa speciesa (ANI 98.72%, aln 93.5%); "
           "44 of 45 items carry the marker. Placement is consistent with the tree.")
    assert lint(txt) == []

def test_headings_and_quotes_ignored():
    assert lint("# Clearly a heading\n> quoted: this is obviously fine") == []
