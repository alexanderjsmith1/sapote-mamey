"""v9.7.428 -- a lab strain/collection code shaped like [A-Z]{1,2}\\d{5,} must not be
counted as a second FASTA-record identity by screen_reference_definitions().

Reproduced on real 16S definitions this workspace already holds: "Streptomyces sp. CB01635",
"strain CCTCC AA97020", "strain YIM B13505". Every one refused admission before this fix,
21/22 wrongly (the 22nd, `strain NR_170483.1`, carries a genuine RefSeq-style namespace
prefix and stays correctly held). One of the 21 was a registry-ruled outgroup tip, which made
its panel unbuildable, not merely smaller.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import phylo_place as place

SEQ = "ACGT" * 300


def fasta(tmp_path, header):
    p = tmp_path / "ref.fasta"
    p.write_text(f"{header}\n{SEQ}\n")
    return str(p)


@pytest.mark.parametrize("header", [
    ">NR_114444.1 Pseudonocardia xinjiangensis strain CCTCC AA97020 16S ribosomal RNA, partial sequence",
    ">NR_114441.1 Pseudonocardia yunnanensis strain CCTCC M90959 16S ribosomal RNA, partial sequence",
    ">NR_118632.1 Pseudonocardia sediminis strain YIM M13141 16S ribosomal RNA, partial sequence",
    ">MF455323.1 Streptomyces sp. CB01635 16S ribosomal RNA gene, partial sequence",
    ">MF573418.1 Micromonospora sp. strain HA13703 16S ribosomal RNA gene, partial sequence",
    ">MT250993.1 Streptomyces sp. strain PKU-EA00015 16S ribosomal RNA gene, partial sequence",
    ">PP099786.1 Streptomyces sp. AN120604 16S ribosomal RNA gene, partial sequence",
    ">PQ358315.1 Streptomyces sp. strain S609007 16S ribosomal RNA gene, partial sequence",
    ">PQ608416.1 Streptomyces sp. strain YIM B13505 16S ribosomal RNA gene, partial sequence",
    ">Y10844.1 Streptomyces sp. 16S rRNA gene, strain B71277",
    # the actual outgroup header that blocked a real panel build
    ">NR_042363_1_Actinospica_outgroup_for_Streptomycetaceae Actinospica acidiphila strain "
    "GE134766 16S ribosomal RNA, partial sequence",
])
def test_a_strain_or_collection_code_is_not_a_second_accession(tmp_path, header):
    assert place.screen_reference_definitions(fasta(tmp_path, header)) == []


def test_a_genuinely_embedded_second_accession_still_holds(tmp_path):
    """Negative control: a namespace-prefixed token stays a real conflict, strain-context or not."""
    header = ">OP848182.1 Streptomyces sp. strain NR_170483.1 16S ribosomal RNA gene, partial sequence"
    rejected = place.screen_reference_definitions(fasta(tmp_path, header))
    assert rejected == [(rejected[0][0], "MULTIPLE_FASTA_DEFINITIONS_OR_ACCESSIONS")]


def test_two_bare_modern_accessions_with_no_strain_context_still_hold(tmp_path):
    """A header's own leading id is exempt; free text with no strain/collection marker at all
    is NOT exempt just for lacking a namespace prefix -- context, not format, is what excuses it."""
    header = ">PP099786.1 Streptomyces sp. related deposit PQ200000.1 duplicate record"
    rejected = place.screen_reference_definitions(fasta(tmp_path, header))
    assert rejected == [(rejected[0][0], "MULTIPLE_FASTA_DEFINITIONS_OR_ACCESSIONS")]


def test_uncultured_and_clone_holds_are_unaffected(tmp_path):
    """This patch touches only the multi-accession branch; the shared definition screen
    (uncultured/clone/unidentified/enrichment) must still fire exactly as before."""
    rejected = place.screen_reference_definitions(
        fasta(tmp_path, ">AB000001.1 Uncultured Streptomyces sp. clone JR-24 16S ribosomal RNA gene"))
    assert rejected and rejected[0][1] != "MULTIPLE_FASTA_DEFINITIONS_OR_ACCESSIONS"
