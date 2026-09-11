r"""Reference-label behaviour pinned against the shapes that actually occur in production.

Two defect classes shipped in consecutive sealed cuts and neither was caught by the suite:

  * up to v9.7.417 the producer published a **strain code in the accession slot** on 164 of 2,035
    accession-bearing reference tips -- `'N. colli NR 170398 1 (KY2.1)'`, where `KY2.1` is a strain
    designation and the real `NR_170398.1` survives only as unparenthesised stray text.
  * v9.7.418 fixed that and introduced an **uncaught** `REFERENCE_ACCESSION_CONFLICT` on 36 tips,
    because the accession pattern also matches a bare `[A-Z]{1,2}\d{5,}` token and deposited strain
    codes have that shape. `_ref_label` is called unguarded in the writer loop, so the run dies.

Both were found by running real tips through the function, not by the unit tests. The tips below
are taken verbatim from `*_ggtree_annotation.tsv` files in the production corpus (2,091 unique
reference tips across 212 files) and cover every shape class that corpus contains. They are a
frozen fixture, so this guard is portable and needs no workspace data.

The assertions are deliberately about the *contract*, not exact strings: whatever is published in
the parenthetical slot must be an NCBI-style accession that actually occurs in the tip. A label may
legitimately change; publishing a strain code where a reader expects an accession may not.
"""

import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PRODUCER = ROOT / "tools" / "build_placement_ggtree_inputs.py"

# Accession-shaped token as it appears in a raw tip (version suffix may be `_1` or `.1`).
RAW_ACC = re.compile(r"(?:NR|NZ|NC|NG|XR|GCF|GCA)_?\d+", re.I)
# Accession-shaped token as it may legitimately be published.
PUB_ACC = re.compile(r"^(?:NR|NZ|NC|NG|XR|GCF|GCA)_?\d+(?:\.\d+)?$", re.I)


def _mod():
    spec = importlib.util.spec_from_file_location("_bpgi_corpus", PRODUCER)
    m = importlib.util.module_from_spec(spec)
    sys.modules["_bpgi_corpus"] = m
    try:
        spec.loader.exec_module(m)
    except SystemExit:
        pass
    return m


def _norm(s):
    return re.sub(r"[^A-Za-z0-9]", "", s or "").upper()


def _published(label):
    """The parenthetical the reader will take as the accession, ignoring the outgroup marker."""
    for chunk in reversed(re.findall(r"\(([^)]*)\)", label or "")):
        if chunk.strip().lower() != "outgroup":
            return chunk.strip()
    return ""


# (tip, modal genus) -- verbatim production shapes, one per class.
RESOLVABLE = [
    # a strain code sits beside the real accession (the 164-defect class, and the 36-refusal class)
    ("Nocardia_colli_strain_KY2_1__NR_170398_1", "Nocardia"),
    ("Streptomyces_pratisoli_strain_MS1_AVA_4_NR_200022", "Streptomyces"),
    ("Actinomadura_physcomitrii_LD22_NR_174263.1_TYPE", "Actinomadura"),
    ("NR_180229_1_Amycolatopsis_panacis_strain_YIM_PH21725_16S_ribosomal", "Amycolatopsis"),
    ("NR_025565_1_Amycolatopsis_vancoresmycina_strain_ST101170_16S_r", "Amycolatopsis"),
    ("NR_114444_1_Pseudonocardia_xinjiangensis_strain_CCTCC_AA97020_1", "Pseudonocardia"),
    # leading accession, ordinary shape
    ("NG_061057_1_Knufia_cryptophialidica_DAOM", "Knufia"),
    ("Streptomyces_champavatii_strain_NBRC_15392_NR_112451", "Streptomyces"),
    # doubled accession with a strain number that must not be truncated away
    ("Pseudonocardia_thermophila_ATCC_19285_NR_118886_1", "Saccharopolyspora"),
    # a TYPE suffix after the accession
    ("Actinacidiphila_bryophytorum_NEAU_HZ10_NR_146707.1_TYPE", "Actinacidiphila"),
]

# Multi-record concatenations: two or more COMPLETE reference records glued into one tip. There is
# no single right answer, so the producer must refuse rather than choose. Five such tips exist in
# the corpus; the third merges three DIFFERENT species into one tip.
CONCATENATED = [
    "NR_109504_1_Amycolatopsis_dongchuanensis_strain_YIM_75904_16S_ribosomal_RNA_partial_sequence"
    "_NR_118259_1_Amycolatopsis_dongchuanensis_strain_YIM_75904_16S_ribosomal_RNA_partial_sequence",
    "NR_041207_1_Streptomyces_griseolus_strain_NBRC_3415_16S_ribosomal_RNA_partial_sequence"
    "_NR_112493_1_Streptomyces_griseolus_strain_NBRC_3719_16S_ribosomal_RNA_partial_sequence",
    "NR_026535_1_Streptomyces_odorifer_strain_DSM_40347_16S_ribosomal_RNA_partial_sequence"
    "_NR_119341_1_Streptomyces_albidoflavus_strain_DSM_40455_16S_ribosomal_RNA_partial_sequence"
    "_NR_119342_1_Streptomyces_coelicolor_strain_DSM_40233_16S_ribosomal_RN",
]


def test_producer_is_present():
    assert PRODUCER.is_file(), f"missing {PRODUCER}"


@pytest.mark.parametrize("tip,modal", RESOLVABLE)
def test_a_resolvable_tip_never_publishes_a_non_accession(tip, modal):
    """The 164-defect contract: what is in the parens must be an accession from this tip."""
    label = _mod()._ref_label(tip, modal)
    shown = _published(label)
    assert shown, f"no accession published for a tip that carries one: {label!r}"
    assert PUB_ACC.match(shown), (
        f"a non-accession was published where a reader expects one: {shown!r} in {label!r}"
    )
    assert _norm(shown) in _norm(tip), (
        f"published accession {shown!r} does not occur in the tip: {label!r}"
    )


@pytest.mark.parametrize("tip,modal", RESOLVABLE)
def test_a_resolvable_tip_does_not_raise(tip, modal):
    """The 36-refusal contract.

    `_ref_label` is called unguarded in the writer loop, so a raise here is not a blank label --
    it ends the run. A tip with exactly one namespace-anchored candidate is resolvable and must
    not refuse.
    """
    _mod()._ref_label(tip, modal)


@pytest.mark.parametrize("tip", CONCATENATED)
def test_a_multi_record_tip_still_refuses(tip):
    """Negative control. Two complete records glued together have no single right answer, and
    guessing between them is exactly the failure the refusal exists to prevent."""
    with pytest.raises(ValueError, match="REFERENCE_ACCESSION_CONFLICT"):
        _mod()._ref_label(tip, "Streptomyces")


def test_the_fixture_still_covers_both_defect_classes():
    """Keeps this file from decaying into a list nobody can interpret."""
    assert len(RESOLVABLE) >= 10 and len(CONCATENATED) >= 3
    assert any("KY2" in t for t, _ in RESOLVABLE), "the strain-code collision case must stay"
    assert any(t.startswith("NG_") or t.startswith("NR_") for t, _ in RESOLVABLE), \
        "the leading-accession case must stay"
