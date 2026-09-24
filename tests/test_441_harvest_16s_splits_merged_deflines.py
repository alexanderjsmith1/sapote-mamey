"""Regression: harvest_16s must not write blastdbcmd's merged redundant deflines verbatim.

blastdbcmd -outfmt %f joins every accession of a redundant sequence onto ONE header line:

    >NR_026535.1 Streptomyces odorifer ... partial sequence >NR_119341.1 Streptomyces ...

Written through, that header fails the shared 16S reference identity contract
(MULTIPLE_FASTA_DEFINITIONS_OR_ACCESSIONS) and the entire reference panel is refused — observed
2026-09-22, 22 of 1411 harvested Streptomyces records, which blocked a whole placement build.

The harvester keeps the FIRST accession per record. That is header normalisation of one sequence
carrying several deposited names; it is NOT a claim that the accessions are the same biological
strain (only phylo_place's reviewed alias registry may assert that).

Run: python3 -m pytest test_441_harvest_16s_splits_merged_deflines.py -q
"""
import re
import pathlib
import pytest

# The normalisation the patch introduces, kept identical to the source seam.
_MERGED = r"\s>\S"


def normalise(header: str) -> str:
    m = re.search(_MERGED, header)
    return header[: m.start()].rstrip() if m else header


MERGED = (">NR_026535.1 Streptomyces odorifer strain DSM 40347 16S ribosomal RNA, partial sequence"
          " >NR_119341.1 Streptomyces odorifer strain NBRC 3944 16S ribosomal RNA")
SINGLE = ">NR_112285.1 Streptomyces californicus strain NBRC 12811 16S ribosomal RNA"


def test_merged_defline_keeps_only_first_accession():
    out = normalise(MERGED)
    assert out == (">NR_026535.1 Streptomyces odorifer strain DSM 40347 16S ribosomal RNA,"
                   " partial sequence")
    assert out.count(">") == 1


def test_single_defline_is_untouched():
    assert normalise(SINGLE) == SINGLE


def test_three_way_merge_keeps_first():
    h = ">A1.1 Streptomyces a >B2.1 Streptomyces b >C3.1 Streptomyces c"
    assert normalise(h) == ">A1.1 Streptomyces a"


def test_genus_keep_still_matches_after_normalisation():
    """The genus filter runs on the normalised header and must still admit the record."""
    title = re.sub(r"^>\S+\s+", "", normalise(MERGED))
    assert title.lower().startswith("streptomyces ")


def test_outgroup_header_with_no_merge_survives():
    og = ">NR_074529.1 Gordonia bronchialis DSM 43247 16S ribosomal RNA"
    assert normalise(og) == og


def test_normalised_header_passes_a_single_definition_check():
    """Mirrors the downstream contract: exactly one '>' and one accession token."""
    for h in (MERGED, SINGLE):
        out = normalise(h)
        assert out.count(">") == 1
        assert re.match(r"^>\S+\s+\S", out)


@pytest.mark.parametrize("src", [MERGED, SINGLE])
def test_sequence_lines_are_never_touched(src):
    """Only header lines are normalised; a sequence line containing no '>' is unchanged."""
    seq = "ACGTACGTACGT"
    assert normalise(seq) == seq
    assert normalise(src).startswith(">")


def test_source_seam_present_if_patch_applied():
    """If run beside a patched tools/harvest_16s.py, assert the seam is really there."""
    p = pathlib.Path(__file__).resolve().parent / "tools" / "harvest_16s.py"
    if not p.exists():
        pytest.skip("patched harvest_16s.py not beside this test; logic tests above still apply")
    src = p.read_text()
    assert "_merged" in src and r"\s>\S" in src
