"""C4: outgroups must be registry-declared exactly one rank out."""
import pytest

from mamey.phylo_evidence import PhyloEvidenceError, _outgroup_row

HEADER = ("tree_scope\tingroup_taxon\tfamily\toutgroup_genus\t"
          "outgroup_species_strain\tassembly_accession\tstatus\trationale\n")


def test_genus_outgroup_requires_registry_declared_sister_genus(tmp_path):
    registry = tmp_path / "outgroups.tsv"
    registry.write_text(HEADER +
        "genus\tAlpha\tAlphaceae\tBeta\tBeta exemplar TYPE-1\tGCF_000000001.1\tLOCKED\tdistant phylum\n")
    with pytest.raises(PhyloEvidenceError) as caught:
        _outgroup_row(registry, "Alpha", "genus", "Beta_exemplar_TYPE-1")
    assert caught.value.code == "OUTGROUP_TOO_DISTANT"

    registry.write_text(HEADER +
        "genus\tAlpha\tAlphaceae\tBeta\tBeta exemplar TYPE-1\tGCF_000000001.1\tLOCKED\tsister genus, same family\n")
    assert _outgroup_row(registry, "Alpha", "genus", "Beta_exemplar_TYPE-1")["rank_check"] == "ONE_RANK_OUT_REGISTRY_DECLARED"


def test_family_outgroup_requires_sister_family_or_order_declaration(tmp_path):
    registry = tmp_path / "outgroups.tsv"
    registry.write_text(HEADER +
        "family\tAlphaceae\tAlphaceae\tGamma\tGamma exemplar TYPE-2\tGCF_000000002.1\tLOCKED\tunrelated reference\n")
    with pytest.raises(PhyloEvidenceError) as caught:
        _outgroup_row(registry, "Alphaceae", "family", "Gamma_exemplar_TYPE-2")
    assert caught.value.code == "OUTGROUP_TOO_DISTANT"
