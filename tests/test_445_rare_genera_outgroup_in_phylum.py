"""445: the rare-genera 16S outgroup is the in-phylum Bifidobacterium ruling, fetched by accession.

The owner ruled on 2026-09-29 that rare-genera 16S trees root on Bifidobacterium bifidum KCTC 3202 (NR_044771.1).
The Pseudomonas root it replaces joined next to one ingroup genus and made it sister to all the others.
The shipped snapshot must carry the ruling, and the ruled accession must sit inside outgroup_species_strain,
because that is the only place get_16s reads an accession from; without it the fetch falls back to a name pick.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHIPPED = ROOT / "mamey" / "data" / "outgroup_registry.tsv"


def _rare_genera_row():
    rows = [ln.split("\t") for ln in SHIPPED.read_text(encoding="utf-8").splitlines()
            if ln.startswith("group\trare_genera\t")]
    assert len(rows) == 1, f"expected one rare_genera group row, found {len(rows)}"
    return rows[0]


def test_rare_genera_outgroup_is_in_phylum_bifidobacterium():
    row = _rare_genera_row()
    assert row[3] == "Bifidobacterium"
    assert row[4].startswith("Bifidobacterium bifidum KCTC 3202")
    assert row[6].startswith("ALEX_RULED_2026-09-29")


def test_rare_genera_ruled_accession_is_fetchable_by_accession():
    row = _rare_genera_row()
    m = re.search(r"\((N[RC]_\d+\.\d+)\)", row[4])
    assert m, "the ruled accession must be in outgroup_species_strain, where get_16s reads it"
    assert m.group(1) == row[5] == "NR_044771.1"
