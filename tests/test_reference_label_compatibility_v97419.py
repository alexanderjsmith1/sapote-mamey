"""Reference-label compatibility regression — reference tip labels lost the strain NUMBER of a type strain.

Two causes, measured over 230 real reference tips and 27,959 type-strain tips in the 16S store:

1. The v9.7.417 accession strip used `re.search` — ONE match. The registry outgroup fetcher emits a
   tip carrying the accession TWICE, so the survivor stayed in the text as stray words and inflated
   the organism string 37 -> 49 chars. 2 of the 5 real truncations came from this, not the cap.
2. The cap itself was a bare 34. 48 is the length of the longest abbreviated subsp.-subsp. binomial
   and the cap at which the 9 store-wide cases where truncation hides a DIFFERENT taxon stop
   colliding.

Not a correctness bug: the accession is stripped BEFORE the cap and re-appended AFTER, so it is never
truncated and guarantees uniqueness — ZERO full-label collisions across all 27,959 store tips. This is
readability: a reader could not cite "DSM 40225" from a figure that rendered "... DSM".

CORRECTION, 2026-09-09. The v9.7.418 seal reimplemented this repair and, in doing so, FIXED SOMETHING
I HAD WRONG: it renders the accession in its canonical NCBI form, "NR_149213.1", where my version
stripped the underscore to "NR149213.1". The canonical form is what
OFFICIAL_DATA/REFERENCE_POOL_REGISTRY_2026-09.tsv and OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv both carry;
the underscore-less form appears in NO OFFICIAL_DATA table and is not resolvable at NCBI. These tests
asserted MY form, so they FAILED against the corrected engine — a test pinning a defect is worse than
no test, because the next composer reading a red suite would "fix" the engine back to the broken form.
Corrected here to assert the canonical accession.

Consequence already in the world: every per-genus figure delivered 2026-09-08 under
AS Strain Master/_PLACEMENT/PER_GENUS_DELIVERABLE_2026-09-08/ prints the underscore-less
accession. They need a re-render against .418 before anyone cites one.
"""
import importlib.util
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _mod(monkeypatch=None):
    p = os.path.join(ROOT, "tools", "build_placement_ggtree_inputs.py")
    spec = importlib.util.spec_from_file_location("bpgi_budget", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


DOUBLED = ("Pseudonocardia_Pseudonocardia_thermophila_ATCC_19285_NR_118886_1_NR_118886_1_"
           "outgroup_for_Saccharothrix_Pseudonocardia_thermophila_16S_ribosomal_RNA")


def test_a_doubled_accession_no_longer_eats_the_strain_number():
    """v9.7.417 rendered this real outgroup tip as 'Pseudonocardia thermophila ATCC (NR118886.1)'."""
    lab = _mod()._ref_label(DOUBLED, "Saccharothrix")
    assert "19285" in lab, f"strain number lost: {lab}"
    assert lab.count("NR_118886") == 1
    assert "NR 118886" not in lab.replace("NR_118886",""), f"a second raw accession survived into the text: {lab}"


@pytest.mark.parametrize("tip,modal,must_contain", [
    ("NR_044855_1_Saccharothrix_mutabilis_subsp_capreolus_DSM_40225_16S_ribosomal_RNA",
     "Saccharothrix", "40225"),
    ("NR_042711_1_Streptomyces_brasiliensis_DSM_43159_16S_ribosomal_RNA", "Streptomyces", "43159"),
])
def test_real_truncation_offenders_keep_their_collection_number(tip, modal, must_contain):
    lab = _mod()._ref_label(tip, modal)
    assert must_contain in lab, f"collection number lost: {lab}"


def test_the_ordinary_short_label_is_unchanged():
    """Guard the guard: raising a cap must not restyle labels that never hit it."""
    lab = _mod()._ref_label(
        "NR_149213_1_Kribbella_soli_strain_FMN22_16S_ribosomal_RNA_partial_sequence", "Kribbella")
    assert lab == "K. soli FMN22 (NR_149213)"


def test_the_cap_is_derived_and_overridable(monkeypatch):
    m = _mod()
    assert m.REF_LABEL_CHARS == 48, "48 = longest abbreviated subsp.-subsp. binomial"
    monkeypatch.setenv("GG_REF_LABEL_CHARS", "20")
    m2 = _mod()
    assert m2.REF_LABEL_CHARS == 20
    lab = m2._ref_label("NR_044855_1_Saccharothrix_mutabilis_subsp_capreolus_DSM_40225_16S", "X")
    assert len(lab.split(" (")[0]) <= 20


def test_truncation_still_happens_on_a_word_boundary():
    """The cap moved; the .417 rule that it never cuts mid-token must survive."""
    m = _mod()
    lab = m._ref_label("NR_000001_1_Aaaaaaaaaa_bbbbbbbbbb_cccccccccc_dddddddddd_eeeeeeeeee_16S", "Z")
    name = lab.split(" (")[0]
    assert not name.endswith("-") and "  " not in name
    assert all(len(tok) > 1 or tok.isalpha() for tok in name.split())
