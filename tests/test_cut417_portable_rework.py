"""Portable input admission and fail-closed regressions for the release rework."""
import importlib.util
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]

def load(rel, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / Path(rel).parent))
    spec = importlib.util.spec_from_file_location('rework_' + Path(rel).stem, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_blast_query_requires_complete_identity(monkeypatch):
    mod = load('deliverable_tools/ingest_blastp.py', monkeypatch)
    with pytest.raises(ValueError, match='QUERY_REQUIRES'):
        mod.query_identity('SYNTH__alias__gene')
    title = 'SYNTH__NODE_1_length_10000_cov_10__region001__alias__gene'
    strain, locator, gene, row = mod.query_identity(title)
    assert row['exact_locus_identity'] == 'SYNTH / NODE_1_length_10000_cov_10 / region001 / alias'
    assert locator == title.rsplit('__', 1)[0]
    with pytest.raises(ValueError):
        mod.query_identity(title.replace('SYNTH', '..'))
    with pytest.raises(ValueError):
        mod.query_identity(title.replace('NODE_1_length_10000_cov_10', 'NODE_1'))

def test_old_rollup_refused_before_reuse(tmp_path, monkeypatch):
    mod = load('deliverable_tools/ingest_blastp.py', monkeypatch)
    p = tmp_path / 'old.csv'
    p.write_text('strain,bgc_id,gene\nSYNTH,alias,gene\n')
    before = p.read_bytes()
    with pytest.raises(ValueError):
        mod.load_existing_roll(p)
    assert p.read_bytes() == before

def test_widget_resolver_exception_is_not_silently_replaced(monkeypatch):
    mod = load('deliverable_tools/_bigscape_data.py', monkeypatch)
    def broken(_):
        raise RuntimeError('resolver broke')
    monkeypatch.setattr(mod, '_canonical_strain', broken)
    with pytest.raises(RuntimeError, match='resolver broke'):
        mod.strain_of('Genus species collection 1.region001.gbk', 'Genus species collection')

def test_explicit_metadata_never_discovers_neighbor_workspace(tmp_path, monkeypatch):
    mod = load('tools/build_placement_ggtree_inputs.py', monkeypatch)
    monkeypatch.chdir(tmp_path)
    assert mod._find_host_table('') == ''
    assert mod._load_aux() == {}
    p = tmp_path / 'metadata.tsv'
    p.write_text('strain\thost\tregion\taccession\nSYNTH\tmoss\tCountry: Province\tTEST001\n')
    assert mod._load_aux([str(p)])['SYNTH']['region'] == 'Country: Province'
    q = tmp_path / 'conflict.tsv'
    q.write_text('strain\thost\tregion\taccession\nSYNTH\tant\tCountry: Province\tTEST001\n')
    with pytest.raises(ValueError, match='CONFLICT'):
        mod._load_aux([str(p), str(q)])
    q.write_text('strain\thost\nSYNTH\tmoss\n')
    with pytest.raises(ValueError, match='SCHEMA'):
        mod._load_aux([str(q)])
