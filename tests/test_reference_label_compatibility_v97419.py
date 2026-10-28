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

Historical consequence recorded for the 2026-09-08 per-genus deliverables: their
figures printed the underscore-less accession and required re-rendering against .418.
The original deployment path is omitted here, not renamed as a historical receipt.
Exact historical labels remain in the maintainer's crosswalk outside CODE.
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


