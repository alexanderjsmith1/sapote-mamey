"""C5: present dedup review files need a nonblank unique species key."""
from mamey.phylo_evidence import _dedup


def test_real_review_schema_without_species_is_typed_hold_not_parse_error(tmp_path):
    review = tmp_path / "GENOME_DEDUP_REVIEW.tsv"
    review.write_text(
        "action\tpath\tmetadata(genus|family|acc|bp|contigs|GC)\tintegrity_flag\tgroup\tnote\n"
        "KEEP\trefs/a.fna\tAlpha|Alphaceae|acc=GCF_1|1bp|1ctg|GC50\t\tgroup-a\t2 dup(s)\n"
        "DELETE_CANDIDATE\told/a.fna\tAlpha|Alphaceae|acc=GCF_1|1bp|1ctg|GC50\t\tgroup-a\tkeep=refs/a.fna\n")
    result = _dedup(review)
    assert result["state"] == "DEDUP_NOT_VERIFIED"
    assert result["reason"] == "species_column_missing"
    assert result["kept"] == 1 and result["dropped"] == 1


def test_blank_or_duplicate_kept_species_is_not_verified(tmp_path):
    review = tmp_path / "review.tsv"
    review.write_text("action\tspecies\nKEEP\tAlpha one\nKEEP\talpha one\n")
    assert _dedup(review)["reason"] == "kept_species_non_unique"
    review.write_text("action\tspecies\nKEEP\t\n")
    assert _dedup(review)["reason"] == "kept_species_blank"
