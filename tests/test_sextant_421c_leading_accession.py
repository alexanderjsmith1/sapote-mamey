"""v9.7.421 — a non-type reference could never resolve an accession conflict.

`_ref_accession`'s disambiguation branch returns a survivor only if it matches
`^(NZ|NC|NG|NR|XR|GCF|GCA)_`. A non-type record's own accession is a plain GenBank accession, so no
non-type conflict could ever resolve. Measured store-wide on 16S Database/rrna16s.sqlite (sequence
present, seq_len>1200): conflicts run 449/26,104 (1.720%) across the non-type pool against
11/27,425 (0.040%) for type strains. Two of ten panels produced no figure at all because of it.
"""
import importlib.util, os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILDER = os.path.join(ROOT, "tools", "build_placement_ggtree_inputs.py")


def _m():
    spec = importlib.util.spec_from_file_location("bpgi", BUILDER)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def test_a_leading_accession_resolves_a_bare_designation():
    """The real failure: A00969 is a strain code, KU382719.1 is the record."""
    assert _m()._ref_accession(
        "KU382719_1_Streptomyces_sp_A00969_16S_ribosomal_RNA_gene_partial_sequence") == "KU382719.1"


def test_a_clean_type_strain_is_unaffected():
    assert _m()._ref_accession(
        "NR_042115_1_Actinomadura_fulvescens_strain_DSM_43923_16S") == "NR_042115.1"


@pytest.mark.parametrize("tip", [
    "NR_123456_1_MW444715_1",                       # two versioned accessions
    "NR_123456_1_strain_NR_234567_1",               # a declared strain field holding a real accession
    "Gordonia_Gordonia_bronchialis_DSM_43247_NR_074529_1_NR_119065_1_outgroup",  # two records fused
])
def test_two_real_accessions_still_refuse(tip):
    """NEGATIVE CONTROL. The rescue must not swallow a genuine conflict.

    An earlier, broader version of this rule returned the leading token unconditionally and broke 18
    shipped tests. A later candidate that is namespaced OR carries a version suffix is a real
    accession, not a designation, and the tip stays a refusal.
    """
    with pytest.raises(ValueError):
        _m()._ref_accession(tip)


def test_the_rule_is_positional_not_namespace_preference():
    src = open(BUILDER, encoding="utf-8").read()
    i = src.index("REFERENCE_ACCESSION_CONFLICT")
    block = src[max(0, i - 2500):i]
    assert "m.start() == 0" in block, "the rescue must key on position, not on namespace"
