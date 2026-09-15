"""Shape and identity rules for the shipped outgroup registry snapshot (mamey/data/outgroup_registry.tsv).

The snapshot mirrors the owner's ruled OFFICIAL_DATA/OUTGROUP_REGISTRY.tsv, so its rules follow that
file's own header: every row names a species and the record the build fetches. A genome row carries a
GC[AF]_ accession. A 16S-only row (`16S_local_RefSeq`, or the older `PROVISIONAL_16S_only` marker) is
either PROVISIONAL or names the NR_ record it fetches in the species column. A `group` scope is a ruled
multi-family panel and may carry the NR_ accession directly.
"""
import pathlib
import re

TSV = pathlib.Path(__file__).resolve().parent.parent / "mamey" / "data" / "outgroup_registry.tsv"
GENOME = re.compile(r"GC[AF]_\d+\.\d+")
NR_16S = re.compile(r"NR_\d+\.\d+")
SIXTEEN_S_ONLY = {"16S_local_RefSeq", "PROVISIONAL_16S_only"}


def _rows():
    return [l.split("\t") for l in TSV.read_text().splitlines()
            if l.strip() and not l.startswith("#") and not l.startswith("tree_scope")]


def test_real_accessions():
    for r in _rows():
        species, acc, status = r[4], r[5], r[6]
        if acc in SIXTEEN_S_ONLY:
            # A 16S-only outgroup must either stay PROVISIONAL or name the exact NR_ record it fetches
            # (the registry's own "name the species, not just the genus" rule).
            assert status == "PROVISIONAL" or NR_16S.search(species), \
                f"16S-only row for {r[1]} is {status!r} but names no NR_ record: {species!r}"
            continue
        assert GENOME.fullmatch(acc) or NR_16S.fullmatch(acc), f"bad acc {acc} ({r[1]})"


def test_outgroup_not_ingroup():
    for r in _rows():
        assert r[3] != r[1], f"outgroup==ingroup {r[1]}"


def test_scope_valid():
    for r in _rows():
        assert r[0] in ("genus", "family", "group"), f"bad scope {r[0]} ({r[1]})"


def test_reverified_accession_organism_names_are_consistent():
    # Owner ruling 2026-09-15: the organism names in the ruled rows stand, and the accessions were
    # corrected to the type-material reference genomes of those organisms (NCBI Assembly esummary,
    # fromtype = "assembly from type material").
    expected = {
        "GCF_000284295.1": ("Actinoplanes", "Actinoplanes missouriensis 431"),
        "GCF_000023245.1": ("Actinosynnema", "Actinosynnema mirum DSM 43827"),
    }
    retired = {
        "GCF_039528075.1",  # resolves to Catellatospora coxensis, not Actinoplanes missouriensis
        "GCA_018139085.1",  # resolves to Actinosynnema pretiosum, not Actinosynnema mirum
    }
    seen = set()
    for row in _rows():
        assert row[5] not in retired, f"retired accession still in the snapshot: {row[5]} ({row[1]})"
        if row[5] in expected:
            seen.add(row[5])
            assert (row[3], row[4]) == expected[row[5]], (row[1], row[3], row[4], row[5])
    assert seen == set(expected), f"expected both ruled accessions in the snapshot, saw {sorted(seen)}"
