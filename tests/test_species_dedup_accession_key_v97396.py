"""Regression test — v97396: tools/phylo_place.py::_species_key() read the LEADING ACCESSION of an
NCBI 16S RefSeq title as the binomial, so `one_per_species` dedup collapsed nothing by species.

RefSeq 16S titles are 'NR_######.#  Genus species strain ... 16S ribosomal RNA'. The old code did
`toks = re.split(r"[ _]+", header); key = toks[0] toks[1]` -> 'NR 115365.1'. Every reference then
got a UNIQUE species key = its own accession, and `--one-per-species` kept ALL same-species type
strains (observed live: 2x S. kasugaensis, 2x S. albiaxialis, 6x S. griseus survived a "one per
species" backbone; Alex flagged the duplicate tips on the placement figure). The fix strips a
leading accession token before reading the binomial. Subspecies must STAY distinct (the engine's
documented invariant) so a real subsp. is never silently merged.

Runs as a normal bundle test: place in tests/, `pytest tests/test_species_dedup_accession_key_v97396.py`.
Exercises the real, unmocked `_species_key` and `_dedup_reference` code paths.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import phylo_place as pp  # noqa: E402


def test_species_key_reads_binomial_not_accession_v97396():
    # RefSeq-style titles: accession leads, binomial follows.
    assert pp._species_key(
        "NR_024724.1 Streptomyces kasugaensis strain M338-M1 16S ribosomal RNA, partial sequence"
    ) == "streptomyces kasugaensis"
    assert pp._species_key(
        "NR_112419.1 Streptomyces kasugaensis strain NBRC 13851 16S ribosomal RNA, partial sequence"
    ) == "streptomyces kasugaensis"
    # A bare-organism title (no accession) must still parse to the binomial.
    assert pp._species_key(
        "NR_043378.1 Streptomyces albiaxialis 16S ribosomal RNA, partial sequence"
    ) == "streptomyces albiaxialis"
    # Generic (non-NR) accession prefix, e.g. a GenBank-extracted title.
    assert pp._species_key(
        "MK123456.1 Streptomyces coelicolor strain A3(2) 16S ribosomal RNA"
    ).startswith("streptomyces coelicolor")


def test_subspecies_stay_distinct_v97396():
    k1 = pp._species_key("NR_042301.1 Streptomyces libani subsp. rufus strain LMG 20087 16S ribosomal RNA")
    k2 = pp._species_key("NR_041139.1 Streptomyces libani strain NBRC 13452 16S ribosomal RNA gene")
    assert k1 != k2, "a real subspecies must not merge into the parent species"
    assert "subsp rufus" in k1


def test_one_per_species_collapses_same_species_refseq_v97396(tmp_path):
    fa = tmp_path / "ref.fasta"
    fa.write_text(
        ">NR_024724.1 Streptomyces kasugaensis strain M338-M1 16S ribosomal RNA, partial sequence\n"
        "ACGTACGTACGTAAAACCCCGGGGTTTTACGTACGTACGTACGTACGTACGTACGTAAAA\n"
        ">NR_112419.1 Streptomyces kasugaensis strain NBRC 13851 16S ribosomal RNA, partial sequence\n"
        "ACGTACGTACGTAAAACCCCGGGGTTTTACGTACGTACGTACGTACGTACGTACGTTTTT\n"
        ">NR_043378.1 Streptomyces albus strain CSSP327 16S ribosomal RNA, partial sequence\n"
        "TTTTGGGGCCCCAAAATTTTGGGGCCCCAAAATTTTGGGGCCCCAAAATTTTGGGGCCCC\n",
        encoding="utf-8",
    )
    out = tmp_path / "ref.dedup.fasta"
    rpt = tmp_path / "reference_dedup.tsv"
    kept, dropped = pp._dedup_reference(str(fa), str(out), str(rpt), one_per_species=True)
    # 2 kasugaensis strains -> 1; albus -> 1. Total 2 kept, 1 dropped.
    assert kept == 2 and dropped == 1
    keys = {pp._species_key(h) for h, _ in pp._read_fasta_pairs(str(out))}
    assert keys == {"streptomyces kasugaensis", "streptomyces albus"}
