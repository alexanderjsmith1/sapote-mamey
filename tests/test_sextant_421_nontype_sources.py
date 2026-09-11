"""v9.7.421 — asking for non-type references must reach non-type records, and must say what it did.

Three defects on one composition path, each reproduced generically on a temporary store:

  1. `--refs nontype:Nx` named only the directed-fetch source, so a composition asking for non-type
     references could not reach a store's harvested candidate pools at all. Those pools were
     reachable only through 'all', which also pulls type strains — so no composition could ask for
     a non-type panel and get one.
  2. Widening the source map is not an admission rule. A harvested pool is not certified non-type:
     a store may hold records it positively marks as type material. Admitting those under a
     'nontype' request misreports what is on the tree.
  3. The per-kind diagnostic predicted the selected count before the selection loop ran. The loop
     de-duplicates by strain, so the prediction and the measurement diverge in exactly the case
     the diagnostic exists to expose.

No live services and no workspace paths: every fixture is a temporary SQLite store, and the
admission rule is exercised through the real rank_references() on its no-candidates path, which
returns before any BLAST executable is reached.
"""
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import phylo_16s_build_db as build
import phylo_16s_panel as panel

SEQ = "ACGT" * 350   # 1,400 nt: inside the 421b reference length bound
QUERIES = [('QQ000001', 'Exampla bacterium 16S ribosomal RNA gene', SEQ, 'AS-001')]


def rec(acc, source, designation, is_type=None, genus='Exampla',
        definition='Exampla bacterium 16S ribosomal RNA gene', seq=SEQ, uncultured=0):
    return (acc, acc + '.1', source, definition, 'Exampla bacterium', genus,
            designation, '[]', is_type, seq, len(seq) if seq else None, None, 'fixture', uncultured)


def store(tmp_path, rows, name='store.sqlite'):
    db = tmp_path / name
    with sqlite3.connect(db) as con:
        con.executescript(build.SCHEMA)
        for r in rows:
            build.upsert(con, [r], r[2])
    return sqlite3.connect(db)


class _BlastReached(Exception):
    """Raised in place of resolving a BLAST executable, to prove the pool was non-empty.

    rank_references() returns early when no candidate is admitted, so reaching the executable
    lookup at all is the observable signal that a record passed the admission rule. Patching the
    lookup keeps the test portable: it needs no BLAST+ install and runs no alignment.
    """


@pytest.fixture
def no_blast(monkeypatch):
    def boom(*a, **k):
        raise _BlastReached()
    monkeypatch.setattr(panel._p16, 'blast_bin', boom)


# ── the admission rule, through the real rank_references() ──────────────────────────────

def test_recorded_type_material_is_excluded_from_a_nontype_request(tmp_path, no_blast):
    """The only candidate is marked type material: a non-type request must find nothing to rank."""
    con = store(tmp_path, [rec('AA000001', 'pdf_candidate', 'IS_TYPE', is_type=1)])
    got = panel.rank_references(con, QUERIES, ('pdf_candidate',), set(), None, exclude_type=True)
    assert got == [], 'a record the store marks as type material was admitted to a non-type panel'


def test_the_exclusion_is_opt_in_so_every_other_kind_is_unchanged(tmp_path, no_blast):
    """Negative control: the same store, same call, without the flag — the record IS a candidate."""
    con = store(tmp_path, [rec('AA000001', 'pdf_candidate', 'IS_TYPE', is_type=1)])
    with pytest.raises(_BlastReached):
        panel.rank_references(con, QUERIES, ('pdf_candidate',), set(), None, exclude_type=False)


def test_unrecorded_type_status_is_not_reclassified(tmp_path, no_blast):
    """is_type IS NULL means 'unknown' in the store schema. It stays admissible either way."""
    con = store(tmp_path, [rec('AA000003', 'pdf_candidate', 'UNRECORDED', is_type=None)])
    with pytest.raises(_BlastReached):
        panel.rank_references(con, QUERIES, ('pdf_candidate',), set(), None, exclude_type=True)


def test_recorded_nontype_is_admitted(tmp_path, no_blast):
    con = store(tmp_path, [rec('AA000002', 'pdf_candidate', 'NOT_TYPE', is_type=0)])
    with pytest.raises(_BlastReached):
        panel.rank_references(con, QUERIES, ('pdf_candidate',), set(), None, exclude_type=True)


def review(con, accession, role):
    con.execute(
        "INSERT INTO record_type_review VALUES (?,?,?,?,?,?,?)",
        (accession, role, '', 'https://example.test/evidence', 'fixture review',
         '2026-09-11', 'test authority'),
    )
    con.commit()


def test_reviewed_nontype_overrides_imported_type_flag(tmp_path, no_blast):
    con = store(tmp_path, [rec('AA000007', 'refseq_type', 'REVIEWED_NONTYPE', is_type=1)])
    review(con, 'AA000007', 'cultured_non_type_reference')
    with pytest.raises(_BlastReached):
        panel.rank_references(con, QUERIES, ('refseq_type',), set(), None, exclude_type=True)
    assert panel.rank_references(con, QUERIES, ('refseq_type',), set(), None,
                                 require_type=True) == []


