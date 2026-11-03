import json
import pytest
from tests.test_450_gap_rescue_fresh_split_families import fresh_saved_split

@pytest.mark.parametrize('mode', ['disabled', 'skipped', 'drawn'])
def test_existing_maps_are_not_mistaken_for_current(fresh_saved_split, monkeypatch, mode):
    f = fresh_saved_split
    f.out.mkdir(parents=True)
    (f.out / 'gap_rescue.png').write_bytes(b'old png')
    (f.out / 'gap_rescue.pdf').write_bytes(b'old pdf')
    def draw(*args, **kwargs):
        if mode == 'skipped':
            return None
        (f.out / 'gap_rescue.png').write_bytes(b'new png')
        (f.out / 'gap_rescue.pdf').write_bytes(b'new pdf')
        return {}
    monkeypatch.setattr(f.gdr, 'draw_locus_map', draw)
    receipt = f.gdr.analyse_region('SYNTHETIC', f.prots, f.regions, f.core, f.reference,
        'Explicit reference', 'saved fixture', f.out, hits=f.hits, threads=3, sensitivity='sensitive', mibig_db=f.db, pfam=f.pfam, figure=mode != 'disabled',
        write_proteins=False, gene_table=False)
    disk = json.loads((f.out / 'gap_rescue_receipt.json').read_text())
    assert receipt == disk
    if mode == 'drawn':
        assert receipt['preexisting_map_files_unverified'] == []
        assert len(receipt['map_outputs']) == 2
    else:
        assert receipt['preexisting_map_files_unverified'] == ['gap_rescue.png', 'gap_rescue.pdf']
        assert receipt['map_outputs'] == []
        assert (f.out / 'gap_rescue.png').read_bytes() == b'old png'
        assert (f.out / 'gap_rescue.pdf').read_bytes() == b'old pdf'

def test_broken_symlink_is_listed_as_unverified(fresh_saved_split):
    f = fresh_saved_split
    f.out.mkdir(parents=True)
    (f.out / 'gap_rescue.pdf').symlink_to(f.out / 'missing')
    receipt = f.gdr.analyse_region('SYNTHETIC', f.prots, f.regions, f.core, f.reference,
        'Explicit reference', 'saved fixture', f.out, hits=f.hits, threads=3, sensitivity='sensitive', mibig_db=f.db, pfam=f.pfam, figure=False,
        write_proteins=False, gene_table=False)
    assert receipt['preexisting_map_files_unverified'] == ['gap_rescue.pdf']
    assert receipt['map_outputs'] == []

def test_failed_drawing_keeps_unverified_receipt(fresh_saved_split, monkeypatch):
    f = fresh_saved_split
    f.out.mkdir(parents=True)
    old = f.out / 'gap_rescue.png'
    old.write_bytes(b'old png')
    def fail(*args, **kwargs):
        raise RuntimeError('synthetic drawing failure')
    monkeypatch.setattr(f.gdr, 'draw_locus_map', fail)
    with pytest.raises(RuntimeError, match='synthetic drawing failure'):
        f.gdr.analyse_region('SYNTHETIC', f.prots, f.regions, f.core, f.reference,
            'Explicit reference', 'saved fixture', f.out, hits=f.hits, threads=3,
            sensitivity='sensitive', mibig_db=f.db, pfam=f.pfam, figure=True,
            write_proteins=False, gene_table=False)
    receipt = json.loads((f.out / 'gap_rescue_receipt.json').read_text())
    assert receipt['preexisting_map_files_unverified'] == ['gap_rescue.png']
    assert receipt['map_outputs'] == [] and old.read_bytes() == b'old png'

from tests.test_450_gap_rescue_current_maps import batch_maps, _run

def test_batch_skipped_draw_preserves_unverified_aggregate(batch_maps, monkeypatch):
    b = batch_maps
    receipt = _run(b, False)
    assert receipt['preexisting_aggregate_map_unverified'] == b.combined.name
    assert receipt['combined_map_pdf'] == '' and b.combined.read_bytes().startswith(b'prior')

def test_batch_current_aggregate_clears_preexisting_marker(batch_maps, monkeypatch):
    b = batch_maps
    def draw(*args, **kwargs):
        b.png.write_bytes(b'new png')
        b.pdf.write_bytes(b'new pdf')
        return {}
    monkeypatch.setattr(b.f.gdr, 'draw_locus_map', draw)
    receipt = _run(b, True)
    assert receipt['preexisting_aggregate_map_unverified'] == ''
    assert receipt['combined_map_pdf'] == b.combined.name

def test_batch_failed_attempt_retains_unverified_marker(batch_maps, monkeypatch):
    b = batch_maps
    def fail(*args, **kwargs):
        raise RuntimeError('synthetic batch failure')
    monkeypatch.setattr(b.f.gdr, 'draw_locus_map', fail)
    with pytest.raises(RuntimeError, match='synthetic batch failure'):
        _run(b, True)
    receipt = json.loads((b.f.out / 'run_receipt.json').read_text())
    assert receipt['status'] == 'FAILED'
    assert receipt['preexisting_aggregate_map_unverified'] == b.combined.name
    assert receipt['combined_map_pdf'] == ''
