"""RiPP motif identity must not be borrowed from the focus enzyme."""
import json
import zipfile

from mamey.antismash_evidence import extract_ripp_cores
from mamey import antismash_tables as tables


def _archive(tmp_path, motifs):
    archive = tmp_path / 'input.zip'
    record = {'id': 'ctg1', 'modules': {'antismash.modules.lanthipeptides': {'motifs': motifs}}}
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('run/input.json', json.dumps({'records': [record]}))
    return archive


def test_precursor_tag_and_coordinates_come_from_precursor(tmp_path, monkeypatch):
    archive = _archive(tmp_path, {'enzyme': [{'core': 'SCTTC', 'locus_tag': 'precursor'}]})
    evidence = {'ripp_cores': extract_ripp_cores(archive)}
    assert evidence['ripp_cores'][0]['locus_tag'] == 'enzyme'
    monkeypatch.setattr(tables, 'extract_cds_features', lambda _: [
        {'contig': 'ctg1', 'locus_tag': 'enzyme', 'start': 10, 'end': 100, 'strand': 1},
        {'contig': 'ctg1', 'locus_tag': 'precursor', 'start': 200, 'end': 260, 'strand': -1},
    ])
    row = tables.build_structured_tables(archive, evidence, [])['ripp_motifs'][0]
    assert (row['locus_tag'], row['start'], row['end'], row['strand']) == ('precursor', 200, 260, -1)
    assert 'CDS_LOCUS_COORDINATES' in row['mapping_method']
    assert json.loads(row['detail_json'])['locus_tag'] == 'precursor'


def test_different_precursor_without_coordinates_does_not_borrow_enzyme(tmp_path, monkeypatch):
    archive = _archive(tmp_path, {'enzyme': [{'core': 'SCTTC', 'locus_tag': 'precursor'}]})
    evidence = {'ripp_cores': extract_ripp_cores(archive)}
    evidence['ripp_cores'][0].update(start=10, end=100, strand=1)
    monkeypatch.setattr(tables, 'extract_cds_features', lambda _: [])
    row = tables.build_structured_tables(archive, evidence, [])['ripp_motifs'][0]
    assert (row['locus_tag'], row['start'], row['end']) == ('precursor', '', '')
    assert 'NO_COORDINATE' in row['mapping_method']


def test_flat_thiopeptide_preserves_normalized_cds_tag(tmp_path):
    archive = _archive(tmp_path, [{'core': 'SCTTC', 'locus_tag': 'ctg1_2_thiopeptide', 'peptide_class': 'thiopeptide'}])
    evidence = {'ripp_cores': extract_ripp_cores(archive)}
    row = tables.build_structured_tables(archive, evidence, [])['ripp_motifs'][0]
    assert row['locus_tag'] == 'ctg1_2'


def test_grouped_motif_with_class_suffix_uses_the_precursor_cds_tag(tmp_path, monkeypatch):
    # Real antiSMASH output: the group key is an enzyme, and the motif is named <precursor>_<class>.
    archive = _archive(tmp_path, {'ctg1_20': [{'core': 'SCTTC', 'locus_tag': 'ctg1_21_lanthipeptide',
                                               'peptide_class': 'lanthipeptide'}]})
    evidence = {'ripp_cores': extract_ripp_cores(archive)}
    monkeypatch.setattr(tables, 'extract_cds_features', lambda _: [
        {'contig': 'ctg1', 'locus_tag': 'ctg1_20', 'start': 10, 'end': 100, 'strand': 1},
        {'contig': 'ctg1', 'locus_tag': 'ctg1_21', 'start': 200, 'end': 260, 'strand': -1},
    ])
    row = tables.build_structured_tables(archive, evidence, [])['ripp_motifs'][0]
    assert row['locus_tag'] == 'ctg1_21'
    assert (row['start'], row['end'], row['strand']) == (200, 260, -1)


def test_class_suffix_stem_that_is_not_a_cds_is_not_invented(tmp_path, monkeypatch):
    archive = _archive(tmp_path, {'ctg1_20': [{'core': 'SCTTC', 'locus_tag': 'ctg1_99_lanthipeptide',
                                               'peptide_class': 'lanthipeptide'}]})
    evidence = {'ripp_cores': extract_ripp_cores(archive)}
    monkeypatch.setattr(tables, 'extract_cds_features', lambda _: [
        {'contig': 'ctg1', 'locus_tag': 'ctg1_20', 'start': 10, 'end': 100, 'strand': 1},
    ])
    row = tables.build_structured_tables(archive, evidence, [])['ripp_motifs'][0]
    assert row['locus_tag'] == 'ctg1_99_lanthipeptide'
    assert row['start'] == ''
