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
    assert pp._species_key("REF_NR_116093.1") == ""


def test_one_per_species_never_merges_accession_only_unknowns(tmp_path):
    fa = tmp_path / "ref.fasta"
    fa.write_text(
        ">REF_NR_900001.1\n" + "ACGT" * 50 + "\n"
        ">REF_NR_900002.1\n" + "TGCA" * 50 + "\n")
    kept, dropped = pp._dedup_reference(
        str(fa), str(tmp_path / "out.fa"), str(tmp_path / "report.tsv"),
        one_per_species=True)
    assert (kept, dropped) == (2, 0)


def test_panel_metadata_restores_species_for_accession_only_headers(tmp_path):
    fa = tmp_path / "panel.fasta"
    fa.write_text(
        ">REF_NR_900001.1\n" + "ACGT" * 50 + "\n"
        ">REF_NR_900002.1\n" + "TGCA" * 50 + "\n"
        ">REF_NR_900003.1\n" + "GATC" * 50 + "\n")
    meta = tmp_path / "panel_meta.tsv"
    meta.write_text(
        "tip\ttaxon\trole\n"
        "REF_NR_900001.1\tStreptomyces pratensis\treference\n"
        "REF_NR_900002.1\tStreptomyces pratensis\treference\n"
        "REF_NR_900003.1\tStreptomyces albus\treference\n")
    kept, dropped = pp._dedup_reference(
        str(fa), str(tmp_path / "out.fa"), str(tmp_path / "report.tsv"),
        one_per_species=True, reference_metadata=str(meta))
    assert (kept, dropped) == (2, 1)
    assert "dropped:one-per-species" in (tmp_path / "report.tsv").read_text()


def test_query_role_in_reference_metadata_refuses(tmp_path):
    fa = tmp_path / "panel.fasta"
    fa.write_text(">AS_1\nACGT\n")
    meta = tmp_path / "panel_meta.tsv"
    meta.write_text("tip\ttaxon\trole\nAS_1\tStreptomyces sp.\tquery\n")
    try:
        pp._dedup_reference(str(fa), str(tmp_path / "out.fa"), str(tmp_path / "report.tsv"),
                            reference_metadata=str(meta))
    except ValueError as exc:
        assert str(exc) == "QUERY_PRESENT_IN_REFERENCE_FASTA:AS_1"
    else:
        raise AssertionError("a query row in a reference FASTA must refuse")


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


def test_verified_collection_synonyms_collapse_before_inference(tmp_path):
    fa = tmp_path / "ref.fasta"
    fa.write_text(
        ">NR_116093.1 Streptomyces drozdowiczii strain NRRL B-24297 16S ribosomal RNA\n"
        + "ACGT" * 370 + "\n"
        ">NR_041424.1 Streptomyces drozdowiczii strain NBRC 101007 16S ribosomal RNA\n"
        + "ACGT" * 369 + "ACGA\n",
        encoding="utf-8",
    )
    out = tmp_path / "ref.dedup.fasta"
    report = tmp_path / "reference_dedup.tsv"
    kept, dropped = pp._dedup_reference(str(fa), str(out), str(report))
    assert (kept, dropped) == (1, 1)
    assert "dropped:verified-strain-alias" in report.read_text(encoding="utf-8")
    assert len(pp._read_fasta_pairs(str(out))) == 1

    # The real reference producer may preserve only a REF_<accession> token.
    fa.write_text(
        ">REF_NR_116093.1\n" + "ACGT" * 370 + "\n"
        ">REF_NR_041424.1\n" + "ACGT" * 369 + "ACGA\n",
        encoding="utf-8",
    )
    kept, dropped = pp._dedup_reference(str(fa), str(out), str(report))
    assert (kept, dropped) == (1, 1)


def test_unlisted_same_species_strains_remain_distinct(tmp_path):
    fa = tmp_path / "ref.fasta"
    fa.write_text(
        ">NR_900001.1 Streptomyces exampleii strain NRRL B-1 16S ribosomal RNA\n"
        + "ACGT" * 50 + "\n"
        ">NR_900002.1 Streptomyces exampleii strain NBRC 2 16S ribosomal RNA\n"
        + "TGCA" * 50 + "\n",
        encoding="utf-8",
    )
    kept, dropped = pp._dedup_reference(
        str(fa), str(tmp_path / "out.fa"), str(tmp_path / "report.tsv"))
    assert (kept, dropped) == (2, 0)


def test_alias_registry_conflicts_fail_closed(tmp_path):
    aliases = tmp_path / "aliases.tsv"
    aliases.write_text(
        "alias_group\tspecies\taccession\tstrain_designation\tauthority_state\tevidence_url\n"
        "g1\tgenusa alpha\tNR_000001\tA\tOWNER_ACCEPTED\thttps://example.invalid/1\n"
        "g2\tgenusa alpha\tNR_000001\tA\tOWNER_ACCEPTED\thttps://example.invalid/2\n",
        encoding="utf-8",
    )
    fa = tmp_path / "ref.fasta"
    fa.write_text(">NR_000001.1 Genusa alpha strain A\nACGT\n", encoding="utf-8")
    try:
        pp._dedup_reference(str(fa), str(tmp_path / "out.fa"),
                            str(tmp_path / "report.tsv"), strain_aliases=str(aliases))
    except ValueError as exc:
        assert str(exc).startswith("STRAIN_ALIAS_REGISTRY_CONFLICT")
    else:
        raise AssertionError("conflicting accession aliases must refuse")


def test_one_per_genus_is_explicit_and_keeps_one_reference_per_genus(tmp_path):
    fa = tmp_path / "ref.fasta"
    fa.write_text(
        ">NR_000001.1 Genusa alpha strain A 16S ribosomal RNA\n" + "ACGT" * 40 + "\n"
        ">NR_000002.1 Genusa beta strain B 16S ribosomal RNA\n" + "TGCA" * 41 + "\n"
        ">NR_000003.1 Genusb gamma strain C 16S ribosomal RNA\n" + "GATC" * 42 + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "ref.dedup.fasta"
    report = tmp_path / "reference_dedup.tsv"
    kept, dropped = pp._dedup_reference(
        str(fa), str(out), str(report), one_per_genus=True)
    assert (kept, dropped) == (2, 1)
    assert {pp._genus_key(h) for h, _ in pp._read_fasta_pairs(str(out))} == {
        "genusa", "genusb"}
    assert "dropped:one-per-genus" in report.read_text(encoding="utf-8")


def test_reference_density_modes_are_mutually_exclusive(tmp_path):
    fa = tmp_path / "ref.fasta"
    fa.write_text(">NR_000001.1 Genusa alpha\nACGT\n", encoding="utf-8")
    try:
        pp._dedup_reference(
            str(fa), str(tmp_path / "out.fa"), str(tmp_path / "out.tsv"),
            one_per_species=True, one_per_genus=True)
    except ValueError as exc:
        assert str(exc) == "REFERENCE_DENSITY_MODES_CONFLICT"
    else:
        raise AssertionError("conflicting density modes must refuse")
