"""Regression test (BLACK_CHERRY wave 19, base .383): genes_for_gbk() must emit the `_aa`
key that bigscape_clinker_widget.cluster_dark_proteins() pops, or the "identical-sequence
grey-gene links" feature (reference-dark proteins linked across tracks by sequence
similarity) is silently dead in every real run -- no error, no gap in the output, the
ribbons + legend entry ("similar sequence, no Pfam (likely same protein)") just never fire.

Exercises the REAL production functions end-to-end against a minimal real-schema SQLite
DB (same cds/hsp/gbk shape used elsewhere in this suite, e.g. tests/test_bigscape_combined_run.py).
"""
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

# widget + its data helper ship in deliverable_tools/, not beside this test (mirrors the
# path convention used by tests/test_clinker_figure_cleanup_v9_7_383.py).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deliverable_tools"))

from _bigscape_data import genes_for_gbk  # noqa: E402
import bigscape_clinker_widget as widget  # noqa: E402


def _make_db(path):
    db = sqlite3.connect(path)
    cur = db.cursor()
    cur.execute("CREATE TABLE gbk (id INTEGER PRIMARY KEY, path TEXT, organism TEXT)")
    cur.execute(
        "CREATE TABLE cds (id INTEGER PRIMARY KEY, gbk_id INTEGER, nt_start INTEGER, "
        "nt_stop INTEGER, orf_num INTEGER, strand INTEGER, gene_kind TEXT, aa_seq TEXT)"
    )
    cur.execute(
        "CREATE TABLE hsp (id INTEGER PRIMARY KEY, cds_id INTEGER, accession TEXT, bit_score REAL)"
    )
    seq_a = ("MSTAHKILAVDDNEIVRQLIRTALEKAGYQVVVAADGEAALEIARSTHPDLVTMDVIMPRLDGIEATRRIRELDPRV" * 2)
    seq_b = seq_a[:20] + "K" + seq_a[21:]  # one substitution -> near-identical, well above cutoff
    for i, seq in enumerate((seq_a, seq_b), start=1):
        cur.execute("INSERT INTO gbk VALUES (?, ?, ?)", (i, f"/fake/track{i}.region001.gbk", "Bacteria"))
        cur.execute("INSERT INTO cds VALUES (?, ?, 0, 300, 1, 1, 'other', ?)", (i, i, seq))
    db.commit()
    db.close()


@pytest.fixture
def two_track_genes():
    with tempfile.TemporaryDirectory() as td:
        dbp = os.path.join(td, "t.db")
        _make_db(dbp)
        con = sqlite3.connect(dbp)
        genes_a = genes_for_gbk(con, 1)
        genes_b = genes_for_gbk(con, 2)
        con.close()
        yield genes_a, genes_b


def test_genes_for_gbk_emits_the_key_cluster_dark_proteins_consumes(two_track_genes):
    """Producer/consumer contract: cluster_dark_proteins() pops g["_aa"]; genes_for_gbk()
    must actually set it, or the pop always yields the default (None)."""
    genes_a, _ = two_track_genes
    assert genes_a, "fixture produced no genes"
    assert "_aa" in genes_a[0], (
        "genes_for_gbk() no longer emits '_aa' -- cluster_dark_proteins() will silently "
        "treat every gene as sequence-less and never link reference-dark proteins"
    )
    assert genes_a[0]["_aa"], "_aa must carry the actual amino-acid sequence, not empty/None"


def test_near_identical_reference_dark_proteins_get_linked_across_tracks(two_track_genes):
    """End-to-end: two near-identical no-Pfam proteins in adjacent tracks must come out of
    cluster_dark_proteins() sharing the same `seq` cluster label, so the client-side amber
    'same reference-dark protein' ribbon has something real to draw."""
    genes_a, genes_b = two_track_genes
    tracks = [
        {"strain": "T1", "genes": genes_a},
        {"strain": "T2", "genes": genes_b},
    ]
    orthogroups = {}  # no shared Pfam orthogroups -> both genes are "dark" by definition
    widget.cluster_dark_proteins(tracks, orthogroups)

    seqs = [g.get("seq") for t in tracks for g in t["genes"]]
    assert all(s is not None for s in seqs), (
        "reference-dark proteins were not linked at all -- the amber ribbon feature is dead"
    )
    assert len(set(seqs)) == 1, "the two near-identical dark proteins got different cluster labels"


def test_raw_sequence_never_leaks_into_the_gene_dict_after_clustering(two_track_genes):
    """cluster_dark_proteins() must still strip `_aa` after use, so the fix doesn't regress
    the documented payload-compactness guarantee (raw AA sequences never reach the client)."""
    genes_a, genes_b = two_track_genes
    tracks = [{"strain": "T1", "genes": genes_a}, {"strain": "T2", "genes": genes_b}]
    widget.cluster_dark_proteins(tracks, {})
    for t in tracks:
        for g in t["genes"]:
            assert "_aa" not in g, "raw amino-acid sequence leaked past cluster_dark_proteins()"