def test_reviewed_type_overrides_imported_nontype_flag(tmp_path, no_blast):
    con = store(tmp_path, [rec('AA000008', 'external', 'REVIEWED_TYPE', is_type=0)])
    review(con, 'AA000008', 'type_reference')
    with pytest.raises(_BlastReached):
        panel.rank_references(con, QUERIES, ('external',), set(), None, require_type=True)
    assert panel.rank_references(con, QUERIES, ('external',), set(), None,
                                 exclude_type=True) == []


def test_the_existing_quality_screens_still_apply(tmp_path, no_blast):
    """Widening the sources must not widen the sequence / uncultured / clone screens."""
    for acc, kw in [('AA000004', dict(seq=None)),
                    ('AA000005', dict(uncultured=1)),
                    ('AA000006', dict(definition='Uncultured bacterium clone X 16S rRNA gene'))]:
        con = store(tmp_path, [rec(acc, 'pdf_candidate', 'X', is_type=0, **kw)], name=acc + '.sqlite')
        assert panel.rank_references(con, QUERIES, ('pdf_candidate',), set(), None,
                                     exclude_type=True) == [], acc


# ── the composition: which sources are requested, and what the diagnostic reports ───────

def _panel_db(tmp_path, extra):
    return store(tmp_path, [rec('QQ000001', 'as_governed', 'AS-001', is_type=0)] + extra,
                 name='panel.sqlite')


def _args(refs):
    return SimpleNamespace(strains=None, set=None, genus='Exampla', scope_genus=None,
                           habitat_tags=None, refs=refs, outgroup=None)


def test_a_nontype_request_reaches_the_harvested_pools_and_excludes_type(tmp_path, monkeypatch):
    con = _panel_db(tmp_path, [])
    seen = {}

    def fake_rank(c, queries, sources, exclude, scope_genus, tags=None, exclude_type=False, require_type=False):
        seen['sources'] = tuple(sources); seen['exclude_type'] = exclude_type; seen['require_type'] = require_type
        return []

    monkeypatch.setattr(panel, 'rank_references', fake_rank)
    panel.prepare_panel(con, _args('nontype:1x'))
    assert 'pdf_candidate' in seen['sources'] and 'attribute_candidate' in seen['sources']
    assert 'nontype_fetch' in seen['sources'], 'the directed-fetch source must not be dropped'
    assert 'refseq_type' not in seen['sources'] and 'external' not in seen['sources']
    assert seen['exclude_type'] is True
    assert seen['require_type'] is False


def test_a_type_request_is_untouched(tmp_path, monkeypatch):
    """Negative control: this must pass before and after the patch."""
    con = _panel_db(tmp_path, [])
    seen = {}

    def fake_rank(c, queries, sources, exclude, scope_genus, tags=None, exclude_type=False, require_type=False):
        seen['sources'] = tuple(sources); seen['exclude_type'] = exclude_type; seen['require_type'] = require_type
        return []

    monkeypatch.setattr(panel, 'rank_references', fake_rank)
    panel.prepare_panel(con, _args('type:1x'))
    assert seen['sources'] == ('refseq_type',) and seen['exclude_type'] is False
    assert seen['require_type'] is True


def test_the_reported_count_is_measured_after_deduplication(tmp_path, monkeypatch, capsys):
    """Two ranked candidates, one strain. Requesting 2 must report selected=1, not 2."""
    con = _panel_db(tmp_path, [rec('RR000001', 'pdf_candidate', 'REF_A', is_type=0),
                               rec('RR000002', 'pdf_candidate', 'REF_B', is_type=0)])
    with con:
        con.executemany("INSERT INTO record_strain(acc_base,strain_uid) VALUES(?,?)",
                        [('RR000001', 'S:1'), ('RR000002', 'S:1')])

    def fake_rank(c, queries, sources, exclude, scope_genus, tags=None, exclude_type=False, require_type=False):
        return [('RR000001', 'd', SEQ, 'Exampla bacterium', 'pdf_candidate', '99.1', '1400'),
                ('RR000002', 'd', SEQ, 'Exampla bacterium', 'pdf_candidate', '99.0', '1400')]

    monkeypatch.setattr(panel, 'rank_references', fake_rank)
    _records, counts = panel.prepare_panel(con, _args('nontype:2x'))
    assert counts[0] == dict(kind='nontype', requested=2, selected=1), counts[0]
    err = capsys.readouterr().err
    assert 'selected=1' in err, f'the diagnostic must report the measured count, got: {err!r}'
    assert 'ranked=2' in err and 'skipped_duplicate_strain=1' in err, err


def test_the_receipt_composition_shape_is_unchanged(tmp_path, monkeypatch):
    """Guard on this patch itself: the receipt's composition entries stay exactly three keys."""
    con = _panel_db(tmp_path, [])
    monkeypatch.setattr(panel, 'rank_references', lambda *a, **k: [])
    _records, counts = panel.prepare_panel(con, _args('nontype:1x'))
    assert set(counts[0]) == {'kind', 'requested', 'selected'}
