from pathlib import Path
import csv

from mamey.bgc_blastp_panel import select_panel, write_panel, assign_rounds, panel_rows, first_pass_rows
from mamey.models import BGCRecord, CDSFeature


def _bgc(bid='BGC001', start=1, end=3000):
    return BGCRecord(bgc_id=bid, contig='ctg1', region_number=int(bid[-3:]), start=start, end=end, contig_length=10000, products=['NRPS'], node_id='ctg1', antismash_region='region001')


def _cds(start, end, locus, product, seq='M' * 250, note=''):
    return CDSFeature('ctg1', start, end, 1, locus, product, seq, '', {'note': [note], 'sec_met_domain': [product]})


def test_selects_two_per_bgc_prefer_core_and_context():
    bgcs = [_bgc('BGC001', 1, 3000), _bgc('BGC002', 4000, 7000)]
    cds = [
        _cds(100, 900, 'core1', 'NRPS adenylation domain'),
        _cds(1000, 1800, 'ctx1', 'ABC transporter'),
        _cds(4300, 5000, 'core2', 'phosphoenolpyruvate mutase'),
        _cds(5100, 6000, 'ctx2', 'transcriptional regulator'),
    ]
    rows = panel_rows(bgcs, cds, 'AS-TEST', genes_per_bgc=2)
    assert len(rows) == 4
    assert {r['bgc_id'] for r in rows} == {'BGC001', 'BGC002'}
    assert {r['selection_role'] for r in rows} >= {'core', 'context'}


def test_first_pass_is_curated_high_value_subset():
    bgcs = [_bgc(f'BGC{i:03d}', i * 10000, i * 10000 + 3000) for i in range(1, 41)]
    cds = []
    for i, b in enumerate(bgcs, 1):
        cds.append(CDSFeature('ctg1', b.start + 10, b.start + 600, 1, f'core{i}', 'PKS ketosynthase', 'M' * 300, '', {'sec_met_domain': ['PKS ketosynthase']}))
        cds.append(CDSFeature('ctg1', b.start + 700, b.start + 1300, 1, f'ctx{i}', 'ABC transporter', 'M' * 300, '', {'sec_met_domain': ['ABC transporter']}))
    rows = panel_rows(bgcs, cds, 'AS-TEST', genes_per_bgc=2)
    first = first_pass_rows(rows, first_pass_size=30)
    assert len(first) == 30
    assert len({r['bgc_id'] for r in first}) == 30
    assert all(r['selection_role'] in {'core', 'context'} for r in first)


def test_rounds_obey_protein_and_residue_limits(tmp_path):
    bgcs = [_bgc(f'BGC{i:03d}', i * 10000, i * 10000 + 3000) for i in range(1, 7)]
    cds = []
    for i, b in enumerate(bgcs, 1):
        cds.append(CDSFeature('ctg1', b.start + 10, b.start + 600, 1, f'core{i}', 'PKS ketosynthase', 'M' * 300, '', {'sec_met_domain': ['PKS ketosynthase']}))
        cds.append(CDSFeature('ctg1', b.start + 700, b.start + 1300, 1, f'ctx{i}', 'ABC transporter', 'M' * 300, '', {'sec_met_domain': ['ABC transporter']}))
    summary = write_panel(tmp_path, 'AS-TEST', bgcs, cds, genes_per_bgc=2, proteins_per_file=5, max_residues=100000, first_pass_size=4)
    assert summary['curated_unique_proteins'] == 12
    assert summary['one_best_unique_proteins'] == 6
    manifest = tmp_path / 'AS-TEST_BGC_BLASTP_PANEL_selection_manifest.csv'
    rows = list(csv.DictReader(manifest.open()))
    assert rows
    batch_summary = list(csv.DictReader((tmp_path / 'AS-TEST_NCBI_safe_batch_summary.csv').open()))
    assert batch_summary
    assert all(int(r['residues']) <= 100000 for r in batch_summary)
    curated = [r for r in batch_summary if r['panel_scope'].startswith('curated_')]
    assert [int(r['proteins']) for r in curated] == [4, 4, 4]  # BGC pairs preserved with 5-protein cap


def test_residue_limit_starts_new_round(tmp_path):
    bgcs = [_bgc('BGC001', 1, 3000), _bgc('BGC002', 4000, 7000)]
    cds = [
        _cds(100, 900, 'a', 'PKS ketosynthase', 'M' * 1200),
        _cds(1200, 2000, 'b', 'ABC transporter', 'M' * 1200),
        CDSFeature('ctg1', 4100, 4900, 1, 'c', 'PKS ketosynthase', 'M' * 1200, '', {'sec_met_domain': ['PKS ketosynthase']}),
        CDSFeature('ctg1', 5100, 5900, 1, 'd', 'ABC transporter', 'M' * 1200, '', {'sec_met_domain': ['ABC transporter']}),
    ]
    summary = write_panel(tmp_path, 'AS-TEST', bgcs, cds, genes_per_bgc=2, proteins_per_file=20, max_residues=2500, first_pass_size=2)
    assert summary['round_count'] >= 4
    batch_summary = list(csv.DictReader((tmp_path / 'AS-TEST_NCBI_safe_batch_summary.csv').open()))
    assert all(int(r['residues']) <= 2500 for r in batch_summary)


def test_giant_multidomain_is_flagged_and_isolated(tmp_path):
    bgcs = [_bgc('BGC001', 1, 6000)]
    cds = [
        _cds(100, 5000, 'giant', 'NRPS adenylation condensation carrier protein', 'M' * 3000),
        _cds(5100, 5800, 'ctx', 'ABC transporter', 'M' * 300),
    ]
    write_panel(tmp_path, 'AS-TEST', bgcs, cds, genes_per_bgc=2, proteins_per_file=20, max_residues=90000, first_pass_size=2, giant_aa_threshold=2500)
    rows = list(csv.DictReader((tmp_path / 'AS-TEST_BGC_BLASTP_PANEL_selection_manifest.csv').open()))
    assert any(r['warning'] == 'giant_multidomain_protein_consider_domain_followup' for r in rows)
    batch_summary = list(csv.DictReader((tmp_path / 'AS-TEST_NCBI_safe_batch_summary.csv').open()))
    assert any(int(r['proteins']) == 1 and int(r['residues']) == 3000 for r in batch_summary)


def test_outputs_iterative_user_guide_mentions_downloading_both_files(tmp_path):
    bgcs = [_bgc('BGC001', 1, 3000)]
    cds = [_cds(100, 900, 'core1', 'phosphoenolpyruvate mutase')]
    write_panel(tmp_path, 'AS-TEST', bgcs, cds)
    guide = (tmp_path / 'AS-TEST_BGC_BLASTP_PANEL_USER_GUIDE.md').read_text()
    assert 'Hit Table' in guide            # the CSV hit list
    assert 'Single-file XML2' in guide     # the enrichment file
    assert 'both' in guide                 # the guide tells users to download BOTH result files
    assert 'ingest-blastp' in guide        # and how to ingest them offline
    assert 'Max target sequences = 10' in guide
